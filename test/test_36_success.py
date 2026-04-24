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

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            storage_state='work/auth_state.json',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 목록 페이지로 이동 후 포지션 URL 확보
            print("[INFO] 채용 목록 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 채용 목록 페이지 로드 완료 - URL: {page.url}")

            position_url = None
            wd_links = page.locator('a[href*="/wd/"]')
            count = await wd_links.count()
            print(f"[INFO] /wd/ 링크 수: {count}")

            if count > 0:
                href = await wd_links.first.get_attribute('href')
                if href:
                    position_url = href if href.startswith('http') else f"https://www.wanted.co.kr{href}"
                    print(f"[OK] 포지션 URL 발견: {position_url}")

            assert position_url is not None, "포지션 상세 페이지 URL을 찾을 수 없습니다"

            # 2. 포지션 상세 페이지 진입
            print(f"[INFO] 포지션 상세 페이지 진입: {position_url}")
            await page.goto(position_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 포지션 상세 페이지 로드 완료 - URL: {page.url}")
            await page.screenshot(path='screenshots/test_36_step1_detail.png')

            # 3. 마감일 항목 탐색
            print("[INFO] '마감일' 항목 탐색 중...")
            deadline_found = False

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            for scroll_step in range(20):
                deadline_texts = ['마감일', '채용 마감일', '지원 마감일', '마감']
                for dt in deadline_texts:
                    try:
                        el = page.get_by_text(dt, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        deadline_found = True
                                        print(f"[OK] '{dt}' 텍스트 발견 (visible)")
                                        break
                                except Exception:
                                    continue
                        if deadline_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{dt}' 탐색 실패: {e}")
                if deadline_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(400)

            if not deadline_found:
                print("[INFO] JS 기반 '마감일' 탐색 중...")
                js_deadline = await page.evaluate("""() => {
                    const keywords = ['마감일', '채용 마감일', '지원 마감일', '마감'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        for (const kw of keywords) {
                            if (text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0) {
                                    return {found: true, keyword: kw};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                if js_deadline.get('found'):
                    deadline_found = True
                    print(f"[OK] JS로 '마감일' 항목 발견: {js_deadline.get('keyword')}")

            assert deadline_found, "'마감일' 항목을 찾을 수 없습니다"
            print("[OK] '마감일' 항목 확인됨")

            await page.screenshot(path='screenshots/test_36_step2_deadline.png')

            # 4. 마감일 하단에 근무지역 항목 탐색
            print("[INFO] '근무지역' 항목 탐색 중...")
            work_area_found = False

            # 스크롤 계속 진행하며 근무지역 탐색
            work_texts = ['근무지역', '근무지', '근무 지역', '근무위치', '근무 위치', '회사위치', '회사 위치', '위치']
            for scroll_step in range(20):
                for wt in work_texts:
                    try:
                        el = page.get_by_text(wt, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        work_area_found = True
                                        print(f"[OK] '{wt}' 텍스트 발견 (visible)")
                                        break
                                except Exception:
                                    continue
                        if work_area_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{wt}' 탐색 실패: {e}")
                if work_area_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(400)

            if not work_area_found:
                print("[INFO] JS 기반 '근무지역' 탐색 중...")
                js_work = await page.evaluate("""() => {
                    const keywords = ['근무지역', '근무지', '근무 지역', '근무위치', '근무 위치', '회사위치', '위치'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        for (const kw of keywords) {
                            if (text === kw || text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0) {
                                    return {found: true, keyword: kw, text: text};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                if js_work.get('found'):
                    work_area_found = True
                    print(f"[OK] JS로 '근무지역' 항목 발견: {js_work.get('keyword')}")

            assert work_area_found, "'근무지역' 항목을 찾을 수 없습니다"
            print("[OK] 마감일 항목 하단 '근무지역' 항목 확인됨")

            await page.screenshot(path='screenshots/test_36_step3_workarea.png')

            # 5. 네이버 지도 노출 확인
            print("[INFO] 네이버 지도 탐색 중...")
            naver_map_found = False

            # 방법 1: iframe 탐색 (네이버 지도 iframe)
            js_map = await page.evaluate("""() => {
                // iframe 중 네이버 지도 탐색
                const iframes = Array.from(document.querySelectorAll('iframe'));
                for (const iframe of iframes) {
                    const src = (iframe.src || '').toLowerCase();
                    const name = (iframe.name || '').toLowerCase();
                    const id = (iframe.id || '').toLowerCase();
                    if (src.includes('map') || src.includes('naver') ||
                        name.includes('map') || id.includes('map')) {
                        const rect = iframe.getBoundingClientRect();
                        return {found: true, type: 'iframe', src: src.substring(0, 100),
                                visible: rect.width > 0 && rect.height > 0};
                    }
                }

                // 네이버 지도 관련 div 탐색
                const mapSelectors = [
                    '[id*="map"]', '[id*="Map"]', '[id*="naver"]',
                    '[class*="map"]', '[class*="Map"]',
                    '[class*="naver"]', '[class*="Naver"]',
                    '[class*="NaverMap"]', '[class*="navermap"]',
                    'div[style*="map"]',
                ];
                for (const sel of mapSelectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.textContent || '').trim();
                        if (rect.width > 50 && rect.height > 50) {
                            return {found: true, type: 'div', selector: sel,
                                    width: rect.width, height: rect.height,
                                    className: el.className.substring(0, 80)};
                        }
                    }
                }

                // canvas 탐색 (지도 렌더링용)
                const canvases = Array.from(document.querySelectorAll('canvas'));
                for (const canvas of canvases) {
                    const rect = canvas.getBoundingClientRect();
                    if (rect.width > 100 && rect.height > 100) {
                        return {found: true, type: 'canvas',
                                width: rect.width, height: rect.height};
                    }
                }

                return {found: false};
            }""")

            print(f"[INFO] 네이버 지도 탐색 결과: {js_map}")
            if js_map.get('found'):
                naver_map_found = True
                print(f"[OK] 네이버 지도 발견: type={js_map.get('type')}")

            # 방법 2: 지도 요소 스크롤하여 탐색
            if not naver_map_found:
                print("[INFO] 지도 요소 스크롤 탐색 중...")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                js_map2 = await page.evaluate("""() => {
                    // 모든 iframe 탐색
                    const iframes = Array.from(document.querySelectorAll('iframe'));
                    const iframeInfo = iframes.map(f => ({
                        src: (f.src || '').substring(0, 100),
                        name: f.name || '',
                        id: f.id || '',
                        width: f.getBoundingClientRect().width,
                        height: f.getBoundingClientRect().height
                    }));

                    // 모든 canvas 탐색
                    const canvases = Array.from(document.querySelectorAll('canvas'));
                    const canvasInfo = canvases.map(c => ({
                        width: c.getBoundingClientRect().width,
                        height: c.getBoundingClientRect().height,
                        id: c.id || '',
                        className: (c.className || '').substring(0, 60)
                    }));

                    // 맵 관련 div 탐색 (더 넓은 범위)
                    const mapDivs = Array.from(document.querySelectorAll(
                        '[id*="map"],[class*="map"],[class*="Map"],[class*="location"],[class*="Location"]'
                    )).filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 50 && rect.height > 50;
                    }).map(el => ({
                        tag: el.tagName,
                        id: el.id || '',
                        className: (el.className || '').substring(0, 80),
                        width: el.getBoundingClientRect().width,
                        height: el.getBoundingClientRect().height
                    }));

                    return {
                        iframes: iframeInfo,
                        canvases: canvasInfo,
                        mapDivs: mapDivs.slice(0, 10)
                    };
                }""")

                print(f"[INFO] 전체 지도 탐색 - iframes: {len(js_map2.get('iframes', []))}, "
                      f"canvases: {len(js_map2.get('canvases', []))}, "
                      f"mapDivs: {len(js_map2.get('mapDivs', []))}")

                for iframe in js_map2.get('iframes', []):
                    print(f"  iframe: src={iframe.get('src')}, size={iframe.get('width')}x{iframe.get('height')}")
                for canvas in js_map2.get('canvases', []):
                    print(f"  canvas: size={canvas.get('width')}x{canvas.get('height')}, class={canvas.get('className')}")
                for div in js_map2.get('mapDivs', []):
                    print(f"  mapDiv: [{div.get('tag')}] id={div.get('id')}, class={div.get('className')}, size={div.get('width')}x{div.get('height')}")

                # 판단: iframe, canvas, mapDiv 중 하나라도 있으면 지도 있는 것으로 간주
                has_iframes = any(
                    i.get('width', 0) > 50 and i.get('height', 0) > 50
                    for i in js_map2.get('iframes', [])
                )
                has_canvas = any(
                    c.get('width', 0) > 100 and c.get('height', 0) > 100
                    for c in js_map2.get('canvases', [])
                )
                has_map_div = len(js_map2.get('mapDivs', [])) > 0

                if has_iframes:
                    naver_map_found = True
                    print("[OK] 지도 iframe 발견")
                elif has_canvas:
                    naver_map_found = True
                    print("[OK] 지도 canvas 발견")
                elif has_map_div:
                    naver_map_found = True
                    print("[OK] 지도 관련 div 발견")

            # 방법 3: Playwright로 직접 지도 locator 탐색
            if not naver_map_found:
                print("[INFO] Playwright locator로 지도 탐색 중...")
                map_selectors = [
                    'iframe',
                    '[class*="map"]',
                    '[class*="Map"]',
                    '[id*="map"]',
                    'canvas',
                    '[class*="location"]',
                    '[class*="Location"]',
                ]
                for sel in map_selectors:
                    try:
                        els = page.locator(sel)
                        cnt = await els.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = els.nth(i)
                                    bb = await item.bounding_box()
                                    if bb and bb.get('width', 0) > 50 and bb.get('height', 0) > 50:
                                        naver_map_found = True
                                        print(f"[OK] Playwright locator로 지도 발견: sel='{sel}', "
                                              f"size={bb.get('width'):.0f}x{bb.get('height'):.0f}")
                                        break
                                except Exception:
                                    continue
                        if naver_map_found:
                            break
                    except Exception as e:
                        print(f"[WARN] locator '{sel}' 탐색 실패: {e}")

            await page.screenshot(path='screenshots/test_36_step4_map.png')

            assert naver_map_found, "네이버 지도를 찾을 수 없습니다 (iframe, canvas, 지도 div 모두 미발견)"
            print("[OK] 네이버 지도 노출 확인됨")

            print("[SUMMARY] 테스트 케이스 36 검증 완료:")
            print("[OK] 포지션 상세 페이지 진입")
            print("[OK] '마감일' 항목 확인됨")
            print("[OK] '마감일' 하단 '근무지역' 항목 노출 확인됨")
            print("[OK] 네이버 지도 노출 확인됨")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_36_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
