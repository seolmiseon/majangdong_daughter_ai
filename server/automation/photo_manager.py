# server/automation/photo_manager.py

"""
사진 창고 관리 시스템
- 폴더에서 랜덤으로 사진 선택
- 사용 이력 추적하여 중복 방지
- 모든 사진을 사용하면 다시 처음부터 순환
"""

import os
import random
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class PhotoManager:
    """사진 창고 관리 클래스"""

    def __init__(self, photo_dir: str = "server/photo_storage"):
        """
        Args:
            photo_dir: 사진이 저장된 디렉토리 경로
        """
        self.photo_dir = Path(photo_dir)
        self.history_file = self.photo_dir / "usage_history.json"

        # 디렉토리 생성
        self.photo_dir.mkdir(parents=True, exist_ok=True)

        # 사용 이력 로드
        self.usage_history = self._load_history()

    def _load_history(self) -> dict:
        """사용 이력 JSON 파일 로드"""
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"used_photos": [], "last_reset": None}

    def _save_history(self):
        """사용 이력 JSON 파일 저장"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.usage_history, f, ensure_ascii=False, indent=2)

    def get_available_photos(self) -> List[str]:
        """
        사용 가능한 이미지 파일 목록 반환

        Returns:
            이미지 파일명 리스트
        """
        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        photos = [
            f.name
            for f in self.photo_dir.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        ]
        return photos

    def get_random_photo(self) -> Optional[tuple[str, bytes]]:
        """
        랜덤으로 사진 선택 (중복 방지)

        Returns:
            (파일명, 바이트 데이터) 튜플 또는 None
        """
        all_photos = self.get_available_photos()

        if not all_photos:
            print("⚠️ 사진 창고가 비어있습니다!")
            return None

        # 아직 사용하지 않은 사진들
        used_photos = set(self.usage_history.get("used_photos", []))
        unused_photos = [p for p in all_photos if p not in used_photos]

        # 모든 사진을 사용했으면 리셋
        if not unused_photos:
            print("🔄 모든 사진을 사용했습니다. 사용 이력을 초기화합니다.")
            self.usage_history["used_photos"] = []
            self.usage_history["last_reset"] = datetime.now().isoformat()
            unused_photos = all_photos

        # 랜덤 선택
        selected_photo = random.choice(unused_photos)
        photo_path = self.photo_dir / selected_photo

        # 파일 읽기
        try:
            with open(photo_path, "rb") as f:
                photo_data = f.read()

            # 사용 이력 업데이트
            self.usage_history["used_photos"].append(selected_photo)
            self._save_history()

            print(f"✅ 선택된 사진: {selected_photo}")
            return (selected_photo, photo_data)

        except Exception as e:
            print(f"❌ 사진 읽기 실패: {e}")
            return None

    def add_photo(self, photo_data: bytes, filename: str) -> bool:
        """
        새 사진을 창고에 추가

        Args:
            photo_data: 이미지 바이트 데이터
            filename: 저장할 파일명

        Returns:
            성공 여부
        """
        try:
            photo_path = self.photo_dir / filename
            with open(photo_path, "wb") as f:
                f.write(photo_data)
            print(f"✅ 사진 추가 완료: {filename}")
            return True
        except Exception as e:
            print(f"❌ 사진 추가 실패: {e}")
            return False

    def get_stats(self) -> dict:
        """
        사진 창고 통계 정보

        Returns:
            통계 딕셔너리
        """
        all_photos = self.get_available_photos()
        used_photos = self.usage_history.get("used_photos", [])
        return {
            "total_photos": len(all_photos),
            "used_photos": len(used_photos),
            "remaining_photos": len(all_photos) - len(used_photos),
            "last_reset": self.usage_history.get("last_reset"),
        }


# 싱글톤 인스턴스
_photo_manager: Optional[PhotoManager] = None


def get_photo_manager() -> PhotoManager:
    """PhotoManager 싱글톤 인스턴스 반환"""
    global _photo_manager
    if _photo_manager is None:
        _photo_manager = PhotoManager()
    return _photo_manager


# 테스트 코드
if __name__ == "__main__":
    manager = PhotoManager()

    print("\n📊 사진 창고 현황:")
    stats = manager.get_stats()
    print(f"  전체 사진: {stats['total_photos']}장")
    print(f"  사용한 사진: {stats['used_photos']}장")
    print(f"  남은 사진: {stats['remaining_photos']}장")

    print("\n🎲 랜덤 사진 선택 테스트:")
    result = manager.get_random_photo()
    if result:
        filename, data = result
        print(f"  선택된 사진: {filename}")
        print(f"  크기: {len(data)} bytes")
    else:
        print("  ⚠️ 사진 창고가 비어있습니다.")
        print(
            "  💡 server/photo_storage/ 폴더에 고기 사진을 20~30장 넣어주세요!"
        )
