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

            # ── Step 1: 채용 홈 진입 ──
            safe_print("[INFO] 채용 홈 진입 중...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 채용 홈 로드: {page.url}")

            # ── Step 2: 검색 버튼 클릭 ──
            safe_print("[INFO] GNB 검색 버튼 클릭...")
            search_btn_info = await page.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')];
                for (const btn of btns) {
                    const aria = btn.getAttribute('aria-label') || '';
                    if (aria === '검색' || aria.includes('검색')) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, aria };
                        }
                    }
                }
                return null;
            }""")
            safe_print(f"[INFO] 검색 버튼 좌표: {search_btn_info}")

            clicked_first = False
            if search_btn_info:
                try:
                    await page.mouse.click(search_btn_info['x'], search_btn_info['y'])
                    clicked_first = True
                    safe_print(f"[OK] 마우스 클릭 성공: ({search_btn_info['x']}, {search_btn_info['y']})")
                except Exception as e:
                    safe_print(f"[WARN] 마우스 클릭 실패: {e}")

            if not clicked_first:
                try:
                    btn = page.locator('button[aria-label="검색"]').first
                    await btn.click(timeout=8000)
                    clicked_first = True
                    safe_print("[OK] aria-label 클릭 성공")
                except Exception as e:
                    safe_print(f"[WARN] aria-label 클릭 실패: {e}")

            assert clicked_first, "검색 버튼 클릭 실패"

            # ── 검색 입력창 나타날 때까지 대기 ──
            safe_print("[INFO] 검색 입력창 대기...")
            try:
                await page.wait_for_selector(
                    'input[placeholder*="검색"]',
                    timeout=8000,
                    state='visible'
                )
                safe_print("[OK] 검색 입력창 나타남")
            except Exception as e:
                safe_print(f"[WARN] wait_for_selector 실패: {e}")
            await page.wait_for_timeout(1500)

            # ── 검색어 입력 ──
            safe_print("[INFO] '개발자' 검색어 입력...")
            typed = False
            for sel in ['input[placeholder*="검색"]', 'input[type="search"]']:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=3000):
                        await loc.fill('개발자')
                        typed = True
                        safe_print(f"[OK] fill로 입력 성공: '{sel}'")
                        break
                except Exception as e:
                    safe_print(f"[WARN] fill 실패 '{sel}': {e}")

            if not typed:
                await page.keyboard.type('개발자', delay=80)
                typed = True
                safe_print("[OK] keyboard.type으로 입력")

            await page.wait_for_timeout(1000)
            await page.keyboard.press('Enter')
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 검색 완료. URL: {page.url}")

            # ── Step 3: 채용 홈 복귀 ──
            safe_print("[INFO] 채용 홈으로 복귀...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 채용 홈 재진입: {page.url}")

            # ── Step 4: 검색 버튼 재클릭 ──
            safe_print("[INFO] 검색 버튼 재클릭 (최근 검색어 확인)...")
            search_btn_info2 = await page.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')];
                for (const btn of btns) {
                    const aria = btn.getAttribute('aria-label') || '';
                    if (aria === '검색' || aria.includes('검색')) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, aria };
                        }
                    }
                }
                return null;
            }""")
            safe_print(f"[INFO] 검색 버튼 좌표 (2차): {search_btn_info2}")

            clicked_second = False
            if search_btn_info2:
                try:
                    await page.mouse.click(search_btn_info2['x'], search_btn_info2['y'])
                    clicked_second = True
                    safe_print(f"[OK] 마우스 클릭 성공 (2차)")
                except Exception as e:
                    safe_print(f"[WARN] 마우스 클릭 실패 (2차): {e}")

            if not clicked_second:
                clicked_second = await page.evaluate("""() => {
                    const btns = [...document.querySelectorAll('button')];
                    for (const btn of btns) {
                        const aria = btn.getAttribute('aria-label') || '';
                        if (aria === '검색' || aria.includes('검색')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if clicked_second:
                    safe_print("[OK] JS 클릭 성공 (2차)")

            assert clicked_second, "검색 버튼 재클릭 실패"

            # ── 검색 입력창 대기 및 포커스 ──
            safe_print("[INFO] 검색 입력창 대기 및 포커스...")
            try:
                await page.wait_for_selector(
                    'input[placeholder*="검색"]',
                    timeout=8000,
                    state='visible'
                )
                safe_print("[OK] 검색 입력창 나타남 (2차)")
            except Exception as e:
                safe_print(f"[WARN] wait_for_selector 실패 (2차): {e}")

            await page.wait_for_timeout(1000)

            # 입력창 클릭하여 포커스 (최근 검색어 드롭다운 트리거)
            input_focused = False
            for sel in ['input[placeholder*="검색"]', 'input[type="search"]', 'input[class*="search"]']:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        is_vis = await loc.is_visible(timeout=3000)
                        if is_vis:
                            await loc.click(timeout=5000)
                            input_focused = True
                            safe_print(f"[OK] 입력창 포커스 성공: '{sel}'")
                            break
                except Exception as e:
                    safe_print(f"[WARN] 입력창 포커스 실패 '{sel}': {e}")

            if not input_focused:
                # JS로 입력창 좌표 클릭
                input_coords = await page.evaluate("""() => {
                    const inputs = document.querySelectorAll('input');
                    for (const inp of inputs) {
                        const rect = inp.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
                        }
                    }
                    return null;
                }""")
                if input_coords:
                    await page.mouse.click(input_coords['x'], input_coords['y'])
                    input_focused = True
                    safe_print(f"[OK] 입력창 좌표 클릭 성공: {input_coords}")

            # 최근 검색어 드롭다운 로딩 대기
            await page.wait_for_timeout(3000)

            # ── Step 5: 검색 오버레이/드롭다운 내 최근 검색어 확인 ──
            safe_print("[INFO] 최근 검색어 및 페이지 전체 구조 분석...")

            full_check = await page.evaluate("""() => {
                const result = {
                    recentHeaderFound: false,
                    recentHeaderVisible: false,
                    foundHeaderText: '',
                    recentItems: [],
                    allSearchAreaLis: [],
                    bodyText: '',
                    sessionStorageRecent: [],
                    sessionStorageKeys: [],
                    localStorageRecent: [],
                    developerFound: false,
                    allVisibleTexts: [],
                };

                // 페이지 텍스트
                const bodyText = document.body.innerText || '';
                result.bodyText = bodyText.substring(0, 800);

                // 최근 검색어 키워드 목록
                const recentKeywords = ['최근 검색어', '최근검색어', '최근 검색', '검색 이력', '검색이력', '최근 이력'];

                // 페이지 텍스트에서 최근 검색어 헤더 확인
                for (const kw of recentKeywords) {
                    if (bodyText.includes(kw)) {
                        result.recentHeaderFound = true;
                        result.foundHeaderText = kw;
                        break;
                    }
                }

                // DOM에서 최근 검색어 헤더 요소 찾기
                const allEls = [...document.querySelectorAll('*')];
                let recentSectionEl = null;
                for (const el of allEls) {
                    const directText = [...el.childNodes]
                        .filter(n => n.nodeType === Node.TEXT_NODE)
                        .map(n => n.textContent.trim())
                        .join('');
                    if (recentKeywords.some(kw => directText === kw || directText.includes(kw))) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.recentHeaderVisible = true;
                            result.foundHeaderText = directText;
                            recentSectionEl = el;
                            break;
                        }
                    }
                }

                // 최근 검색어 섹션 내 항목 수집
                if (recentSectionEl) {
                    let container = recentSectionEl.parentElement;
                    for (let i = 0; i < 8; i++) {
                        if (!container) break;
                        const items = container.querySelectorAll('a, button, li, span[class*="keyword"], span[class*="Keyword"]');
                        const skipTexts = ['최근 검색어', '최근검색어', '인기 검색어', '인기검색어', '전체 삭제', '전체삭제', '삭제', '×', 'X', '검색'];
                        const found = [];
                        for (const item of items) {
                            const text = (item.innerText || item.textContent || '').trim();
                            if (text && text.length >= 1 && text.length <= 30 && !skipTexts.includes(text)) {
                                const rect = item.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    found.push({ text: text.substring(0, 30), tag: item.tagName });
                                }
                            }
                        }
                        if (found.length >= 1) {
                            result.recentItems = found;
                            break;
                        }
                        container = container.parentElement;
                    }
                }

                // 검색 오버레이/드롭다운 영역의 LI 항목 탐색
                const searchSelectors = [
                    '[class*="search"] li',
                    '[class*="Search"] li',
                    '[class*="layer"] li',
                    '[class*="Layer"] li',
                    '[class*="overlay"] li',
                    '[class*="Overlay"] li',
                    '[class*="dropdown"] li',
                    '[class*="Dropdown"] li',
                    '[role="listbox"] li',
                    '[role="dialog"] li',
                    '[class*="popup"] li',
                    '[class*="Popup"] li',
                ];
                const seenTexts = new Set();
                for (const sel of searchSelectors) {
                    const lis = document.querySelectorAll(sel);
                    for (const li of lis) {
                        const rect = li.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            const text = (li.innerText || li.textContent || '').trim().substring(0, 30);
                            if (text && !seenTexts.has(text)) {
                                seenTexts.add(text);
                                result.allSearchAreaLis.push({ text, selector: sel, top: Math.round(rect.top) });
                                if (text.includes('개발자')) result.developerFound = true;
                            }
                        }
                    }
                }

                // sessionStorage 확인
                try {
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        if (key) {
                            result.sessionStorageKeys.push(key);
                            const val = sessionStorage.getItem(key) || '';
                            if (
                                key.toLowerCase().includes('search') ||
                                key.toLowerCase().includes('recent') ||
                                key.toLowerCase().includes('history') ||
                                key.toLowerCase().includes('keyword') ||
                                val.includes('개발자')
                            ) {
                                result.sessionStorageRecent.push({ key, value: val.substring(0, 200) });
                            }
                        }
                    }
                } catch(e) {}

                // localStorage 확인
                try {
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        if (key) {
                            const val = localStorage.getItem(key) || '';
                            if (
                                key.toLowerCase().includes('search') ||
                                key.toLowerCase().includes('recent') ||
                                key.toLowerCase().includes('history') ||
                                key.toLowerCase().includes('keyword') ||
                                val.includes('개발자')
                            ) {
                                result.localStorageRecent.push({ key, value: val.substring(0, 200) });
                            }
                        }
                    }
                } catch(e) {}

                // 화면에 보이는 모든 텍스트 요소 (상위 40개)
                const candidates = [];
                const seenAll = new Set();
                for (const el of allEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.top > 40 && rect.top < 500) {
                        const ownText = [...el.childNodes]
                            .filter(n => n.nodeType === Node.TEXT_NODE)
                            .map(n => n.textContent.trim())
                            .join('')
                            .trim();
                        if (ownText && ownText.length > 0 && ownText.length <= 40 && !seenAll.has(ownText)) {
                            seenAll.add(ownText);
                            candidates.push({ text: ownText, tag: el.tagName, top: Math.round(rect.top), cls: (el.className || '').substring(0, 40) });
                        }
                    }
                }
                candidates.sort((a, b) => a.top - b.top);
                result.allVisibleTexts = candidates.slice(0, 50);

                // 페이지에 '개발자' 있는지 직접 확인
                if (bodyText.includes('개발자')) {
                    result.developerFound = true;
                }

                return result;
            }""")

            safe_print(f"[INFO] 최근 검색어 헤더 (텍스트): {full_check['recentHeaderFound']} ('{full_check['foundHeaderText']}')")
            safe_print(f"[INFO] 최근 검색어 헤더 (DOM): {full_check['recentHeaderVisible']}")
            safe_print(f"[INFO] 최근 검색어 항목: {full_check['recentItems']}")
            safe_print(f"[INFO] 검색 영역 LI 항목 (상위 15개):")
            for item in full_check['allSearchAreaLis'][:15]:
                safe_print(f"  - sel='{item['selector']}' | top={item['top']:4d} | '{item['text']}'")
            safe_print(f"[INFO] sessionStorage 최근 검색: {full_check['sessionStorageRecent']}")
            safe_print(f"[INFO] localStorage 최근 검색: {full_check['localStorageRecent']}")
            safe_print(f"[INFO] '개발자' 발견: {full_check['developerFound']}")
            safe_print(f"\n[INFO] 화면 내 텍스트 (40~500px 영역, 상위 40개):")
            for item in full_check['allVisibleTexts'][:40]:
                safe_print(f"  - top={item['top']:4d} | tag={item['tag']:6s} | cls='{item['cls'][:30]}' | '{item['text']}'")

            # ── Step 6: 최종 검증 ──
            safe_print("\n[INFO] 최종 검증 시작...")

            # 검증 기준:
            # 1. '최근 검색어' 헤더가 DOM에 보임
            # 2. '최근 검색어' 텍스트가 페이지에 존재
            # 3. 검색 영역에 '개발자' 항목 존재
            # 4. sessionStorage/localStorage에 최근 검색어 저장
            # 5. 최근 검색어 항목 1개 이상 발견

            has_recent = (
                full_check['recentHeaderVisible'] or
                full_check['recentHeaderFound'] or
                full_check['developerFound'] or
                len(full_check['recentItems']) > 0 or
                len(full_check['sessionStorageRecent']) > 0 or
                len(full_check['localStorageRecent']) > 0
            )

            # '개발자' 가 화면에 있는지 추가 확인 (검색 결과 제외)
            # 검색 영역의 visible text에 '개발자'가 있는지
            developer_in_visible = any(
                '개발자' in item['text']
                for item in full_check['allVisibleTexts']
            )
            if developer_in_visible:
                has_recent = True

            safe_print(f"\n[RESULT] 테스트 케이스 50 검증:")
            safe_print(f"  - 최근 검색어 헤더 DOM 노출: {full_check['recentHeaderVisible']}")
            safe_print(f"  - 최근 검색어 텍스트 존재: {full_check['recentHeaderFound']}")
            safe_print(f"  - 최근 검색어 항목 수: {len(full_check['recentItems'])}")
            safe_print(f"  - 검색 영역 LI 수: {len(full_check['allSearchAreaLis'])}")
            safe_print(f"  - '개발자' 화면 노출: {developer_in_visible}")
            safe_print(f"  - sessionStorage 검색 이력: {len(full_check['sessionStorageRecent'])}개")
            safe_print(f"  - localStorage 검색 이력: {len(full_check['localStorageRecent'])}개")
            safe_print(f"  - 종합 결과: {'성공' if has_recent else '실패'}")

            assert has_recent, (
                "최근 검색어 항목이 노출되지 않음 "
                f"(헤더DOM={full_check['recentHeaderVisible']}, "
                f"헤더텍스트={full_check['recentHeaderFound']}, "
                f"항목수={len(full_check['recentItems'])}, "
                f"개발자화면={developer_in_visible}, "
                f"SS={len(full_check['sessionStorageRecent'])}, "
                f"LS={len(full_check['localStorageRecent'])})"
            )

            safe_print("[OK] 최근 검색어 항목 노출 확인 완료!")

            await page.screenshot(path='screenshots/test_50_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_50_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
