# server/api/naver_place.py

"""
네이버 플레이스 크롤러 연동
리뷰 조회, 답글 등록, 리뷰 신고 기능 제공

Playwright 기반 웹 크롤링을 사용하여 네이버 플레이스와 상호작용합니다.
"""

import asyncio
import concurrent.futures
from typing import Optional, Dict, List
from playwright.async_api import async_playwright
from server.llm_service.config.settings import settings


class NaverPlaceAPI:
    """네이버 플레이스 크롤러 클래스 (Playwright 기반)"""
    
    def __init__(self):
        """네이버 플레이스 크롤러 초기화"""
        self.base_url = "https://place.naver.com"
        self.map_url = "https://map.naver.com"
        
        
    def _run_async(self, coro):
        """비동기 함수를 동기적으로 실행하는 헬퍼"""
        try:
            # 현재 실행 중인 이벤트 루프 확인
            loop = asyncio.get_running_loop()
            # 이미 실행 중이면 새 스레드에서 실행
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # 실행 중인 이벤트 루프가 없으면 새로 생성
            return asyncio.run(coro)
    
    async def _get_reviews_async(
        self,
        place_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Optional[List[Dict]]:
        """
        리뷰 목록 조회 (비동기 내부 구현)
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            limit: 조회할 리뷰 수
            offset: 시작 위치
        
        Returns:
            리뷰 목록 또는 None (실패 시)
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{place_id}"
                await page.goto(place_url, wait_until="networkidle")
                
                # 리뷰 섹션 찾기 및 스크롤
                try:
                    # 리뷰 탭 클릭 (필요한 경우)
                    review_tab = page.locator("text=리뷰").first
                    if await review_tab.count() > 0:
                        await review_tab.click()
                        await page.wait_for_timeout(1000)
                    
                    reviews = []
                    review_items = page.locator("[class*='review'], [class*='Review']").all()
                    
                    # 리뷰 스크롤하여 더 로드
                    for _ in range(min(3, limit // 10)):  # 최대 3번 스크롤
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500)
                    
                    # 리뷰 요소 수집
                    review_elements = page.locator("[class*='review'], [class*='Review'], li").all()
                    count = 0
                    
                    for element in review_elements:
                        if count >= limit:
                            break
                        
                        try:
                            text = await element.inner_text()
                            if len(text) > 20:  # 의미있는 리뷰인지 확인
                                reviews.append({
                                    "id": f"review_{count}",
                                    "text": text[:500],  # 최대 500자
                                    "rating": None,  # 별점은 별도 파싱 필요
                                })
                                count += 1
                        except:
                            continue
                    
                    await browser.close()
                    
                    if reviews:
                        return reviews[offset:offset+limit]
                    return []
                    
                except Exception as e:
                    print(f"⚠️ 리뷰 파싱 중 오류: {str(e)}")
                    await browser.close()
                    return []
                    
        except Exception as e:
            print(f"❌ 리뷰 조회 중 오류: {str(e)}")
            return None
    
    def get_reviews(
        self,
        place_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Optional[List[Dict]]:
        """
        리뷰 목록 조회
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            limit: 조회할 리뷰 수
            offset: 시작 위치
        
        Returns:
            리뷰 목록 또는 None (실패 시)
        """
        return self._run_async(self._get_reviews_async(place_id, limit, offset))
    
    async def _post_reply_async(
        self,
        review_id: str,
        reply_text: str
    ) -> bool:
        """
        답글 등록 (비동기 내부 구현)
        
        Args:
            review_id: 네이버 플레이스 리뷰 ID (또는 place_id)
            reply_text: 등록할 답글 텍스트
        
        Returns:
            등록 성공 여부
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{review_id}" if not review_id.startswith("http") else review_id
                await page.goto(place_url, wait_until="networkidle")
                
                try:
                    # 리뷰 섹션으로 이동
                    review_tab = page.locator("text=리뷰").first
                    if await review_tab.count() > 0:
                        await review_tab.click()
                        await page.wait_for_timeout(2000)
                    
                    # 답글 작성 버튼 찾기 (첫 번째 리뷰에 답글 작성)
                    reply_button = page.locator("text=답글", "text=답변", "button:has-text('답글')").first
                    
                    if await reply_button.count() > 0:
                        await reply_button.click()
                        await page.wait_for_timeout(1000)
                        
                        # 답글 입력 필드 찾기 및 입력
                        textarea = page.locator("textarea, [contenteditable='true']").first
                        if await textarea.count() > 0:
                            await textarea.fill(reply_text)
                            await page.wait_for_timeout(500)
                            
                            # 등록 버튼 클릭
                            submit_button = page.locator("button:has-text('등록'), button:has-text('작성')").first
                            if await submit_button.count() > 0:
                                await submit_button.click()
                                await page.wait_for_timeout(2000)
                                
                                await browser.close()
                                print(f"✅ 답글 등록 성공: {review_id}")
                                return True
                    
                    await browser.close()
                    print(f"⚠️ 답글 작성 버튼을 찾을 수 없습니다: {review_id}")
                    return False
                    
                except Exception as e:
                    await browser.close()
                    print(f"❌ 답글 등록 중 오류: {str(e)}")
                    return False
                
        except Exception as e:
            print(f"❌ 답글 등록 중 오류: {str(e)}")
            return False
    
    def post_reply(
        self,
        review_id: str,
        reply_text: str
    ) -> bool:
        """
        답글 등록
        
        Args:
            review_id: 네이버 플레이스 리뷰 ID 또는 place_id
            reply_text: 등록할 답글 텍스트
        
        Returns:
            등록 성공 여부
        """
        return self._run_async(self._post_reply_async(review_id, reply_text))
    
    async def _report_review_async(
        self,
        review_id: str,
        reason: str = "부적절한 리뷰"
    ) -> bool:
        """
        리뷰 신고 (비동기 내부 구현)
        
        Args:
            review_id: 네이버 플레이스 리뷰 ID 또는 place_id
            reason: 신고 사유
        
        Returns:
            신고 성공 여부
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{review_id}" if not review_id.startswith("http") else review_id
                await page.goto(place_url, wait_until="networkidle")
                
                # 리뷰 섹션으로 이동
                review_tab = page.locator("text=리뷰").first
                if await review_tab.count() > 0:
                    await review_tab.click()
                    await page.wait_for_timeout(2000)
                
                # 신고 버튼 찾기 (보통 더보기 메뉴에 있음)
                more_button = page.locator("[aria-label*='더보기'], [class*='more'], [class*='More']").first
                if await more_button.count() > 0:
                    await more_button.click()
                    await page.wait_for_timeout(500)
                
                # 신고 버튼 클릭
                report_button = page.locator("text=신고", "button:has-text('신고')").first
                if await report_button.count() > 0:
                    await report_button.click()
                    await page.wait_for_timeout(1000)
                    
                    # 신고 사유 선택 및 제출
                    reason_option = page.locator(f"text={reason}").first
                    if await reason_option.count() > 0:
                        await reason_option.click()
                        await page.wait_for_timeout(500)
                    
                    submit_button = page.locator("button:has-text('제출'), button:has-text('신고')").first
                    if await submit_button.count() > 0:
                        await submit_button.click()
                        await page.wait_for_timeout(2000)
                        
                        await browser.close()
                        print(f"✅ 리뷰 신고 성공: {review_id}")
                        return True
                
                await browser.close()
                print(f"⚠️ 신고 버튼을 찾을 수 없습니다: {review_id}")
                return False
                
        except Exception as e:
            print(f"❌ 리뷰 신고 중 오류: {str(e)}")
            return False
    
    def report_review(
        self,
        review_id: str,
        reason: str = "부적절한 리뷰"
    ) -> bool:
        """
        리뷰 신고
        
        Args:
            review_id: 네이버 플레이스 리뷰 ID 또는 place_id
            reason: 신고 사유
        
        Returns:
            신고 성공 여부
        """
        return self._run_async(self._report_review_async(review_id, reason))
    
    async def _get_place_info_async(self, place_id: str) -> Optional[Dict]:
        """
        가게 정보 조회 (비동기 내부 구현)
        
        Args:
            place_id: 네이버 플레이스 가게 ID
        
        Returns:
            가게 정보 딕셔너리 또는 None
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{place_id}"
                await page.goto(place_url, wait_until="networkidle")
                
                try:
                    # 가게 정보 추출
                    place_info = {
                        "id": place_id,
                        "name": None,
                        "address": None,
                        "phone": None,
                        "rating": None,
                        "url": place_url
                    }
                    
                    # 가게 이름
                    name_selectors = ["h1", "[class*='title']", "[class*='name']"]
                    for selector in name_selectors:
                        name_elem = page.locator(selector).first
                        if await name_elem.count() > 0:
                            place_info["name"] = await name_elem.inner_text()
                            break
                    
                    # 주소
                    address_selectors = ["[class*='address']", "[class*='location']"]
                    for selector in address_selectors:
                        addr_elem = page.locator(selector).first
                        if await addr_elem.count() > 0:
                            place_info["address"] = await addr_elem.inner_text()
                            break
                    
                    # 전화번호
                    phone_selectors = ["[class*='phone']", "[class*='tel']"]
                    for selector in phone_selectors:
                        phone_elem = page.locator(selector).first
                        if await phone_elem.count() > 0:
                            place_info["phone"] = await phone_elem.inner_text()
                            break
                    
                    # 평점
                    rating_selectors = ["[class*='rating']", "[class*='score']"]
                    for selector in rating_selectors:
                        rating_elem = page.locator(selector).first
                        if await rating_elem.count() > 0:
                            rating_text = await rating_elem.inner_text()
                            try:
                                place_info["rating"] = float(rating_text.split()[0])
                            except:
                                pass
                            break
                    
                    await browser.close()
                    return place_info
                    
                except Exception as e:
                    await browser.close()
                    print(f"⚠️ 가게 정보 파싱 중 오류: {str(e)}")
                    return None
                
        except Exception as e:
            print(f"❌ 가게 정보 조회 중 오류: {str(e)}")
            return None
    
    def get_place_info(self, place_id: str) -> Optional[Dict]:
        """
        가게 정보 조회
        
        Args:
            place_id: 네이버 플레이스 가게 ID
        
        Returns:
            가게 정보 딕셔너리 또는 None
        """
        return self._run_async(self._get_place_info_async(place_id))
    
    async def _upload_photo_async(
        self,
        place_id: str,
        image_data: bytes,
        description: str
    ) -> bool:
        """
        업체 사진 업로드 (비동기 내부 구현)
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            image_data: 이미지 바이너리 데이터
            description: 사진 설명
        
        Returns:
            업로드 성공 여부
        """
        try:
            import tempfile
            import os
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{place_id}"
                await page.goto(place_url, wait_until="networkidle")
                
                try:
                    # 사진 업로드 섹션 찾기 (보통 "사진" 또는 "갤러리" 탭)
                    photo_tab = page.locator("text=사진", "text=갤러리").first
                    if await photo_tab.count() > 0:
                        await photo_tab.click()
                        await page.wait_for_timeout(2000)
                    
                    # 사진 업로드 버튼 찾기
                    upload_button = page.locator("text=사진 올리기", "text=업로드", "[type='file']").first
                    
                    if await upload_button.count() > 0:
                        # 임시 파일에 이미지 저장
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                            tmp_file.write(image_data)
                            tmp_path = tmp_file.name
                        
                        try:
                            # 파일 업로드
                            await upload_button.set_input_files(tmp_path)
                            await page.wait_for_timeout(2000)
                            
                            # 설명 입력 (있는 경우)
                            description_input = page.locator("textarea, input[type='text']").first
                            if await description_input.count() > 0:
                                await description_input.fill(description)
                                await page.wait_for_timeout(500)
                            
                            # 업로드 완료 버튼 클릭
                            submit_button = page.locator("button:has-text('등록'), button:has-text('업로드')").first
                            if await submit_button.count() > 0:
                                await submit_button.click()
                                await page.wait_for_timeout(3000)
                                
                                await browser.close()
                                os.unlink(tmp_path)
                                print(f"✅ 업체 사진 업로드 성공: {place_id}")
                                return True
                            
                            os.unlink(tmp_path)
                            
                        except Exception as e:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                            raise e
                    
                    await browser.close()
                    print(f"⚠️ 사진 업로드 버튼을 찾을 수 없습니다: {place_id}")
                    return False
                    
                except Exception as e:
                    await browser.close()
                    print(f"❌ 업체 사진 업로드 중 오류: {str(e)}")
                    return False
                
        except Exception as e:
            print(f"❌ 업체 사진 업로드 중 오류: {str(e)}")
            return False
    
    def upload_photo(
        self,
        place_id: str,
        image_data: bytes,
        description: str
    ) -> bool:
        """
        업체 사진 업로드
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            image_data: 이미지 바이너리 데이터
            description: 사진 설명
        
        Returns:
            업로드 성공 여부
        """
        return self._run_async(self._upload_photo_async(place_id, image_data, description))
    
    async def _post_news_async(
        self,
        place_id: str,
        title: str,
        content: str,
        images: Optional[List[bytes]] = None
    ) -> bool:
        """
        새 소식 등록 (비동기 내부 구현)
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            title: 소식 제목
            content: 소식 내용
            images: 이미지 리스트 (선택사항)
        
        Returns:
            등록 성공 여부
        """
        try:
            import tempfile
            import os
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 네이버 플레이스 페이지로 이동
                place_url = f"{self.base_url}/place/{place_id}"
                await page.goto(place_url, wait_until="networkidle")
                
                # 새 소식 작성 버튼 찾기
                news_button = page.locator("text=새 소식", "text=글쓰기", "button:has-text('새 소식')").first
                
                if await news_button.count() > 0:
                    await news_button.click()
                    await page.wait_for_timeout(2000)
                    
                    # 제목 입력
                    title_input = page.locator("input[type='text'], input[placeholder*='제목']").first
                    if await title_input.count() > 0:
                        await title_input.fill(title)
                        await page.wait_for_timeout(500)
                    
                    # 내용 입력
                    content_input = page.locator("textarea, [contenteditable='true']").first
                    if await content_input.count() > 0:
                        await content_input.fill(content)
                        await page.wait_for_timeout(500)
                    
                    # 이미지 업로드 (있는 경우)
                    if images:
                        tmp_paths = []
                        try:
                            for idx, img_data in enumerate(images):
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                    tmp_file.write(img_data)
                                    tmp_paths.append(tmp_file.name)
                            
                            # 이미지 업로드 버튼 찾기
                            image_input = page.locator("[type='file']").first
                            if await image_input.count() > 0:
                                await image_input.set_input_files(tmp_paths)
                                await page.wait_for_timeout(2000)
                            
                        finally:
                            # 임시 파일 정리
                            for tmp_path in tmp_paths:
                                if os.path.exists(tmp_path):
                                    os.unlink(tmp_path)
                    
                    # 등록 버튼 클릭
                    submit_button = page.locator("button:has-text('등록'), button:has-text('작성')").first
                    if await submit_button.count() > 0:
                        await submit_button.click()
                        await page.wait_for_timeout(3000)
                        
                        await browser.close()
                        print(f"✅ 새 소식 등록 성공: {place_id}")
                        return True
                
                await browser.close()
                print(f"⚠️ 새 소식 작성 버튼을 찾을 수 없습니다: {place_id}")
                return False
                
        except Exception as e:
            print(f"❌ 새 소식 등록 중 오류: {str(e)}")
            return False
    
    def post_news(
        self,
        place_id: str,
        title: str,
        content: str,
        images: Optional[List[bytes]] = None
    ) -> bool:
        """
        새 소식 등록
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            title: 소식 제목
            content: 소식 내용
            images: 이미지 리스트 (선택사항)
        
        Returns:
            등록 성공 여부
        """
        return self._run_async(self._post_news_async(place_id, title, content, images))


# 싱글톤 인스턴스
_naver_place_api: Optional[NaverPlaceAPI] = None


def get_naver_place_api() -> NaverPlaceAPI:
    """NaverPlaceAPI 싱글톤 인스턴스 반환"""
    global _naver_place_api
    if _naver_place_api is None:
        _naver_place_api = NaverPlaceAPI()
    return _naver_place_api


# 편의 함수들
def post_reply_to_naver(review_id: str, reply_text: str) -> bool:
    """
    네이버 플레이스에 답글 등록
    
    Args:
        review_id: 네이버 플레이스 리뷰 ID
        reply_text: 등록할 답글 텍스트
    
    Returns:
        등록 성공 여부
    """
    api = get_naver_place_api()
    return api.post_reply(review_id, reply_text)


def report_review_to_naver(review_id: str, reason: str = "부적절한 리뷰") -> bool:
    """
    네이버 플레이스에 리뷰 신고
    
    Args:
        review_id: 네이버 플레이스 리뷰 ID
        reason: 신고 사유
    
    Returns:
        신고 성공 여부
    """
    api = get_naver_place_api()
    return api.report_review(review_id, reason)

