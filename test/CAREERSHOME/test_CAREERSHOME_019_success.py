import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # '출퇴근' 관련 섹션 찾기 (구: '출퇴근 걱정없는 역세권 포지션' / 신: '출퇴근 편한 포지션')
            TARGET_TEXTS = ['출퇴근 걱정없는 역세권 포지션', '출퇴근 편한 포지션']

            section_abs = await page.evaluate("""(targetTexts) => {
                const articles = document.querySelectorAll('article');
                for (const article of articles) {
                    for (const target of targetTexts) {
                        if (article.textContent.includes(target)) {
                            const rect = article.getBoundingClientRect();
                            const absoluteTop = window.scrollY + rect.top;
                            return { absoluteTop: Math.round(absoluteTop), target };
                        }
                    }
                }
                return null;
            }""", TARGET_TEXTS)

            assert section_abs is not None, "출퇴근 편한 포지션 섹션을 찾을 수 없음"

            # 섹션이 뷰포트 중간에 오도록 스크롤
            target_scroll = max(0, section_abs['absoluteTop'] - 200)
            await page.evaluate(f"window.scrollTo(0, {target_scroll})")
            await page.wait_for_timeout(1500)

            # '지도로 공고 찾기' 링크(버튼) href 확인
            map_href = await page.evaluate("""(targetTexts) => {
                const articles = document.querySelectorAll('article');
                for (const article of articles) {
                    for (const target of targetTexts) {
                        if (article.textContent.includes(target)) {
                            const mapLink = article.querySelector('a[href*="position-map"]');
                            return mapLink ? mapLink.href : null;
                        }
                    }
                }
                return null;
            }""", TARGET_TEXTS)

            assert map_href is not None, "'지도로 공고 찾기' 버튼을 찾을 수 없음"

            # 화면 상단에 노출되는 인앱 메시지(브레이즈) 오버레이가 클릭을 가로채는 경우가 있어 제거
            await page.evaluate("""() => {
                document.querySelectorAll('.ab-in-app-message, [class*="ab-in-app"]').forEach(el => el.remove());
            }""")
            await page.wait_for_timeout(300)

            # '지도로 공고 찾기' 버튼 클릭 (target="_blank" → 새 탭에서 열림)
            map_locator = page.locator(f'a[href="{map_href}"]').first
            async with context.expect_page(timeout=5000) as new_page_info:
                await map_locator.click(timeout=5000)
            target_page = await new_page_info.value
            await target_page.wait_for_load_state('domcontentloaded', timeout=15000)
            await target_page.wait_for_timeout(1000)

            current_url = target_page.url
            print(f"이동된 URL: {current_url}")

            assert 'position-map' in current_url, f"포지션맵 페이지로 이동되지 않음. 현재 URL: {current_url}"
            print("✓ '지도로 공고 찾기' 버튼 클릭 시 포지션맵 페이지로 이동 확인")

            await target_page.screenshot(path='screenshots/test_CAREERSHOME_019_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_019_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
