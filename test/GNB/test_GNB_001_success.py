import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # GNB 메뉴 항목 확인
            missing_items = []

            # 1. wanted 로고 확인
            logo = page.locator('a[href="/"]').first
            logo_visible = await logo.is_visible()
            if not logo_visible:
                logo_alt = page.locator('[class*="gnb"] img, [class*="header"] img, [class*="logo"]').first
                logo_visible = await logo_alt.is_visible()
            if not logo_visible:
                missing_items.append('wanted 로고')

            # 2. 채용 메뉴 확인
            job_menu = page.get_by_role('link', name='채용').first
            job_visible = await job_menu.is_visible()
            if not job_visible:
                missing_items.append('채용')

            # 3. 이력서 메뉴 확인
            resume_menu = page.get_by_role('link', name='이력서').first
            resume_visible = await resume_menu.is_visible()
            if not resume_visible:
                missing_items.append('이력서')

            # 4. 교육•이벤트 메뉴 확인
            edu_menu = page.get_by_role('link', name='교육·이벤트').first
            edu_visible = await edu_menu.is_visible()
            if not edu_visible:
                edu_menu2 = page.get_by_text('교육').first
                edu_visible = await edu_menu2.is_visible()
            if not edu_visible:
                missing_items.append('교육•이벤트')

            # 5. 콘텐츠 메뉴 확인
            content_menu = page.get_by_role('link', name='콘텐츠').first
            content_visible = await content_menu.is_visible()
            if not content_visible:
                missing_items.append('콘텐츠')

            # 6. 소셜 메뉴 확인
            social_menu = page.get_by_role('link', name='소셜').first
            social_visible = await social_menu.is_visible()
            if not social_visible:
                missing_items.append('소셜')

            # 7. 프리랜서 메뉴 확인
            freelancer_menu = page.get_by_role('link', name='프리랜서').first
            freelancer_visible = await freelancer_menu.is_visible()
            if not freelancer_visible:
                missing_items.append('프리랜서')

            # 8. 더보기 메뉴 확인
            more_menu = page.get_by_role('button', name='더보기').first
            more_visible = await more_menu.is_visible()
            if not more_visible:
                more_menu2 = page.get_by_text('더보기').first
                more_visible = await more_menu2.is_visible()
            if not more_visible:
                missing_items.append('더보기')

            # 9. 검색 아이콘 확인
            search_btn = page.get_by_role('button', name='검색').first
            search_visible = await search_btn.is_visible()
            if not search_visible:
                search_btn2 = page.locator('[aria-label="검색"], [class*="search"] button, button[class*="search"]').first
                search_visible = await search_btn2.is_visible()
            if not search_visible:
                missing_items.append('검색(아이콘)')

            # 10. 회원가입/로그인 버튼 확인 (BUTTON 태그)
            login_btn = page.get_by_role('button', name='회원가입/로그인')
            login_visible = await login_btn.is_visible()
            if not login_visible:
                # 텍스트로 직접 탐색
                login_btn2 = page.locator('button').filter(has_text='회원가입/로그인').first
                login_visible = await login_btn2.is_visible()
            if not login_visible:
                login_btn3 = page.get_by_text('회원가입/로그인', exact=False).first
                login_visible = await login_btn3.is_visible()
            if not login_visible:
                missing_items.append('회원가입/로그인')

            # 11. 기업 서비스 버튼 확인
            company_btn = page.get_by_role('link', name='기업 서비스').first
            company_visible = await company_btn.is_visible()
            if not company_visible:
                company_btn2 = page.get_by_text('기업 서비스').first
                company_visible = await company_btn2.is_visible()
            if not company_visible:
                missing_items.append('기업 서비스')

            if missing_items:
                raise AssertionError(f"GNB에서 다음 항목이 보이지 않습니다: {', '.join(missing_items)}")

            print("✅ GNB 모든 메뉴 항목 확인 완료")
            print("  - wanted 로고, 채용, 이력서, 교육•이벤트, 콘텐츠, 소셜, 프리랜서, 더보기, 검색, 회원가입/로그인, 기업 서비스")

            await page.screenshot(path='screenshots/test_26_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_26_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
