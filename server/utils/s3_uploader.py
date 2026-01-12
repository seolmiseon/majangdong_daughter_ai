# server/utils/s3_uploader.py

"""
AWS S3 이미지 업로드 유틸리티
SEO 최적화를 위한 CloudFront CDN 연동
"""

import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from server.llm_service.config.settings import settings


class S3Uploader:
    """S3 이미지 업로드 클래스"""
    
    def __init__(self):
        """S3 클라이언트 초기화"""
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "majangdong-photos")
        self.region = os.getenv("AWS_REGION", "ap-northeast-2")
        self.cloudfront_url = os.getenv("CLOUDFRONT_URL", "")
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY가 설정되지 않았습니다.")
        
        # S3 클라이언트 생성
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region
        )
    
    def upload_image(
        self,
        image_data: bytes,
        filename: str,
        folder: str = "photos",
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        이미지를 S3에 업로드하고 CloudFront URL 반환
        
        Args:
            image_data: 이미지 바이트 데이터
            filename: 저장할 파일명 (SEO 친화적으로)
            folder: S3 폴더 경로
            content_type: 이미지 MIME 타입
        
        Returns:
            CloudFront URL 또는 None (실패 시)
        """
        try:
            # SEO 친화적인 파일명 생성
            safe_filename = self._sanitize_filename(filename)
            s3_key = f"{folder}/{safe_filename}"
            
            # S3에 업로드
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
                CacheControl="max-age=31536000",  # 1년 캐싱 (SEO 최적화)
                Metadata={
                    "uploaded-by": "majangdong-daughter-ai",
                    "seo-optimized": "true"
                }
            )
            
            # CloudFront URL 생성
            if self.cloudfront_url:
                # CloudFront URL이 있으면 사용
                cdn_url = f"{self.cloudfront_url.rstrip('/')}/{s3_key}"
            else:
                # 없으면 S3 직접 URL
                cdn_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            print(f"✅ 이미지 업로드 성공: {s3_key}")
            return cdn_url
            
        except ClientError as e:
            print(f"❌ S3 업로드 실패: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 업로드 중 오류: {str(e)}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        파일명을 SEO 친화적으로 정리
        
        Args:
            filename: 원본 파일명
        
        Returns:
            정리된 파일명
        """
        # 확장자 분리
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix.lower()
        
        # 한글과 영문, 숫자, 하이픈만 허용
        import re
        safe_stem = re.sub(r'[^가-힣a-zA-Z0-9\-]', '-', stem)
        safe_stem = re.sub(r'-+', '-', safe_stem)  # 연속된 하이픈 제거
        safe_stem = safe_stem.strip('-')
        
        # SEO 친화적인 파일명 생성
        # 예: "마장동딸-고기-구이-2024-01-08.jpg"
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d")
        final_name = f"{safe_stem}-{timestamp}{suffix}"
        
        return final_name
    
    def list_images(self, folder: str = "photos", limit: int = 100, return_keys: bool = False) -> list:
        """
        S3에서 이미지 목록 조회
        
        Args:
            folder: 폴더 경로
            limit: 최대 개수
            return_keys: True면 S3 key 리스트 반환, False면 URL 리스트 반환
        
        Returns:
            이미지 URL 리스트 또는 S3 key 리스트
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{folder}/",
                MaxKeys=limit
            )
            
            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        if return_keys:
                            images.append(key)
                        else:
                            if self.cloudfront_url:
                                url = f"{self.cloudfront_url.rstrip('/')}/{key}"
                            else:
                                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                            images.append(url)
            
            return images
            
        except Exception as e:
            print(f"❌ 이미지 목록 조회 실패: {str(e)}")
            return []
    
    def download_image(self, s3_key: str) -> Optional[bytes]:
        """
        S3에서 이미지 다운로드 (boto3 사용)
        
        Args:
            s3_key: S3 객체 키 (예: "photos/image.jpg")
        
        Returns:
            이미지 바이트 데이터 또는 None (실패 시)
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            image_data = response['Body'].read()
            return image_data
        except ClientError as e:
            print(f"❌ S3 이미지 다운로드 실패: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 이미지 다운로드 중 오류: {str(e)}")
            return None
    
    def delete_image(self, s3_key: str) -> bool:
        """
        S3에서 이미지 삭제
        
        Args:
            s3_key: S3 객체 키
        
        Returns:
            성공 여부
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            print(f"✅ 이미지 삭제 성공: {s3_key}")
            return True
        except Exception as e:
            print(f"❌ 이미지 삭제 실패: {str(e)}")
            return False


# 싱글톤 인스턴스
_s3_uploader: Optional[S3Uploader] = None


def get_s3_uploader() -> Optional[S3Uploader]:
    """S3Uploader 싱글톤 인스턴스 반환"""
    global _s3_uploader
    if _s3_uploader is None:
        try:
            _s3_uploader = S3Uploader()
        except ValueError:
            # AWS 자격 증명이 없으면 None 반환
            print("⚠️ S3 업로더 초기화 실패: AWS 자격 증명이 없습니다.")
            return None
    return _s3_uploader

