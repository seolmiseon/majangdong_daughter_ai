# server/api/routers/marketing_agent_router.py

"""
마케팅 에이전트 API 엔드포인트
FastAPI router를 통해 마케팅 에이전트 기능을 제공
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from server.llm_service.agents.marketing_agent import MarketingAgent, get_marketing_agent

# Router 생성
router = APIRouter(
    prefix="/api/marketing",
    tags=["marketing"]
)

# MarketingAgent 인스턴스 (싱글톤 패턴)
_agent: Optional[MarketingAgent] = None

def get_agent() -> MarketingAgent:
    """MarketingAgent 인스턴스를 싱글톤으로 관리"""
    global _agent
    if _agent is None:
        _agent = get_marketing_agent()
    return _agent


# Request/Response 모델 정의
class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str
    stream: bool = False  # 스트리밍 여부 (현재는 미지원)


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    success: bool = True
    error: Optional[str] = None


# API 엔드포인트

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """
    마케팅 에이전트와 대화
    
    - **message**: 사용자의 질문이나 요청
    - **stream**: 스트리밍 여부 (True면 스트리밍, False면 일반 응답)
    
    예시:
    - "광고 현황이 어때요?" → Tool을 사용하여 광고 상태 조회 후 조언
    - "광고 문구 추천해줘" → 일반적인 조언 제공
    """
    try:
        agent = get_agent()
        
        if request.stream:
            # 스트리밍 응답
            def generate():
                try:
                    for chunk in agent.chat_stream(request.message):
                        # Server-Sent Events (SSE) 형식으로 전송
                        yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    # 종료 신호
                    yield f"data: {json.dumps({'content': '', 'done': True}, ensure_ascii=False)}\n\n"
                except Exception as e:
                    error_msg = f"스트리밍 중 오류 발생: {str(e)}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True}, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # 일반 응답
            response_text = agent.chat(request.message)
            return ChatResponse(response=response_text, success=True)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"에이전트 응답 생성 중 오류 발생: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    에이전트 상태 확인
    """
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "agent_initialized": agent is not None,
            "tools_count": len(agent.tools) if agent else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/tools")
async def list_tools():
    """
    사용 가능한 Tool 목록 조회
    """
    try:
        agent = get_agent()
        tools_info = []
        
        for tool in agent.tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description,
            })
        
        return {
            "tools": tools_info,
            "count": len(tools_info)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tool 목록 조회 중 오류 발생: {str(e)}"
        )

