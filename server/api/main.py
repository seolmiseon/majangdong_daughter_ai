# server/api/main.py

"""
FastAPI 메인 애플리케이션
모든 API 라우터를 등록하고 서버를 실행
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.api.routers import review_reply_router
from server.api.routers import marketing_agent_router
from server.api.routers import photo_upload_router
from server.llm_service.config.settings import settings

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="마장동딸 AI - 리뷰 답글 자동화 및 마케팅 에이전트 API"
)

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(review_reply_router.router)
app.include_router(marketing_agent_router.router)
app.include_router(photo_upload_router.router)

# 루트 엔드포인트
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "마장동딸 AI API",
        "version": settings.VERSION,
        "endpoints": {
            "review": "/api/review",
            "marketing": "/api/marketing",
            "photo": "/api/photo",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


# 서버 실행 (개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 모드: 코드 변경 시 자동 재시작
    )

