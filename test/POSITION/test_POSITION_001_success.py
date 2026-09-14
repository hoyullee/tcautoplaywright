import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"
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

            # 탐색 페이지로 이동하여 포지션 카드 선택
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)  # 검증 대상이 아닌 팝업 정리

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"Found position card with href: {href}")

            # 포지션 상세 페이지로 직접 이동
            position_url = f'https://www.wanted.co.kr{href}'
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            print(f"Navigated to position detail page: {position_url}")

            # '포지션 상세' 섹션 확인 (텍스트 형식으로 노출)
            position_detail_found = False

            # 방법 1: '포지션 상세' 텍스트 직접 탐색
            try:
                detail_header = page.get_by_text('포지션 상세', exact=False)
                await detail_header.first.wait_for(state='visible', timeout=5000)
                print("Found '포지션 상세' text")
                position_detail_found = True
            except Exception:
                print("'포지션 상세' text not found directly")

            if not position_detail_found:
                # 방법 2: 주요업무 텍스트가 있는 섹션 확인 (포지션 상세 내용)
                try:
                    content = page.locator('p, div, section').filter(has_text='주요업무').first
                    await content.wait_for(state='visible', timeout=5000)
                    print("Found position detail content with '주요업무'")
                    position_detail_found = True
                except Exception:
                    pass

            if not position_detail_found:
                # 방법 3: JobDescription 관련 클래스 탐색
                try:
                    job_section = page.locator('[class*="JobDescription"]').first
                    await job_section.wait_for(state='visible', timeout=5000)
                    print("Found JobDescription section")
                    position_detail_found = True
                except Exception:
                    pass

            assert position_detail_found, "포지션 상세 섹션(텍스트 형식)을 찾을 수 없습니다"

            # '상세 정보 더 보기' 버튼 확인
            more_info_found = False

            # 방법 1: 버튼 role로 찾기
            try:
                btn = page.get_by_role('button', name='상세 정보 더 보기')
                await btn.wait_for(state='visible', timeout=5000)
                print("Found '상세 정보 더 보기' button by role")
                more_info_found = True
            except Exception:
                pass

            if not more_info_found:
                # 방법 2: 텍스트로 찾기
                try:
                    btn = page.get_by_text('상세 정보 더 보기').first
                    await btn.wait_for(state='visible', timeout=5000)
                    print("Found '상세 정보 더 보기' by text")
                    more_info_found = True
                except Exception:
                    pass

            if not more_info_found:
                # 방법 3: 스크롤 후 재탐색
                await page.evaluate('window.scrollBy(0, 800)')
                await page.wait_for_timeout(1000)
                try:
                    btn = page.get_by_text('상세 정보 더 보기').first
                    await btn.wait_for(state='visible', timeout=5000)
                    print("Found '상세 정보 더 보기' after scrolling")
                    more_info_found = True
                except Exception:
                    pass

            assert more_info_found, "'상세 정보 더 보기' 버튼을 찾을 수 없습니다"

            await page.screenshot(path='screenshots/test_POSITION_001_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_001_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
