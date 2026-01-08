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
    error: Optional[str] = None


class ReplyListResponse(BaseModel):
    """답글 목록 응답 모델"""
    replies: List[Dict]
    total: int


class PostReplyRequest(BaseModel):
    """답글 등록 요청 모델"""
    reply_id: Optional[str] = Field(None, description="저장된 답글 ID")
    review_id: str = Field(..., description="네이버 플레이스 리뷰 ID")
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
            "reply_text": result.get("reply_text", ""),
            "reply_tone": result.get("reply_tone", ""),
            "nuance_analysis": result.get("nuance_analysis", ""),
            "posted": False
        }
        
        # 자동 등록 요청 시
        posted = False
        if request.auto_post and result.get("should_reply", False) and request.review_id:
            try:
                # 네이버 플레이스 API 연동
                posted = post_reply_to_naver(
                    request.review_id,
                    result.get("reply_text", "")
                )
            except Exception as e:
                # 자동 등록 실패해도 답글 생성은 성공으로 처리
                print(f"⚠️ 자동 등록 실패: {str(e)}")
                posted = False
        
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
            reply_text=result.get("reply_text", ""),
            reply_tone=result.get("reply_tone", ""),
            nuance_analysis=result.get("nuance_analysis", ""),
            review_id=request.review_id,
            posted=posted
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
    - **review_id**: 네이버 플레이스 리뷰 ID (필수)
    - **reply_text**: 답글 텍스트 (reply_id가 없을 경우 필수)
    
    Returns:
        등록 성공 여부
    """
    try:
        # reply_id가 있으면 DB에서 찾기
        if request.reply_id:
            reply = get_review_reply(request.reply_id)
            if not reply:
                raise HTTPException(
                    status_code=404,
                    detail=f"답글을 찾을 수 없습니다: {request.reply_id}"
                )
            reply_text = reply.get("reply_text", "")
        else:
            if not request.reply_text:
                raise HTTPException(
                    status_code=400,
                    detail="reply_id 또는 reply_text가 필요합니다."
                )
            reply_text = request.reply_text
        
        # 네이버 플레이스 API 연동
        success = post_reply_to_naver(request.review_id, reply_text)
        
        # DB 업데이트
        if request.reply_id:
            update_reply_posted_status(
                request.reply_id,
                success,
                datetime.now().isoformat() if success else None
            )
        
        return {
            "success": success,
            "message": "답글 등록 기능은 현재 개발 중입니다." if not success else "답글이 등록되었습니다.",
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

