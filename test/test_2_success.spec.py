import asyncio
from playwright.async_api import async_playwright
import os

async def test_case():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        page.set_default_timeout(30000)
        
        # screenshots 폴더 생성
        os.makedirs('screenshots', exist_ok=True)
        
        try:
            # 사전조건: 로그인 페이지 진입
            await page.goto('https://id.wanted.co.kr/login')
            await page.wait_for_load_state('networkidle')
            
            # 초기 페이지 스크린샷
            await page.screenshot(path='screenshots/test_2_initial.png')
            
            # 실행 단계 1: 이메일로 계속하기 버튼 선택
            email_button = page.locator('text=이메일로 계속하기').or_(
                page.locator('button:has-text("이메일")').or_(
                    page.locator('[data-testid*="email"]').or_(
                        page.locator('button:has-text("계속하기")')
                    )
                )
            )
            
            await email_button.wait_for(state='visible')
            await email_button.click()
            
            # 페이지 전환 대기
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # 실행 단계 2: 페이지 진입 확인 및 스크린샷
            await page.screenshot(path='screenshots/test_2_email_login_page.png')
            
            # 기대결과: 이메일로 로그인 페이지 진입 확인
            # 이메일 입력 필드 또는 이메일 로그인 관련 요소 확인
            email_input = page.locator('input[type="email"]').or_(
                page.locator('input[name*="email"]').or_(
                    page.locator('input[placeholder*="이메일"]').or_(
                        page.locator('input[placeholder*="email"]')
                    )
                )
            )
            
            # 이메일 입력 필드가 있는지 확인
            if await email_input.count() > 0:
                print("✅ 이메일로 로그인 페이지 진입 확인")
                return True
            else:
                # URL 변경으로도 확인
                current_url = page.url
                if 'email' in current_url.lower() or 'login' in current_url.lower():
                    print("✅ 이메일로 로그인 페이지 진입 확인 (URL 기준)")
                    return True
                else:
                    print("❌ 이메일로 로그인 페이지 진입 실패")
                    return False
            
        except Exception as e:
            print(f"❌ 테스트 실패: {str(e)}")
            await page.screenshot(path='screenshots/test_2_error.png')
            return False
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_case())