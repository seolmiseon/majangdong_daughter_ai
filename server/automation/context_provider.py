# server/automation/context_provider.py

"""
날씨/요일 컨텍스트 제공 시스템
- 현재 날씨 정보 조회
- 요일별 맞춤 메시지
- AI 프롬프트에 상황 정보 제공
"""

import requests
from datetime import datetime
from typing import Dict, Optional


class ContextProvider:
    """컨텍스트 정보 제공 클래스"""

    def __init__(self):
        # 무료 날씨 API (OpenWeatherMap 대신 간단한 대안 사용 가능)
        self.weather_api_key = None  # 필요시 설정

    def get_day_context(self) -> str:
        """
        요일별 컨텍스트 메시지 생성

        Returns:
            요일별 맞춤 메시지
        """
        now = datetime.now()
        weekday = now.weekday()  # 0=월요일, 6=일요일
        hour = now.hour

        # 요일별 메시지
        day_messages = {
            0: "월요일 블루를 맛있는 고기로 날려버리세요",
            1: "화요일, 한 주의 피로를 고기로 풀어보세요",
            2: "수요일 중반, 힘을 내야 할 때 고기가 답입니다",
            3: "목요일, 주말이 코앞! 미리 예약하세요",
            4: "불금! 오늘 저녁 계획은 마장동딸",
            5: "주말엔 가족과 함께 고기 파티",
            6: "일요일, 내일을 위한 에너지 충전",
        }

        # 시간대별 추가 메시지
        if 11 <= hour < 14:
            time_msg = "점심시간"
        elif 17 <= hour < 22:
            time_msg = "저녁시간"
        else:
            time_msg = ""

        base_msg = day_messages.get(weekday, "오늘")
        if time_msg:
            return f"{time_msg}, {base_msg}"
        return base_msg

    def get_weather_context(self, city: str = "Seoul") -> Optional[str]:
        """
        날씨 기반 컨텍스트 메시지 생성
        (간단한 시뮬레이션 버전 - 실제 API 연동 시 확장 가능)

        Args:
            city: 도시명

        Returns:
            날씨 관련 메시지 또는 None
        """
        # 실제 날씨 API를 사용하려면 여기에 API 호출 코드 추가
        # 현재는 시간대 기반 간단한 메시지 제공

        now = datetime.now()
        hour = now.hour

        if hour < 6:
            return "새벽 공기가 차갑네요. 따뜻한 국밥 한 그릇 어때요?"
        elif hour < 12:
            return "상쾌한 아침입니다"
        elif hour < 18:
            return "따뜻한 오후네요"
        elif hour < 22:
            return "저녁이 되었습니다. 고기 굽는 소리가 들리시나요?"
        else:
            return "밤늦은 시간, 야식으로 고기는 어떠세요?"

    def get_full_context(self) -> Dict[str, str]:
        """
        전체 컨텍스트 정보 반환

        Returns:
            컨텍스트 딕셔너리
        """
        return {
            "day_context": self.get_day_context(),
            "weather_context": self.get_weather_context() or "",
            "timestamp": datetime.now().isoformat(),
        }

    def generate_prompt_context(self) -> str:
        """
        AI 프롬프트에 사용할 컨텍스트 문자열 생성

        Returns:
            프롬프트에 삽입할 컨텍스트 문자열
        """
        ctx = self.get_full_context()
        day_msg = ctx["day_context"]
        weather_msg = ctx["weather_context"]

        context_parts = []
        if day_msg:
            context_parts.append(f"오늘 상황: {day_msg}")
        if weather_msg:
            context_parts.append(f"날씨/분위기: {weather_msg}")

        if context_parts:
            return "\n".join(context_parts)
        return ""


# 싱글톤 인스턴스
_context_provider: Optional[ContextProvider] = None


def get_context_provider() -> ContextProvider:
    """ContextProvider 싱글톤 인스턴스 반환"""
    global _context_provider
    if _context_provider is None:
        _context_provider = ContextProvider()
    return _context_provider


# 테스트 코드
if __name__ == "__main__":
    provider = ContextProvider()

    print("\n📅 현재 컨텍스트:")
    ctx = provider.get_full_context()
    print(f"  요일 메시지: {ctx['day_context']}")
    print(f"  날씨 메시지: {ctx['weather_context']}")
    print(f"  타임스탬프: {ctx['timestamp']}")

    print("\n📝 AI 프롬프트용 컨텍스트:")
    print(provider.generate_prompt_context())
