import asyncio
import os

import pandas as pd
import plotly.express as px
import requests  # <-- 추가됨 (API 호출용)
import streamlit as st
from PIL import Image  # <-- 추가됨 (이미지 처리용)

# (기존 모듈들)
from server.llm_service.services.solar_service import SolarService
from server.scrapers.place_scraper import PlaceScraper
from server.utils.logger import save_rank_log

# 1. 페이지 설정
st.set_page_config(
    page_title="마장동딸 통합 마케팅 솔루션", page_icon="🥩", layout="wide"
)

# 2. 스타일 지정
st.markdown(
    """
    <style>
    .main { background-color: #f5f5f5; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #FF4B4B; color: white; font-weight: bold; }
    .status-box { 
        padding: 20px; 
        border-radius: 10px; 
        background-color: white; 
        border-left: 5px solid #FF4B4B; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #262730;  /* Streamlit 기본 텍스트 색상 명시 */
        font-size: 14px;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🥩 마장동딸: AI 통합 마케팅 솔루션")
st.write("네이버 순위 추적과 AI 마케팅 글쓰기를 한곳에서 관리하세요.")
st.divider()

# --- 탭(Tabs) 생성: 기능 분리 ---
tab1, tab2 = st.tabs(["📈 실시간 순위 분석", "📸 AI 마케팅 글쓰기"])


# ==============================================================================
# 탭 1: 실시간 순위 분석 (기존 코드)
# ==============================================================================
with tab1:
    st.header("🔍 네이버 지도 순위 추적")

    # 사이드바 대신 탭 내부 컬럼 사용 (더 깔끔하게)
    col_input1, col_input2, col_btn = st.columns([2, 2, 1])

    with col_input1:
        keyword = st.text_input(
            "분석 키워드", value="마장동 소고기", key="rank_keyword"
        )
    with col_input2:
        store_name = st.text_input("우리 가게 이름", value="마장동딸", key="rank_store")
    with col_btn:
        st.write("")  # 줄맞춤용 공백
        st.write("")
        search_btn = st.button("순위 분석 시작", key="rank_btn")

    col1, col2 = st.columns([1, 1])

    # 비동기 실행 헬퍼
    def run_async(coroutine):
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coroutine)

    if search_btn:
        try:
            with col1:
                st.subheader("📍 현재 노출 현황")
                with st.spinner("로봇이 네이버 지도를 훑고 있습니다... (약 10초)"):
                    scraper = PlaceScraper()
                    rank = run_async(scraper.get_store_rank(keyword, store_name))

                    if rank and rank > 0:
                        st.metric("현재 순위", f"{rank}위", "상위권 진입 목표!")
                        st.success(f"축하합니다! 현재 {rank}위입니다.")
                    else:
                        st.metric(
                            "현재 순위", "순위 밖", delta="-", delta_color="inverse"
                        )
                        st.error("50위 내에서 찾을 수 없습니다.")
                        rank = 100

                    try:
                        save_rank_log(store_name, keyword, rank)
                    except:
                        pass

            with col2:
                st.subheader("🤖 Solar Pro 전략 리포트")
                with st.spinner("전략 수립 중..."):
                    solar = SolarService()
                    advice = solar.get_marketing_advice(store_name, keyword, rank)
                    st.markdown(
                        f'<div class="status-box">{advice.replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True,
                    )

        except Exception as e:
            st.error(f"오류 발생: {e}")

    # 차트 영역
    st.subheader("📈 순위 히스토리")
    data_path = "data/rank_history.csv"
    if os.path.exists(data_path):
        try:
            df = pd.read_csv(data_path)
            filtered_df = df[df["store_name"] == store_name]
            if not filtered_df.empty:
                fig = px.line(
                    filtered_df,
                    x="timestamp",
                    y="rank",
                    title=f"'{store_name}' 순위 변화",
                    markers=True,
                )
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("아직 데이터가 없습니다.")
        except Exception:
            st.info("데이터 로드 중 오류.")


# ==============================================================================
# 탭 2: AI 마케팅 글쓰기 (새로 추가된 기능!)
# ==============================================================================
with tab2:
    st.header("📸 AI 사진 분석 & 홍보글 생성")
    st.write(
        "사진을 올리면 AI가 **'마장동 3대장 전략'**을 적용한 블로그/인스타용 글을 써줍니다."
    )

    upload_col, result_col = st.columns([1, 1])

    with upload_col:
        uploaded_file = st.file_uploader(
            "맛있는 고기 사진을 올려주세요!",
            type=["jpg", "png", "jpeg"],
            key="photo_uploader",
        )

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="업로드된 사진", use_container_width=True)

            if st.button("✨ AI 홍보글 생성하기", key="photo_btn"):
                with st.spinner("Gemini가 경쟁사(인생한우 등) 분석 중... 🤖"):
                    try:
                        # FastAPI 서버로 요청 전송
                        files = {
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type,
                            )
                        }
                        backend_url = "http://localhost:8000/api/photo/analyze"

                        response = requests.post(backend_url, files=files)

                        if response.status_code == 200:
                            result = response.json()
                            if result["success"]:
                                st.session_state["ai_result"] = result[
                                    "description"
                                ]  # 결과 저장
                            else:
                                st.error(f"실패: {result.get('error')}")
                        else:
                            st.error(f"서버 오류: {response.status_code}")
                    except Exception as e:
                        st.error(f"서버 연결 실패! (Backend가 켜져 있나요?) : {e}")

    with result_col:
        st.subheader("📝 생성된 마케팅 문구")
        if "ai_result" in st.session_state:
            st.success("작성 완료! 복사해서 네이버 새 소식에 붙여넣으세요.")
            st.text_area("결과물", value=st.session_state["ai_result"], height=300)
            st.info(
                "💡 팁: 이 문구는 '인생한우', '본앤브레드', '용문집' 검색 유입을 노리고 작성되었습니다."
            )
        else:
            st.info("👈 왼쪽에서 사진을 올리고 버튼을 눌러주세요.")
