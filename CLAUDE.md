# CLAUDE.md (AI 협업 지침서)

## 1. 비동기(Async/Await) 설계 원칙
LLM 추론 과정(Upstage Solar, Gemini Vision 등)에서 발생하는 필연적인 네트워크 I/O 병목을 해결하기 위해, 본 프로젝트(마장동딸 AI)는 FastAPI와 병렬 친화적인 비동기 패턴을 엄격히 적용했습니다.

* **라우터 계층 비동기화**: 파일명 `server/api/routers/review_reply_router.py` 내의 모든 엔드포인트(예: `@router.post("/reply") async def generate_review_reply(...)`)에 명시적인 `async def`를 적용하여 수십 건의 리뷰가 동시 인입되더라도 메인 이벤트 루프(Event Loop)가 차단(Blocking)되지 않도록 설계되었습니다.
* **외부 통신(I/O) 대기 처리**: AI 모델 API 호출(`solar_service.py`)과 `naver_place.py`의 비동기 웹 스크래핑/등록 과정(`post_reply_to_naver` 함수)이 I/O 바운드 작업으로 명확히 분리되어 있어, 타 클라이언트의 응답 대기시간을 최소화하는 고성능 스레드 제어를 보여줍니다.

## 2. 가드레일(Moderation) 로직 구현 형태
LLM의 환각(Hallucination) 및 부적절한 텍스트 생성을 차단하기 위해 2중 안전망(Moderation) 규칙이 코드에 내장되어 있습니다.

* **의미적 가드레일 (LangGraph 내부 프롬프트)**: `server/llm_service/agents/review_workflow.py`의 `first_judge_node` 함수에서 한국어 특유의 이중부정("맛이 없지는 않아요" -> 중립/긍정)과 구어체("JMT", "맵찔이")를 식별할 수 있도록 시스템 프롬프트(System Prompt)가 세팅되어 있습니다. 이는 정상(`NORMAL`), 애매함(`REVIEW_NEEDED`), 악성(`MALICIOUS`)으로 세분화된 상태(State) 분류의 핵심 잣대가 됩니다.
* **규칙 기반 가드레일 (Policy Checker)**: `server/utils/policy_checker.py` 파일의 `NaverPlacePolicyChecker` 클래스에 하드코딩된 금지어 리스트(`self.forbidden_keywords = ["할인", "이벤트", "프로모션", "특가"...]`)를 사용하여, 네이버 플레이스 가이드라인을 위반하는 용어가 텍스트에 포함되었는지 `check_policy_compliance()` 함수를 통해 강제 검열(Filter)하고 위반 시 재생성 루프를 구동합니다.

