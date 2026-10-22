import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups, poll_until
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

            # 1. '포지션 상세' 섹션 확인
            position_detail_found = False

            try:
                detail_header = page.get_by_text('포지션 상세', exact=False)
                await detail_header.first.wait_for(state='visible', timeout=5000)
                print("Found '포지션 상세' text")
                position_detail_found = True
            except Exception:
                print("'포지션 상세' text not found directly")

            if not position_detail_found:
                try:
                    job_section = page.locator('[class*="JobDescription"]').first
                    await job_section.wait_for(state='visible', timeout=5000)
                    print("Found JobDescription section")
                    position_detail_found = True
                except Exception:
                    pass

            if not position_detail_found:
                try:
                    content = page.locator('p, div, section').filter(has_text='주요업무').first
                    await content.wait_for(state='visible', timeout=5000)
                    print("Found position detail content with '주요업무'")
                    position_detail_found = True
                except Exception:
                    pass

            assert position_detail_found, "포지션 상세 섹션을 찾을 수 없습니다"

            # 2. '상세 정보 더 보기' 버튼 찾기 (스크롤 후 탐색)
            await page.evaluate('window.scrollBy(0, 600)')
            await page.wait_for_timeout(800)

            btn = None

            # 방법 1: role로 찾기
            try:
                btn_candidate = page.get_by_role('button', name='상세 정보 더 보기')
                await btn_candidate.wait_for(state='visible', timeout=5000)
                btn = btn_candidate
                print("Found '상세 정보 더 보기' button by role")
            except Exception:
                pass

            # 방법 2: 텍스트로 찾기
            if btn is None:
                try:
                    btn_candidate = page.get_by_text('상세 정보 더 보기').first
                    await btn_candidate.wait_for(state='visible', timeout=5000)
                    btn = btn_candidate
                    print("Found '상세 정보 더 보기' by text")
                except Exception:
                    pass

            # 방법 3: CSS 셀렉터로 찾기
            if btn is None:
                await page.evaluate('window.scrollBy(0, 600)')
                await page.wait_for_timeout(800)
                try:
                    btn_candidate = page.locator('button:has-text("상세 정보 더 보기")').first
                    await btn_candidate.wait_for(state='visible', timeout=5000)
                    btn = btn_candidate
                    print("Found '상세 정보 더 보기' by CSS selector")
                except Exception:
                    pass

            assert btn is not None, "'상세 정보 더 보기' 버튼을 찾을 수 없습니다"

            # 버튼 클릭 전 현재 콘텐츠 높이 측정
            content_height_before = await page.evaluate("""() => {
                const detailSection = document.querySelector('[class*="JobDescription"]') ||
                                      document.querySelector('[class*="content"]') ||
                                      document.querySelector('main');
                return detailSection ? detailSection.scrollHeight : document.body.scrollHeight;
            }""")
            print(f"Content height before click: {content_height_before}")

            # '상세 정보 더 보기' 버튼 클릭
            await btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            await btn.click()
            print("Clicked '상세 정보 더 보기' button")

            # 클릭 후 추가 내용 노출 확인
            # 공고마다 확장 애니메이션/렌더링 속도가 달라 고정 시간 한 번만 보고
            # 판정하면(예: 1.5초 대기 후 단발 확인) 느린 공고에서 재시도가 발생한다.
            # 조건이 만족되는 즉시 끝나고, 느릴 때는 timeout 안에서 반복 확인한다.
            async def check_expanded():
                # 방법 1: 버튼이 사라지거나 변경되었는지 확인
                btn_text_after = page.get_by_text('상세 정보 더 보기')
                if await btn_text_after.count() == 0:
                    print("Button disappeared - content expanded")
                    return True

                # 방법 2: 콘텐츠 높이가 증가했는지 확인
                content_height_after = await page.evaluate("""() => {
                    const detailSection = document.querySelector('[class*="JobDescription"]') ||
                                          document.querySelector('[class*="content"]') ||
                                          document.querySelector('main');
                    return detailSection ? detailSection.scrollHeight : document.body.scrollHeight;
                }""")
                if content_height_after > content_height_before:
                    print(f"Content height increased - additional content is displayed ({content_height_after})")
                    return True

                # 방법 3: 페이지 전체 높이 증가 확인
                page_height_after = await page.evaluate('document.body.scrollHeight')
                if page_height_after > content_height_before:
                    print("Page height increased after click")
                    return True

                # 방법 4: '접기' 또는 '간략히' 버튼 등 토글 버튼이 나타났는지 확인
                collapse_btn = page.get_by_role('button', name='접기')
                if await collapse_btn.count() > 0:
                    print("Found '접기' button - content expanded")
                    return True

                return False

            content_expanded = await poll_until(check_expanded, timeout=5000, interval=300)
            assert content_expanded, "버튼 클릭 후 포지션 상세 내용이 추가 노출되지 않았습니다"
            print("AUTOMATION_SUCCESS: 포지션 상세 내용 추가 노출 확인 완료")

            await page.screenshot(path='screenshots/test_POSITION_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
