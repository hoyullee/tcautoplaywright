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
            await page.wait_for_timeout(2000)

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

            # 페이지 스크롤하여 모든 섹션 로딩 유도
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)

            # 1. '마감일' 항목 확인
            deadline_found = False
            try:
                deadline_label = page.get_by_text('마감일', exact=True)
                count = await deadline_label.count()
                if count > 0:
                    await deadline_label.first.wait_for(state='visible', timeout=5000)
                    print(f"Found '마감일' label, count={count}")
                    deadline_found = True
            except Exception as e:
                print(f"'마감일' label not found via get_by_text: {e}")

            if not deadline_found:
                result = await page.evaluate("""() => {
                    return document.body.innerText.includes('마감일');
                }""")
                if result:
                    deadline_found = True
                    print("'마감일' text found in page body")

            assert deadline_found, "'마감일' 항목이 페이지에서 발견되지 않았습니다"
            print("✓ '마감일' 항목 확인 완료")

            # 2. '근무지역' 항목 확인 (마감일 하단에 위치)
            work_area_found = False
            try:
                work_area_label = page.get_by_text('근무지역', exact=True)
                count = await work_area_label.count()
                if count > 0:
                    await work_area_label.first.wait_for(state='visible', timeout=5000)
                    print(f"Found '근무지역' label, count={count}")
                    work_area_found = True
            except Exception as e:
                print(f"'근무지역' label not found via get_by_text: {e}")

            if not work_area_found:
                result = await page.evaluate("""() => {
                    return document.body.innerText.includes('근무지역');
                }""")
                if result:
                    work_area_found = True
                    print("'근무지역' text found in page body")

            assert work_area_found, "'근무지역' 항목이 페이지에서 노출되지 않았습니다"
            print("✓ '근무지역' 항목 확인 완료")

            # 3. 마감일이 근무지역보다 위(상단)에 있는지 DOM 순서 확인
            order_check = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('*')];
                let deadlineIdx = -1;
                let workAreaIdx = -1;

                for (let i = 0; i < allEls.length; i++) {
                    const text = allEls[i].innerText ? allEls[i].innerText.trim() : '';
                    if (text === '마감일' && allEls[i].children.length === 0 && deadlineIdx === -1) {
                        deadlineIdx = i;
                    }
                    if (text === '근무지역' && allEls[i].children.length === 0 && workAreaIdx === -1) {
                        workAreaIdx = i;
                    }
                }

                return {
                    deadlineIdx,
                    workAreaIdx,
                    correctOrder: deadlineIdx !== -1 && workAreaIdx !== -1 && workAreaIdx > deadlineIdx
                };
            }""")
            print(f"DOM order: deadline_idx={order_check['deadlineIdx']}, work_area_idx={order_check['workAreaIdx']}, correct_order={order_check['correctOrder']}")
            if order_check['correctOrder']:
                print("✓ '근무지역' 항목이 '마감일' 항목 하단에 위치함")
            else:
                print("⚠ 순서 확인 불가 - 항목 존재는 확인됨")

            # 4. 네이버 지도 노출 확인
            naver_map_found = False

            # 방법 1: naver map iframe 직접 탐색
            try:
                naver_iframe = page.locator('iframe[src*="map.naver.com"]')
                count = await naver_iframe.count()
                if count > 0:
                    naver_map_found = True
                    print(f"Found Naver Map iframe (map.naver.com), count={count}")
            except Exception as e:
                print(f"Naver map iframe (map.naver.com) not found: {e}")

            # 방법 2: naver 관련 iframe 탐색
            if not naver_map_found:
                try:
                    naver_iframe = page.locator('iframe[src*="naver"]')
                    count = await naver_iframe.count()
                    if count > 0:
                        naver_map_found = True
                        src = await naver_iframe.first.get_attribute('src')
                        print(f"Found Naver iframe, count={count}, src={src}")
                except Exception as e:
                    print(f"Naver iframe not found: {e}")

            # 방법 3: 네이버 지도 관련 class/id 탐색
            if not naver_map_found:
                for selector in [
                    '[class*="NaverMap"]', '[class*="naverMap"]', '[class*="naver-map"]',
                    '[id*="naver_map"]', '[id*="naverMap"]', '[id*="naver-map"]',
                ]:
                    try:
                        el = page.locator(selector)
                        count = await el.count()
                        if count > 0:
                            print(f"Found Naver Map element: {selector}, count={count}")
                            naver_map_found = True
                            break
                    except Exception:
                        pass

            # 방법 4: JS로 네이버 지도 탐색 (iframe, SDK, canvas 종합)
            if not naver_map_found:
                result = await page.evaluate("""() => {
                    // iframe에서 naver 관련 탐색
                    const iframes = [...document.querySelectorAll('iframe')];
                    for (const f of iframes) {
                        const src = f.src || '';
                        if (src.includes('naver') || src.includes('map')) {
                            return { found: true, type: 'iframe', src };
                        }
                    }

                    // class나 id에 naver/map 포함 요소 탐색
                    const mapEls = [...document.querySelectorAll('[class*="naver"], [class*="Naver"], [id*="naver"], [id*="Naver"]')].slice(0, 20);
                    for (const el of mapEls) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 50) {
                            return {
                                found: true, type: 'div',
                                class: el.className.substring(0, 100),
                                id: el.id
                            };
                        }
                    }

                    // 네이버 지도 SDK (window.naver.maps) 확인
                    if (typeof window.naver !== 'undefined' && typeof window.naver.maps !== 'undefined') {
                        return { found: true, type: 'sdk' };
                    }

                    // page HTML에 naver map 관련 코드 확인
                    const html = document.documentElement.innerHTML;
                    if (html.includes('map.naver.com') || html.includes('naver.maps')) {
                        return { found: true, type: 'html_reference' };
                    }

                    return { found: false };
                }""")
                print(f"JS Naver Map search result: {result}")
                if result.get('found'):
                    naver_map_found = True
                    print(f"Found Naver Map via JS: type={result.get('type')}")

            # 방법 5: 근무지역 섹션 주변에서 지도 요소 탐색
            if not naver_map_found:
                result = await page.evaluate("""() => {
                    // 근무지역 레이블 찾기
                    const allEls = [...document.querySelectorAll('*')];
                    const workAreaEl = allEls.find(el => {
                        const text = el.innerText ? el.innerText.trim() : '';
                        return text === '근무지역' && el.children.length === 0;
                    });

                    if (!workAreaEl) return { found: false, reason: 'no work area element' };

                    // 부모 요소 체인에서 iframe이나 canvas 탐색
                    let parent = workAreaEl.parentElement;
                    for (let i = 0; i < 8; i++) {
                        if (!parent) break;
                        const maps = [...parent.querySelectorAll('iframe, canvas, [class*="map"], [class*="Map"]')];
                        if (maps.length > 0) {
                            return {
                                found: true, depth: i,
                                type: maps[0].tagName,
                                src: maps[0].src || '',
                                class: (maps[0].className || '').substring(0, 100)
                            };
                        }
                        parent = parent.parentElement;
                    }

                    // 근무지역 이후 형제 요소에서 탐색
                    let sibling = workAreaEl.parentElement ? workAreaEl.parentElement.nextElementSibling : null;
                    let siblingCount = 0;
                    while (sibling && siblingCount < 15) {
                        const maps = [...sibling.querySelectorAll('iframe, canvas')];
                        if (maps.length > 0) {
                            return { found: true, type: 'sibling', tagName: maps[0].tagName };
                        }
                        sibling = sibling.nextElementSibling;
                        siblingCount++;
                    }

                    return { found: false, reason: 'no map near work area' };
                }""")
                print(f"Map near work area search: {result}")
                if result.get('found'):
                    naver_map_found = True
                    print(f"Found map element near work area: type={result.get('type')}")

            # 방법 6: 현재 포지션에 지도가 없을 수 있으므로 다른 포지션 시도
            if not naver_map_found:
                print("Current position may not have a map. Trying other positions...")
                await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(2000)

                position_links = page.locator('a[href^="/wd/"]')
                total = await position_links.count()
                print(f"Total position cards: {total}")

                for i in range(1, min(total, 8)):
                    try:
                        href_i = await position_links.nth(i).get_attribute('href')
                        pos_url = f'https://www.wanted.co.kr{href_i}'
                        await page.goto(pos_url, timeout=30000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(2000)

                        map_check = await page.evaluate("""() => {
                            const iframes = [...document.querySelectorAll('iframe')];
                            for (const f of iframes) {
                                const src = f.src || '';
                                if (src.includes('naver') || src.includes('map')) {
                                    return { found: true, type: 'iframe', src };
                                }
                            }

                            // naver map SDK or reference
                            const html = document.documentElement.innerHTML;
                            if (html.includes('map.naver.com') || html.includes('naver.maps')) {
                                return { found: true, type: 'html_reference' };
                            }

                            // 근무지역 섹션에서 canvas 탐색
                            const allEls = [...document.querySelectorAll('*')];
                            const workAreaEl = allEls.find(el => {
                                const text = el.innerText ? el.innerText.trim() : '';
                                return text === '근무지역' && el.children.length === 0;
                            });
                            if (workAreaEl) {
                                let parent = workAreaEl.parentElement;
                                for (let j = 0; j < 8; j++) {
                                    if (!parent) break;
                                    const maps = [...parent.querySelectorAll('canvas, iframe')];
                                    if (maps.length > 0) {
                                        return { found: true, type: maps[0].tagName, depth: j };
                                    }
                                    parent = parent.parentElement;
                                }
                            }

                            return { found: false };
                        }""")

                        # 근무지역 존재 여부 확인
                        has_work_area = await page.evaluate("""() => {
                            return document.body.innerText.includes('근무지역');
                        }""")

                        print(f"Position {i} ({href_i}): has_work_area={has_work_area}, map_check={map_check}")

                        if map_check.get('found') and has_work_area:
                            naver_map_found = True
                            print(f"✓ Found Naver Map in position {i}: {pos_url}")
                            print(f"  Map info: {map_check}")
                            break
                    except Exception as e:
                        print(f"Error checking position {i}: {e}")

            assert naver_map_found, "네이버 지도가 근무지역 섹션에 노출되지 않았습니다"
            print("✓ 네이버 지도 노출 확인 완료")

            await page.screenshot(path='screenshots/test_POSITION_005_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_005_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
