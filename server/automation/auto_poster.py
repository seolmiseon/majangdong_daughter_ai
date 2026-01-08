# server/automation/auto_poster.py

"""
자동 게시 시스템
- 스마트 콘텐츠 생성
- 네이버 플레이스 자동 업로드
- 크론잡으로 실행 가능
- 로깅 및 에러 처리
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.automation.smart_content_generator import get_content_generator
from server.api.naver_place import get_naver_place_api


class AutoPoster:
    """자동 게시 시스템"""

    def __init__(self, place_id: str):
        """
        Args:
            place_id: 네이버 플레이스 가게 ID
        """
        self.place_id = place_id
        self.content_generator = get_content_generator()
        self.naver_api = get_naver_place_api()
        self.log_file = Path("server/automation/auto_post_log.txt")

    def _log(self, message: str):
        """로그 기록"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)

        # 파일에도 기록
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"⚠️ 로그 파일 쓰기 실패: {e}")

    def post_to_naver(self, dry_run: bool = False, allow_promotions: bool = False) -> bool:
        """
        네이버 플레이스에 새 소식 자동 게시

        Args:
            dry_run: True일 경우 실제 업로드 없이 테스트만 수행
            allow_promotions: True면 할인/이벤트 언급 허용 (금지어 체크 안 함)

        Returns:
            성공 여부
        """
        self._log("━━━━━━ 자동 게시 시작 ━━━━━━")
        
        if allow_promotions:
            self._log("💡 할인/이벤트 언급 허용 모드 (금지어 체크 건너뜀)")

        # 1. 콘텐츠 생성
        self._log("🎨 콘텐츠 생성 중...")
        content = self.content_generator.generate_post_content(
            check_forbidden_words=not allow_promotions
        )

        if not content:
            self._log("❌ 콘텐츠 생성 실패")
            return False

        self._log(f"✅ 콘텐츠 생성 완료: {content['description'][:50]}...")

        # 2. Dry run 모드 (테스트)
        if dry_run:
            self._log("🧪 [DRY RUN 모드] 실제 업로드는 하지 않습니다.")
            self._log(f"  - 사진: {content['image_filename']}")
            self._log(f"  - 설명: {content['description']}")
            self._log(f"  - 컨텍스트: {content['context']}")
            return True

        # 3. 네이버 플레이스 업로드
        self._log("📤 네이버 플레이스 업로드 중...")

        try:
            # 제목은 설명의 첫 30자
            title = (
                content["description"][:30] + "..."
                if len(content["description"]) > 30
                else content["description"]
            )

            # 새 소식 등록
            success = self.naver_api.post_news(
                place_id=self.place_id,
                title=title,
                content=content["description"],
                images=[content["image_data"]],
            )

            if success:
                self._log("✅ 네이버 플레이스 업로드 성공!")
                return True
            else:
                self._log("❌ 네이버 플레이스 업로드 실패")
                return False

        except Exception as e:
            self._log(f"❌ 업로드 중 오류 발생: {e}")
            return False

        finally:
            self._log("━━━━━━ 자동 게시 종료 ━━━━━━\n")

    def test_system(self):
        """
        시스템 전체 테스트 (실제 업로드 없음)
        """
        print("\n🧪 자동 게시 시스템 테스트\n")

        # 1. 사진 창고 확인
        print("1️⃣ 사진 창고 확인:")
        stats = self.content_generator.photo_manager.get_stats()
        print(f"  전체 사진: {stats['total_photos']}장")
        print(f"  남은 사진: {stats['remaining_photos']}장")

        if stats["total_photos"] == 0:
            print("\n⚠️ 사진이 없습니다!")
            print(
                "  server/photo_storage/ 폴더에 고기 사진을 20~30장 넣어주세요.\n"
            )
            return

        # 2. 컨텍스트 생성 확인
        print("\n2️⃣ 컨텍스트 생성 확인:")
        context = self.content_generator.context_provider.get_full_context()
        print(f"  요일: {context['day_context']}")
        print(f"  날씨: {context['weather_context']}")

        # 3. 콘텐츠 생성 테스트 (dry run)
        print("\n3️⃣ 콘텐츠 생성 및 업로드 테스트:")
        success = self.post_to_naver(dry_run=True)

        if success:
            print("\n✅ 모든 테스트 통과!")
            print(
                "\n💡 실제 자동 게시를 시작하려면: "
                "python server/automation/auto_poster.py --post"
            )
        else:
            print("\n❌ 테스트 실패. 위 로그를 확인하세요.")


def main():
    """메인 실행 함수 (크론잡용)"""
    import argparse

    parser = argparse.ArgumentParser(description="마장동딸 자동 게시 시스템")
    parser.add_argument(
        "--place-id",
        default="YOUR_PLACE_ID",  # 실제 플레이스 ID로 변경 필요
        help="네이버 플레이스 가게 ID",
    )
    parser.add_argument(
        "--post", action="store_true", help="실제로 게시 (기본값: 테스트만)"
    )
    parser.add_argument(
        "--test", action="store_true", help="시스템 전체 테스트"
    )
    parser.add_argument(
        "--allow-promotions",
        action="store_true",
        help="할인/이벤트 언급 허용 (금지어 체크 안 함) - 사장님이 할인/이벤트 하고 싶을 때 사용",
    )

    args = parser.parse_args()

    poster = AutoPoster(place_id=args.place_id)

    if args.test:
        # 전체 시스템 테스트
        poster.test_system()
    elif args.post:
        # 실제 게시
        success = poster.post_to_naver(
            dry_run=False, allow_promotions=args.allow_promotions
        )
        sys.exit(0 if success else 1)
    else:
        # 기본값: dry run
        poster.post_to_naver(dry_run=True, allow_promotions=args.allow_promotions)


if __name__ == "__main__":
    main()
