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
    
    # 3. API 키 (보안 관리)
    UPSTAGE_API_KEY: Optional[str] = os.getenv("UPSTAGE_API_KEY") # Optional 추가 권장
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")   # Optional 추가 권장

    # 구글 API 키
    GOOGLE_AI_API_KEY: Optional[str] = os.getenv("GOOGLE_AI_API_KEY")
    
    
    # 4. 네이버 광고 API 설정
    NAVER_AD_API_KEY: Optional[str] = os.getenv("NAVER_AD_API_KEY")
    NAVER_AD_SECRET_KEY: Optional[str] = os.getenv("NAVER_AD_SECRET_KEY")
    NAVER_AD_CUSTOMER_ID: Optional[str] = os.getenv("NAVER_AD_CUSTOMER_ID")
    
    # 5. 네이버 플레이스 API 설정
    NAVER_PLACE_API_KEY: Optional[str] = os.getenv("NAVER_PLACE_API_KEY")
    NAVER_PLACE_ACCESS_TOKEN: Optional[str] = os.getenv("NAVER_PLACE_ACCESS_TOKEN")
    
    # 6. 하이브리드 검색 가중치
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