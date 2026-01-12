# server/llm_service/services/gemini_vision.py

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from server.llm_service.config.settings import settings

# 환경 변수 로드 (.env 파일)
load_dotenv()

# 전역 변수로 클라이언트 관리
gemini_client = None
gemini_api_key = settings.GOOGLE_AI_API_KEY
gemini_model = settings.GEMINI_MODEL

if gemini_api_key:
    try:
        # 새로운 통합 SDK 사용
        gemini_client = genai.Client(api_key=gemini_api_key)
        print(f"✅ Gemini Vision Client Initialized (New SDK)")
        print(f"📌 사용 모델: {gemini_model}")
    except Exception as e:
        print(f"❌ Gemini Initialization Error: {e}")
else:
    print("⚠️ Warning: GOOGLE_AI_API_KEY not found.")


def analyze_image_with_flash(image_bytes: bytes, prompt: str) -> str:
    """
    이미지 바이트 데이터를 받아서 Gemini Vision으로 분석 결과를 반환
    (새로운 google-genai SDK 사용, 유료 모델 지원)
    
    Args:
        image_bytes: 분석할 이미지 바이트 데이터
        prompt: 이미지 분석 프롬프트
        
    Returns:
        AI가 생성한 분석 결과 텍스트
    """
    if not gemini_client:
        return "오류: Gemini 클라이언트가 초기화되지 않았습니다. API 키를 확인해주세요."

    try:
        # 새로운 SDK 사용: generate_content 메서드
        # Part.from_text()와 Part.from_bytes()는 키워드 인자 사용
        # 설정 파일에서 모델 선택 (유료 모델 지원)
        response = gemini_client.models.generate_content(
            model=gemini_model,  # settings.GEMINI_MODEL에서 가져옴 (유료 모델 선택 가능)
            contents=[
                types.Content(
                    role='user',
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(
                            data=image_bytes,
                            mime_type='image/jpeg'
                        )
                    ]
                )
            ]
        )

        # 텍스트 결과 반환
        return response.text

    except Exception as e:
        print(f"Gemini Analysis Error: {e}")
        return f"에러 발생: AI 분석 중 문제가 생겼습니다. ({str(e)})"