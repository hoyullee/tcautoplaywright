import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import asyncio
from playwright.async_api import async_playwright

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR', timezone_id='Asia/Seoul',
            user_agent=REAL_UA, viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        # 1. 메인 페이지 → JS 클릭으로 로그인 이동
        await page.goto('https://www.wanted.co.kr/', timeout=30000)
        await page.wait_for_load_state('load')
        await page.wait_for_timeout(3000)
        await page.evaluate("""() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const loginBtn = buttons.find(b => b.innerText.includes('회원가입') || b.innerText.includes('로그인'));
            if (loginBtn) loginBtn.click();
        }""")
        await page.wait_for_url('**/login**', timeout=15000)
        await page.wait_for_load_state('load')
        await page.wait_for_timeout(2000)
        print(f"Step 1 - Login page URL: {page.url}")

        # 2. 이메일로 계속하기 클릭
        email_btn = page.get_by_role('button', name='이메일로 계속하기')
        count = await email_btn.count()
        print(f"Email button count: {count}")

        if count > 0:
            await email_btn.click()
            await page.wait_for_timeout(2000)
            print(f"Step 2 - After email click URL: {page.url}")

            # 이메일 입력 필드 확인
            inputs = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).map(el => ({
                    type: el.type,
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    id: el.id || ''
                }));
            }""")
            print(f"Input fields after email click:")
            for inp in inputs:
                print(f"  {inp}")

            btns = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button')).map(b => ({
                    text: b.innerText.trim().substring(0, 40),
                    type: b.type
                })).filter(b => b.text);
            }""")
            print(f"Buttons after email click:")
            for b in btns:
                print(f"  {b}")

        await page.screenshot(path='screenshots/email_login_page.png')
        await browser.close()

asyncio.run(check())
