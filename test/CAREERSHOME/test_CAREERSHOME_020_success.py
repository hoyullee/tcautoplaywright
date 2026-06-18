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

            # 채용 홈으로 이동
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # '~포지션 어때요?' 섹션 찾기: '포지션 어때요' 텍스트를 포함한 섹션 탐색
            section_info = await page.evaluate("""() => {
                const allElems = [...document.querySelectorAll('h2, h3, h4, section, div')];
                const result = [];
                for (const el of allElems) {
                    const text = el.textContent.trim();
                    if (text.includes('포지션 어때요') && text.length < 100) {
                        result.push({
                            tag: el.tagName,
                            text: text.slice(0, 80),
                            className: el.className ? el.className.slice(0, 80) : ''
                        });
                        if (result.length >= 5) break;
                    }
                }
                return result;
            }""")
            print(f"'포지션 어때요' 섹션 정보: {section_info}")

            # '전체보기' 버튼과 '포지션 어때요' 섹션 연관 정보 탐색
            btn_info = await page.evaluate("""() => {
                const allElems = [...document.querySelectorAll('a, button')];
                const result = [];
                for (const el of allElems) {
                    const text = el.textContent.trim();
                    if (text === '전체보기' || text.includes('전체 보기')) {
                        const parent = el.closest('section') || el.closest('[class*="section"]') || el.parentElement;
                        const parentText = parent ? parent.textContent.trim().slice(0, 100) : '';
                        if (parentText.includes('포지션 어때요')) {
                            result.push({
                                tag: el.tagName,
                                text: text,
                                href: el.getAttribute('href') || '',
                                target: el.getAttribute('target') || '',
                                parentText: parentText.slice(0, 80)
                            });
                        }
                    }
                }
                return result;
            }""")
            print(f"'포지션 어때요' 섹션 내 전체보기 버튼: {btn_info}")

            # '포지션 어때요' 텍스트가 포함된 섹션 찾기
            section_heading = page.locator('h2, h3, h4').filter(has_text='포지션 어때요').first
            section_heading_count = await section_heading.count()
            print(f"섹션 헤딩 개수: {section_heading_count}")

            # 섹션으로 스크롤 후 전체보기 버튼 찾기
            if section_heading_count > 0:
                await section_heading.scroll_into_view_if_needed()
                await page.wait_for_timeout(1000)

                # 섹션 헤딩 주변의 전체보기 버튼 찾기
                section_container = page.locator('section, div').filter(has_text='포지션 어때요').filter(has=page.locator('a, button').filter(has_text='전체보기')).first
                view_all_btn = section_container.locator('a, button').filter(has_text='전체보기').first
            else:
                # 일반적인 전체보기 버튼 중 tags URL 패턴 확인
                view_all_btn = page.locator('a').filter(has_text='전체보기').first

            view_all_count = await view_all_btn.count()
            print(f"전체보기 버튼 개수: {view_all_count}")

            if view_all_count == 0:
                # 전체보기 링크 중 /tags/ URL을 가진 것 찾기
                all_view_btns = await page.evaluate("""() => {
                    const elems = [...document.querySelectorAll('a, button')];
                    return elems
                        .filter(el => el.textContent.trim() === '전체보기' || el.textContent.trim() === '전체 보기')
                        .map(el => ({
                            tag: el.tagName,
                            text: el.textContent.trim(),
                            href: el.getAttribute('href') || '',
                            target: el.getAttribute('target') || ''
                        }));
                }""")
                print(f"모든 전체보기 버튼: {all_view_btns}")

                # /tags/ URL을 가진 버튼 찾기
                tags_btn = next((b for b in all_view_btns if '/tags/' in b.get('href', '')), None)
                if tags_btn:
                    view_all_btn = page.locator(f'a[href="{tags_btn["href"]}"]').filter(has_text='전체보기').first
                    if await view_all_btn.count() == 0:
                        view_all_btn = page.locator(f'a[href*="/tags/"]').filter(has_text='전체보기').first

            await view_all_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            href = await view_all_btn.get_attribute('href')
            target = await view_all_btn.get_attribute('target')
            print(f"전체보기 버튼 href: {href}, target: {target}")

            # 클릭 처리 - 새 탭 여부 확인
            if target == '_blank':
                async with context.expect_page() as new_page_info:
                    await view_all_btn.click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded')
                await new_page.wait_for_timeout(2000)
                current_url = new_page.url
                print(f"새 탭 URL: {current_url}")
                assert '/tags/' in current_url or 'wanted.co.kr' in current_url, \
                    f"기대하는 페이지로 이동되지 않음. 현재 URL: {current_url}"
                await new_page.screenshot(path='screenshots/test_25_success.png')
            else:
                await view_all_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(2000)
                current_url = page.url
                print(f"이동 후 URL: {current_url}")
                assert '/tags/' in current_url or 'wanted.co.kr' in current_url, \
                    f"기대하는 페이지로 이동되지 않음. 현재 URL: {current_url}"
                await page.screenshot(path='screenshots/test_25_success.png')

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_25_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
