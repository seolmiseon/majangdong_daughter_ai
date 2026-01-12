import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    # 1. 프로젝트 기본 정보
    PROJECT_NAME: str = "Majandong-Daughter-AI"
    VERSION: str = "1.0.0"
    
    # 2. 모델 설정
    LLM_MODEL: str = os.getenv("LLM_MODEL", "solar-pro") 
    SOLAR_MODEL: str = "solar-pro"
    EMBEDDING_MODEL: str = "solar-embedding-1-large"
    
    # Gemini Vision 모델 설정 (비용 효율 최적화)
    # 💰 비용 절감 추천: models/gemini-2.0-flash (기본값)
    #   - 무료 티어 지원 (월 15회 무료)
    #   - 유료 사용 시: 입력 $0.075/1M 토큰, 출력 $0.30/1M 토큰
    #   - 월 60회 사용 시 예상 비용: 약 1-2원
    #   - 정확도: 높음 (이미지 분석 및 콘텐츠 생성에 충분)
    # 
    # 사용 가능한 모델:
    # - models/gemini-2.0-flash (기본, ⭐ 비용 효율 최고, 추천!)
    # - models/gemini-1.5-flash (유료, 비용 효율적이지만 2.0-flash보다 약간 비쌈)
    # - models/gemini-1.5-pro (유료, 고품질이지만 비용이 높음 - 비추천)
    # - models/gemini-2.0-flash-exp (실험적, 불안정할 수 있음)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")
    
    # 3. API 키 (보안 관리)
    UPSTAGE_API_KEY: Optional[str] = os.getenv("UPSTAGE_API_KEY") # Optional 추가 권장
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")   # Optional 추가 권장

    # 구글 API 키 (유료 API 키 사용 권장)
    GOOGLE_AI_API_KEY: Optional[str] = os.getenv("GOOGLE_AI_API_KEY")
    
    
    # 4. 네이버 광고 API 설정
    NAVER_AD_API_KEY: Optional[str] = os.getenv("NAVER_AD_API_KEY")
    NAVER_AD_SECRET_KEY: Optional[str] = os.getenv("NAVER_AD_SECRET_KEY")
    NAVER_AD_CUSTOMER_ID: Optional[str] = os.getenv("NAVER_AD_CUSTOMER_ID")
    
    # 5. 네이버 플레이스 API 설정
    NAVER_PLACE_API_KEY: Optional[str] = os.getenv("NAVER_PLACE_API_KEY")
    NAVER_PLACE_ACCESS_TOKEN: Optional[str] = os.getenv("NAVER_PLACE_ACCESS_TOKEN")
    
    # 네이버 로그인 정보 (MY플레이스 사업자 계정)
    NAVER_ID: Optional[str] = os.getenv("NAVER_ID")
    NAVER_PASSWORD: Optional[str] = os.getenv("NAVER_PASSWORD")
    
    # 6. AWS S3 설정 (이미지 스토리지)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: Optional[str] = os.getenv("AWS_S3_BUCKET", "majangdong-photos")
    AWS_REGION: Optional[str] = os.getenv("AWS_REGION", "ap-northeast-2")
    CLOUDFRONT_URL: Optional[str] = os.getenv("CLOUDFRONT_URL")
    
    # 7. 하이브리드 검색 가중치
    RRF_K: int = 60
    SEMANTIC_WEIGHT: float = 0.7
    LEXICAL_WEIGHT: float = 0.3

    # .env 파일을 자동으로 읽어오기 위한 설정
    # extra='ignore' 옵션을 넣으면 정의되지 않은 변수가 있어도 에러를 안 냅니다.
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra='ignore'  # <-- [팁] 이렇게 하면 나중에 다른 키가 .env에 있어도 에러 안 남
    )

settings = Settings()