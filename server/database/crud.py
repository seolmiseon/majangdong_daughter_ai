# server/database/crud.py

"""
리뷰 답글 CRUD 함수
데이터베이스 작업을 위한 편의 함수들
"""

from typing import Optional, List, Dict
from datetime import datetime
from server.database.models import get_db


def create_review_reply(reply_data: Dict) -> str:
    """
    리뷰 답글 생성
    
    Args:
        reply_data: 답글 데이터 딕셔너리
    
    Returns:
        생성된 답글 ID
    """
    db = get_db()
    
    # ID가 없으면 자동 생성
    if "id" not in reply_data or not reply_data["id"]:
        reply_data["id"] = f"reply_{int(datetime.now().timestamp() * 1000)}"
    
    # created_at이 없으면 현재 시간 설정
    if "created_at" not in reply_data or not reply_data["created_at"]:
        reply_data["created_at"] = datetime.now().isoformat()
    
    return db.create_reply(reply_data)


def get_review_reply(reply_id: str) -> Optional[Dict]:
    """
    리뷰 답글 조회
    
    Args:
        reply_id: 답글 ID
    
    Returns:
        답글 데이터 딕셔너리 또는 None
    """
    db = get_db()
    return db.get_reply(reply_id)


def list_review_replies(
    limit: int = 10,
    offset: int = 0,
    verdict: Optional[str] = None
) -> List[Dict]:
    """
    리뷰 답글 목록 조회
    
    Args:
        limit: 조회할 답글 수
        offset: 시작 위치
        verdict: 필터링할 판단 결과
    
    Returns:
        답글 데이터 리스트
    """
    db = get_db()
    return db.list_replies(limit=limit, offset=offset, verdict=verdict)


def count_review_replies(verdict: Optional[str] = None) -> int:
    """
    리뷰 답글 개수 조회
    
    Args:
        verdict: 필터링할 판단 결과
    
    Returns:
        답글 개수
    """
    db = get_db()
    return db.count_replies(verdict=verdict)


def update_reply_posted_status(
    reply_id: str,
    posted: bool,
    posted_at: Optional[str] = None
):
    """
    답글 등록 상태 업데이트
    
    Args:
        reply_id: 답글 ID
        posted: 등록 여부
        posted_at: 등록 시간 (ISO 형식, None이면 현재 시간)
    """
    db = get_db()
    
    if posted_at is None and posted:
        posted_at = datetime.now().isoformat()
    
    db.update_posted_status(reply_id, posted, posted_at)

