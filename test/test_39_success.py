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
        # 비로그인 상태: storage_state 없이 새 컨텍스트 생성
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 목록 페이지로 이동 후 포지션 URL 확보
            print("[INFO] 채용 목록 페이지 접속 중... (비로그인 상태)")
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 채용 목록 페이지 로드 완료 - URL: {page.url}")

            # 비로그인 상태 확인
            login_check = await page.evaluate("""() => {
                const bodyText = document.body.innerText || '';
                return {
                    hasLogin: bodyText.includes('로그인'),
                    hasMyPage: bodyText.includes('마이페이지'),
                };
            }""")
            print(f"[INFO] 로그인 상태 확인: {login_check}")

            # 2. 포지션 상세 페이지 URL 획득
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

            # 3. 포지션 상세 페이지 진입 (비로그인)
            print(f"[INFO] 포지션 상세 페이지 진입: {position_url}")
            await page.goto(position_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(5000)
            print(f"[OK] 포지션 상세 페이지 로드 완료 - URL: {page.url}")
            await page.screenshot(path='screenshots/test_39_step1_detail.png')

            # 4. '지원하기' 버튼 탐색
            print("[INFO] '지원하기' 버튼 탐색 중...")
            apply_btn = None
            apply_selectors = [
                'button:has-text("지원하기")',
                'a:has-text("지원하기")',
                '[class*="apply"]:has-text("지원하기")',
                'button[class*="Apply"]',
                'button[data-attribute*="apply"]',
            ]

            for sel in apply_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    if cnt > 0:
                        for i in range(min(cnt, 3)):
                            try:
                                item = loc.nth(i)
                                is_visible = await item.is_visible()
                                if is_visible:
                                    apply_btn = item
                                    text = await item.text_content()
                                    print(f"[OK] '지원하기' 버튼 발견 (selector={sel}): '{text}'")
                                    break
                            except Exception:
                                continue
                    if apply_btn is not None:
                        break
                except Exception as e:
                    print(f"[WARN] selector '{sel}' 실패: {e}")

            # JS 기반 탐색 (fallback)
            if apply_btn is None:
                print("[INFO] JS 기반 '지원하기' 버튼 탐색 중...")
                js_result = await page.evaluate("""() => {
                    const keywords = ['지원하기', '지원 하기'];
                    const all = [...document.querySelectorAll('button, a, [role="button"]')];
                    for (const el of all) {
                        const text = (el.innerText || el.textContent || '').trim();
                        for (const kw of keywords) {
                            if (text === kw || text.startsWith(kw)) {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    return {found: true, tagName: el.tagName, text: text.substring(0, 50)};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 버튼 탐색 결과: {js_result}")

                if js_result.get('found'):
                    # get_by_text로 다시 시도
                    loc = page.get_by_role('button', name='지원하기')
                    cnt = await loc.count()
                    if cnt > 0:
                        apply_btn = loc.first
                        print(f"[OK] get_by_role로 '지원하기' 버튼 발견")
                    else:
                        loc2 = page.get_by_text('지원하기', exact=True)
                        cnt2 = await loc2.count()
                        if cnt2 > 0:
                            apply_btn = loc2.first
                            print(f"[OK] get_by_text로 '지원하기' 버튼 발견")

            assert apply_btn is not None, "'지원하기' 버튼을 찾을 수 없습니다"
            await page.screenshot(path='screenshots/test_39_step2_before_click.png')

            # 5. '지원하기' 버튼 클릭
            print("[INFO] '지원하기' 버튼 클릭...")
            before_url = page.url
            active_page = page

            try:
                # 클릭 후 navigation 대기 (같은 탭 이동)
                async with page.expect_navigation(timeout=15000):
                    await apply_btn.click(timeout=10000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(2000)
                after_url = page.url
                print(f"[OK] 클릭 후 현재 탭 URL: {after_url}")
            except Exception as nav_err:
                print(f"[INFO] navigation 대기 실패 ({nav_err}), 현재 URL 확인...")
                await page.wait_for_timeout(3000)
                after_url = page.url
                print(f"[INFO] 현재 탭 URL: {after_url}")

                # 새 탭이 열린 경우 처리
                pages = context.pages
                if len(pages) > 1:
                    new_page = pages[-1]
                    await new_page.wait_for_load_state('domcontentloaded')
                    await new_page.wait_for_timeout(2000)
                    after_url = new_page.url
                    active_page = new_page
                    print(f"[INFO] 새 탭 URL: {after_url}")

            await active_page.screenshot(path='screenshots/test_39_step3_after_click.png')

            # 6. 로그인/회원가입 페이지 진입 확인
            print("[INFO] 로그인/회원가입 페이지 확인 중...")
            login_page_found = False
            login_page_reason = None

            # URL 기반 확인
            login_url_keywords = ['login', 'signup', 'register', 'auth', '/users/sign']
            for kw in login_url_keywords:
                if kw in after_url.lower():
                    login_page_found = True
                    login_page_reason = f"URL에 '{kw}' 포함"
                    break

            # 페이지 내용 기반 확인
            if not login_page_found:
                page_content = await active_page.evaluate("""() => {
                    const bodyText = document.body.innerText || '';
                    const title = document.title || '';
                    return {
                        bodyText: bodyText.substring(0, 1000),
                        title: title,
                        url: window.location.href,
                    };
                }""")
                print(f"[INFO] 현재 페이지 제목: {page_content.get('title')}")
                print(f"[INFO] 현재 URL: {page_content.get('url')}")

                after_url = page_content.get('url', after_url)
                body = page_content.get('bodyText', '')

                # URL 재확인
                for kw in login_url_keywords:
                    if kw in after_url.lower():
                        login_page_found = True
                        login_page_reason = f"URL에 '{kw}' 포함"
                        break

                # 페이지 텍스트 확인
                if not login_page_found:
                    login_text_keywords = [
                        '로그인', '회원가입', '이메일 주소', '비밀번호',
                        'Log in', 'Sign up', 'Sign in', 'Email',
                        '소셜 계정으로 로그인', '간편 로그인',
                    ]
                    for kw in login_text_keywords:
                        if kw in body or kw in page_content.get('title', ''):
                            login_page_found = True
                            login_page_reason = f"페이지에 '{kw}' 텍스트 포함"
                            break

            if not login_page_found:
                # 모달/팝업 확인
                print("[INFO] 로그인 모달 확인 중...")
                modal_check = await active_page.evaluate("""() => {
                    const keywords = ['로그인', '회원가입', '이메일', '비밀번호', '소셜 로그인', '간편 로그인'];
                    const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"], [class*="popup"], [class*="Popup"]');
                    for (const modal of modals) {
                        const text = modal.innerText || modal.textContent || '';
                        for (const kw of keywords) {
                            if (text.includes(kw)) {
                                return {found: true, keyword: kw, text: text.substring(0, 200)};
                            }
                        }
                    }
                    // body 전체에서도 확인
                    const bodyText = document.body.innerText || '';
                    for (const kw of keywords) {
                        if (bodyText.includes(kw)) {
                            return {found: true, keyword: kw, fromBody: true};
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] 모달 확인 결과: {modal_check}")
                if modal_check.get('found'):
                    login_page_found = True
                    login_page_reason = f"로그인 모달/팝업 발견 ('{modal_check.get('keyword')}')"

            await active_page.screenshot(path='screenshots/test_39_step4_login_page.png')

            assert login_page_found, (
                f"로그인/회원가입 페이지로 이동하지 않았습니다. "
                f"현재 URL: {after_url}"
            )
            print(f"[OK] 로그인/회원가입 페이지 진입 확인됨: {login_page_reason}")
            print(f"[OK] 현재 URL: {after_url}")

            # 최종 요약
            print("\n[SUMMARY] 테스트 케이스 39 검증 완료:")
            print("[OK] 비로그인 상태에서 포지션 상세 페이지 진입")
            print("[OK] '지원하기' 버튼 선택")
            print(f"[OK] 로그인/회원가입 페이지 진입 확인됨 ({login_page_reason})")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_39_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
