#!/usr/bin/env python3
"""
핸드폰에서 받은 사진을 AWS S3로 직접 업로드하는 스크립트

사용법:
    python scripts/upload_to_s3.py /path/to/photos/
    python scripts/upload_to_s3.py photo1.jpg photo2.jpg
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가 (scripts 폴더 기준으로 상위 디렉토리)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.utils.s3_uploader import get_s3_uploader  # noqa: E402


def upload_photos(photo_paths: list[str]):
    """사진들을 S3에 업로드"""
    uploader = get_s3_uploader()
    
    if not uploader:
        print("❌ S3 업로더를 초기화할 수 없습니다.")
        print("   .env 파일에 AWS 자격 증명을 설정하세요:")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY")
        print("   - AWS_S3_BUCKET")
        print("   - CLOUDFRONT_URL (선택사항)")
        return
    
    uploaded_count = 0
    failed_count = 0
    
    for photo_path in photo_paths:
        path = Path(photo_path)
        
        if not path.exists():
            print(f"⚠️ 파일을 찾을 수 없습니다: {photo_path}")
            failed_count += 1
            continue
        
        if not path.is_file():
            print(f"⚠️ 파일이 아닙니다: {photo_path}")
            failed_count += 1
            continue
        
        # 이미지 파일인지 확인
        if path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
            print(f"⚠️ 이미지 파일이 아닙니다: {photo_path}")
            failed_count += 1
            continue
        
        try:
            # 파일 읽기
            with open(path, 'rb') as f:
                image_data = f.read()
            
            # S3에 업로드
            filename = path.name
            url = uploader.upload_image(
                image_data=image_data,
                filename=filename,
                folder="photos",
                content_type=f"image/{path.suffix[1:].lower()}"
            )
            
            if url:
                print(f"✅ 업로드 성공: {filename}")
                print(f"   URL: {url}")
                uploaded_count += 1
            else:
                print(f"❌ 업로드 실패: {filename}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ 오류 발생 ({photo_path}): {str(e)}")
            failed_count += 1
    
    print(f"\n📊 업로드 완료:")
    print(f"   성공: {uploaded_count}개")
    print(f"   실패: {failed_count}개")


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python scripts/upload_to_s3.py /path/to/photos/")
        print("  python scripts/upload_to_s3.py photo1.jpg photo2.jpg")
        sys.exit(1)
    
    photo_paths = []
    
    for arg in sys.argv[1:]:
        path = Path(arg)
        
        if path.is_dir():
            # 디렉토리면 모든 이미지 파일 찾기
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                photo_paths.extend(path.glob(ext))
                photo_paths.extend(path.glob(ext.upper()))
        elif path.is_file():
            # 파일이면 직접 추가
            photo_paths.append(path)
        else:
            print(f"⚠️ 경로를 찾을 수 없습니다: {arg}")
    
    if not photo_paths:
        print("❌ 업로드할 이미지 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    print(f"📸 {len(photo_paths)}개의 이미지를 업로드합니다...\n")
    upload_photos(photo_paths)


if __name__ == "__main__":
    main()

