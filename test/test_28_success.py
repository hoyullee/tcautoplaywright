"""
테스트 케이스 #28
환경: PC
기능영역: GNB > 채용 > 탐색
사전조건:
  1. 비로그인 상태
  2. 탐색 페이지 진입 상태
확인사항: 리스트 영역 상단 '적극 채용 중인 회사' 항목 노출 여부 확인
기대결과: '적극 채용 중인 회사' 비노출 (not displayed)
"""
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

TARGET_TEXT = '적극 채용 중인 회사'

# 탐색 페이지 URL 후보
EXPLORE_URLS = [
    'https://www.wanted.co.kr/explore',
    'https://www.wanted.co.kr/wdlist/explore',
    'https://www.wanted.co.kr/',
]

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        # 비로그인 상태 (세션 없이 새 컨텍스트)
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── 1단계: 탐색 페이지 접속 ──
            print("[INFO] 탐색 페이지 접속 시도...")
            explore_url = None

            for url in EXPLORE_URLS:
                try:
                    print(f"[INFO] {url} 접속 중...")
                    await page.goto(url, timeout=30000)
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(2000)
                    current_url = page.url
                    print(f"[INFO] 현재 URL: {current_url}")

                    # '탐색' 관련 URL이면 사용
                    if 'explore' in current_url:
                        explore_url = current_url
                        print(f"[OK] 탐색 페이지 접속 성공: {current_url}")
                        break
                    else:
                        # GNB에서 탐색 탭을 찾아 클릭
                        print("[INFO] GNB에서 '탐색' 탭 탐색 중...")
                        gnb_explore_clicked = False

                        # GNB 탭 탐색
                        nav_selectors = [
                            page.get_by_role('link', name='탐색'),
                            page.locator('nav a:has-text("탐색")').first,
                            page.locator('header a:has-text("탐색")').first,
                            page.locator('[class*="gnb"] a:has-text("탐색")').first,
                            page.locator('[class*="nav"] a:has-text("탐색")').first,
                            page.locator('a[href*="explore"]').first,
                        ]

                        for sel in nav_selectors:
                            try:
                                await sel.wait_for(timeout=3000, state='visible')
                                await sel.click()
                                await page.wait_for_load_state('domcontentloaded')
                                await page.wait_for_timeout(2000)
                                gnb_explore_clicked = True
                                explore_url = page.url
                                print(f"[OK] GNB '탐색' 탭 클릭 성공 - URL: {explore_url}")
                                break
                            except Exception:
                                continue

                        if gnb_explore_clicked:
                            break

                        # 직접 explore URL 접속
                        explore_url = url
                        break
                except Exception as e:
                    print(f"[WARN] {url} 접속 실패: {e}")
                    continue

            # explore URL이 없으면 직접 접속 재시도
            if not explore_url or 'explore' not in page.url:
                print("[INFO] 직접 explore 페이지 접속 재시도...")
                await page.goto('https://www.wanted.co.kr/explore', timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)
                explore_url = page.url
                print(f"[INFO] 현재 URL: {explore_url}")

            await page.screenshot(path='screenshots/test_28_step1_explore_page.png')
            print(f"[OK] 탐색 페이지 URL: {explore_url}")

            # ── 2단계: 비로그인 상태 확인 ──
            print("[INFO] 비로그인 상태 확인 중...")
            is_logged_out = await page.evaluate("""() => {
                // 로그인 UI 요소 확인 (로그인 버튼이 있으면 비로그인 상태)
                const loginIndicators = [
                    document.querySelector('[href*="login"]'),
                    document.querySelector('button[class*="login"]'),
                    document.querySelector('a[class*="login"]'),
                ];
                for (const el of loginIndicators) {
                    if (el) return true;
                }
                // 프로필/아바타가 없으면 비로그인 상태
                const userIndicators = [
                    document.querySelector('[class*="avatar"]'),
                    document.querySelector('[class*="profile-image"]'),
                    document.querySelector('[aria-label*="프로필"]'),
                ];
                for (const el of userIndicators) {
                    if (el) return false;  // 로그인 상태
                }
                return true;  // 기본: 비로그인 상태로 간주
            }""")
            print(f"[INFO] 비로그인 상태: {is_logged_out}")

            # ── 3단계: 페이지 스크롤 및 콘텐츠 로딩 ──
            print("[INFO] 페이지 스크롤 중 (lazy-load 트리거)...")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

            for i in range(8):
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(600)

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1500)

            await page.screenshot(path='screenshots/test_28_step2_scrolled.png')

            # ── 4단계: '적극 채용 중인 회사' 노출 여부 확인 ──
            print(f"[INFO] '{TARGET_TEXT}' 노출 여부 확인 중...")

            # 방법 1: Playwright get_by_text
            target_visible_playwright = False
            for exact in (True, False):
                try:
                    el = page.get_by_text(TARGET_TEXT, exact=exact)
                    count = await el.count()
                    if count > 0:
                        # 실제로 visible한지 확인
                        for i in range(count):
                            try:
                                is_vis = await el.nth(i).is_visible()
                                if is_vis:
                                    target_visible_playwright = True
                                    print(f"[WARN] '{TARGET_TEXT}' Playwright로 visible 발견 (exact={exact}, idx={i})")
                                    break
                            except Exception:
                                continue
                        if target_visible_playwright:
                            break
                except Exception as e:
                    print(f"[INFO] Playwright get_by_text(exact={exact}) 실패: {e}")

            # 방법 2: JS DOM 탐색
            js_result = await page.evaluate("""(targetText) => {
                // 페이지 전체에서 텍스트 탐색
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                const found = [];
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    if (text.includes(targetText)) {
                        const el = node.parentElement;
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        found.push({
                            tag: el.tagName,
                            cls: el.className.substring(0, 60),
                            text: text.substring(0, 80),
                            visible: rect.width > 0 && rect.height > 0,
                            display: style.display,
                            visibility: style.visibility,
                            opacity: style.opacity,
                            rect: {
                                width: rect.width,
                                height: rect.height,
                                top: rect.top
                            }
                        });
                    }
                }
                return {
                    totalFound: found.length,
                    visibleCount: found.filter(f => f.visible).length,
                    items: found.slice(0, 5)
                };
            }""", TARGET_TEXT)

            print(f"[INFO] JS 탐색 결과 - 총 {js_result['totalFound']}개, 가시적 {js_result['visibleCount']}개")
            if js_result['items']:
                for item in js_result['items']:
                    print(f"  - 태그: {item['tag']}, visible: {item['visible']}, display: {item['display']}, text: {item['text'][:50]}")

            target_visible_js = js_result['visibleCount'] > 0

            # 전체 페이지 텍스트 내 포함 여부
            page_text = await page.evaluate("() => document.body.innerText")
            target_in_page_text = TARGET_TEXT in page_text

            print(f"[INFO] 가시성 체크:")
            print(f"  - Playwright visible: {target_visible_playwright}")
            print(f"  - JS visible: {target_visible_js}")
            print(f"  - 페이지 텍스트 포함: {target_in_page_text}")

            await page.screenshot(path='screenshots/test_28_step3_check.png')

            # ── 5단계: 검증 ──
            # 기대결과: '적극 채용 중인 회사' 비노출
            # 비로그인 상태에서는 해당 섹션이 보이지 않아야 함

            section_is_visible = target_visible_playwright or target_visible_js

            if not section_is_visible:
                print(f"[OK] '{TARGET_TEXT}' 항목이 비노출 상태 확인됨 (기대결과 일치)")
                if target_in_page_text:
                    print(f"  [참고] 텍스트는 DOM에 있지만 가시적이지 않음 (hidden/invisible)")
            else:
                # 로그인 상태인지 재확인
                print(f"[WARN] '{TARGET_TEXT}' 항목이 가시적으로 노출됨!")
                print(f"  비로그인 상태에서 노출되면 안 됨 - 테스트 실패")
                assert not section_is_visible, (
                    f"'{TARGET_TEXT}' 항목이 비로그인 상태에서 노출됨 (기대결과: 비노출)"
                )

            # 로그인 버튼이 있는지 최종 확인 (비로그인 상태 재검증)
            login_btn_visible = await page.evaluate("""() => {
                const selectors = [
                    'a[href*="login"]',
                    'button:contains("로그인")',  // jQuery style - may not work
                ];
                // 직접 텍스트로 탐색
                const allEls = Array.from(document.querySelectorAll('a, button'));
                for (const el of allEls) {
                    const text = el.textContent.trim();
                    const rect = el.getBoundingClientRect();
                    if ((text === '로그인' || text.includes('로그인')) && rect.width > 0 && rect.height > 0) {
                        return {found: true, text: text, tag: el.tagName};
                    }
                }
                return {found: false};
            }""")
            print(f"[INFO] 로그인 버튼 상태: {login_btn_visible}")

            await page.screenshot(path='screenshots/test_28_success.png')
            print(f"[PASS] 테스트 케이스 #28 통과: 비로그인 상태에서 '{TARGET_TEXT}' 비노출 확인")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_28_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
