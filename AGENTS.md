# AGENTS.md (에이전틱 워크플로우 명세서)

## 1. 상태 머신(State Machine) 구조 설계
LangGraph의 `StateGraph`를 활용하여 에이전트 간 데이터(추론 컨텍스트)가 유실되지 않도록 견고한 흐름 제어를 구현했습니다.

* **상태 객체 (State Object)**: `server/llm_service/agents/review_reply_workflow.py` 파일 내 `TypedDict` 형태로 선언된 `ReviewReplyState`. 여기에는 `review_text` (원문), `first_judge_result` (1차 뉘앙스 분석 결과), `final_verdict` (최종 판결: `MALICIOUS`/`REVIEW_NEEDED`/`NORMAL`), `reply_text` (생성 완료된 답글) 등의 값이 담기며 각 노드는 이 상태 딕셔너리를 읽고(Read) 수정(Write)하며 다음 엣지(Edge)로 상태 변화를 전파합니다.
* **제어 흐름 (Control Flow)**: 단순 선형(Sequential) 진행이 아닌, 조건부 라우팅(Conditional Routing) 도입. `first_judge_node`의 1차 판단 결과가 명확할 경우 심층분석(`second_judge_node`)을 건너뛰고 바로 답글 생성(`generate_reply_node`) 혹은 조기 종료(END)로 넘어가며, 이는 토큰 요금(Cost)을 줄이려는 DAG(유향 비순환 그래프) 구조를 가집니다.

## 2. 멀티 에이전트(Multi-Agent) 역할 분담
본 비즈니스 로직(마장동딸 AI)은 에이전트 페르소나를 완벽히 분리하고 위임했습니다.

* **`Review Analyzer` (상담/판단 전담)**: `first_judge_node`와 `second_judge_node`로 구성된 리뷰 분석가 에이전트. 네이버 플레이스 리뷰의 감정선을 정밀 분석하여 '단순 불만'과 악질적인 영업 방해 행위를 오직 이 에이전트만이 판단합니다. 
* **`Content Generator / Marketing Writer` (마케팅 작성 전담)**: `server/llm_service/agents/marketing_agent.py` 및 `review_reply_workflow.py` 내부의 답글 생성 노드. 분석가 에이전트가 `NORMAL`(정상)로 판별한 데이터만을 넘겨받고, 그에 어울리는 브랜드 톤앤매너로 대답하거나 S3 이미지(Gemini Vision)를 통해 추출된 매장 정보를 조합(Context Providers 등)하여 '새소식 홍보 콘텐츠'를 발행하는 데 특화되어 있습니다.
