# server/automation/photo_manager.py

"""
S3 기반 사진 창고 관리 시스템
- S3에서 랜덤으로 사진 선택
- 사용 이력 추적하여 중복 방지
- 모든 사진을 사용하면 다시 처음부터 순환
- FastAPI 비동기 환경 지원 (run_in_executor 사용)
"""

import os
import random
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from server.utils.s3_uploader import get_s3_uploader


class PhotoManager:
    """S3 기반 사진 창고 관리 클래스"""

    def __init__(self):
        """S3 기반 PhotoManager 초기화"""
        self.s3_uploader = get_s3_uploader()
        self.history_file = Path("server/automation/photo_usage_history.json")
        self._executor = ThreadPoolExecutor(max_workers=2)  # 비동기 실행용 스레드 풀
        
        # 사용 이력 로드
        self.usage_history = self._load_history()
        
        if not self.s3_uploader:
            print("⚠️ S3 업로더를 초기화할 수 없습니다. AWS 자격 증명을 확인하세요.")

    def _load_history(self) -> dict:
        """사용 이력 JSON 파일 로드"""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 사용 이력 로드 실패: {e}")
        return {"used_photos": [], "last_reset": None}

    def _save_history(self):
        """사용 이력 JSON 파일 저장"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.usage_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 사용 이력 저장 실패: {e}")

    def get_available_photos(self) -> List[str]:
        """
        S3에서 사용 가능한 이미지 S3 key 목록 반환

        Returns:
            이미지 S3 key 리스트 (예: ["photos/image1.jpg", "photos/image2.jpg"])
        """
        if not self.s3_uploader:
            return []
        
        try:
            # S3에서 이미지 목록 가져오기 (S3 key로 반환)
            image_keys = self.s3_uploader.list_images(folder="photos", limit=1000, return_keys=True)
            return image_keys
        except Exception as e:
            print(f"❌ S3 이미지 목록 조회 실패: {e}")
            return []

    def get_random_photo(self) -> Optional[Tuple[str, bytes]]:
        """
        S3에서 랜덤으로 사진 선택 (중복 방지) - boto3로 직접 다운로드

        Returns:
            (파일명, 바이트 데이터) 튜플 또는 None
        """
        if not self.s3_uploader:
            print("⚠️ S3 업로더가 초기화되지 않았습니다.")
            return None

        all_photos = self.get_available_photos()

        if not all_photos:
            print("⚠️ S3에 사진이 없습니다!")
            print("   💡 upload_to_s3.py 스크립트로 사진을 업로드하세요.")
            return None

        # 아직 사용하지 않은 사진들 (S3 key 기준)
        used_photos = set(self.usage_history.get("used_photos", []))
        unused_photos = [s3_key for s3_key in all_photos if s3_key not in used_photos]

        # 모든 사진을 사용했으면 리셋
        if not unused_photos:
            print("🔄 모든 사진을 사용했습니다. 사용 이력을 초기화합니다.")
            self.usage_history["used_photos"] = []
            self.usage_history["last_reset"] = datetime.now().isoformat()
            unused_photos = all_photos

        # 랜덤 선택
        selected_s3_key = random.choice(unused_photos)
        
        # S3 key에서 파일명 추출
        filename = selected_s3_key.split("/")[-1]

        # boto3로 이미지 다운로드
        try:
            photo_data = self.s3_uploader.download_image(selected_s3_key)
            
            if not photo_data:
                print(f"❌ 사진 다운로드 실패: {selected_s3_key}")
                return None

            # 사용 이력 업데이트
            self.usage_history["used_photos"].append(selected_s3_key)
            self._save_history()

            print(f"✅ 선택된 사진: {filename} (S3)")
            return (filename, photo_data)

        except Exception as e:
            print(f"❌ 사진 다운로드 실패: {e}")
            return None

    async def get_random_photo_async(self) -> Optional[Tuple[str, bytes]]:
        """
        S3에서 랜덤으로 사진 선택 (비동기 버전) - FastAPI에서 사용
        
        Returns:
            (파일명, 바이트 데이터) 튜플 또는 None
        """
        # 동기 함수를 스레드 풀에서 실행하여 이벤트 루프 블로킹 방지
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.get_random_photo)

    def add_photo(self, photo_data: bytes, filename: str) -> bool:
        """
        새 사진을 S3에 추가

        Args:
            photo_data: 이미지 바이트 데이터
            filename: 저장할 파일명

        Returns:
            성공 여부
        """
        if not self.s3_uploader:
            print("⚠️ S3 업로더가 초기화되지 않았습니다.")
            return False

        try:
            # S3에 업로드
            url = self.s3_uploader.upload_image(
                image_data=photo_data,
                filename=filename,
                folder="photos"
            )
            
            if url:
                print(f"✅ 사진 추가 완료: {filename} → {url}")
                return True
            else:
                print(f"❌ 사진 추가 실패: {filename}")
                return False
                
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
            "storage": "S3 (CloudFront CDN)"
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
    print(f"  저장소: {stats['storage']}")

    print("\n🎲 랜덤 사진 선택 테스트:")
    result = manager.get_random_photo()
    if result:
        filename, data = result
        print(f"  선택된 사진: {filename}")
        print(f"  크기: {len(data)} bytes")
    else:
        print("  ⚠️ S3에 사진이 없습니다.")
        print("  💡 upload_to_s3.py 스크립트로 사진을 업로드하세요!")
