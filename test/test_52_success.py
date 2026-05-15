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

            # ── Step 1: 이력서 목록 페이지 진입 ──
            safe_print("[INFO] 이력서 목록 페이지(cv/list) 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 이력서 작성 페이지로 이동 ──
            safe_print("[INFO] 이력서 작성 페이지로 이동 시도...")

            # 페이지 내 버튼/링크 탐색
            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').substring(0, 500),
                    visibleButtons: [],
                    cvLinks: [],
                };

                const allBtns = [...document.querySelectorAll('button, a, [role="button"]')];
                for (const btn of allBtns) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    const rect = btn.getBoundingClientRect();
                    const href = btn.href || '';
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.visibleButtons.push({
                            tag: btn.tagName,
                            text: text.substring(0, 60),
                            href: href.substring(0, 80),
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                        });
                        // cv 관련 링크 모음
                        if (href.includes('/cv/') || href.includes('/resume/')) {
                            result.cvLinks.push({ text: text.substring(0, 60), href: href.substring(0, 80) });
                        }
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_info['url']}")
            safe_print(f"[INFO] 페이지 미리보기: {page_info['bodyText']}")
            safe_print("[INFO] 상위 20개 버튼/링크:")
            for btn in page_info['visibleButtons'][:20]:
                safe_print(f"  - [{btn['tag']:6s}] ({btn['x']:4d},{btn['y']:4d}) '{btn['text'][:50]}' href='{btn['href'][:50]}'")
            safe_print("[INFO] CV 관련 링크:")
            for lnk in page_info['cvLinks']:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")

            # cv/edit 또는 cv/write URL의 링크가 있으면 직접 이동
            cv_writing_url = None
            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/edit', '/cv/write']):
                    cv_writing_url = href
                    break

            before_url = page.url
            clicked = False

            # 방법 1: CV 링크로 직접 이동
            if cv_writing_url:
                safe_print(f"[INFO] CV 작성 링크 직접 이동: {cv_writing_url}")
                await page.goto(cv_writing_url, timeout=30000)
                clicked = True
            else:
                # 방법 2: 버튼 텍스트로 찾기
                new_btn_keywords = [
                    '새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                    '새로 만들기', '작성하기', '이력서 추가', '이력서 쓰기',
                ]
                for kw in new_btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=False)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] get_by_text 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if clicked:
                try:
                    await page.wait_for_url(
                        lambda url: url != before_url,
                        timeout=8000
                    )
                except Exception:
                    pass
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(4000)

            after_url = page.url
            safe_print(f"[INFO] 이동 후 URL: {after_url}")

            # ── Step 3: LNB 영역 탐색 ──
            safe_print("[INFO] LNB 메뉴 영역 탐색 중...")
            lnb_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').substring(0, 800),
                    lnbItems: [],
                    allNavItems: [],
                    sidebarItems: [],
                };

                // LNB / sidebar 탐색 (nav, aside, [class*='side'], [class*='lnb'], [class*='nav'])
                const lnbSelectors = [
                    'nav', 'aside',
                    '[class*="side"]', '[class*="lnb"]', '[class*="Lnb"]',
                    '[class*="nav"]', '[class*="Nav"]',
                    '[class*="sidebar"]', '[class*="Sidebar"]',
                    '[class*="review"]', '[class*="Review"]',
                    '[class*="menu"]', '[class*="Menu"]',
                ];

                const allItems = new Set();
                for (const sel of lnbSelectors) {
                    const elems = document.querySelectorAll(sel);
                    for (const el of elems) {
                        const text = (el.innerText || el.textContent || '').trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && text.length > 0 && text.length < 300) {
                            const key = `${sel}|${text.substring(0, 50)}`;
                            if (!allItems.has(key)) {
                                allItems.add(key);
                                result.allNavItems.push({
                                    selector: sel,
                                    text: text.substring(0, 80),
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                });
                            }
                        }
                    }
                }

                // 이력서 리뷰 관련 텍스트 탐색
                const reviewKeywords = ['포지션 맞춤 리뷰', '이력서 리뷰', '리뷰'];
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const text = (el.innerText || '').trim();
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        for (const kw of reviewKeywords) {
                            if (text === kw || text.includes(kw)) {
                                result.lnbItems.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 80),
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                });
                                break;
                            }
                        }
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {lnb_info['url']}")
            safe_print(f"[INFO] 페이지 미리보기:\n{lnb_info['bodyText']}")
            safe_print(f"[INFO] 이력서 리뷰 관련 항목 ({len(lnb_info['lnbItems'])}개):")
            for item in lnb_info['lnbItems']:
                safe_print(f"  - [{item['tag']}] ({item['x']},{item['y']}) '{item['text'][:80]}'")
            safe_print(f"[INFO] NAV 관련 요소 ({len(lnb_info['allNavItems'])}개):")
            for item in lnb_info['allNavItems'][:20]:
                safe_print(f"  - sel={item['selector']:30s} ({item['x']:4d},{item['y']:4d}) w={item['width']:4d} '{item['text'][:60]}'")

            # ── Step 4: 검증 ──
            # 기대 결과: LNB에 '포지션 맞춤 리뷰'와 '이력서 리뷰' 항목이 있어야 함
            # 페이지 전체 텍스트 (줄바꿈 정규화)
            full_page_text = await page.evaluate("() => document.body.innerText || ''")
            # 줄바꿈을 공백으로 정규화 (DOM에서 '포지션\n맞춤 리뷰' 형태일 수 있음)
            normalized_text = ' '.join(full_page_text.split())

            has_position_review = '포지션 맞춤 리뷰' in normalized_text
            has_resume_review = '이력서 리뷰' in normalized_text

            safe_print(f"[INFO] '포지션 맞춤 리뷰' 노출 여부: {has_position_review}")
            safe_print(f"[INFO] '이력서 리뷰' 노출 여부: {has_resume_review}")

            # LNB aside 요소 내 버튼 상세 확인
            lnb_detail = await page.evaluate("""() => {
                const result = {
                    lnbButtons: [],
                    positionReviewBtn: null,
                    resumeReviewBtn: null,
                    panelVisible: false,
                };

                // aside 내 버튼/탭 탐색
                const asideEls = document.querySelectorAll('aside button, aside [role="tab"], aside a');
                for (const el of asideEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const info = {
                            tag: el.tagName,
                            rawText: rawText.substring(0, 50),
                            normText: normText.substring(0, 50),
                            classes: (el.className || '').substring(0, 100),
                            ariaSelected: el.getAttribute('aria-selected') || '',
                            ariaPressed: el.getAttribute('aria-pressed') || '',
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                        };
                        result.lnbButtons.push(info);

                        if (normText.includes('포지션 맞춤 리뷰') || normText.includes('포지션\\n맞춤')) {
                            result.positionReviewBtn = info;
                        }
                        if (normText === '이력서 리뷰' || normText.includes('이력서 리뷰')) {
                            result.resumeReviewBtn = info;
                        }
                    }
                }

                // 포지션 맞춤 리뷰 패널 확인
                const allText = (document.body.innerText || '').replace(/\\s+/g, ' ');
                result.panelVisible = allText.includes('포지션 맞춤 이력서 리뷰') ||
                                      allText.includes('합격 데이터를 기반');

                return result;
            }""")

            safe_print(f"[INFO] LNB 버튼 목록:")
            for btn in lnb_detail['lnbButtons']:
                safe_print(f"  - [{btn['tag']}] ({btn['x']},{btn['y']}) norm='{btn['normText']}' raw='{btn['rawText']}'")
            safe_print(f"[INFO] '포지션 맞춤 리뷰' 버튼: {lnb_detail['positionReviewBtn']}")
            safe_print(f"[INFO] '이력서 리뷰' 버튼: {lnb_detail['resumeReviewBtn']}")
            safe_print(f"[INFO] '포지션 맞춤 리뷰' 패널 노출: {lnb_detail['panelVisible']}")

            # 검증: '포지션 맞춤 리뷰' LNB 버튼 확인
            # (normalized text 또는 LNB 버튼 직접 확인)
            position_review_found = (
                has_position_review or
                lnb_detail['positionReviewBtn'] is not None
            )
            resume_review_found = (
                has_resume_review or
                lnb_detail['resumeReviewBtn'] is not None
            )
            panel_found = lnb_detail['panelVisible']

            safe_print(f"[INFO] 최종 검증 - '포지션 맞춤 리뷰': {position_review_found}")
            safe_print(f"[INFO] 최종 검증 - '이력서 리뷰': {resume_review_found}")
            safe_print(f"[INFO] 최종 검증 - '포지션 맞춤 리뷰 패널': {panel_found}")

            assert position_review_found, (
                f"'포지션 맞춤 리뷰' LNB 항목이 페이지에 없음 (URL: {lnb_info['url']})"
            )
            assert resume_review_found, (
                f"'이력서 리뷰' LNB 항목이 페이지에 없음 (URL: {lnb_info['url']})"
            )
            assert panel_found, (
                f"'포지션 맞춤 리뷰' 패널이 표시되지 않음 (URL: {lnb_info['url']})"
            )

            safe_print("[OK] LNB 메뉴 항목 검증 완료!")
            safe_print("[OK] '포지션 맞춤 리뷰' 및 '이력서 리뷰' 항목 확인됨")

            await page.screenshot(path='screenshots/test_52_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_52_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
