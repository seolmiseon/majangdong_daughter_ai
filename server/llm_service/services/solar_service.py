# server/llm_service/services/solar_service.py

from openai import OpenAI

from server.llm_service.config.settings import settings


class SolarService:
    def __init__(self):
        # settings.py에 있는 키와 모델명을 사용
        self.client = OpenAI(
            api_key=settings.UPSTAGE_API_KEY,
            base_url="https://api.upstage.ai/v1"
        )
        # settings.SOLAR_MODEL 사용
        self.model = settings.SOLAR_MODEL

    def chat_stream(self, user_message: str):
        """
        사용자 메시지를 받아 Solar의 답변을 스트리밍으로 반환하는 함수
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 마장동 고기집 홍보를 돕는 AI 마케터입니다.",
                    },
                    {"role": "user", "content": user_message},
                ],
                stream=True,
            )

            # 제너레이터(Generator) 형태로 반환하여 프론트엔드/콘솔에 실시간 출력 가능
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            print(f"❌ Solar API 호출 중 오류 발생: {e}")
            yield "죄송합니다. AI 연결에 문제가 생겼습니다."

    def get_marketing_advice(
        self, store_name: str, keyword: str, rank: int
    ) -> str:
        """
        순위 정보를 바탕으로 마케팅 조언을 생성하는 메서드 (단발성 호출)
        """
        # 순위에 따른 프롬프트 컨텍스트 설정
        if rank > 50:
            situation = (
                "현재 순위 밖으로 노출이 매우 저조함. "
                "기본적인 플레이스 세팅 점검과 리뷰 작업이 시급함."
            )
        elif rank > 10:
            situation = (
                "1페이지 진입은 했으나 상위권(1~5위) 도약이 필요함. "
                "클릭을 유도할 사진이나 콘텐츠 업데이트가 필요."
            )
        else:
            situation = (
                "현재 최상위권 유지 중. "
                "경쟁사의 견제를 방어하고 방문자 만족도 관리에 집중해야 함."
            )

        prompt = f"""
        당신은 마장동 고기집 전문 마케팅 AI 컨설턴트입니다.

        [가게 정보]
        - 가게명: {store_name}
        - 타겟 키워드: {keyword}
        - 현재 순위: {rank}위
        - 상황 진단: {situation}

        [중요 제약사항]
        - 할인, 무료, 이벤트, 쿠폰, 증정, 프로모션, 특가, 세일 등의 단어 사용 금지
        - 구체적인 가격(만원, 천원, %) 언급 금지
        - 자연스러운 마케팅 전략만 제안 (할인/이벤트 없이)

        [허용되는 전략 예시]
        - 사진 업데이트 (실사진, 다양한 각도)
        - 키워드 최적화 (검색어 자연스럽게 포함)
        - 리뷰 관리 (답글 작성, 소통)
        - 콘텐츠 다양화 (메뉴 소개, 가게 분위기)
        - SNS 연동 (블로그, 인스타그램)

        위 정보를 바탕으로 사장님이 당장 실행해야 할 구체적인 마케팅 전략 3가지를
        번호를 매겨서 간결하고 임팩트 있게(이모지 사용) 제안해주세요.
        할인/이벤트 없이 자연스러운 마케팅 방법만 제안하세요.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 요식업 마케팅 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content
            return content if content else "AI 응답을 생성할 수 없습니다."
        except Exception as e:
            print(f"Solar API Error: {e}")
            return (
                "죄송합니다. 현재 AI 전략가가 잠시 생각을 정리 중입니다. "
                "(API 호출 오류)"
            )

# --- 테스트 실행 코드 (if __name__ == "__main__":) ---
if __name__ == "__main__":
    solar = SolarService()

    print(f"🤖 Solar({solar.model})에게 질문하는 중...\n")

    # 1. 스트리밍 테스트
    print("--- [테스트 1] 일반 대화 (스트리밍) ---")
    print("Solar: ", end="")
    for token in solar.chat_stream("친구 고기집 네이버 광고 문구 좀 추천해줘"):
        print(token, end="", flush=True)
    print("\n")

    # 2. 마케팅 조언 테스트
    print("--- [테스트 2] 마케팅 조언 (단답형) ---")
    advice = solar.get_marketing_advice("마장동딸", "마장동 한우", 55)
    print(advice)
