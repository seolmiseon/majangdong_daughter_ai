# server/automation/smart_content_generator.py

"""
안전한 콘텐츠 자동 생성 시스템
- 할인/이벤트 언급 금지
- 날씨/요일 컨텍스트 자동 삽입
- 사진 분석 기반 자연스러운 글 생성
"""

from typing import Optional
from server.llm_service.services.gemini_vision import analyze_image_with_flash
from server.automation.context_provider import get_context_provider
from server.automation.photo_manager import get_photo_manager


class SmartContentGenerator:
    """안전장치가 적용된 스마트 콘텐츠 생성기"""

    # 🔒 안전장치 1: 금지어 목록
    # ⚠️ 주의: 너무 광범위하면 자연스러운 표현도 막힘
    # 과도한 할인/이벤트만 막고, 자연스러운 마케팅은 허용
    FORBIDDEN_WORDS = [
        # 과도한 할인/이벤트 표현 (스팸으로 보일 수 있음)
        "할인",
        "무료",
        "이벤트",
        "쿠폰",
        "증정",
        "프로모션",
        "특가",
        "세일",
        "%",  # "10% 할인" 같은 표현
        # 구체적인 가격 언급 (정책 위반 소지)
        "만원",
        "천원",
        # "서비스"는 제거 - "서비스가 좋다" 같은 자연스러운 표현 허용
        # "원"은 제거 - 너무 광범위함
    ]

    def __init__(self):
        self.context_provider = get_context_provider()
        self.photo_manager = get_photo_manager()

    def _build_safe_prompt(self, context_info: str, allow_promotions: bool = False) -> str:
        """
        안전장치가 적용된 프롬프트 생성

        Args:
            context_info: 날씨/요일 컨텍스트
            allow_promotions: True면 할인/이벤트 언급 허용

        Returns:
            안전한 프롬프트
        """
        if allow_promotions:
            # 할인/이벤트 허용 모드
            prompt = f"""
✅ [작성 가이드]
- 음식의 맛, 신선도, 품질 묘사
- 가게 분위기, 인테리어, 청결함
- 계절감, 날씨와 어울리는 음식 추천
- 따뜻하고 친근한 사장님 톤
- 할인/이벤트 언급 가능 (자연스럽게)
- "추천", "인기", "맛있음" 같은 긍정적 표현

📅 [오늘의 상황]
{context_info}

📝 [작성 요청]
이 음식 사진을 보고 네이버 플레이스 '새 소식'용 설명을 작성해주세요.
- 50-100자 이내
- ⭐ 최우선: '마장동 소고기' 키워드를 반드시 자연스럽게 포함 (현재 22위, 상위권 진입 목표)
- ⭐ 높은 우선순위: '마장동 한우' 키워드도 가능하면 포함 (현재 34위)
- '마장동딸', '신선' 같은 키워드도 자연스럽게 포함
- 사장님이 직접 쓴 것처럼 친근하고 따뜻한 톤
- 할인/이벤트가 있다면 자연스럽게 언급 가능

예시 (좋은 예시):
"비 오는 날엔 따뜻한 마장동 소고기 한 점이 최고죠. 마장동딸에서 갓 손질한 신선한 한우로
마음까지 따뜻하게 녹여드립니다 💕"

예시 (더 좋은 예시):
"마장동 소고기 맛집을 찾고 계신가요? 마장동딸에서 프리미엄 한우로 특별한 식사 경험을 해보세요."
"""
        else:
            # 기본 모드 (금지어 체크)
            prompt = f"""
🔒 [중요 제약사항 - 반드시 준수]
- 과도한 할인/이벤트 표현 금지: "할인", "무료", "이벤트", "쿠폰", "증정", "프로모션", "특가", "세일"
- 구체적인 가격 언급 금지: "만원", "천원", "%" (예: "10% 할인", "1만원")
- 긴급성 조장 표현 주의: "오늘만", "한정" (가끔은 괜찮지만 과도하면 안 됨)

✅ [허용되는 내용 - 자연스러운 마케팅]
- 음식의 맛, 신선도, 품질 묘사
- 가게 분위기, 인테리어, 청결함
- 계절감, 날씨와 어울리는 음식 추천
- 따뜻하고 친근한 사장님 톤
- "서비스가 좋다", "특별한 맛" 같은 자연스러운 표현 ✅
- "추천", "인기", "맛있음" 같은 긍정적 표현 ✅

📅 [오늘의 상황]
{context_info}

📝 [작성 요청]
이 음식 사진을 보고 네이버 플레이스 '새 소식'용 설명을 작성해주세요.
- 50-100자 이내
- '마장동딸', '한우', '신선', '마장동' 같은 키워드 자연스럽게 포함
- 사장님이 직접 쓴 것처럼 친근하고 따뜻한 톤
- 위 제약사항을 반드시 준수

예시 (좋은 문구):
"비 오는 날엔 따뜻한 고기 한 점이 최고죠. 마장동딸에서 갓 손질한 신선한 한우로
마음까지 따뜻하게 녹여드립니다 💕"

예시 (나쁜 문구 - 절대 금지):
"오늘만 한우 10% 할인! 서둘러 방문하세요!" ❌
"""
        return prompt

    def _check_forbidden_words(self, content: str) -> tuple[bool, list[str]]:
        """
        금지어 검사

        Args:
            content: 검사할 텍스트

        Returns:
            (검사 통과 여부, 발견된 금지어 목록)
        """
        found_words = [word for word in self.FORBIDDEN_WORDS if word in content]
        is_safe = len(found_words) == 0
        return is_safe, found_words

    def generate_post_content(
        self, max_retries: int = 3, check_forbidden_words: bool = True
    ) -> Optional[dict[str, any]]:
        """
        안전한 게시물 콘텐츠 생성 (동기 버전 - 크론잡용)

        Args:
            max_retries: AI가 금지어를 사용할 경우 재시도 횟수
            check_forbidden_words: 금지어 체크 여부 (False면 할인/이벤트 언급 가능)

        Returns:
            {
                "image_filename": str,
                "image_data": bytes,
                "description": str,
                "context": str
            } 또는 None
        """
        # 1. 랜덤 사진 선택 (동기 버전)
        photo_result = self.photo_manager.get_random_photo()
        if not photo_result:
            print("❌ 사용 가능한 사진이 없습니다.")
            return None

        filename, image_data = photo_result

        # 2. 컨텍스트 정보 생성
        context_info = self.context_provider.generate_prompt_context()

        # 3. 안전한 프롬프트 생성
        allow_promotions = not check_forbidden_words
        safe_prompt = self._build_safe_prompt(context_info, allow_promotions=allow_promotions)

        # 4. AI로 설명 생성 (재시도 로직)
        for attempt in range(max_retries):
            print(f"🤖 AI 콘텐츠 생성 중... (시도 {attempt + 1}/{max_retries})")

            description = analyze_image_with_flash(image_data, safe_prompt)

            # 에러 체크
            if "에러" in description or "오류" in description:
                print(f"❌ AI 생성 실패: {description}")
                continue

            # 🔒 안전장치 2: 금지어 검사 (선택적)
            if check_forbidden_words:
                is_safe, found_words = self._check_forbidden_words(description)

                if is_safe:
                    print("✅ 안전한 콘텐츠 생성 완료!")
                    return {
                        "image_filename": filename,
                        "image_data": image_data,
                        "description": description,
                        "context": context_info,
                    }
                else:
                    print(
                        f"⚠️ 금지어 발견: {found_words}. "
                        f"재생성 중... ({attempt + 1}/{max_retries})"
                    )
            else:
                # 금지어 체크 안 함 - 할인/이벤트 언급 가능
                print("✅ 콘텐츠 생성 완료! (금지어 체크 건너뜀)")
                return {
                    "image_filename": filename,
                    "image_data": image_data,
                    "description": description,
                    "context": context_info,
                }

        print("❌ 최대 재시도 횟수 초과. 안전한 콘텐츠 생성 실패.")
        return None

    async def generate_post_content_async(
        self, max_retries: int = 3, check_forbidden_words: bool = True
    ) -> Optional[dict[str, any]]:
        """
        안전한 게시물 콘텐츠 생성 (비동기 버전 - FastAPI용)

        Args:
            max_retries: AI가 금지어를 사용할 경우 재시도 횟수
            check_forbidden_words: 금지어 체크 여부 (False면 할인/이벤트 언급 가능)

        Returns:
            {
                "image_filename": str,
                "image_data": bytes,
                "description": str,
                "context": str
            } 또는 None
        """
        # 1. 랜덤 사진 선택 (비동기 버전 - 이벤트 루프 블로킹 방지)
        photo_result = await self.photo_manager.get_random_photo_async()
        if not photo_result:
            print("❌ 사용 가능한 사진이 없습니다.")
            return None

        filename, image_data = photo_result

        # 2. 컨텍스트 정보 생성
        context_info = self.context_provider.generate_prompt_context()

        # 3. 안전한 프롬프트 생성
        allow_promotions = not check_forbidden_words
        safe_prompt = self._build_safe_prompt(context_info, allow_promotions=allow_promotions)

        # 4. AI로 설명 생성 (재시도 로직)
        for attempt in range(max_retries):
            print(f"🤖 AI 콘텐츠 생성 중... (시도 {attempt + 1}/{max_retries})")

            description = analyze_image_with_flash(image_data, safe_prompt)

            # 에러 체크
            if "에러" in description or "오류" in description:
                print(f"❌ AI 생성 실패: {description}")
                continue

            # 🔒 안전장치 2: 금지어 검사 (선택적)
            if check_forbidden_words:
                is_safe, found_words = self._check_forbidden_words(description)

                if is_safe:
                    print("✅ 안전한 콘텐츠 생성 완료!")
                    return {
                        "image_filename": filename,
                        "image_data": image_data,
                        "description": description,
                        "context": context_info,
                    }
                else:
                    print(
                        f"⚠️ 금지어 발견: {found_words}. "
                        f"재생성 중... ({attempt + 1}/{max_retries})"
                    )
            else:
                # 금지어 체크 안 함 - 할인/이벤트 언급 가능
                print("✅ 콘텐츠 생성 완료! (금지어 체크 건너뜀)")
                return {
                    "image_filename": filename,
                    "image_data": image_data,
                    "description": description,
                    "context": context_info,
                }

        print("❌ 최대 재시도 횟수 초과. 안전한 콘텐츠 생성 실패.")
        return None

    def generate_preview(self) -> Optional[str]:
        """
        게시 전 미리보기 생성 (테스트용)

        Returns:
            생성된 콘텐츠 미리보기 문자열
        """
        result = self.generate_post_content()
        if not result:
            return None

        preview = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📸 선택된 사진: {result['image_filename']}
📅 컨텍스트: {result['context']}

📝 생성된 설명:
{result['description']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return preview


# 싱글톤 인스턴스
_content_generator: Optional[SmartContentGenerator] = None


def get_content_generator() -> SmartContentGenerator:
    """SmartContentGenerator 싱글톤 인스턴스 반환"""
    global _content_generator
    if _content_generator is None:
        _content_generator = SmartContentGenerator()
    return _content_generator


# 테스트 코드
if __name__ == "__main__":
    generator = SmartContentGenerator()

    print("\n🎨 스마트 콘텐츠 생성 테스트\n")

    # 미리보기 생성
    preview = generator.generate_preview()

    if preview:
        print(preview)
    else:
        print("❌ 콘텐츠 생성 실패")
        print("\n💡 다음을 확인하세요:")
        print("  1. S3에 사진이 업로드되어 있는지 (upload_to_s3.py 사용)")
        print("  2. Gemini API 키가 설정되어 있는지")
        print("  3. 네트워크 연결이 정상인지")
