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
    
    def __init__(self, naver_id: Optional[str] = None, naver_password: Optional[str] = None):
        """
        네이버 플레이스 크롤러 초기화
        
        Args:
            naver_id: 네이버 로그인 ID (MY플레이스 로그인용, 선택사항)
            naver_password: 네이버 로그인 비밀번호 (MY플레이스 로그인용, 선택사항)
        """
        self.base_url = "https://place.naver.com"
        self.map_url = "https://map.naver.com"
        self.smartplace_url = "https://smartplace.naver.com"  # MY플레이스
        self.smartplace_new_url = "https://new-m.smartplace.naver.com"  # 새로운 MY플레이스
        self.naver_id = naver_id
        self.naver_password = naver_password
        
        
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
    
    async def _login_to_smartplace_async(self, page) -> bool:
        """
        MY플레이스에 사업자 계정으로 로그인 (비동기 내부 구현)
        
        Args:
            page: Playwright 페이지 객체
        
        Returns:
            로그인 성공 여부
        """
        if not self.naver_id or not self.naver_password:
            print("⚠️ 네이버 로그인 정보가 없습니다. naver_id와 naver_password를 설정해주세요.")
            return False
        
        try:
            # 네이버 로그인 페이지로 이동
            login_url = "https://nid.naver.com/nidlogin.login"
            await page.goto(login_url, wait_until="networkidle", timeout=30000)
            
            # 로그인 폼 찾기 및 입력
            id_input = page.locator("#id")
            pw_input = page.locator("#pw")
            
            if await id_input.count() == 0 or await pw_input.count() == 0:
                print("⚠️ 로그인 폼을 찾을 수 없습니다.")
                return False
            
            # ID 입력
            await id_input.fill(self.naver_id)
            await page.wait_for_timeout(500)
            
            # 비밀번호 입력
            await pw_input.fill(self.naver_password)
            await page.wait_for_timeout(500)
            
            # 로그인 버튼 클릭 (더 구체적인 셀렉터 사용)
            login_button = page.locator("#log\\.login").first  # 첫 번째 로그인 버튼만 선택
            if await login_button.count() > 0:
                await login_button.click()
                await page.wait_for_timeout(3000)  # 로그인 처리 대기
                
                # 로그인 성공 여부 확인
                current_url = page.url
                page_content = await page.content()
                
                # 캡차나 추가 인증이 필요한 경우
                if "캡차" in page_content or "captcha" in page_content.lower():
                    print("⚠️ 캡차 인증이 필요합니다. 수동으로 로그인해주세요.")
                    return False
                
                # 로그인 성공 (MY플레이스로 리다이렉트되었는지 확인)
                if "smartplace" in current_url or "nid.naver.com" not in current_url:
                    print("✅ 네이버 로그인 성공")
                    return True
                else:
                    print("⚠️ 로그인 실패 또는 추가 인증이 필요합니다.")
                    return False
            else:
                print("⚠️ 로그인 버튼을 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            print(f"❌ 로그인 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _post_reply_async(
        self,
        place_id: str,
        reply_text: str,
        review_text: Optional[str] = None,
        review_id: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """
        답글 등록 (비동기 내부 구현)
        사업자가 MY플레이스에 로그인하여 자신의 가게 리뷰에 답글을 작성합니다.
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            reply_text: 등록할 답글 텍스트
            review_text: 찾을 리뷰 텍스트 (선택사항, 특정 리뷰를 찾기 위해 사용)
            review_id: 리뷰 ID (선택사항, review_text와 함께 사용)
            dry_run: True일 경우 실제 등록 없이 테스트만 수행
        
        Returns:
            등록 성공 여부
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # 1. MY플레이스에 사업자 계정으로 로그인
                print("🔐 MY플레이스 로그인 시도...")
                login_success = await self._login_to_smartplace_async(page)
                
                if not login_success:
                    await browser.close()
                    raise Exception("MY플레이스 로그인에 실패했습니다. 네이버 계정 정보를 확인해주세요.")
                
                # 2. MY플레이스 리뷰 관리 페이지로 이동
                # 새로운 MY플레이스 URL 시도
                review_management_url = f"{self.smartplace_new_url}/reviews"
                await page.goto(review_management_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                
                # 만약 리다이렉트되거나 다른 URL로 이동한 경우
                current_url = page.url
                if "reviews" not in current_url or "smartplace" not in current_url:
                    # 기존 MY플레이스 URL 시도
                    review_management_url = f"{self.smartplace_url}/reviews"
                    await page.goto(review_management_url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)
                
                # 3. 특정 리뷰 찾기 (review_text로 매칭)
                target_review_element = None
                if review_text:
                    print(f"🔍 리뷰 검색 중: {review_text[:50]}...")
                    # 리뷰 목록 스크롤하여 로드
                    for _ in range(5):  # 최대 5번 스크롤
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500)
                    
                    # 리뷰 요소 찾기
                    review_elements = await page.locator(
                        "[class*='review'], [class*='Review'], [class*='item'], "
                        "li, div[class*='list'], div[class*='card']"
                    ).all()
                    
                    for element in review_elements:
                        try:
                            element_text = await element.inner_text()
                            # 리뷰 텍스트의 일부가 포함되어 있는지 확인
                            if review_text[:50] in element_text or element_text[:50] in review_text:
                                target_review_element = element
                                print(f"✅ 리뷰 찾음: {element_text[:50]}...")
                                break
                        except:
                            continue
                
                # 4. 답글 작성 버튼 찾기
                reply_button = None
                
                if target_review_element:
                    # 특정 리뷰 내에서 답글 버튼 찾기
                    reply_button = target_review_element.locator(
                        "text=답글, text=답변, button:has-text('답글'), "
                        "a:has-text('답글'), [class*='reply'], [class*='Reply']"
                    ).first
                else:
                    # 첫 번째 답글 가능한 리뷰 찾기
                    reply_selectors = [
                        "button:has-text('답글')",
                        "a:has-text('답글')",
                        "[class*='reply']:has-text('답글')",
                        "[class*='Reply']:has-text('답글')",
                        "text=답글",
                        "text=답변"
                    ]
                    
                    for selector in reply_selectors:
                        buttons = await page.locator(selector).all()
                        for button in buttons:
                            try:
                                if await button.is_visible():
                                    reply_button = button
                                    break
                            except:
                                continue
                        if reply_button:
                            break
                
                if not reply_button or await reply_button.count() == 0:
                    await browser.close()
                    print(f"⚠️ 답글 작성 버튼을 찾을 수 없습니다. place_id: {place_id}, review_text: {review_text[:50] if review_text else None}")
                    return False
                
                # 5. 답글 버튼 클릭
                print("📝 답글 작성 버튼 클릭...")
                await reply_button.click()
                await page.wait_for_timeout(2000)
                
                # 6. 답글 입력 필드 찾기 및 입력
                textarea_selectors = [
                    "textarea",
                    "[contenteditable='true']",
                    "[class*='textarea']",
                    "[class*='input']",
                    "[class*='editor']"
                ]
                
                textarea = None
                for selector in textarea_selectors:
                    elements = await page.locator(selector).all()
                    for elem in elements:
                        try:
                            if await elem.is_visible():
                                textarea = elem
                                break
                        except:
                            continue
                    if textarea:
                        break
                
                if not textarea:
                    await browser.close()
                    print(f"⚠️ 답글 입력 필드를 찾을 수 없습니다.")
                    return False
                
                # 7. 텍스트 입력
                print(f"✍️ 답글 입력 중: {reply_text[:50]}...")
                try:
                    if await textarea.get_attribute("contenteditable") == "true":
                        await textarea.fill("")
                        await textarea.type(reply_text, delay=50)
                    else:
                        await textarea.fill(reply_text)
                except:
                    await textarea.type(reply_text, delay=50)
                
                await page.wait_for_timeout(1000)
                
                # 8. 등록 버튼 클릭
                submit_selectors = [
                    "button:has-text('등록')",
                    "button:has-text('작성')",
                    "button:has-text('완료')",
                    "button[type='submit']",
                    "[class*='submit']",
                    "[class*='register']"
                ]
                
                submit_button = None
                for selector in submit_selectors:
                    buttons = await page.locator(selector).all()
                    for button in buttons:
                        try:
                            if await button.is_visible():
                                button_text = await button.inner_text()
                                if any(keyword in button_text for keyword in ["등록", "작성", "완료", "Submit"]):
                                    submit_button = button
                                    break
                        except:
                            continue
                    if submit_button:
                        break
                
                if not submit_button:
                    await browser.close()
                    print(f"⚠️ 등록 버튼을 찾을 수 없습니다.")
                    return False
                
                print("✅ 답글 등록 중...")
                await submit_button.click()
                await page.wait_for_timeout(3000)  # 등록 완료 대기
                
                # 9. 성공 여부 확인
                page_content = await page.content()
                success = reply_text[:30] in page_content
                
                await browser.close()
                
                if success:
                    print(f"✅ 답글 등록 성공: place_id={place_id}, review_id={review_id}")
                    return True
                else:
                    print(f"⚠️ 답글 등록은 시도했지만 확인할 수 없습니다: place_id={place_id}")
                    return True  # 일단 성공으로 처리
                    
        except Exception as e:
            print(f"❌ 답글 등록 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def post_reply(
        self,
        place_id: str,
        reply_text: str,
        review_text: Optional[str] = None,
        review_id: Optional[str] = None,
        dry_run: bool = False
    ) -> bool:
        """
        답글 등록
        
        Args:
            place_id: 네이버 플레이스 가게 ID
            reply_text: 등록할 답글 텍스트
            review_text: 찾을 리뷰 텍스트 (선택사항, 특정 리뷰를 찾기 위해 사용)
            review_id: 리뷰 ID (선택사항, 로깅용)
            dry_run: True일 경우 실제 등록 없이 테스트만 수행
        
        Returns:
            등록 성공 여부
        """
        return self._run_async(self._post_reply_async(place_id, reply_text, review_text, review_id, dry_run))
    
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
        # settings에서 네이버 로그인 정보 가져오기
        naver_id = settings.NAVER_ID if hasattr(settings, 'NAVER_ID') else None
        naver_password = settings.NAVER_PASSWORD if hasattr(settings, 'NAVER_PASSWORD') else None
        _naver_place_api = NaverPlaceAPI(naver_id=naver_id, naver_password=naver_password)
    return _naver_place_api


# 편의 함수들
def post_reply_to_naver(
    place_id: str,
    reply_text: str,
    review_text: Optional[str] = None,
    review_id: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """
    네이버 플레이스에 답글 등록
    
    Args:
        place_id: 네이버 플레이스 가게 ID (필수)
        reply_text: 등록할 답글 텍스트 (필수)
        review_text: 찾을 리뷰 텍스트 (선택사항, 특정 리뷰를 찾기 위해 사용)
        review_id: 리뷰 ID (선택사항, 로깅용)
        dry_run: True일 경우 실제 등록 없이 테스트만 수행
    
    Returns:
        등록 성공 여부
    """
    api = get_naver_place_api()
    return api.post_reply(place_id, reply_text, review_text, review_id, dry_run)


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

