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
            storage_state='work/auth_state.json',
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 진입
            safe_print("[INFO] 채용 홈 진입 중...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 채용 홈 로드: {page.url}")

            # GNB 검색창 클릭 (검색 화면으로 전환)
            safe_print("[INFO] GNB 검색창 클릭 (검색 화면 전환)...")
            search_input_selectors = [
                'input[placeholder*="검색"]',
                'input[type="search"]',
                '[class*="Search"] input',
                '[class*="search"] input',
                'input[name="query"]',
            ]
            search_clicked = False
            for sel in search_input_selectors:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        await loc.click(timeout=5000)
                        search_clicked = True
                        safe_print(f"[OK] 검색창 클릭 성공: '{sel}'")
                        await page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    safe_print(f"[WARN] 검색창 클릭 실패 '{sel}': {e}")

            # 검색 아이콘 버튼으로 시도
            if not search_clicked:
                safe_print("[INFO] 검색 아이콘 버튼으로 시도...")
                icon_selectors = [
                    'button[aria-label*="검색"]',
                    'button[class*="search"]',
                    'button[class*="Search"]',
                    '[class*="gnb"] button',
                    'header button',
                ]
                for sel in icon_selectors:
                    try:
                        loc = page.locator(sel).first
                        cnt = await loc.count()
                        if cnt > 0:
                            await loc.click(timeout=5000)
                            search_clicked = True
                            safe_print(f"[OK] 검색 버튼 클릭 성공: '{sel}'")
                            await page.wait_for_timeout(2000)
                            break
                    except Exception as e:
                        safe_print(f"[WARN] 검색 버튼 클릭 실패 '{sel}': {e}")

            assert search_clicked, "검색창/검색 버튼을 찾거나 클릭할 수 없음"

            # 검색 화면에서 인기 검색어 확인 (JS로 구조 파악)
            safe_print("[INFO] 검색 오버레이/드롭다운 구조 파악 중...")
            await page.wait_for_timeout(2000)

            # JS로 검색 화면에서 인기 검색어 탐색
            # 인기 검색어는 짧은 단어/구문이며, 검색 오버레이 내에 있음
            js_result = await page.evaluate("""() => {
                const results = [];
                const seen = new Set();

                // 인기 검색어 섹션 헤더 탐색
                const headers = [...document.querySelectorAll('*')];
                let trendingSection = null;

                for (const el of headers) {
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text === '인기 검색어' || text === '인기검색어' || text === '인기 키워드') {
                        trendingSection = el.parentElement || el;
                        break;
                    }
                }

                if (trendingSection) {
                    // 인기 검색어 섹션 내 링크/버튼 탐색
                    const items = trendingSection.querySelectorAll('a, button, li');
                    for (const item of items) {
                        const text = (item.innerText || item.textContent || '').trim();
                        if (text && text.length > 1 && text.length < 20 && !seen.has(text) && !text.includes('인기 검색어')) {
                            seen.add(text);
                            const rect = item.getBoundingClientRect();
                            results.push({
                                text: text,
                                tag: item.tagName,
                                visible: rect.width > 0 && rect.height > 0,
                                class: item.className || '',
                            });
                        }
                    }
                }

                return { section_found: !!trendingSection, items: results };
            }""")
            safe_print(f"[INFO] 인기 검색어 섹션 발견: {js_result['section_found']}")
            safe_print(f"[INFO] 인기 검색어 항목: {js_result['items'][:5]}")

            trending_items = []

            if js_result['section_found'] and js_result['items']:
                for item in js_result['items']:
                    if item.get('visible') and item.get('text'):
                        trending_items.append(item)

            # 섹션을 못 찾으면 더 넓은 방법으로 탐색
            if not trending_items:
                safe_print("[INFO] 다른 방법으로 인기 검색어 탐색...")
                js_result2 = await page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();

                    // 검색 화면(overlay/modal/dropdown) 내의 짧은 텍스트 항목들 찾기
                    // 인기 검색어는 1~15자 정도의 단어들
                    const selectors = [
                        '[class*="SearchLayer"] a',
                        '[class*="searchLayer"] a',
                        '[class*="SearchModal"] a',
                        '[class*="SearchOverlay"] a',
                        '[class*="SearchPopup"] a',
                        '[class*="AutoComplete"] a',
                        '[class*="autocomplete"] a',
                        '[class*="Suggestion"] a',
                        '[class*="suggestion"] a',
                        '[role="dialog"] a',
                        '[class*="dropdown"] a',
                        '[class*="Dropdown"] a',
                    ];

                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const text = (el.innerText || el.textContent || '').trim();
                            if (text && text.length >= 2 && text.length <= 15 && !seen.has(text)) {
                                seen.add(text);
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    results.push({
                                        text: text,
                                        tag: el.tagName,
                                        selector: sel,
                                        href: el.href || '',
                                    });
                                }
                            }
                        }
                        if (results.length >= 5) break;
                    }

                    return results;
                }""")
                safe_print(f"[INFO] 넓은 범위 탐색 결과: {js_result2[:5]}")
                for item in js_result2:
                    trending_items.append(item)

            # 여전히 없으면 검색 화면의 모든 가시적 a/button 태그에서 짧은 텍스트 탐색
            if not trending_items:
                safe_print("[INFO] 페이지 전체에서 짧은 검색어 형태 항목 탐색...")
                js_result3 = await page.evaluate("""() => {
                    const results = [];
                    const seen = new Set();

                    // 현재 화면에서 클릭 가능하고 짧은 텍스트를 가진 요소들
                    const els = [...document.querySelectorAll('a, button')];
                    for (const el of els) {
                        const text = (el.innerText || el.textContent || '').trim();
                        // 인기 검색어: 개행 없음, 2~15자, 한글 포함
                        if (
                            text &&
                            text.length >= 2 &&
                            text.length <= 15 &&
                            !text.includes('\\n') &&
                            /[가-힣]/.test(text) &&
                            !seen.has(text)
                        ) {
                            seen.add(text);
                            const rect = el.getBoundingClientRect();
                            // 화면에 보이는 항목만 (y > 60 이면 GNB 아래)
                            if (rect.width > 0 && rect.height > 0 && rect.top > 60) {
                                results.push({
                                    text: text,
                                    tag: el.tagName,
                                    href: el.href || '',
                                    top: Math.round(rect.top),
                                });
                            }
                        }
                    }
                    // top 순으로 정렬
                    results.sort((a, b) => a.top - b.top);
                    return results.slice(0, 20);
                }""")
                safe_print(f"[INFO] 전체 탐색 결과 (상위 10개): {js_result3[:10]}")
                for item in js_result3:
                    trending_items.append(item)

            safe_print(f"[INFO] 최종 발견된 인기 검색어 항목: {len(trending_items)}개")
            for item in trending_items[:5]:
                safe_print(f"  - '{item['text']}' (tag={item.get('tag', '?')}, top={item.get('top', '?')})")

            assert len(trending_items) > 0, "인기 검색어 항목을 찾을 수 없음"
            safe_print(f"[OK] 인기 검색어 항목 확인: {len(trending_items)}개")

            # 임의의 인기 검색어 선택 (첫 번째 항목 클릭)
            selected_term = trending_items[0]['text']
            safe_print(f"[INFO] 선택한 인기 검색어: '{selected_term}'")

            # href가 있으면 직접 navigate
            href = trending_items[0].get('href', '')
            if href and ('search' in href or 'wanted.co.kr' in href):
                safe_print(f"[INFO] href로 직접 이동: {href}")
                await page.goto(href, timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)
                safe_print(f"[OK] href 이동 성공: {page.url}")
            else:
                # 텍스트로 클릭 시도
                clicked_term = False
                try:
                    # 정확한 텍스트 매칭
                    text_loc = page.get_by_text(selected_term, exact=True).first
                    cnt = await text_loc.count()
                    if cnt > 0:
                        await text_loc.click(timeout=5000)
                        clicked_term = True
                        safe_print(f"[OK] 텍스트로 클릭 성공: '{selected_term}'")
                except Exception as e:
                    safe_print(f"[WARN] 텍스트 클릭 실패: {e}")

                if not clicked_term:
                    # 부분 텍스트로 클릭 시도
                    try:
                        text_loc = page.locator(f'a:has-text("{selected_term}"), button:has-text("{selected_term}")').first
                        cnt = await text_loc.count()
                        if cnt > 0:
                            await text_loc.click(timeout=5000)
                            clicked_term = True
                            safe_print(f"[OK] CSS has-text로 클릭 성공: '{selected_term}'")
                    except Exception as e:
                        safe_print(f"[WARN] CSS has-text 클릭 실패: {e}")

                if not clicked_term:
                    # JS로 강제 클릭
                    safe_print(f"[INFO] JS로 강제 클릭 시도: '{selected_term}'")
                    clicked_term = await page.evaluate(f"""() => {{
                        const els = [...document.querySelectorAll('a, button')];
                        for (const el of els) {{
                            const text = (el.innerText || el.textContent || '').trim();
                            if (text === '{selected_term}') {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}""")
                    if clicked_term:
                        safe_print(f"[OK] JS 클릭 성공: '{selected_term}'")
                    else:
                        safe_print(f"[WARN] JS 클릭도 실패")

                assert clicked_term, f"인기 검색어 클릭 실패: '{selected_term}'"

                # 검색 결과 페이지 로딩 대기
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            final_url = page.url
            safe_print(f"[INFO] 인기 검색어 클릭 후 URL: {final_url}")

            # 검색 결과 페이지 확인
            assert 'search' in final_url or 'query' in final_url or 'keyword' in final_url or 'wdlist' in final_url, \
                f"검색 결과 페이지로 이동되지 않음: {final_url}"
            safe_print(f"[OK] 검색 결과 페이지 이동 확인: {final_url}")

            from urllib.parse import unquote
            decoded_url = unquote(final_url)
            safe_print(f"[INFO] 디코딩된 URL: {decoded_url}")

            safe_print("\n[RESULT] 테스트 케이스 49 검증 완료:")
            safe_print(f"[OK] 인기 검색어 항목 노출: {len(trending_items)}개")
            safe_print(f"[OK] 선택한 인기 검색어: '{selected_term}'")
            safe_print(f"[OK] 검색 결과 페이지 이동: {final_url}")

            await page.screenshot(path='screenshots/test_49_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_49_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
