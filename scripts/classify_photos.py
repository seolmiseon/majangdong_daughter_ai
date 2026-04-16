#!/usr/bin/env python3
"""
AI로 가게 사진과 제품 사진을 자동 분류하는 스크립트

사용법:
    python scripts/classify_photos.py
"""

import shutil
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.llm_service.services.gemini_vision import (  # noqa: E402
    analyze_image_with_flash,
)

# 분류할 폴더 경로
backup_folder_path = (
    "/home/seolmiseon/majangdong-daughter-ai/majang_images/duplicates_backup"
)
main_folder = "/home/seolmiseon/majangdong-daughter-ai/majang_images"

print("🤖 AI 사진 분류 시작...")
print("📂 백업 폴더:", backup_folder_path)
print("📂 복구 대상: 가게 외관/내부 사진\n")

# 백업 폴더의 모든 이미지 파일 찾기
image_files = []
for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
    image_files.extend(Path(backup_folder_path).glob(ext))
    image_files.extend(Path(backup_folder_path).glob(ext.upper()))

print(f"📸 총 {len(image_files)}개의 이미지를 분석합니다...\n")  # noqa: E501

# 분류 결과 저장
store_photos = []  # 가게 사진
product_photos = []  # 제품 사진

for i, image_path in enumerate(image_files, 1):
    print(f"[{i}/{len(image_files)}] 분석 중: {image_path.name}")

    try:
        # 이미지 읽기
        with open(image_path, 'rb') as f:
            image_data = f.read()

        # Gemini Vision으로 분석
        prompt = """이 사진을 분류해주세요:

        A. 가게 사진 (외관, 내부, 인테리어, 간판, 매장 전경)
        B. 제품 사진 (고기, 음식, 요리)

        답변 형식:
        분류: A 또는 B
        이유: 한 줄 설명
        """

        result = analyze_image_with_flash(image_data, prompt)

        # 결과 파싱
        if result and "분류:" in result:
            if "분류: A" in result or "분류:A" in result:
                store_photos.append(image_path)
                print("   ✅ 가게 사진으로 분류")
            else:
                product_photos.append(image_path)
                print("   📦 제품 사진으로 분류")
        else:
            print("   ⚠️ 분류 실패, 건너뜀")

    except Exception as e:
        print(f"   ❌ 오류: {str(e)}")
        continue

    print()

# 결과 요약
print("=" * 50)
print(f"📊 분류 완료:")
print(f"   🏪 가게 사진: {len(store_photos)}개")
print(f"   🥩 제품 사진: {len(product_photos)}개")
print("=" * 50)

# 가게 사진 복구
if store_photos:
    print(f"\n🔄 {len(store_photos)}개의 가게 사진을 복구합니다...\n")  # noqa: E501

    for photo in store_photos:
        try:
            dest = Path(main_folder) / photo.name
            shutil.move(str(photo), str(dest))
            print(f"✅ 복구: {photo.name}")
        except Exception as e:
            print(f"❌ 복구 실패 ({photo.name}): {str(e)}")

    print("\n✨ 가게 사진 복구 완료!")
    print("   메인 폴더:", main_folder)
else:
    print("\n⚠️ 가게 사진을 찾지 못했습니다.")
