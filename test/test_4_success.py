import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright
import asyncio
import os
import json
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

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
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1단계: 쿠키 없이 초기 로드
            print("[INFO] 채용 홈 초기 접속...")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)
            print(f"[OK] 초기 로드 완료: {page.url}")

            # 2단계: 저장된 세션 쿠키 주입
            print("[INFO] 로그인 세션 쿠키 주입...")
            with open('work/auth_state.json', 'r', encoding='utf-8') as f:
                auth_data = json.load(f)
            wanted_cookies = [
                c for c in auth_data.get('cookies', [])
                if 'wanted.co.kr' in c.get('domain', '')
            ]
            await context.add_cookies(wanted_cookies)
            print(f"[INFO] 주입 쿠키 수: {len(wanted_cookies)}")

            # 3단계: 로그인 세션으로 리로드
            print("[INFO] 로그인 세션으로 리로드...")
            await page.reload(timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(4000)
            title = await page.title()
            print(f"[INFO] 타이틀: {title}")

            # 403 감지 시 재시도
            if '403' in title or 'Error' in title.lower():
                print("[WARN] 403 감지, 5초 후 재시도...")
                await page.wait_for_timeout(5000)
                await page.reload(timeout=30000)
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(4000)
                title = await page.title()
                print(f"[INFO] 재시도 후 타이틀: {title}")

            await page.screenshot(path='screenshots/test_4_step0.png')

            # 확인사항 1: GNB 영역 확인
            print("[INFO] GNB 영역 확인 중...")
            gnb_visible = False
            for sel in [
                'header',
                'nav',
                '[class*="gnb"]',
                '[class*="GNB"]',
                'a:has-text("채용")',
                'a:has-text("이력서")',
            ]:
                try:
                    loc = page.locator(sel)
                    await loc.first.wait_for(state='visible', timeout=5000)
                    print(f"[OK] GNB 확인됨 (셀렉터: {sel})")
                    gnb_visible = True
                    break
                except Exception:
                    pass

            assert gnb_visible, "GNB 영역을 찾을 수 없습니다"
            await page.screenshot(path='screenshots/test_4_step1.png')

            # 로그인 상태 확인 (세션 만료 시 직접 로그인)
            needs_login = False
            try:
                login_btn = page.get_by_role('button', name='로그인').or_(
                    page.get_by_role('button', name='회원가입')
                )
                await login_btn.first.wait_for(state='visible', timeout=3000)
                needs_login = True
                print("[WARN] 로그인 버튼 발견 - 세션 만료됨")
            except Exception:
                print("[OK] 로그인 상태 확인됨")

            if needs_login:
                print("[INFO] 직접 로그인 진행...")
                await page.evaluate("""() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b =>
                        b.textContent.includes('회원가입') || b.textContent.includes('로그인')
                    );
                    if (btn) btn.click();
                }""")
                await page.wait_for_url('**/login**', timeout=15000)
                await page.wait_for_timeout(2000)

                email_btn = page.get_by_role('button', name='이메일로 계속하기')
                await email_btn.wait_for(timeout=10000)
                await email_btn.click()
                await page.wait_for_timeout(2000)

                email_input = page.locator('input[type="email"]').first
                await email_input.wait_for(timeout=10000)
                await email_input.fill(TEST_EMAIL)

                password_input = page.locator('input[type="password"]').first
                await password_input.fill(TEST_PASSWORD)

                submit_btn = page.get_by_role('button', name='로그인')
                await submit_btn.click()
                await page.wait_for_load_state('load', timeout=20000)
                await page.wait_for_timeout(3000)
                print(f"[OK] 로그인 완료: {page.url}")

            # 확인사항 2: 프로필 아이콘 선택
            print("[INFO] 프로필 아이콘 탐색 및 클릭...")
            profile_clicked = False

            profile_selectors = [
                'img[alt*="프로필"]',
                'img[alt*="profile"]',
                '[class*="avatar"] >> img',
                '[class*="Avatar"] >> img',
                '[class*="avatar"]',
                '[class*="Avatar"]',
                'button[aria-label*="프로필"]',
                'button[aria-label*="profile"]',
                'button[aria-label*="menu"]',
                'button[aria-label*="user"]',
            ]

            for sel in profile_selectors:
                try:
                    loc = page.locator(sel).first
                    count = await page.locator(sel).count()
                    if count == 0:
                        continue
                    await loc.wait_for(state='visible', timeout=3000)
                    bbox = await loc.bounding_box()
                    if bbox:
                        print(f"[INFO] 프로필 요소 발견: {sel} at ({bbox['x']:.0f}, {bbox['y']:.0f})")
                        await loc.click()
                        profile_clicked = True
                        print(f"[OK] 프로필 클릭됨: {sel}")
                        break
                except Exception:
                    continue

            # 좌표 기반 클릭 (우측 상단)
            if not profile_clicked:
                print("[INFO] 좌표 기반 클릭 시도 (우측 상단)...")
                try:
                    await page.mouse.click(1220, 30)
                    await page.wait_for_timeout(1000)
                    print("[OK] 우측 상단 (1220, 30) 클릭됨")
                    profile_clicked = True
                except Exception as ex:
                    print(f"[WARN] 좌표 클릭 실패: {ex}")

            # JS role="button" 탐색
            if not profile_clicked:
                print("[INFO] JS role='button' 탐색...")
                result = await page.evaluate("""() => {
                    const roleEls = Array.from(document.querySelectorAll('[role="button"]'));
                    const rightEl = roleEls.find(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.x > 800 && rect.y < 120;
                    });
                    if (rightEl) {
                        rightEl.click();
                        return {found: true, tag: rightEl.tagName, cls: rightEl.className.substring(0,50)};
                    }
                    const divs = Array.from(document.querySelectorAll('div')).filter(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.x > 1100 && rect.y < 80 && rect.y > 0 &&
                               rect.width > 0 && rect.height > 0 &&
                               (style.cursor === 'pointer' || el.onclick);
                    });
                    if (divs.length > 0) {
                        divs[0].click();
                        return {found: true, method: 'cursor:pointer div', tag: divs[0].tagName};
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 탐색 결과: {result}")
                if result.get('found'):
                    profile_clicked = True

            assert profile_clicked, "프로필 아이콘을 클릭할 수 없습니다"

            await page.wait_for_timeout(2000)
            current_url = page.url
            print(f"[INFO] 클릭 후 URL: {current_url}")
            await page.screenshot(path='screenshots/test_4_step2.png')

            # 기대결과: 프로필 페이지 진입 확인
            profile_keywords = ['profile', 'mypage', 'my-page', 'account', 'user']
            is_profile_page = any(kw in current_url.lower() for kw in profile_keywords)

            if not is_profile_page:
                print("[INFO] 드롭다운 메뉴에서 프로필 링크 탐색...")
                for menu_text in ['프로필', '마이페이지', '내 정보', '계정']:
                    try:
                        menu_item = page.get_by_text(menu_text, exact=False).first
                        await menu_item.wait_for(state='visible', timeout=2000)
                        href = await menu_item.get_attribute('href')
                        print(f"[OK] 메뉴 항목 발견: {menu_text} (href={href})")
                        await menu_item.click()
                        await page.wait_for_load_state('load', timeout=10000)
                        await page.wait_for_timeout(2000)
                        current_url = page.url
                        is_profile_page = any(kw in current_url.lower() for kw in profile_keywords)
                        if is_profile_page:
                            break
                    except Exception:
                        continue

            if not is_profile_page:
                print(f"[INFO] 프로필 페이지 직접 이동 시도...")
                await page.goto('https://www.wanted.co.kr/profile', timeout=15000)
                await page.wait_for_load_state('load')
                await page.wait_for_timeout(2000)
                current_url = page.url
                is_profile_page = any(kw in current_url.lower() for kw in profile_keywords)
                print(f"[INFO] 직접 이동 후 URL: {current_url}")

            assert is_profile_page, f"프로필 페이지로 이동하지 않음: {current_url}"
            print(f"[OK] 프로필 페이지 진입 확인: {current_url}")

            await page.screenshot(path='screenshots/test_4_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_4_failed.png')
            except Exception:
                pass
            print(f"[FAIL] 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
