# server/database/models.py

"""
데이터베이스 모델 정의
SQLite를 사용한 리뷰 답글 저장소
"""

import sqlite3
import os
from typing import Optional, List, Dict
from datetime import datetime


class ReviewReplyDB:
    """리뷰 답글 SQLite 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "data/review_replies.db"):
        """
        데이터베이스 초기화
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        # data 디렉토리 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn
    
    def _init_db(self):
        """데이터베이스 테이블 초기화"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_replies (
                id TEXT PRIMARY KEY,
                review_text TEXT NOT NULL,
                review_rating INTEGER NOT NULL CHECK(review_rating >= 1 AND review_rating <= 5),
                review_id TEXT,
                final_verdict TEXT NOT NULL CHECK(final_verdict IN ('MALICIOUS', 'REVIEW_NEEDED', 'NORMAL')),
                confidence REAL NOT NULL,
                reason TEXT,
                should_report INTEGER NOT NULL DEFAULT 0,
                should_reply INTEGER NOT NULL DEFAULT 0,
                reply_text TEXT,
                reply_tone TEXT,
                nuance_analysis TEXT,
                created_at TEXT NOT NULL,
                posted INTEGER NOT NULL DEFAULT 0,
                posted_at TEXT
            )
        """)
        
        # 인덱스 생성 (조회 성능 향상)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_id ON review_replies(review_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_final_verdict ON review_replies(final_verdict)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON review_replies(created_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def create_reply(self, reply_data: Dict) -> str:
        """
        답글 생성
        
        Args:
            reply_data: 답글 데이터 딕셔너리
        
        Returns:
            생성된 답글 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO review_replies (
                id, review_text, review_rating, review_id,
                final_verdict, confidence, reason, should_report,
                should_reply, reply_text, reply_tone, nuance_analysis,
                created_at, posted, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reply_data.get("id"),
            reply_data.get("review_text"),
            reply_data.get("review_rating"),
            reply_data.get("review_id"),
            reply_data.get("final_verdict"),
            reply_data.get("confidence", 0.0),
            reply_data.get("reason", ""),
            1 if reply_data.get("should_report", False) else 0,
            1 if reply_data.get("should_reply", False) else 0,
            reply_data.get("reply_text", ""),
            reply_data.get("reply_tone", ""),
            reply_data.get("nuance_analysis", ""),
            reply_data.get("created_at"),
            1 if reply_data.get("posted", False) else 0,
            reply_data.get("posted_at")
        ))
        
        conn.commit()
        reply_id = reply_data.get("id")
        conn.close()
        
        return reply_id
    
    def get_reply(self, reply_id: str) -> Optional[Dict]:
        """
        답글 조회
        
        Args:
            reply_id: 답글 ID
        
        Returns:
            답글 데이터 딕셔너리 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM review_replies WHERE id = ?
        """, (reply_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_dict(row)
        return None
    
    def list_replies(
        self,
        limit: int = 10,
        offset: int = 0,
        verdict: Optional[str] = None
    ) -> List[Dict]:
        """
        답글 목록 조회
        
        Args:
            limit: 조회할 답글 수
            offset: 시작 위치
            verdict: 필터링할 판단 결과
        
        Returns:
            답글 데이터 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if verdict:
            cursor.execute("""
                SELECT * FROM review_replies
                WHERE final_verdict = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (verdict, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM review_replies
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
    
    def count_replies(self, verdict: Optional[str] = None) -> int:
        """
        답글 개수 조회
        
        Args:
            verdict: 필터링할 판단 결과
        
        Returns:
            답글 개수
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if verdict:
            cursor.execute("""
                SELECT COUNT(*) FROM review_replies
                WHERE final_verdict = ?
            """, (verdict,))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM review_replies
            """)
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def update_posted_status(self, reply_id: str, posted: bool, posted_at: Optional[str] = None):
        """
        답글 등록 상태 업데이트
        
        Args:
            reply_id: 답글 ID
            posted: 등록 여부
            posted_at: 등록 시간 (ISO 형식)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE review_replies
            SET posted = ?, posted_at = ?
            WHERE id = ?
        """, (1 if posted else 0, posted_at, reply_id))
        
        conn.commit()
        conn.close()
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """SQLite Row를 딕셔너리로 변환"""
        return {
            "id": row["id"],
            "review_text": row["review_text"],
            "review_rating": row["review_rating"],
            "review_id": row["review_id"],
            "final_verdict": row["final_verdict"],
            "confidence": row["confidence"],
            "reason": row["reason"],
            "should_report": bool(row["should_report"]),
            "should_reply": bool(row["should_reply"]),
            "reply_text": row["reply_text"],
            "reply_tone": row["reply_tone"],
            "nuance_analysis": row["nuance_analysis"],
            "created_at": row["created_at"],
            "posted": bool(row["posted"]),
            "posted_at": row["posted_at"]
        }


# 싱글톤 인스턴스
_db_instance: Optional[ReviewReplyDB] = None


def get_db() -> ReviewReplyDB:
    """ReviewReplyDB 싱글톤 인스턴스 반환"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ReviewReplyDB()
    return _db_instance

