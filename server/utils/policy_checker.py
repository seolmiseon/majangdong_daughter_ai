# server/utils/policy_checker.py

"""
네이버 플레이스 정책 준수 검증 모듈
답글이 네이버 정책을 준수하는지 자동으로 검증
"""

from typing import Dict, List, Tuple
import re


class NaverPlacePolicyChecker:
    """네이버 플레이스 정책 준수 검증 클래스"""
    
    def __init__(self):
        """정책 체크리스트 초기화"""
        # 금지 키워드 (광고성, 홍보성 표현)
        self.forbidden_keywords = [
            "할인", "이벤트", "프로모션", "특가", "세일",
            "지금 바로", "바로 오세요", "즉시 방문",
            "광고", "홍보", "마케팅"
        ]
        
        # 패턴화된 표현 (반복 사용 시 감지)
        self.patterned_expressions = [
            "감사합니다",
            "많은 관심",
            "다음에도",
            "방문해 주셔서"
        ]
        
        # 최소 길이 (너무 짧으면 기계적)
        self.min_length = 20
        
        # 최대 길이 (너무 길면 의심)
        self.max_length = 500
    
    def check_policy_compliance(self, reply_text: str, review_text: str = None) -> Dict:
        """
        답글이 네이버 정책을 준수하는지 검증
        
        Args:
            reply_text: 검증할 답글 텍스트
            review_text: 원본 리뷰 텍스트 (맞춤형 검증용)
        
        Returns:
            검증 결과 딕셔너리
        """
        issues = []
        warnings = []
        score = 100  # 기본 점수
        
        # 1. 금지 키워드 체크
        forbidden_found = []
        for keyword in self.forbidden_keywords:
            if keyword in reply_text:
                forbidden_found.append(keyword)
                score -= 20
        
        if forbidden_found:
            issues.append({
                "type": "forbidden_keyword",
                "message": f"금지 키워드 발견: {', '.join(forbidden_found)}",
                "severity": "high"
            })
        
        # 2. 길이 체크
        if len(reply_text) < self.min_length:
            issues.append({
                "type": "too_short",
                "message": f"답글이 너무 짧습니다 (최소 {self.min_length}자 권장)",
                "severity": "medium"
            })
            score -= 10
        
        if len(reply_text) > self.max_length:
            warnings.append({
                "type": "too_long",
                "message": f"답글이 너무 깁니다 (최대 {self.max_length}자 권장)",
                "severity": "low"
            })
            score -= 5
        
        # 3. 패턴화된 표현 체크 (반복 사용 감지)
        pattern_count = sum(1 for pattern in self.patterned_expressions if pattern in reply_text)
        if pattern_count >= 3:
            warnings.append({
                "type": "patterned_expression",
                "message": "패턴화된 표현이 과도하게 사용되었습니다",
                "severity": "medium"
            })
            score -= 15
        
        # 4. 자연스러움 체크 (리뷰 내용과의 연관성)
        if review_text:
            # 리뷰의 주요 키워드가 답글에 포함되어 있는지 확인
            review_keywords = self._extract_keywords(review_text)
            reply_keywords = self._extract_keywords(reply_text)
            
            common_keywords = set(review_keywords) & set(reply_keywords)
            if len(common_keywords) == 0 and len(review_keywords) > 0:
                warnings.append({
                    "type": "low_relevance",
                    "message": "리뷰 내용과 답글이 연관성이 낮습니다",
                    "severity": "medium"
                })
                score -= 10
        
        # 5. 기계적 표현 체크
        mechanical_patterns = [
            r"^감사합니다\.?$",  # "감사합니다."만 있는 경우
            r"^감사합니다\.\s*$",
            r"항상\s+감사합니다\.?$"
        ]
        
        for pattern in mechanical_patterns:
            if re.match(pattern, reply_text.strip()):
                issues.append({
                    "type": "mechanical_expression",
                    "message": "너무 기계적인 표현입니다",
                    "severity": "high"
                })
                score -= 20
                break
        
        # 6. 진정성 체크 (개인화 요소)
        personalization_indicators = [
            "말씀", "의견", "피드백", "조언",
            "개선", "반영", "참고"
        ]
        
        has_personalization = any(indicator in reply_text for indicator in personalization_indicators)
        if not has_personalization and len(reply_text) > 50:
            warnings.append({
                "type": "low_personalization",
                "message": "개인화된 표현이 부족합니다",
                "severity": "low"
            })
            score -= 5
        
        # 최종 점수 조정 (0-100 범위)
        score = max(0, min(100, score))
        
        # 통과 여부 판단
        high_severity_issues = [issue for issue in issues if issue["severity"] == "high"]
        passed = len(high_severity_issues) == 0 and score >= 70
        
        return {
            "passed": passed,
            "score": score,
            "issues": issues,
            "warnings": warnings,
            "recommendation": self._get_recommendation(score, issues, warnings)
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 주요 키워드 추출"""
        # 간단한 키워드 추출 (명사 위주)
        # 실제로는 더 정교한 NLP 처리가 필요할 수 있음
        words = re.findall(r'\b\w{2,}\b', text)
        # 불용어 제거
        stopwords = ["것", "수", "등", "및", "또한", "그리고", "하지만", "그러나"]
        keywords = [w for w in words if w not in stopwords and len(w) >= 2]
        return keywords[:10]  # 상위 10개만
    
    def _get_recommendation(self, score: int, issues: List, warnings: List) -> str:
        """검증 결과에 따른 권장사항"""
        if score >= 90:
            return "✅ 정책 준수 우수. 그대로 사용 가능합니다."
        elif score >= 70:
            return "⚠️ 정책 준수 양호. 일부 개선 권장."
        elif score >= 50:
            return "⚠️ 정책 준수 보통. 수정 후 사용 권장."
        else:
            return "❌ 정책 준수 미흡. 반드시 수정 필요."
    
    def check_reply_variety(self, reply_history: List[str]) -> Dict:
        """
        답글 다양성 체크 (반복 패턴 감지)
        
        Args:
            reply_history: 최근 작성한 답글 목록
        
        Returns:
            다양성 검증 결과
        """
        if len(reply_history) < 2:
            return {
                "passed": True,
                "message": "답글 이력이 부족하여 다양성 검증 불가"
            }
        
        # 유사도 체크 (간단한 방식)
        similarities = []
        for i in range(len(reply_history)):
            for j in range(i + 1, len(reply_history)):
                similarity = self._calculate_similarity(reply_history[i], reply_history[j])
                similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        # 평균 유사도가 80% 이상이면 패턴화된 것으로 판단
        passed = avg_similarity < 0.8
        
        return {
            "passed": passed,
            "average_similarity": avg_similarity,
            "message": "답글이 너무 유사합니다. 다양성을 높여주세요." if not passed else "답글 다양성 양호"
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """두 텍스트의 유사도 계산 (간단한 방식)"""
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0


# 싱글톤 인스턴스
_policy_checker: NaverPlacePolicyChecker = None


def get_policy_checker() -> NaverPlacePolicyChecker:
    """NaverPlacePolicyChecker 싱글톤 인스턴스 반환"""
    global _policy_checker
    if _policy_checker is None:
        _policy_checker = NaverPlacePolicyChecker()
    return _policy_checker
