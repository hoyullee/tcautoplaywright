import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 1. '출퇴근 걱정없는 역세권 포지션' 섹션 찾기
            section_title = page.get_by_text('출퇴근 걱정없는 역세권 포지션', exact=True)
            await section_title.wait_for(state='visible', timeout=15000)
            assert await section_title.is_visible(), "'출퇴근 걱정없는 역세권 포지션' 텍스트가 보이지 않습니다"
            print("[OK] '출퇴근 걱정없는 역세권 포지션' 섹션 확인")

            # 섹션으로 스크롤
            await section_title.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            # 2. 섹션 내 '지도로 공고 찾기' 버튼 찾기
            # 먼저 evaluate로 버튼 정보 수집
            btn_info = await page.evaluate("""() => {
                const headings = document.querySelectorAll('h2, h3, h4, strong, span, p, div');
                for (const heading of headings) {
                    if (heading.textContent && heading.textContent.trim() === '출퇴근 걱정없는 역세권 포지션') {
                        let parent = heading.parentElement;
                        for (let i = 0; i < 10; i++) {
                            if (!parent) break;
                            const buttons = parent.querySelectorAll('button, a');
                            for (const btn of buttons) {
                                const text = btn.textContent && btn.textContent.trim();
                                if (text && text.includes('지도로 공고 찾기')) {
                                    return {
                                        found: true,
                                        tag: btn.tagName,
                                        href: btn.getAttribute('href'),
                                        text: text
                                    };
                                }
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
                return { found: false };
            }""")
            print(f"Button info: {btn_info}")

            map_btn = None

            if btn_info.get('found'):
                href = btn_info.get('href')
                tag = btn_info.get('tag', '').lower()
                if href:
                    map_btn = page.locator(f'a[href="{href}"]').first
                    print(f"[OK] '지도로 공고 찾기' 링크 발견 (href: {href})")
                else:
                    # href 없는 버튼인 경우
                    map_btn = page.get_by_role('button', name='지도로 공고 찾기')
                    if await map_btn.count() == 0:
                        map_btn = page.get_by_text('지도로 공고 찾기', exact=True)
                    print("[OK] '지도로 공고 찾기' 버튼 발견")
            else:
                # 방법 2: 섹션 컨테이너 내에서 탐색
                section_container = page.locator('section, div').filter(
                    has=page.get_by_text('출퇴근 걱정없는 역세권 포지션', exact=True)
                ).first

                btn_candidate = section_container.get_by_role('link', name='지도로 공고 찾기')
                if await btn_candidate.count() > 0:
                    map_btn = btn_candidate.first
                    print("[OK] '지도로 공고 찾기' 버튼 발견 (섹션 컨테이너 내)")
                else:
                    btn_candidate2 = section_container.get_by_role('button', name='지도로 공고 찾기')
                    if await btn_candidate2.count() > 0:
                        map_btn = btn_candidate2.first
                        print("[OK] '지도로 공고 찾기' 버튼 발견 (섹션 컨테이너 내, button role)")
                    else:
                        # 방법 3: 페이지 전체에서 '지도로 공고 찾기' 텍스트 링크/버튼 찾기
                        all_links = page.get_by_text('지도로 공고 찾기')
                        count = await all_links.count()
                        print(f"Found {count} '지도로 공고 찾기' elements total")
                        if count > 0:
                            map_btn = all_links.first

            assert map_btn is not None, "'지도로 공고 찾기' 버튼을 찾을 수 없습니다"

            # 3. '지도로 공고 찾기' 버튼 클릭 - 새 탭 열릴 수도 있으므로 처리
            await map_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 새 탭 열릴 경우 대비
            async with context.expect_page() as new_page_info:
                await map_btn.click()
                try:
                    new_page = await new_page_info.value
                    await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                    new_url = new_page.url
                    print(f"[NEW TAB] Navigated to: {new_url}")
                    page = new_page  # 스크린샷을 위해 page 교체
                except Exception:
                    # 새 탭이 안 열린 경우 현재 페이지에서 확인
                    await page.wait_for_load_state('domcontentloaded', timeout=30000)
                    new_url = page.url
                    print(f"[SAME TAB] Navigated to: {new_url}")

            # 4. 포지션맵 페이지 이동 확인
            print(f"Final URL: {new_url}")
            assert 'position-map' in new_url, f"'포지션맵' 페이지로 이동되지 않았습니다. URL: {new_url}"
            print("[OK] '포지션맵' 페이지로 이동 확인")

            page_title = await page.title()
            print(f"Page title: {page_title}")

            await page.screenshot(path='screenshots/test_12_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_12_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
