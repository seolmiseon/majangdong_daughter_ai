# server/llm_service/agents/marketing_agent.py

"""
마케팅 에이전트: Tool과 LLM을 바인딩하여 마케팅 조언을 제공하는 에이전트
"""

import json
from typing import List, Dict, Any
from server.llm_service.services.solar_service import SolarService
from server.llm_service.tools import get_marketing_tools
from server.llm_service.prompts.marketing_prompts import MARKETING_SYSTEM_PROMPT


class MarketingAgent:
    """
    마장동딸 고기집의 마케팅을 도와주는 AI 에이전트
    Tool을 사용하여 실시간 데이터를 조회하고 실용적인 조언을 제공
    """
    
    def __init__(self):
        self.solar_service = SolarService()
        self.tools = get_marketing_tools()
        self.system_prompt = MARKETING_SYSTEM_PROMPT
        
        # LangChain Tool을 OpenAI format으로 변환
        self.openai_tools = self._convert_tools_to_openai_format()
    
    def _convert_tools_to_openai_format(self) -> List[Dict[str, Any]]:
        """
        LangChain Tool을 OpenAI API format으로 변환
        """
        openai_tools = []
        
        for tool in self.tools:
            # LangChain tool의 스키마 추출
            tool_schema = tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else {}
            
            # Tool의 docstring에서 설명 추출
            description = tool.description or tool.name
            
            # 파라미터 정보 추출
            properties = {}
            required = []
            
            if tool_schema.get('properties'):
                properties = tool_schema['properties']
                required = tool_schema.get('required', [])
            else:
                # args_schema가 없으면 기본 파라미터 추출 시도
                if hasattr(tool, 'args') and tool.args:
                    for param_name, param_info in tool.args.items():
                        properties[param_name] = {
                            "type": param_info.get('type', 'string'),
                            "description": param_info.get('description', '')
                        }
                        if param_info.get('required', False):
                            required.append(param_name)
            
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Tool을 실행하고 결과를 반환
        """
        # Tool 찾기
        tool = None
        for t in self.tools:
            if t.name == tool_name:
                tool = t
                break
        
        if not tool:
            return f"도구 '{tool_name}'를 찾을 수 없습니다."
        
        try:
            # Tool 실행
            result = tool.invoke(tool_args)
            return str(result)
        except Exception as e:
            return f"도구 실행 중 오류 발생: {str(e)}"
    
    def chat(self, user_message: str) -> str:
        """
        사용자 메시지를 받아서 Tool을 사용하여 응답 생성
        
        Args:
            user_message: 사용자의 질문이나 요청
        
        Returns:
            에이전트의 응답
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        max_iterations = 5  # Tool 호출 최대 반복 횟수
        iteration = 0
        
        while iteration < max_iterations:
            try:
                # LLM 호출 (Tool 포함)
                response = self.solar_service.client.chat.completions.create(
                    model=self.solar_service.model,
                    messages=messages,
                    tools=self.openai_tools if self.openai_tools else None,
                    tool_choice="auto",  # LLM이 필요시 Tool 호출 결정
                    temperature=0.7
                )
                
                message = response.choices[0].message
                
                # Tool 호출이 필요한 경우
                if message.tool_calls:
                    # Tool 호출 결과를 messages에 추가
                    messages.append(message)
                    
                    # 각 Tool 호출 실행
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # Tool 실행
                        tool_result = self._execute_tool(tool_name, tool_args)
                        
                        # Tool 결과를 messages에 추가
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                    
                    iteration += 1
                    continue  # 다음 반복에서 Tool 결과를 바탕으로 최종 응답 생성
                
                # Tool 호출이 없거나 최종 응답인 경우
                if message.content:
                    return message.content
                else:
                    return "응답을 생성할 수 없습니다."
                    
            except Exception as e:
                return f"오류가 발생했습니다: {str(e)}"
        
        return "최대 반복 횟수를 초과했습니다. 다시 시도해주세요."
    
    def chat_stream(self, user_message: str):
        """
        스트리밍 방식으로 응답 생성
        Tool 사용이 필요한 경우 Tool 실행 후 결과를 포함하여 스트리밍
        
        Args:
            user_message: 사용자의 질문이나 요청
        
        Yields:
            응답 텍스트 청크
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            try:
                # LLM 호출 (Tool 포함, 스트리밍)
                stream = self.solar_service.client.chat.completions.create(
                    model=self.solar_service.model,
                    messages=messages,
                    tools=self.openai_tools if self.openai_tools else None,
                    tool_choice="auto",
                    stream=True,
                    temperature=0.7
                )
                
                tool_calls = []
                tool_call_id = None
                accumulated_content = ""
                
                # 스트리밍 응답 처리
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    
                    # Tool 호출이 있는 경우
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            if tool_call_delta.index is not None:
                                # Tool 호출 정보 수집
                                if len(tool_calls) <= tool_call_delta.index:
                                    tool_calls.extend([None] * (tool_call_delta.index + 1 - len(tool_calls)))
                                
                                if tool_calls[tool_call_delta.index] is None:
                                    tool_calls[tool_call_delta.index] = {
                                        "id": tool_call_delta.id or "",
                                        "name": tool_call_delta.function.name or "",
                                        "arguments": tool_call_delta.function.arguments or ""
                                    }
                                else:
                                    if tool_call_delta.function.arguments:
                                        tool_calls[tool_call_delta.index]["arguments"] += tool_call_delta.function.arguments
                    
                    # 일반 텍스트 응답
                    if delta.content:
                        accumulated_content += delta.content
                        yield delta.content
                
                # Tool 호출이 있었던 경우
                if tool_calls:
                    # Tool 호출 정보를 messages에 추가
                    tool_calls_for_message = []
                    for tc in tool_calls:
                        if tc:
                            tool_calls_for_message.append({
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": tc["arguments"]
                                }
                            })
                    
                    if tool_calls_for_message:
                        messages.append({
                            "role": "assistant",
                            "content": accumulated_content if accumulated_content else None,
                            "tool_calls": tool_calls_for_message
                        })
                        
                        # Tool 실행
                        for tool_call in tool_calls_for_message:
                            tool_name = tool_call["function"]["name"]
                            try:
                                tool_args = json.loads(tool_call["function"]["arguments"]) if tool_call["function"]["arguments"] else {}
                            except json.JSONDecodeError:
                                tool_args = {}
                            
                            tool_result = self._execute_tool(tool_name, tool_args)
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": tool_result
                            })
                        
                        iteration += 1
                        continue  # 다음 반복에서 Tool 결과를 바탕으로 최종 응답 스트리밍
                
                # Tool 호출이 없거나 최종 응답인 경우 종료
                break
                    
            except Exception as e:
                yield f"\n\n오류가 발생했습니다: {str(e)}"
                break
        
        if iteration >= max_iterations:
            yield "\n\n최대 반복 횟수를 초과했습니다."


# 편의 함수
def get_marketing_agent() -> MarketingAgent:
    """
    MarketingAgent 인스턴스를 생성하여 반환
    """
    return MarketingAgent()


# 테스트 코드
if __name__ == "__main__":
    agent = MarketingAgent()
    
    print("🤖 마케팅 에이전트 테스트\n")
    
    # 테스트 1: Tool 사용 질문
    print("=" * 60)
    print("테스트 1: 광고 현황 조회 (Tool 사용)")
    print("=" * 60)
    response = agent.chat("광고 현황이 어때요?")
    print(f"에이전트: {response}\n")
    
    # 테스트 2: 일반 질문
    print("=" * 60)
    print("테스트 2: 광고 문구 추천 (Tool 미사용)")
    print("=" * 60)
    response = agent.chat("광고 문구 좀 추천해줘")
    print(f"에이전트: {response}\n")

