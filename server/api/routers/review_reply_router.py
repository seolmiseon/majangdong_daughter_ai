# server/api/routers/review_reply_router.py

"""
리뷰 답글 생성 API 엔드포인트
FastAPI router를 통해 리뷰 답글 생성 기능을 제공
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import json
from server.llm_service.agents.review_reply_workflow import process_review
from server.database.crud import (
    create_review_reply,
    get_review_reply,
    list_review_replies,
    count_review_replies,
    update_reply_posted_status
)
from server.api.naver_place import post_reply_to_naver
from server.utils.policy_checker import get_policy_checker

# Router 생성
router = APIRouter(
    prefix="/api/review",
    tags=["review"]
)


# Request/Response 모델 정의

class ReviewReplyRequest(BaseModel):
    """리뷰 답글 생성 요청 모델"""
    review_text: str = Field(..., description="리뷰 텍스트", min_length=1)
    review_rating: int = Field(..., description="리뷰 평점 (1-5점)", ge=1, le=5)
    place_id: Optional[str] = Field(None, description="네이버 플레이스 가게 ID (답글 자동 등록 시 필수)")
    review_id: Optional[str] = Field(None, description="네이버 플레이스 리뷰 ID (선택사항)")
    auto_post: bool = Field(False, description="답글 자동 등록 여부")


class ReviewReplyResponse(BaseModel):
    """리뷰 답글 생성 응답 모델"""
    success: bool
    review_text: str
    review_rating: int
    final_verdict: str  # "MALICIOUS", "REVIEW_NEEDED", "NORMAL"
    confidence: float
    reason: str
    should_report: bool
    should_reply: bool
    reply_text: str
    reply_tone: str
    nuance_analysis: Optional[str] = None
    review_id: Optional[str] = None
    posted: bool = False  # 네이버 플레이스에 등록되었는지 여부
    policy_check: Optional[Dict] = None  # 정책 준수 검증 결과
    error: Optional[str] = None


class ReplyListResponse(BaseModel):
    """답글 목록 응답 모델"""
    replies: List[Dict]
    total: int


class PostReplyRequest(BaseModel):
    """답글 등록 요청 모델"""
    reply_id: Optional[str] = Field(None, description="저장된 답글 ID")
    place_id: str = Field(..., description="네이버 플레이스 가게 ID (필수)")
    review_id: Optional[str] = Field(None, description="네이버 플레이스 리뷰 ID (선택사항, 로깅용)")
    review_text: Optional[str] = Field(None, description="리뷰 텍스트 (선택사항, 특정 리뷰를 찾기 위해 사용)")
    reply_text: Optional[str] = Field(None, description="답글 텍스트 (reply_id가 없을 경우 필수)")


# API 엔드포인트

@router.post("/reply", response_model=ReviewReplyResponse)
async def generate_review_reply(request: ReviewReplyRequest):
    """
    리뷰를 받아서 판단하고 답글 생성
    
    - **review_text**: 판단할 리뷰 텍스트 (필수)
    - **review_rating**: 리뷰 평점 1-5점 (필수)
    - **review_id**: 네이버 플레이스 리뷰 ID (선택사항)
    - **auto_post**: 답글 자동 등록 여부 (기본값: False)
    
    Returns:
        판단 결과 + 답글 생성 결과
    """
    try:
        # 워크플로우 실행
        result = process_review(
            review_text=request.review_text,
            review_rating=request.review_rating
        )
        
        # 정책 준수 검증 및 자동 재생성
        policy_checker = get_policy_checker()
        reply_text = result.get("reply_text", "")
        policy_check_result = None
        max_retries = 3  # 최대 재시도 횟수
        
        if reply_text:
            for attempt in range(max_retries):
                policy_check_result = policy_checker.check_policy_compliance(
                    reply_text=reply_text,
                    review_text=request.review_text
                )
                
                # 정책 준수 통과 또는 점수가 70점 이상이면 OK
                if policy_check_result["passed"] or policy_check_result["score"] >= 70:
                    if attempt > 0:
                        print(f"✅ 정책 준수 검증 통과 (재시도 {attempt}회 후, 점수: {policy_check_result['score']}/100)")
                    else:
                        print(f"✅ 정책 준수 검증 통과 (점수: {policy_check_result['score']}/100)")
                    break
                
                # 정책 미준수 시 재생성
                if attempt < max_retries - 1:
                    print(f"⚠️ 정책 준수 검증 실패 (점수: {policy_check_result['score']}/100, 재시도 {attempt + 1}/{max_retries - 1})")
                    for issue in policy_check_result["issues"]:
                        print(f"  - {issue['message']}")
                    
                    # 재생성 프롬프트에 정책 준수 요구사항 추가
                    from server.llm_service.services.review_reply_generator import get_review_reply_generator
                    generator = get_review_reply_generator()
                    
                    # 정책 문제점을 프롬프트에 반영
                    policy_feedback = []
                    for issue in policy_check_result["issues"]:
                        if issue["type"] == "forbidden_keyword":
                            policy_feedback.append("금지 키워드(할인, 이벤트, 특가 등)를 사용하지 마세요.")
                        elif issue["type"] == "mechanical_expression":
                            policy_feedback.append("기계적인 표현 대신 자연스럽고 개인화된 표현을 사용하세요.")
                        elif issue["type"] == "too_short":
                            policy_feedback.append("답글을 더 길고 구체적으로 작성하세요.")
                    
                    # 재생성
                    regenerate_result = generator.generate_reply(
                        review_text=request.review_text,
                        review_rating=request.review_rating,
                        review_verdict=result.get("final_verdict"),
                        nuance_analysis=result.get("nuance_analysis", "")
                    )
                    
                    reply_text = regenerate_result.get("reply_text", "")
                    
                    if not reply_text:
                        print("⚠️ 재생성 실패, 기존 답글 사용")
                        break
                else:
                    # 최종 시도 실패
                    print(f"⚠️ 정책 준수 검증 최종 실패 (점수: {policy_check_result['score']}/100)")
                    print("  - 최대 재시도 횟수 도달, 기존 답글 사용 (수동 검토 권장)")
                    for issue in policy_check_result["issues"]:
                        print(f"  - {issue['message']}")
        
        # 결과 저장 (SQLite)
        reply_data = {
            "review_text": request.review_text,
            "review_rating": request.review_rating,
            "review_id": request.review_id,
            "final_verdict": result.get("final_verdict", "REVIEW_NEEDED"),
            "confidence": result.get("confidence", 0.0),
            "reason": result.get("reason", ""),
            "should_report": result.get("should_report", False),
            "should_reply": result.get("should_reply", False),
            "reply_text": reply_text,
            "reply_tone": result.get("reply_tone", ""),
            "nuance_analysis": result.get("nuance_analysis", ""),
            "posted": False
        }
        
        # 자동 등록 요청 시
        posted = False
        if request.auto_post and result.get("should_reply", False) and request.place_id:
            try:
                # 네이버 플레이스 API 연동
                posted = post_reply_to_naver(
                    place_id=request.place_id,
                    reply_text=result.get("reply_text", ""),
                    review_text=request.review_text,  # 특정 리뷰를 찾기 위해 리뷰 텍스트 전달
                    review_id=request.review_id
                )
            except Exception as e:
                # 자동 등록 실패해도 답글 생성은 성공으로 처리
                error_message = str(e)
                if "영수증 인증" in error_message:
                    print(f"⚠️ 영수증 인증이 필요합니다: {error_message}")
                    # 영수증 인증이 필요한 경우 특별 처리
                    posted = False
                else:
                    print(f"⚠️ 자동 등록 실패: {error_message}")
                    import traceback
                    traceback.print_exc()
                    posted = False
        elif request.auto_post and not request.place_id:
            print("⚠️ 자동 등록을 위해서는 place_id가 필요합니다.")
        
        reply_data["posted"] = posted
        reply_id = create_review_reply(reply_data)
        
        return ReviewReplyResponse(
            success=True,
            review_text=request.review_text,
            review_rating=request.review_rating,
            final_verdict=result.get("final_verdict", "REVIEW_NEEDED"),
            confidence=result.get("confidence", 0.0),
            reason=result.get("reason", ""),
            should_report=result.get("should_report", False),
            should_reply=result.get("should_reply", False),
            reply_text=reply_text,
            reply_tone=result.get("reply_tone", ""),
            nuance_analysis=result.get("nuance_analysis", ""),
            review_id=request.review_id,
            posted=posted,
            policy_check=policy_check_result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"답글 생성 중 오류 발생: {str(e)}"
        )


@router.get("/replies", response_model=ReplyListResponse)
async def get_replies(
    limit: int = 10,
    offset: int = 0,
    verdict: Optional[str] = None
):
    """
    생성된 답글 목록 조회
    
    - **limit**: 조회할 답글 수 (기본값: 10)
    - **offset**: 시작 위치 (기본값: 0)
    - **verdict**: 필터링할 판단 결과 ("MALICIOUS", "REVIEW_NEEDED", "NORMAL")
    """
    try:
        # SQLite에서 조회 (필터링, 정렬, 페이지네이션 모두 DB에서 처리)
        replies = list_review_replies(limit=limit, offset=offset, verdict=verdict)
        total = count_review_replies(verdict=verdict)
        
        return ReplyListResponse(
            replies=replies,
            total=total
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"답글 목록 조회 중 오류 발생: {str(e)}"
        )


@router.post("/post")
async def post_reply_to_naver(request: PostReplyRequest):
    """
    답글을 네이버 플레이스에 등록
    
    - **reply_id**: 저장된 답글 ID (선택사항)
    - **place_id**: 네이버 플레이스 가게 ID (필수)
    - **review_id**: 네이버 플레이스 리뷰 ID (선택사항, 로깅용)
    - **review_text**: 리뷰 텍스트 (선택사항, 특정 리뷰를 찾기 위해 사용)
    - **reply_text**: 답글 텍스트 (reply_id가 없을 경우 필수)
    
    Returns:
        등록 성공 여부
    """
    try:
        # reply_id가 있으면 DB에서 찾기
        review_text_from_db = None
        if request.reply_id:
            reply = get_review_reply(request.reply_id)
            if not reply:
                raise HTTPException(
                    status_code=404,
                    detail=f"답글을 찾을 수 없습니다: {request.reply_id}"
                )
            reply_text = reply.get("reply_text", "")
            review_text_from_db = reply.get("review_text")  # DB에서 리뷰 텍스트 가져오기
        else:
            if not request.reply_text:
                raise HTTPException(
                    status_code=400,
                    detail="reply_id 또는 reply_text가 필요합니다."
                )
            reply_text = request.reply_text
        
        # review_text 우선순위: 요청 > DB
        review_text = request.review_text or review_text_from_db
        
        # 네이버 플레이스 API 연동
        try:
            success = post_reply_to_naver(
                place_id=request.place_id,
                reply_text=reply_text,
                review_text=review_text,
                review_id=request.review_id
            )
        except Exception as e:
            error_message = str(e)
            if "영수증 인증" in error_message:
                # 영수증 인증이 필요한 경우 특별 처리
                raise HTTPException(
                    status_code=400,
                    detail="영수증 인증이 필요합니다. 네이버 플레이스에서 수동으로 영수증 인증을 완료한 후 다시 시도해주세요."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"답글 등록 중 오류 발생: {error_message}"
                )
        
        # DB 업데이트
        if request.reply_id:
            update_reply_posted_status(
                request.reply_id,
                success,
                datetime.now().isoformat() if success else None
            )
        
        return {
            "success": success,
            "message": "답글이 등록되었습니다." if success else "답글 등록에 실패했습니다.",
            "place_id": request.place_id,
            "review_id": request.review_id,
            "reply_text": reply_text[:50] + "..." if len(reply_text) > 50 else reply_text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"답글 등록 중 오류 발생: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    API 상태 확인
    """
    try:
        total_replies = count_review_replies()
        return {
            "status": "healthy",
            "total_replies": total_replies,
            "service": "review_reply_api"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/reply/{reply_id}")
async def get_reply_by_id(reply_id: str):
    """
    특정 답글 조회
    
    - **reply_id**: 조회할 답글 ID
    """
    try:
        reply = get_review_reply(reply_id)
        
        if not reply:
            raise HTTPException(
                status_code=404,
                detail=f"답글을 찾을 수 없습니다: {reply_id}"
            )
        
        return reply
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"답글 조회 중 오류 발생: {str(e)}"
        )

