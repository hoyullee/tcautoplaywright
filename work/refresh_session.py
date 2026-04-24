import sys
import io
import asyncio
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

async def refresh_session():
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
            # Navigate to login page
            print('[INFO] 로그인 페이지 접속...')
            await page.goto('https://id.wanted.co.kr/login?service=wanted', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)
            print(f'[INFO] URL: {page.url}')

            # Step 1: Click "이메일로 계속하기"
            print('[INFO] "이메일로 계속하기" 버튼 클릭...')
            email_btn = page.locator('button:has-text("이메일로 계속하기")')
            cnt = await email_btn.count()
            if cnt > 0:
                await email_btn.first.click()
                print('[OK] "이메일로 계속하기" 클릭')
                await page.wait_for_timeout(2000)
            else:
                print('[WARN] "이메일로 계속하기" 버튼을 찾을 수 없습니다')

            await page.screenshot(path='screenshots/refresh_login_step1.png')

            # Step 2: Fill email
            print('[INFO] 이메일 입력...')
            all_inputs = page.locator('input')
            cnt_input = await all_inputs.count()
            print(f'[INFO] 입력 필드 수: {cnt_input}')

            email_filled = False
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="이메일"]',
                'input[placeholder*="Email"]',
                'input[id*="email"]',
            ]
            for sel in email_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    if cnt > 0:
                        await loc.first.fill('hoyul.lee+1@wantedlab.com')
                        print(f'[OK] 이메일 입력 (selector={sel})')
                        email_filled = True
                        break
                except Exception as e:
                    continue

            if not email_filled and cnt_input > 0:
                # 첫 번째 visible input에 입력
                for i in range(cnt_input):
                    inp = all_inputs.nth(i)
                    try:
                        visible = await inp.is_visible()
                        if visible:
                            inp_type = await inp.get_attribute('type')
                            if inp_type not in ['hidden', 'submit', 'button', 'checkbox', 'radio']:
                                await inp.fill('hoyul.lee+1@wantedlab.com')
                                print(f'[OK] 이메일 입력 (input[{i}], type={inp_type})')
                                email_filled = True
                                break
                    except Exception:
                        continue

            # Click continue/next button
            print('[INFO] 계속하기 버튼 클릭...')
            continue_selectors = [
                'button[type="submit"]',
                'button:has-text("계속")',
                'button:has-text("다음")',
                'button:has-text("Continue")',
            ]
            for sel in continue_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    if cnt > 0:
                        await loc.first.click()
                        print(f'[OK] 계속 버튼 클릭 (selector={sel})')
                        break
                except Exception:
                    continue

            await page.wait_for_timeout(2000)
            print(f'[INFO] URL: {page.url}')
            await page.screenshot(path='screenshots/refresh_login_step2.png')

            # Step 3: Fill password
            print('[INFO] 비밀번호 입력...')
            pw_input = page.locator('input[type="password"]')
            cnt_pw = await pw_input.count()
            print(f'[INFO] 비밀번호 필드 수: {cnt_pw}')

            if cnt_pw > 0:
                await pw_input.first.fill('wanted12!@')
                print('[OK] 비밀번호 입력 완료')
            else:
                print('[ERROR] 비밀번호 입력 필드를 찾을 수 없습니다')
                # Check page content
                body_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
                print(f'[INFO] 페이지 텍스트: {body_text}')
                return False

            # Step 4: Click login button
            print('[INFO] 로그인 버튼 클릭...')
            login_selectors = [
                'button[type="submit"]',
                'button:has-text("로그인")',
                'button:has-text("계속")',
                'button:has-text("다음")',
            ]
            for sel in login_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    if cnt > 0:
                        await loc.first.click()
                        print(f'[OK] 로그인 버튼 클릭 (selector={sel})')
                        break
                except Exception:
                    continue

            await page.wait_for_timeout(5000)
            print(f'[INFO] 로그인 후 URL: {page.url}')
            await page.screenshot(path='screenshots/refresh_login_step3.png')

            # Verify login
            current_url = page.url
            body_text = await page.evaluate("() => document.body.innerText.substring(0, 300)")
            print(f'[INFO] 페이지 텍스트: {body_text[:200]}')

            # Save session regardless
            await context.storage_state(path='work/auth_state.json')
            print('[OK] 세션 저장 완료: work/auth_state.json')
            return True

        except Exception as e:
            print(f'[ERROR] {e}')
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()

if __name__ == '__main__':
    result = asyncio.run(refresh_session())
    sys.exit(0 if result else 1)
