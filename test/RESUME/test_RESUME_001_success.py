import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = ""
TEST_PASSWORD = ""

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 사전조건: 이력서 탭 진입 (로그인 상태)
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 확인사항 1: 내 이력서 리스트 확인
            current_url = page.url
            assert 'cv' in current_url, f"이력서 페이지가 아닙니다: {current_url}"

            # "새 이력서 작성" 버튼이 있는지 확인 (이력서 리스트 페이지 로드 검증)
            new_resume_btn = page.get_by_role('button', name='새 이력서 작성')
            await new_resume_btn.wait_for(state='visible', timeout=10000)
            print("내 이력서 리스트 페이지 확인 완료")

            # 확인사항 2: 새 이력서 작성 버튼 선택
            await new_resume_btn.click()
            await page.wait_for_load_state('domcontentloaded')

            # 기대결과: 이력서 작성 페이지로 이동 확인
            # URL이 /cv/list가 아닌 이력서 작성/편집 페이지로 변경되어야 함
            await page.wait_for_url(
                lambda url: '/cv/' in url and '/list' not in url,
                timeout=15000
            )
            final_url = page.url
            print(f"이력서 작성 페이지로 이동 완료: {final_url}")

            assert '/cv/' in final_url and '/list' not in final_url, \
                f"이력서 작성 페이지로 이동하지 않았습니다. 현재 URL: {final_url}"

            await page.screenshot(path='screenshots/test_RESUME_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
