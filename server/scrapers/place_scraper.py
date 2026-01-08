import asyncio

from playwright.async_api import async_playwright


class PlaceScraper:
    def __init__(self):
        self.base_url = "https://map.naver.com/v5/search/"

    async def get_store_rank(self, keyword: str, store_name: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(f"https://map.naver.com/v5/search/{keyword}")

            try:
                await page.wait_for_selector("#searchIframe", timeout=10000)
                iframe = page.frame_locator("#searchIframe")

                print(f"🚀 '{store_name}'을(를) 찾으러 깊숙이 내려갑니다...")

                # 💡 무한 스크롤 구현: 친구 가게를 찾을 때까지 최대 5번 스크롤 (약 50위까지)
                for i in range(5):
                    # 마지막 리스트 아이템을 찾아서 그곳으로 스크롤 이동
                    items = await iframe.locator("li").all()
                    if not items:
                        break

                    await items[
                        -1
                    ].scroll_into_view_if_needed()  # 마지막 아이템으로 이동
                    await page.wait_for_timeout(1500)  # 로딩 대기

                    # 현재까지 로드된 아이템들 중에서 친구 가게가 있는지 확인
                    for idx, item in enumerate(items):
                        full_text = await item.inner_text()
                        if store_name in full_text:
                            print(
                                f"✨ 드디어 발견! {store_name}님은 {idx + 1}위에 있습니다."
                            )
                            await browser.close()
                            return idx + 1

                    print(f"   ... {len(items)}위까지 확인 중 ...")

                print(f"😢 50위 안에도 {store_name}이(가) 보이지 않네요.")
                await browser.close()
                return -1

            except Exception as e:
                print(f"⚠️ 에러: {e}")
                await browser.close()
                return -1


if __name__ == "__main__":
    scraper = PlaceScraper()
    # '대구집'으로 테스트해서 로봇이 잘 읽는지 확인해보세요!
    target_store = "마장동딸"
    rank = asyncio.run(scraper.get_store_rank("마장동 소고기", target_store))

    if rank != -1:
        print(f"\n✅ 최종 결과: {target_store}은(는) {rank}위입니다.")
    else:
        print(f"\n❌ 최종 결과: {target_store}을(를) 1페이지에서 찾지 못했습니다.")
