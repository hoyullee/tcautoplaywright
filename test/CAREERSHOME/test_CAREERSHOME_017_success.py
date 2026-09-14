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

            # 마케팅 인앱 메시지(Braze) 팝업이 전체 화면을 덮어 클릭을 가로채는 경우가 있어 닫기 처리
            try:
                iam_iframe = page.locator('iframe.ab-in-app-message')
                if await iam_iframe.count() > 0 and await iam_iframe.is_visible():
                    close_btn = page.frame_locator('iframe.ab-in-app-message').locator('.close')
                    await close_btn.click(timeout=3000)
                    await page.wait_for_timeout(500)
            except Exception:
                pass

            # '최근 본 포지션' 섹션 확인 및 스크롤
            recently_viewed = page.locator('article').filter(
                has=page.locator('h1, h2, h3, h4, h5, h6, strong, span, p').filter(has_text='최근 본 포지션')
            ).first
            await recently_viewed.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # '최근 본 포지션' 텍스트 확인
            assert await recently_viewed.is_visible(), "'최근 본 포지션' 섹션이 보이지 않음"

            # '전체보기' 버튼 찾기 - jobshistory 링크를 직접 찾음
            # 에러 출력에서 href="/jobshistory"인 '전체보기' 링크 확인
            view_all_btn = page.locator('a[href*="jobshistory"]')

            if await view_all_btn.count() == 0:
                # 대안: '최근 본 포지션' 섹션의 article 내 전체보기 링크
                view_all_btn = recently_viewed.get_by_role('link', name='전체보기').first

            if await view_all_btn.count() == 0:
                raise Exception("'최근 본 포지션' 섹션의 '전체보기' 버튼을 찾을 수 없습니다")

            await view_all_btn.first.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center'})")
            await page.wait_for_timeout(500)
            await view_all_btn.first.click()

            # '최근 본 포지션' 페이지로 이동 확인
            await page.wait_for_url('**/jobshistory**', timeout=10000)
            await page.wait_for_load_state('domcontentloaded')

            # URL 확인
            current_url = page.url
            assert 'jobshistory' in current_url, f"Expected jobshistory URL, got: {current_url}"

            await page.screenshot(path='screenshots/test_CAREERSHOME_017_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_017_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
