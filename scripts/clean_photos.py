#!/usr/bin/env python3
"""
구글 드라이브에서 중복 사진 찾아서 정리하는 스크립트

사용법:
    python scripts/clean_photos.py [폴더경로]
    예: python scripts/clean_photos.py "/mnt/c/Users/사용자명/Google Drive/majang_images"
"""

import os
import sys
from pathlib import Path

from difPy import dif

# [1] 구글 드라이브 경로 설정
# 윈도우 경로를 그대로 사용합니다
# 예: G:\내 드라이브\majang_images

# 명령줄 인자로 경로를 받거나, 기본 경로 사용
if len(sys.argv) > 1:
    folder_path = sys.argv[1]
else:
    # 기본 경로 (프로젝트 폴더 안에 사진 폴더를 복사했다고 가정)
    folder_path = "/home/seolmiseon/majangdong-daughter-ai/majang_images"

# 경로가 존재하는지 확인
if not os.path.exists(folder_path):
    print(f"❌ 오류: 경로를 찾을 수 없습니다: {folder_path}")
    print("\n💡 사용법:")
    print("  python scripts/clean_photos.py '/mnt/c/Users/사용자명/Google Drive/majang_images'")
    print("\n또는 스크립트 내부의 folder_path 변수를 수정하세요.")
    sys.exit(1)

print(f"📂 분석 시작: {folder_path} (구글 드라이브에서 실시간 읽는 중...)")
print("⏳ 사진이 많으면 시간이 좀 걸립니다. 잠시만 기다려주세요.")

# [2] 이미지 저장소 구축
build = dif.build(folder_path, recursive=True, show_progress=True)

# [3] 유사도 검사 실행
# similarity="duplicates": 완전 중복만 (MSE=0)
# similarity="similar": 유사한 사진 (MSE 낮음)
# similarity=500: MSE 임계값 (높을수록 더 많이 찾음, 고기 사진은 500~1000 추천)
search = dif.search(build, similarity=500, show_progress=True)

# [4] 결과 요약 출력
print("-" * 30)
print(f"🔎 총 {len(search.result)}개의 중복 그룹을 찾았습니다.")
print(f"🗑️ 중복으로 판명된(삭제 추천) 사진 수: {len(search.lower_quality)}")

# [4] (안전 장치) 바로 삭제하지 말고, 'duplicates' 폴더로 이동시키기
# 친구 사진이니까 혹시 모르니 바로 지우지 마세요!
if len(search.lower_quality) > 0:
    # 중복 사진들을 옮길 폴더 경로 생성
    dupe_folder = os.path.join(folder_path, "duplicates_backup")

    print(f"\n📦 중복 사진들을 다음 폴더로 이동합니다: {dupe_folder}")

    # move_to 기능을 쓰면 알아서 폴더 만들고 옮겨줍니다.
    search.move_to(destination_path=dupe_folder)

    print("✅ 이동 완료! 해당 폴더를 확인하고 나중에 수동으로 지우세요.")
else:
    print("✨ 와우! 중복된 사진이 거의 없습니다. 친구가 사진을 잘 찍었는데요?")
