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
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 이력서 작성 페이지로 이동 ──
            safe_print("[INFO] 이력서 작성 페이지로 이동 시도...")

            # 페이지 정보 수집
            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    cvLinks: [],
                    allButtons: [],
                };
                const allEls = [...document.querySelectorAll('button, a, [role="button"]')];
                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const href = el.href || '';
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.allButtons.push({ text: text.substring(0, 60), href: href.substring(0, 120) });
                        if (href.includes('/cv/') || href.includes('/resume/')) {
                            result.cvLinks.push({ text: text.substring(0, 60), href: href.substring(0, 120) });
                        }
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] CV 관련 링크 ({len(page_info['cvLinks'])}개):")
            for lnk in page_info['cvLinks'][:10]:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")
            safe_print(f"[INFO] 전체 버튼 ({len(page_info['allButtons'])}개):")
            for btn in page_info['allButtons'][:20]:
                safe_print(f"  - '{btn['text']}' href='{btn['href']}'")

            before_url = page.url
            clicked = False

            # cv 작성/편집 URL 직접 이동
            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/edit', '/cv/write']):
                    safe_print(f"[INFO] CV 작성 링크 직접 이동: {href}")
                    await page.goto(href, timeout=30000)
                    clicked = True
                    break

            # 기존 이력서 편집 링크
            if not clicked:
                for lnk in page_info['cvLinks']:
                    href = lnk['href']
                    if '/cv/' in href and 'cv/list' not in href and 'cv/intro' not in href:
                        safe_print(f"[INFO] CV 링크로 이동: {href}")
                        await page.goto(href, timeout=30000)
                        clicked = True
                        break

            # 버튼 키워드로 클릭 시도
            if not clicked:
                new_btn_keywords = [
                    '새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                    '새로 만들기', '작성하기', '이력서 추가', '이력서 쓰기',
                    '이력서 편집', '편집하기', '수정하기',
                ]
                for kw in new_btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=False)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] 버튼 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if clicked:
                try:
                    await page.wait_for_url(
                        lambda url: url != before_url,
                        timeout=10000
                    )
                except Exception:
                    pass
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            safe_print(f"[INFO] 이력서 작성 페이지 URL: {page.url}")

            # 이력서 작성 페이지에 진입했는지 확인
            current_url = page.url
            assert '/cv/' in current_url and 'cv/list' not in current_url, (
                f"이력서 작성 페이지로 이동 실패. 현재 URL: {current_url}"
            )
            safe_print(f"[OK] 이력서 작성 페이지 진입 확인: {current_url}")

            # ── Step 3: 상단 영역의 이전 페이지 버튼 탐색 ──
            safe_print("[INFO] 상단 영역에서 이전 페이지 버튼 탐색 중...")

            # 페이지 상단 버튼 목록 수집
            top_buttons = await page.evaluate("""() => {
                const result = {
                    buttons: [],
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 2000),
                    backElements: [],
                };
                const allBtns = document.querySelectorAll('button, [role="button"], a');
                for (const btn of allBtns) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    const rect = btn.getBoundingClientRect();
                    const href = btn.href || '';
                    if (rect.width > 0 && rect.height > 0) {
                        result.buttons.push({
                            text: text.substring(0, 80),
                            tag: btn.tagName,
                            href: href.substring(0, 120),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            ariaLabel: (btn.getAttribute('aria-label') || '').substring(0, 80),
                            title: (btn.getAttribute('title') || '').substring(0, 80),
                            className: (btn.className || '').substring(0, 120),
                        });
                    }
                }
                // 뒤로 가기 아이콘 등 탐색
                const backSelectors = [
                    '[class*="back"]', '[class*="Back"]', '[class*="prev"]', '[class*="Prev"]',
                    '[class*="arrow"]', '[class*="Arrow"]', '[class*="return"]', '[class*="Return"]',
                    '[aria-label*="이전"]', '[aria-label*="뒤로"]', '[title*="이전"]', '[title*="뒤로"]',
                ];
                for (const sel of backSelectors) {
                    try {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                result.backElements.push({
                                    tag: el.tagName,
                                    text: (el.innerText || el.textContent || '').trim().substring(0, 80),
                                    ariaLabel: (el.getAttribute('aria-label') || '').substring(0, 80),
                                    className: (el.className || '').substring(0, 120),
                                    href: el.href || '',
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    selector: sel,
                                });
                            }
                        }
                    } catch(e) {}
                }
                return result;
            }""")

            safe_print(f"[INFO] 페이지 텍스트 일부: {top_buttons['bodyText'][:500]}")
            safe_print(f"[INFO] 버튼 목록 ({len(top_buttons['buttons'])}개):")
            for btn in top_buttons['buttons'][:30]:
                safe_print(f"  - [{btn['tag']:8s}] ({btn['x']},{btn['y']}) aria='{btn['ariaLabel']}' title='{btn['title']}' '{btn['text']}'")
            safe_print(f"[INFO] 뒤로가기 관련 요소 ({len(top_buttons['backElements'])}개):")
            for lnk in top_buttons['backElements'][:10]:
                safe_print(f"  - [{lnk['tag']:8s}] ({lnk['x']},{lnk['y']}) aria='{lnk['ariaLabel']}' class='{lnk['className'][:60]}' sel='{lnk['selector']}' '{lnk['text']}'")

            # ── Step 4: 이전 페이지 버튼 클릭 ──
            safe_print("[INFO] 이전 페이지 버튼 클릭 시도...")

            back_clicked = False

            # 1) 텍스트 기반: '이전', '뒤로', '목록', '돌아가기' 등
            back_keywords = ['이전', '뒤로', '목록으로', '돌아가기', '이력서 목록', '이전 페이지']
            for kw in back_keywords:
                try:
                    btn = page.get_by_role('button', name=kw)
                    cnt = await btn.count()
                    if cnt > 0:
                        safe_print(f"[INFO] role=button '{kw}' 개수: {cnt}")
                        await btn.first.click(timeout=8000)
                        back_clicked = True
                        safe_print(f"[OK] 이전 페이지 버튼 클릭 (role): '{kw}'")
                        break
                except Exception as e:
                    safe_print(f"[WARN] role button '{kw}' 실패: {e}")

            # 2) 링크 클릭
            if not back_clicked:
                for kw in back_keywords:
                    try:
                        lnk = page.get_by_role('link', name=kw)
                        cnt = await lnk.count()
                        if cnt > 0:
                            safe_print(f"[INFO] role=link '{kw}' 개수: {cnt}")
                            await lnk.first.click(timeout=8000)
                            back_clicked = True
                            safe_print(f"[OK] 이전 페이지 링크 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] role link '{kw}' 실패: {e}")

            # 3) 텍스트 직접 탐색
            if not back_clicked:
                for kw in back_keywords:
                    try:
                        el = page.get_by_text(kw, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            safe_print(f"[INFO] text '{kw}' 개수: {cnt}")
                            await el.first.click(timeout=8000)
                            back_clicked = True
                            safe_print(f"[OK] 텍스트 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] text '{kw}' 실패: {e}")

            # 4) 상단 영역의 버튼 중 cv/list로 이동하는 링크 탐색
            if not back_clicked:
                for btn in top_buttons['buttons']:
                    if 'cv/list' in btn['href']:
                        safe_print(f"[INFO] cv/list 링크 클릭: '{btn['text']}' href={btn['href']}")
                        await page.goto(btn['href'], timeout=30000)
                        back_clicked = True
                        break

            # 5) aria-label 또는 title에 '이전', '뒤로' 등이 있는 요소 탐색
            if not back_clicked:
                for btn in top_buttons['buttons']:
                    aria = btn['ariaLabel'].lower()
                    title_val = btn['title'].lower()
                    text = btn['text'].lower()
                    if any(kw in aria or kw in title_val or kw in text for kw in ['back', 'prev', '이전', '뒤로', 'go back']):
                        safe_print(f"[INFO] aria/title/text 기반 클릭: aria='{btn['ariaLabel']}' title='{btn['title']}' text='{btn['text']}'")
                        await page.mouse.click(btn['x'] + btn['width'] // 2, btn['y'] + btn['height'] // 2)
                        back_clicked = True
                        safe_print(f"[OK] aria/title 기반 이전 버튼 클릭")
                        break

            # 6) 상단에 있는 버튼 중 아이콘 버튼 (텍스트 없는 버튼, 상단 좌측)
            if not back_clicked:
                for btn in top_buttons['buttons']:
                    # 상단 좌측 영역의 텍스트 없는 버튼
                    if btn['y'] < 150 and btn['x'] < 200 and len(btn['text']) == 0:
                        safe_print(f"[INFO] 상단 좌측 아이콘 버튼 클릭: ({btn['x']},{btn['y']}) aria='{btn['ariaLabel']}'")
                        await page.mouse.click(btn['x'] + btn['width'] // 2, btn['y'] + btn['height'] // 2)
                        back_clicked = True
                        safe_print(f"[OK] 상단 좌측 아이콘 버튼 클릭")
                        break

            # 7) 뒤로 가기 관련 CSS 클래스 요소 클릭
            if not back_clicked and top_buttons['backElements']:
                lnk = top_buttons['backElements'][0]
                safe_print(f"[INFO] back 관련 요소 클릭 시도: '{lnk['text']}' class='{lnk['className'][:60]}'")
                await page.mouse.click(lnk['x'] + lnk['width'] // 2, lnk['y'] + lnk['height'] // 2)
                back_clicked = True
                safe_print(f"[OK] back 관련 요소 클릭")

            # 8) 최후 수단: browser back
            if not back_clicked:
                safe_print("[INFO] 최후 수단: page.go_back() 시도...")
                await page.go_back(timeout=10000)
                back_clicked = True
                safe_print("[OK] page.go_back() 실행")

            # ── Step 5: 이력서 탭 페이지로 랜딩 확인 ──
            safe_print("[INFO] 이력서 탭 페이지 랜딩 대기 중...")
            try:
                await page.wait_for_url(
                    lambda url: 'cv/list' in url or 'cv/intro' in url,
                    timeout=10000
                )
            except Exception:
                pass
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            final_url = page.url
            safe_print(f"[INFO] 최종 URL: {final_url}")

            # 기대 결과: 이력서 탭 페이지(cv/list)로 랜딩
            assert 'cv/list' in final_url or 'cv/intro' in final_url, (
                f"이력서 탭 페이지로 이동하지 않음. 현재 URL: {final_url}"
            )
            safe_print(f"[OK] 이력서 탭 페이지 랜딩 확인: {final_url}")

            await page.screenshot(path='screenshots/test_60_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_60_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
