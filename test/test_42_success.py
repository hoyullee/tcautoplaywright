import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

def safe_print(msg):
    try:
        print(msg)
    except Exception:
        print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 비로그인 상태로 채용 홈 진입
            safe_print("[INFO] 채용 홈 접속 중...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 채용 홈 로드: {page.url}")

            # GNB 검색 버튼 찾기 및 클릭
            safe_print("[INFO] GNB 검색 버튼 탐색 중...")

            # JS로 검색 버튼 구조 파악
            search_btn_info = await page.evaluate("""() => {
                const candidates = [...document.querySelectorAll('button, a, [role="button"]')];
                return candidates
                    .filter(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        const label = el.getAttribute('aria-label') || '';
                        const cls = el.className || '';
                        return (
                            text === '검색' ||
                            label.includes('검색') ||
                            cls.includes('search') ||
                            cls.includes('Search')
                        );
                    })
                    .slice(0, 10)
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName,
                            text: (el.innerText || el.textContent || '').trim().substring(0, 50),
                            label: el.getAttribute('aria-label') || '',
                            classes: el.className.substring(0, 100),
                            visible: rect.width > 0 && rect.height > 0,
                        };
                    });
            }""")
            safe_print(f"[INFO] 검색 버튼 후보: {search_btn_info}")

            # 검색 버튼 클릭 시도
            clicked = False
            search_selectors = [
                'button[aria-label="검색"]',
                'a[aria-label="검색"]',
                '[aria-label="검색"]',
                'button:has-text("검색")',
                '[class*="SearchButton"]',
                '[class*="searchButton"]',
                '[class*="search_btn"]',
                'header [class*="search"]',
                'nav [class*="search"]',
            ]

            for sel in search_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        await loc.click()
                        clicked = True
                        safe_print(f"[OK] 검색 버튼 클릭: '{sel}'")
                        break
                except Exception as e:
                    safe_print(f"[WARN] selector '{sel}' 실패: {e}")

            if not clicked:
                # get_by_role 시도
                try:
                    btn = page.get_by_role('button', name='검색')
                    if await btn.count() > 0:
                        await btn.first.click()
                        clicked = True
                        safe_print("[OK] get_by_role로 검색 버튼 클릭")
                except Exception as e:
                    safe_print(f"[WARN] get_by_role 실패: {e}")

            if not clicked:
                raise Exception("GNB 검색 버튼을 찾을 수 없음")

            # 검색 화면 전환 대기
            await page.wait_for_timeout(2000)

            # 현재 상태 파악
            current_url = page.url
            safe_print(f"[INFO] 클릭 후 URL: {current_url}")

            # 1. 검색어 입력 텍스트 박스 확인
            safe_print("[INFO] 검색어 입력 항목 확인 중...")

            input_info = await page.evaluate("""() => {
                const inputs = [...document.querySelectorAll('input')];
                return inputs
                    .filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    })
                    .map(el => ({
                        type: el.type,
                        placeholder: el.placeholder,
                        classes: el.className.substring(0, 100),
                        name: el.name,
                        visible: true,
                    }));
            }""")
            safe_print(f"[INFO] 가시적인 input 목록: {input_info}")

            # 검색 입력 필드 찾기
            search_input_found = False
            input_selectors = [
                'input[type="search"]',
                'input[placeholder*="검색"]',
                'input[name*="search"]',
                'input[class*="search"]',
                'input[class*="Search"]',
                'input[type="text"]',
            ]
            for sel in input_selectors:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible():
                    search_input_found = True
                    safe_print(f"[OK] 검색 입력 필드 발견: '{sel}'")
                    break

            if not search_input_found:
                try:
                    sb = page.get_by_role('searchbox')
                    if await sb.count() > 0 and await sb.is_visible():
                        search_input_found = True
                        safe_print("[OK] searchbox role로 발견")
                except Exception:
                    pass

            if not search_input_found:
                try:
                    tb = page.get_by_role('textbox')
                    if await tb.count() > 0 and await tb.first.is_visible():
                        search_input_found = True
                        safe_print("[OK] textbox role로 발견")
                except Exception:
                    pass

            assert search_input_found, "검색어 입력 텍스트 박스가 노출되지 않음"

            # 2. 인기 검색어 1위~8위 버튼 확인
            safe_print("[INFO] 인기 검색어 확인 중...")

            # JS로 인기 검색어 구조 파악
            popular_info = await page.evaluate("""() => {
                // 인기 검색어 관련 요소 찾기
                const allEls = [...document.querySelectorAll('*')];
                const popularEls = allEls.filter(el => {
                    const cls = (el.className || '').toString();
                    const text = (el.innerText || el.textContent || '').trim();
                    return (
                        cls.includes('popular') ||
                        cls.includes('Popular') ||
                        cls.includes('rank') ||
                        cls.includes('Rank') ||
                        cls.includes('keyword') ||
                        cls.includes('Keyword') ||
                        cls.includes('trending') ||
                        cls.includes('hot') ||
                        text.includes('인기 검색어') ||
                        text.includes('인기검색어') ||
                        text.includes('인기 키워드')
                    );
                });

                // 버튼이나 클릭 가능한 인기 검색어 항목 찾기
                const clickable = [...document.querySelectorAll('button, a, li')].filter(el => {
                    const cls = (el.className || '').toString();
                    const parentCls = el.parentElement ? (el.parentElement.className || '').toString() : '';
                    const rect = el.getBoundingClientRect();
                    return (
                        rect.width > 0 && rect.height > 0 &&
                        (
                            cls.includes('popular') || cls.includes('Popular') ||
                            cls.includes('keyword') || cls.includes('Keyword') ||
                            cls.includes('rank') || cls.includes('Rank') ||
                            cls.includes('trending') || cls.includes('hot') ||
                            parentCls.includes('popular') || parentCls.includes('keyword') ||
                            parentCls.includes('rank') || parentCls.includes('trending')
                        )
                    );
                });

                return {
                    popularElCount: popularEls.slice(0, 5).map(el => ({
                        tag: el.tagName,
                        cls: (el.className || '').toString().substring(0, 80),
                        text: (el.innerText || '').trim().substring(0, 50),
                    })),
                    clickableCount: clickable.length,
                    clickableSample: clickable.slice(0, 10).map(el => ({
                        tag: el.tagName,
                        text: (el.innerText || el.textContent || '').trim().substring(0, 30),
                        cls: (el.className || '').toString().substring(0, 80),
                    })),
                };
            }""")
            safe_print(f"[INFO] 인기 검색어 정보: {popular_info}")

            # 인기 검색어 항목 수 확인
            popular_clickable_count = popular_info.get('clickableCount', 0)

            # Playwright 선택자로도 확인
            playwright_popular_count = 0
            popular_pw_selectors = [
                '[class*="popular"] button',
                '[class*="Popular"] button',
                '[class*="popular"] li',
                '[class*="Popular"] li',
                '[class*="keyword"] li',
                '[class*="Keyword"] li',
                '[class*="rank"] li',
                '[class*="Rank"] li',
                '[class*="trending"] li',
                '[class*="trending"] button',
                '[class*="hot"] button',
                '[class*="hot"] li',
            ]
            for sel in popular_pw_selectors:
                cnt = await page.locator(sel).count()
                if cnt > playwright_popular_count:
                    playwright_popular_count = cnt
                    safe_print(f"[INFO] '{sel}': {cnt}개")

            safe_print(f"[INFO] 인기 검색어 JS 기반 클릭 가능 수: {popular_clickable_count}")
            safe_print(f"[INFO] 인기 검색어 Playwright 기반 최대 수: {playwright_popular_count}")

            # URL이 검색 페이지로 이동했는지도 확인
            if 'search' in current_url:
                safe_print(f"[INFO] 검색 페이지 URL로 전환: {current_url}")

            final_count = max(popular_clickable_count, playwright_popular_count)

            if final_count < 8:
                # 페이지 전체 텍스트에서 인기 검색어 단서 찾기
                body_text = await page.inner_text('body')
                safe_print(f"[INFO] Body 텍스트 일부: {body_text[:500]}")

                # 가시적인 모든 li 개수
                all_li = await page.locator('li:visible').count()
                safe_print(f"[INFO] 가시적인 li 수: {all_li}")

                # 가시적인 모든 button 개수
                all_btn = await page.locator('button:visible').count()
                safe_print(f"[INFO] 가시적인 button 수: {all_btn}")

            assert final_count >= 8, \
                f"인기 검색어 1위~8위 버튼이 충분히 노출되지 않음 (발견된 수: {final_count})"

            safe_print(f"[OK] 인기 검색어 {final_count}개 확인 완료")

            await page.screenshot(path='screenshots/test_42_success.png')
            safe_print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_42_failed.png')
            safe_print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
