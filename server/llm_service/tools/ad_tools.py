# server/llm_service/tools/ad_tools.py

from langchain.tools import tool
from server.api.naver_ads import NaverAdsAPI

@tool
def check_ad_status(query: str = ""):
    """
    네이버 검색광고 캠페인의 현재 상태(노출 중, 중단 등)와 예산 정보를 조회합니다.
    사용자가 광고 현황이나 마케팅 예산에 대해 물어볼 때 사용하세요.
    파라미터 query는 사용하지 않아도 됩니다.
    """
    try:
        api = NaverAdsAPI()
        campaigns = api.test_connection()
        if campaigns:
            return str(campaigns)
        else:
            return "광고 캠페인 정보를 가져올 수 없습니다. API 연결을 확인해주세요."
    except Exception as e:
        return f"광고 정보를 가져오는 중 오류 발생: {str(e)}"