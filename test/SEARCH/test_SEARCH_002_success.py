import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

SEARCH_TERM = "개발자"

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

            # 1. 채용 홈 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 2. GNB 검색 버튼 클릭 → 검색 화면 전환
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1000)

            # 3. 검색어 입력 텍스트박스에 임의 텍스트 입력
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            await search_input.fill(SEARCH_TERM)
            await page.wait_for_timeout(500)

            # 4. 검색 실행 (Enter)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 5. 검색 결과 페이지 URL 확인
            current_url = page.url
            assert 'search' in current_url.lower(), \
                f"검색 결과 페이지로 이동하지 않음. 현재 URL: {current_url}"
            print(f"✅ 검색 결과 페이지 랜딩 확인: {current_url}")

            # 6. 검색어 입력 항목(텍스트박스)에 입력 검색어 노출 확인
            # 검색 결과 페이지의 GNB 영역에 검색어가 span으로 표시됨
            search_keyword_span = page.locator('[class*="SearchKeywordText"]').first
            await search_keyword_span.wait_for(state='visible', timeout=10000)
            keyword_text = await search_keyword_span.inner_text()
            assert SEARCH_TERM in keyword_text, \
                f"검색어 입력 항목에 검색어가 노출되지 않음. 현재 텍스트: '{keyword_text}'"
            print(f"✅ 검색어 입력 항목에 입력 검색어 노출 확인: '{keyword_text}'")

            # 7. 탭 메뉴 노출 확인 (전체/포지션/회사/콘텐츠/소셜/프로필)
            # 검색 결과 탭은 tab 파라미터를 포함한 a 태그로 구성
            tab_map = {
                '전체': 'tab=overview',
                '포지션': 'tab=position',
                '회사': 'tab=company',
                '콘텐츠': 'tab=career',
                '소셜': 'tab=social',
                '프로필': 'tab=profile',
            }

            found_tabs = []
            for tab_name, tab_param in tab_map.items():
                tab_link = page.locator(f'a[href*="{tab_param}"]').first
                is_visible = await tab_link.is_visible()
                if is_visible:
                    found_tabs.append(tab_name)
                else:
                    # 텍스트로 fallback 확인
                    tab_text_el = page.get_by_text(tab_name, exact=False).first
                    if await tab_text_el.is_visible():
                        found_tabs.append(tab_name)

            missing_tabs = [t for t in tab_map.keys() if t not in found_tabs]
            assert len(missing_tabs) == 0, f"누락된 탭: {missing_tabs}"
            print(f"✅ 탭 메뉴 확인 완료 (전체/포지션/회사/콘텐츠/소셜/프로필): {found_tabs}")

            # 8. 전체(overview) 탭 기준 각 섹션 리스트 노출 확인
            # [class*="SectionContainer"] 로 각 섹션 영역 확인
            section_check = await page.evaluate("""(searchTerm) => {
                const containers = [...document.querySelectorAll('[class*="SectionContainer"]')];
                const result = {
                    position: false,
                    company: false,
                    content: false,
                    social: false,
                    profile: false,
                    details: []
                };

                containers.slice(0, 20).forEach(c => {
                    const text = c.innerText.trim();
                    const firstLine = text.split('\\n')[0] || '';
                    const detail = firstLine.substring(0, 50);

                    if (firstLine.includes('포지션')) result.position = true;
                    else if (firstLine.includes('회사')) result.company = true;
                    else if (firstLine.includes('콘텐츠')) result.content = true;
                    else if (firstLine.includes('소셜')) result.social = true;
                    else if (firstLine.includes('프로필')) result.profile = true;

                    if (detail) result.details.push(detail);
                });

                return result;
            }""", SEARCH_TERM)

            print(f"섹션 확인 결과: {section_check}")

            # 포지션 리스트 노출 확인
            assert section_check['position'], "포지션 섹션 리스트가 노출되지 않음"
            print("✅ 포지션 리스트 노출 확인")

            # 회사 리스트 노출 확인
            assert section_check['company'], "회사 섹션 리스트가 노출되지 않음"
            print("✅ 회사 리스트 노출 확인")

            # 콘텐츠 리스트 노출 확인
            assert section_check['content'], "콘텐츠 섹션 리스트가 노출되지 않음"
            print("✅ 콘텐츠 리스트 노출 확인")

            # 소셜 리스트 노출 확인
            assert section_check['social'], "소셜 섹션 리스트가 노출되지 않음"
            print("✅ 소셜 리스트 노출 확인")

            # 프로필 리스트 노출 확인
            assert section_check['profile'], "프로필 섹션 리스트가 노출되지 않음"
            print("✅ 프로필 리스트 노출 확인")

            await page.screenshot(path='screenshots/test_SEARCH_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_SEARCH_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
