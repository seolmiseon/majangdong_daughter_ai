# server/llm_service/agents/review_reply_workflow.py

"""
리뷰 판단 + 답글 생성 통합 워크플로우
리뷰를 판단하고, 정상 리뷰에 대해서는 자동으로 답글 생성
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal, Optional
import json
from server.llm_service.services.solar_service import SolarService
from server.llm_service.prompts.review_judge_prompts import REVIEW_JUDGE_SYSTEM_PROMPT
from server.llm_service.services.review_reply_generator import ReviewReplyGenerator

# 1. 상태(State) 정의: 노드끼리 주고받을 데이터
class ReviewReplyState(TypedDict):
    review_text: str  # 입력 리뷰
    review_rating: Optional[int]  # 리뷰 평점 (1-5점, 선택사항)
    first_judge_result: dict  # 1차 판단 결과
    final_verdict: Literal["MALICIOUS", "REVIEW_NEEDED", "NORMAL"]  # 최종 판단
    confidence: float  # 신뢰도
    reason: str  # 판단 이유
    nuance_analysis: str  # 뉘앙스 분석 결과
    should_report: bool  # 신고 여부
    reply_text: str  # 생성된 답글
    reply_tone: str  # 답글 톤
    should_reply: bool  # 답글 작성 여부

# 서비스 인스턴스 (재사용)
solar_service = SolarService()
reply_generator = ReviewReplyGenerator()

# 2. 노드(Node) 함수 정의 (기존 review_workflow.py의 노드 재사용)

def first_judge_node(state: ReviewReplyState) -> dict:
    """
    1차 판단 노드: 한국어 뉘앙스(이중부정, 구어체, 줄임말)를 정확히 파악
    """
    review_text = state["review_text"]
    
    prompt = f"""
다음 네이버 리뷰를 분석하여 한국어 뉘앙스를 정확히 파악하세요.

리뷰: "{review_text}"

다음 항목을 분석하세요:
1. 이중부정 여부 및 실제 의미 ("맛이 없지는 않아요" → 중립/약간 긍정)
2. 구어체/줄임말 포함 여부 및 의미 ("JMT", "맵찔이", "ㅇㅇ" 등)
3. 뉘앙스 있는 표현 파악 ("그냥 그래요", "나쁘지 않아요" 등)
4. 문맥 전체 의미 파악
5. 명확한 악성 리뷰 여부 (욕설, 허위 정보, 경쟁사 홍보 등)

**중요**: 
- 명확히 악성 리뷰면 (욕설, 허위 정보 등) verdict를 "MALICIOUS"로 설정하고 high_confidence를 true로
- 명확히 정상 리뷰면 (구체적 경험, 건설적 비판 등) verdict를 "NORMAL"로 설정하고 high_confidence를 true로
- 애매하면 verdict를 "REVIEW_NEEDED"로 설정하고 high_confidence를 false로

결과를 다음 JSON 형식으로 반환하세요:
{{
    "nuance_analysis": "이중부정/구어체/뉘앙스 분석 결과 (상세 설명)",
    "actual_meaning": "실제 의미 (긍정/부정/중립)",
    "keywords": ["포함된_주요_키워드"],
    "confidence": 0.0-1.0,
    "verdict": "MALICIOUS" | "REVIEW_NEEDED" | "NORMAL",
    "high_confidence": true/false,
    "reason": "판단 이유 (high_confidence가 true일 때만 상세히)"
}}
"""
    
    try:
        response = solar_service.client.chat.completions.create(
            model=solar_service.model,
            messages=[
                {"role": "system", "content": REVIEW_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        first_result = json.loads(result_text)
        
        high_confidence = first_result.get("high_confidence", False)
        verdict = first_result.get("verdict", "REVIEW_NEEDED")
        
        result = {
            "first_judge_result": first_result,
            "nuance_analysis": first_result.get("nuance_analysis", ""),
        }
        
        if high_confidence:
            result["final_verdict"] = verdict
            result["confidence"] = first_result.get("confidence", 0.9)
            result["reason"] = first_result.get("reason", "1차 판단에서 명확히 판단됨")
            if verdict == "MALICIOUS":
                result["should_report"] = True
        
        return result
    except Exception as e:
        print(f"❌ 1차 판단 중 오류: {e}")
        return {
            "first_judge_result": {
                "nuance_analysis": "분석 실패",
                "actual_meaning": "중립",
                "keywords": [],
                "confidence": 0.0,
                "verdict": "REVIEW_NEEDED",
                "high_confidence": False
            },
            "nuance_analysis": f"오류 발생: {str(e)}",
            "final_verdict": "REVIEW_NEEDED",
            "confidence": 0.0
        }


def second_review_node(state: ReviewReplyState) -> dict:
    """
    2차 검토 노드: 1차 결과를 바탕으로 악성 리뷰 여부 최종 판단
    """
    review_text = state["review_text"]
    first_result = state.get("first_judge_result", {})
    nuance_analysis = state.get("nuance_analysis", "")
    
    prompt = f"""
다음 네이버 리뷰를 1차 분석 결과를 바탕으로 최종 판단하세요.

리뷰: "{review_text}"

1차 분석 결과:
- 뉘앙스 분석: {nuance_analysis}
- 실제 의미: {first_result.get('actual_meaning', '')}
- 키워드: {first_result.get('keywords', [])}

다음 기준으로 판단하세요:

🔴 MALICIOUS (즉시 신고):
- 욕설/비방, 인신공격
- 허위 정보 (가게에 가지 않았는데 리뷰)
- 경쟁사 홍보하며 비방
- 반복 스팸
- 개인정보 공개

🟡 REVIEW_NEEDED (수동 검토):
- 애매한 이중부정 표현
- 뉘앙스 있는 표현으로 판단이 어려운 경우
- 구체적 이유 없이 "별로"라고만 한 경우

🟢 NORMAL (정상 리뷰):
- 구체적인 경험을 바탕으로 한 솔직한 의견
- 건설적 비판
- 긍정적이지만 과장되지 않은 리뷰

결과를 다음 JSON 형식으로 반환하세요:
{{
    "verdict": "MALICIOUS" | "REVIEW_NEEDED" | "NORMAL",
    "confidence": 0.0-1.0,
    "reason": "판단 이유 (한국어로 상세히)",
    "should_report": true/false
}}
"""
    
    try:
        response = solar_service.client.chat.completions.create(
            model=solar_service.model,
            messages=[
                {"role": "system", "content": REVIEW_JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        final_result = json.loads(result_text)
        
        verdict = final_result.get("verdict", "REVIEW_NEEDED")
        should_report = final_result.get("should_report", False)
        
        if verdict == "MALICIOUS":
            should_report = True
        
        return {
            "final_verdict": verdict,
            "confidence": final_result.get("confidence", 0.5),
            "reason": final_result.get("reason", ""),
            "should_report": should_report
        }
    except Exception as e:
        print(f"❌ 2차 검토 중 오류: {e}")
        return {
            "final_verdict": "REVIEW_NEEDED",
            "confidence": 0.0,
            "reason": f"오류 발생: {str(e)}",
            "should_report": False
        }


def reply_generation_node(state: ReviewReplyState) -> dict:
    """
    답글 생성 노드: 정상 리뷰에 대해 사장님 답글 생성
    """
    review_text = state["review_text"]
    review_rating = state.get("review_rating")
    verdict = state.get("final_verdict", "NORMAL")
    nuance_analysis = state.get("nuance_analysis", "")
    
    # 악성 리뷰는 답글 생성하지 않음
    if verdict == "MALICIOUS":
        return {
            "reply_text": "",
            "reply_tone": "악성",
            "should_reply": False
        }
    
    # 평점이 없으면 에러 (네이버 플레이스는 항상 평점이 있음)
    if review_rating is None:
        return {
            "reply_text": "",
            "reply_tone": "중립",
            "should_reply": False
        }
    
    # 답글 생성
    reply_result = reply_generator.generate_reply(
        review_text=review_text,
        review_rating=review_rating,
        review_verdict=verdict,
        nuance_analysis=nuance_analysis
    )
    
    return {
        "reply_text": reply_result.get("reply_text", ""),
        "reply_tone": reply_result.get("tone", "중립"),
        "should_reply": reply_result.get("should_reply", False)
    }


# 3. 조건부 분기 함수들

def first_judge_decision(state: ReviewReplyState) -> Literal["second_review", "reply_generation", "report", "end"]:
    """
    1차 판단 후 분기 결정
    """
    first_result = state.get("first_judge_result", {})
    high_confidence = first_result.get("high_confidence", False)
    verdict = first_result.get("verdict", "REVIEW_NEEDED")
    
    if high_confidence:
        if verdict == "MALICIOUS":
            return "report"  # 악성 리뷰, 신고 처리
        elif verdict == "NORMAL":
            return "reply_generation"  # 정상 리뷰, 답글 생성
        else:
            return "second_review"  # REVIEW_NEEDED, 2차 검토
    else:
        return "second_review"  # 애매한 경우, 2차 검토


def second_review_decision(state: ReviewReplyState) -> Literal["reply_generation", "report", "end"]:
    """
    2차 검토 후 분기 결정
    """
    verdict = state.get("final_verdict", "REVIEW_NEEDED")
    
    if verdict == "MALICIOUS":
        return "report"  # 악성 리뷰, 신고 처리
    elif verdict == "NORMAL":
        return "reply_generation"  # 정상 리뷰, 답글 생성
    else:  # REVIEW_NEEDED
        return "end"  # 수동 검토 필요, 답글 생성하지 않음


# 4. 그래프(Workflow) 조립
workflow = StateGraph(ReviewReplyState)

# 노드 추가
workflow.add_node("first_judge", first_judge_node)  # 1차 판단
workflow.add_node("second_review", second_review_node)  # 2차 검토
workflow.add_node("reply_generation", reply_generation_node)  # 답글 생성

# 엔트리 포인트
workflow.set_entry_point("first_judge")

# 1차 판단 후 조건부 분기
workflow.add_conditional_edges(
    "first_judge",
    first_judge_decision,
    {
        "second_review": "second_review",  # 애매한 경우 2차 검토
        "reply_generation": "reply_generation",  # 정상 리뷰, 답글 생성
        "report": END,  # 악성 리뷰, 신고 처리
        "end": END  # 종료
    }
)

# 2차 검토 후 조건부 분기
workflow.add_conditional_edges(
    "second_review",
    second_review_decision,
    {
        "reply_generation": "reply_generation",  # 정상 리뷰, 답글 생성
        "report": END,  # 악성 리뷰, 신고 처리
        "end": END  # 수동 검토 필요
    }
)

# 답글 생성 후 종료
workflow.add_edge("reply_generation", END)

# 워크플로우 컴파일
app = workflow.compile()


# 편의 함수: 리뷰 판단 + 답글 생성 실행
def process_review(
    review_text: str,
    review_rating: int  # 네이버 플레이스 리뷰는 항상 평점이 있음 (1-5점)
) -> dict:
    """
    리뷰를 받아서 판단하고 답글 생성
    
    Args:
        review_text: 판단할 리뷰 텍스트
        review_rating: 리뷰 평점 (1-5점, 필수) - 네이버 플레이스는 항상 평점이 있음
    
    Returns:
        판단 결과 + 답글 생성 결과
    """
    initial_state = {
        "review_text": review_text,
        "review_rating": review_rating,
        "first_judge_result": {},
        "final_verdict": "REVIEW_NEEDED",
        "confidence": 0.0,
        "reason": "",
        "nuance_analysis": "",
        "should_report": False,
        "reply_text": "",
        "reply_tone": "",
        "should_reply": False
    }
    
    result = app.invoke(initial_state)
    return result


# 테스트 코드
if __name__ == "__main__":
    test_reviews = [
        {
            "text": "JMT! 여기 진짜 맛있어요 강추!",
            "rating": 5
        },
        {
            "text": "맛이 없지는 않은데... 가격이 좀 비싸네요 ㅠㅠ",
            "rating": 3
        },
        {
            "text": "서비스가 너무 느려요. 기다리는 시간이 길었어요.",
            "rating": 2
        },
        {
            "text": "여기 안 갔는데 별점 1점 드립니다.",
            "rating": 1
        }
    ]
    
    for test in test_reviews:
        print(f"\n{'='*60}")
        print(f"리뷰: {test['text']}")
        print(f"평점: {test['rating']}점")
        print(f"{'='*60}")
        
        result = process_review(
            review_text=test['text'],
            review_rating=test['rating']
        )
        
        print(f"최종 판단: {result['final_verdict']}")
        print(f"신뢰도: {result['confidence']:.2f}")
        print(f"신고 여부: {result['should_report']}")
        print(f"답글 작성 여부: {result['should_reply']}")
        if result['should_reply']:
            print(f"답글 톤: {result['reply_tone']}")
            print(f"생성된 답글: {result['reply_text']}")

