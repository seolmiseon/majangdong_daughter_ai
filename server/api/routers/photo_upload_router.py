# server/api/routers/photo_upload_router.py

"""
사진 분석 및 새 소식 자동 등록 API 엔드포인트
AI Vision을 활용한 사진 분석 및 네이버 플레이스 새 소식 텍스트 등록 기능 제공
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from server.api.naver_place import get_naver_place_api
from server.llm_service.services.gemini_vision import analyze_image_with_flash

# Router 생성
router = APIRouter(prefix="/api/photo", tags=["photo"])


# --- 유틸리티 및 상수 정의 ---

def validate_image_file(file: UploadFile):
    """이미지 파일 유효성 검사"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail="이미지 파일만 업로드 가능합니다."
        )

def get_news_prompt(competitors: str = "인생한우, 본앤브레드, 용문집", my_shop: str = "마장동딸") -> str:
    """새 소식용 프롬프트 생성 (중복 제거용)"""
    return f"""
이 사진을 분석해서 네이버 플레이스 '새 소식'용 마케팅 글을 작성해줘.

🚨 중요: 마크다운 문법 절대 사용 금지! 순수 텍스트만 작성!
- **, *, _, # 같은 마크다운 기호 절대 사용 금지
- 제목 형식 금지 (예: **[네이버 플레이스 '새 소식' 마케팅 글]** 같은 것)
- 그냥 본문만 바로 시작!

1. 타겟 고객: 마장동 3대장({competitors})을 검색했지만, 더 특별하고 프라이빗한 맛집을 찾는 미식가.

2. 작성 전략 (숨은 고수 마케팅):
   - 메인: 사진 속 고기의 신선함과 마블링을 아주 먹음직스럽게 묘사 (이모티콘 1-2개 사용 🔥).
   - 연관성 부여 (자연스럽게): 경쟁사 이름을 직접 언급하지 말고, 암묵적으로만 연관성 부여
     - 패턴 A (지역 언급): "마장동 소고기 맛집을 찾고 계신가요? {my_shop}에서 프리미엄 한우를 만나보세요." (⭐ '마장동 소고기' 최우선 키워드 포함)
     - 패턴 B (발견의 기쁨): "마장동 소고기 전문 맛집, {my_shop}을 소개합니다. 아는 사람만 아는 단골집입니다." (⭐ '마장동 소고기' 포함)
     - 패턴 C (자연스러운 추천): "마장동 소고기와 한우를 찾고 계신가요? {my_shop}에서 특별한 식사 경험을 해보세요." (⭐ '마장동 소고기', '한우' 포함)
     - ⚠️ 경쟁사 이름 직접 언급 금지 (스팸으로 인식될 수 있음)

3. 톤앤매너: "나만 알고 싶은 맛집"을 소개하는 자신감 있는 사장님 톤.

4. 해시태그:
   - #{my_shop} #마장동소고기 #마장동한우 (⭐ '마장동 소고기' 최우선 키워드)
   - ⚠️ 경쟁사 이름은 해시태그에 포함하지 마세요 (스팸으로 인식될 수 있음)
   - 자연스러운 키워드만 사용: #마장동소고기 #마장동한우 #한우맛집 등

5. 제약사항:
   - '손님이 없다', '한적하다', '웨이팅' 금지.
   - 길이는 150자 내외.
   - 글자 수 카운트 표시 금지.
   - 제목이나 헤더 없이 본문만 작성!
"""

# Request/Response 모델 정의


class PhotoAnalyzeResponse(BaseModel):
    """사진 분석 응답 모델"""

    success: bool
    description: str
    analysis: Optional[str] = None
    error: Optional[str] = None


class PhotoNewsResponse(BaseModel):
    """사진 분석 및 새 소식 등록 응답 모델"""

    success: bool
    description: str
    posted: bool = False
    place_id: Optional[str] = None
    post_type: Optional[str] = None  # "photo" 또는 "news"
    error: Optional[str] = None


# API 엔드포인트


@router.post("/analyze", response_model=PhotoAnalyzeResponse)
async def analyze_photo(
    file: UploadFile = File(..., description="분석할 이미지 파일"),
    prompt: Optional[str] = Form(None, description="커스텀 프롬프트 (선택사항)"),
):
    """
    사진 분석 및 설명 생성

    - **file**: 분석할 이미지 파일 (JPEG, PNG 등)
    - **prompt**: 커스텀 프롬프트 (선택사항, 기본값: 네이버 플레이스용 설명 생성)

    Returns:
        AI가 생성한 사진 설명
    """
    try:
        # 파일 읽기
        image_data = await file.read()

        # 이미지 형식 검증
        validate_image_file(file)

        # 기본 프롬프트 (네이버 플레이스용)
        default_prompt = get_news_prompt()
        analysis_prompt = prompt if prompt else default_prompt

        # AI Vision으로 사진 분석
        description = analyze_image_with_flash(image_data, analysis_prompt)

        if "에러" in description or "모델이 초기화되지 않았습니다" in description:
            return PhotoAnalyzeResponse(
                success=False, description="", error=description
            )

        return PhotoAnalyzeResponse(
            success=True, description=description, analysis=description
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사진 분석 중 오류 발생: {str(e)}")


@router.post("/upload", response_model=PhotoNewsResponse)
async def upload_photo_to_naver(
    file: UploadFile = File(..., description="업로드할 이미지 파일"),
    place_id: str = Form(..., description="네이버 플레이스 가게 ID"),
    post_type: str = Form("news", description="등록 타입: 'photo' 또는 'news'"),
    auto_post: bool = Form(True, description="네이버 플레이스에 자동 등록 여부"),
    custom_prompt: Optional[str] = Form(None, description="커스텀 프롬프트 (선택사항)"),
):
    """
    사진 업로드 및 네이버 플레이스 자동 등록

    - **file**: 업로드할 이미지 파일
    - **place_id**: 네이버 플레이스 가게 ID
    - **post_type**: 등록 타입 ("photo": 업체 사진, "news": 새 소식)
    - **auto_post**: 네이버 플레이스에 자동 등록 여부
    - **custom_prompt**: 커스텀 프롬프트 (선택사항)

    Returns:
        업로드 및 등록 결과
    """
    try:
        # 파일 읽기
        image_data = await file.read()

        # 이미지 형식 검증
        validate_image_file(file)

        # post_type 검증
        if post_type not in ["photo", "news"]:
            raise HTTPException(
                status_code=400, detail="post_type은 'photo' 또는 'news'만 가능합니다."
            )

        # 프롬프트 선택
        competitors = "인생한우, 본앤브레드, 용문집"
        my_shop = "마장동딸"

        # 2. 프롬프트 선택 로직
        if custom_prompt:
            prompt = custom_prompt

        elif post_type == "photo":
            # 업체 사진용
            prompt = f"""
이 사진을 분석해서 네이버 플레이스 '업체 사진' 설명을 작성해줘.

🚨 마크다운 절대 사용 금지! **, *, _ 같은 기호 사용하지 마!

- 내용: 음식/가게의 매력을 30자 이내로 짧고 강렬하게.
- 키워드: #마장동딸 #마장동한우 #마장동맛집 (자연스러운 키워드만 사용)
- ⚠️ 경쟁사 이름은 해시태그에 포함하지 마세요 (스팸으로 인식될 수 있음)
- 제목 없이 본문만 작성!
"""
        else:  # news (새 소식용)
            prompt = get_news_prompt()

        # AI Vision으로 사진 분석 및 설명 생성
        description = analyze_image_with_flash(image_data, prompt)

        if (
            "에러" in description
            or "모델이 초기화되지 않았습니다" in description
            or "오류" in description
        ):
            return PhotoNewsResponse(success=False, description="", error=description)

        # 네이버 플레이스에 자동 등록
        posted = False
        if auto_post:
            try:
                naver_api = get_naver_place_api()

                if post_type == "photo":
                    # 업체 사진 등록
                    posted = naver_api.upload_photo(place_id, image_data, description)
                else:  # news
                    # 새 소식 등록 (제목은 설명의 첫 30자, 내용은 전체 설명)
                    title = (
                        description[:30] + "..."
                        if len(description) > 30
                        else description
                    )
                    posted = naver_api.post_news(
                        place_id, title, description, [image_data]
                    )

            except Exception as e:
                # 자동 등록 실패해도 사진 분석은 성공으로 처리
                print(f"⚠️ 네이버 플레이스 등록 실패: {str(e)}")
                posted = False

        return PhotoNewsResponse(
            success=True,
            description=description,
            posted=posted,
            place_id=place_id,
            post_type=post_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"사진 업로드 중 오류 발생: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    API 상태 확인
    """
    try:
        # Gemini Vision 모델 초기화 확인
        from server.llm_service.services.gemini_vision import gemini_model

        return {
            "status": "healthy",
            "service": "photo_upload_api",
            "vision_model_ready": gemini_model is not None,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
