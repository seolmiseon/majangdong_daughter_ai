from .ad_tools import check_ad_status
# from .review_tools import analyze_review (다른 툴들도 여기서 import)

# 에이전트에게 전달할 툴 리스트
def get_marketing_tools():
    return [
        check_ad_status,
        # analyze_review,
        # ... 추가되는 툴들 계속 여기에 넣으면 됨
    ]