# server/llm_service/services/review_reply_generator.py

"""
리뷰 답글 자동 생성 서비스
리뷰를 받아서 적절한 사장님 답글을 생성
"""

import json
from typing import Dict, Optional
from server.llm_service.services.solar_service import SolarService
from server.llm_service.prompts.review_reply_prompts import REVIEW_REPLY_SYSTEM_PROMPT


class ReviewReplyGenerator:
    """
    리뷰 답글 자동 생성 서비스
    리뷰 텍스트와 판단 결과를 받아서 적절한 사장님 답글 생성
    """
    
    def __init__(self):
        self.solar_service = SolarService()
        self.system_prompt = REVIEW_REPLY_SYSTEM_PROMPT
    
    def generate_reply(
        self, 
        review_text: str, 
        review_rating: int,  # 네이버 플레이스 리뷰는 항상 평점이 있음
        review_verdict: Optional[str] = None,
        nuance_analysis: Optional[str] = None
    ) -> Dict[str, any]:
        """
        리뷰에 대한 답글 생성 (네이버 플레이스 전용)
        
        Args:
            review_text: 손님이 작성한 리뷰 텍스트
            review_rating: 리뷰 평점 (1-5점, 필수) - 네이버 플레이스는 항상 평점이 있음
            review_verdict: 리뷰 판단 결과 ("MALICIOUS", "REVIEW_NEEDED", "NORMAL")
            nuance_analysis: 뉘앙스 분석 결과 (선택사항)
        
        Returns:
            {
                "reply_text": "생성된 답글 텍스트",
                "tone": "긍정" | "중립" | "부정" | "악성",
                "should_reply": true/false,
                "reason": "답글 작성 이유"
            }
        """
        
        # 악성 리뷰는 답글 작성하지 않음
        if review_verdict == "MALICIOUS":
            return {
                "reply_text": "",
                "tone": "악성",
                "should_reply": False,
                "reason": "악성 리뷰로 판단되어 답글을 작성하지 않습니다. 신고 처리하세요."
            }
        
        # 프롬프트 구성
        prompt_parts = [
            f"다음 손님 리뷰에 대한 사장님 답글을 작성해주세요.",
            f"",
            f"리뷰: \"{review_text}\"",
            f"평점: {review_rating}점"  # 네이버 플레이스는 항상 평점이 있음
        ]
        
        if review_verdict:
            verdict_kr = {
                "MALICIOUS": "악성 리뷰",
                "REVIEW_NEEDED": "수동 검토 필요",
                "NORMAL": "정상 리뷰"
            }.get(review_verdict, "정상 리뷰")
            prompt_parts.append(f"판단 결과: {verdict_kr}")
        
        if nuance_analysis:
            prompt_parts.append(f"뉘앙스 분석: {nuance_analysis}")
        
        prompt_parts.append("")
        prompt_parts.append("위 리뷰에 대해 마장동딸 사장님의 톤앤매너로 적절한 답글을 작성해주세요.")
        
        prompt = "\n".join(prompt_parts)
        
        try:
            response = self.solar_service.client.chat.completions.create(
                model=self.solar_service.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # 일관된 톤앤매너 유지하면서 자연스러운 답글
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # 결과 검증 및 기본값 설정
            reply_text = result.get("reply_text", "")
            tone = result.get("tone", "중립")
            should_reply = result.get("should_reply", True)
            reason = result.get("reason", "")
            
            # 악성 리뷰는 답글 작성하지 않음
            if tone == "악성" or review_verdict == "MALICIOUS":
                should_reply = False
            
            return {
                "reply_text": reply_text,
                "tone": tone,
                "should_reply": should_reply,
                "reason": reason
            }
            
        except Exception as e:
            print(f"❌ 답글 생성 중 오류: {e}")
            return {
                "reply_text": "",
                "tone": "중립",
                "should_reply": False,
                "reason": f"답글 생성 중 오류 발생: {str(e)}"
            }
    
    def generate_reply_from_judge_result(
        self,
        review_text: str,
        review_rating: int,
        judge_result: Dict
    ) -> Dict[str, any]:
        """
        review_workflow.py의 판단 결과를 받아서 답글 생성
        
        Args:
            review_text: 손님이 작성한 리뷰 텍스트
            review_rating: 리뷰 평점 (1-5점, 필수)
            judge_result: review_workflow.py의 judge_review() 결과
        
        Returns:
            답글 생성 결과
        """
        verdict = judge_result.get("final_verdict", "NORMAL")
        nuance_analysis = judge_result.get("nuance_analysis", "")
        
        return self.generate_reply(
            review_text=review_text,
            review_rating=review_rating,
            review_verdict=verdict,
            nuance_analysis=nuance_analysis
        )


# 편의 함수
def get_review_reply_generator() -> ReviewReplyGenerator:
    """
    ReviewReplyGenerator 인스턴스를 생성하여 반환
    """
    return ReviewReplyGenerator()


# 테스트 코드
if __name__ == "__main__":
    generator = ReviewReplyGenerator()
    
    print("🤖 리뷰 답글 생성 테스트\n")
    
    test_reviews = [
        {
            "text": "JMT! 여기 진짜 맛있어요 강추!",
            "verdict": "NORMAL",
            "rating": 5
        },
        {
            "text": "맛이 없지는 않은데... 가격이 좀 비싸네요 ㅠㅠ",
            "verdict": "NORMAL",
            "rating": 3
        },
        {
            "text": "서비스가 너무 느려요. 기다리는 시간이 길었어요.",
            "verdict": "NORMAL",
            "rating": 2
        },
        {
            "text": "여기 안 갔는데 별점 1점 드립니다.",
            "verdict": "MALICIOUS",
            "rating": 1
        }
    ]
    
    for test in test_reviews:
        print("=" * 60)
        print(f"리뷰: {test['text']}")
        print(f"평점: {test['rating']}점")
        print(f"판단: {test['verdict']}")
        print("-" * 60)
        
        result = generator.generate_reply(
            review_text=test['text'],
            review_verdict=test['verdict'],
            review_rating=test['rating']
        )
        
        print(f"톤: {result['tone']}")
        print(f"답글 작성 여부: {result['should_reply']}")
        print(f"답글: {result['reply_text']}")
        print(f"이유: {result['reason']}")
        print()

