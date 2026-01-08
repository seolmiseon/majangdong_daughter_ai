# server/llm_service/services/gemini_vision.py

import os
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 변수 로드 (.env 파일)
load_dotenv()

# 전역 변수로 모델 관리
gemini_model = None
gemini_api_key = os.getenv("GOOGLE_AI_API_KEY")

if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        # Vision 처리에 가장 효율적인 Flash 모델 설정
        gemini_model = genai.GenerativeModel('gemini-flash-latest')
        print("✅ Gemini Flash Vision Model Initialized")
    except Exception as e:
        print(f"❌ Gemini Initialization Error: {e}")
else:
    print("⚠️ Warning: GOOGLE_AI_API_KEY not found.")


def analyze_image_with_flash(image_bytes: bytes, prompt: str) -> str:
    """
    이미지 바이트 데이터를 받아서 Gemini Flash로 분석 결과를 반환
    """
    if not gemini_model:
        return "오류: Gemini 모델이 초기화되지 않았습니다. API 키를 확인해주세요."

    try:
        # Gemini는 이미지 데이터를 dict 형태로 받는 것을 선호합니다.
        # (기본적으로 jpg/png 등을 자동 인식하지만, 명시해주면 더 안전함)
        image_part = {
            "mime_type": "image/jpeg",  # 대부분의 업로드 이미지는 이걸로 처리 가능
            "data": image_bytes
        }

        # 콘텐츠 생성 요청 (프롬프트 + 이미지)
        response = gemini_model.generate_content([prompt, image_part])
        
        # 텍스트 결과 반환
        return response.text

    except Exception as e:
        print(f"Gemini Analysis Error: {e}")
        return f"에러 발생: AI 분석 중 문제가 생겼습니다. ({str(e)})"