from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

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

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # GNB 메뉴 항목 확인
            # 확인 항목: wanted(로고), 채용, 이력서, 교육•이벤트, 콘텐츠, 소셜, 프리랜서, 더보기, 검색(아이콘), 회원가입/로그인, 기업 서비스

            # header 영역으로 범위 제한
            header = page.locator('header').first

            # 1. 로고 확인
            logo = header.locator('a[href="/"]').first
            logo_visible = await logo.is_visible()
            print(f"{'✅' if logo_visible else '❌'} wanted 로고: {'노출' if logo_visible else '미노출'}")
            assert logo_visible, "wanted 로고가 노출되지 않음"

            # 2. 채용 메뉴
            job = header.get_by_role('link', name='채용', exact=True).first
            job_visible = await job.is_visible()
            print(f"{'✅' if job_visible else '❌'} 채용: {'노출' if job_visible else '미노출'}")
            assert job_visible, "채용 메뉴가 노출되지 않음"

            # 3. 이력서 메뉴
            resume = header.get_by_role('link', name='이력서', exact=True).first
            resume_visible = await resume.is_visible()
            print(f"{'✅' if resume_visible else '❌'} 이력서: {'노출' if resume_visible else '미노출'}")
            assert resume_visible, "이력서 메뉴가 노출되지 않음"

            # 4. 교육•이벤트 메뉴 (특수문자 처리)
            edu_locator = header.locator('a').filter(has_text='교육').first
            edu_visible = await edu_locator.is_visible()
            print(f"{'✅' if edu_visible else '❌'} 교육•이벤트: {'노출' if edu_visible else '미노출'}")
            assert edu_visible, "교육•이벤트 메뉴가 노출되지 않음"

            # 5. 콘텐츠 메뉴
            content = header.get_by_role('link', name='콘텐츠', exact=True).first
            content_visible = await content.is_visible()
            print(f"{'✅' if content_visible else '❌'} 콘텐츠: {'노출' if content_visible else '미노출'}")
            assert content_visible, "콘텐츠 메뉴가 노출되지 않음"

            # 6. 소셜 메뉴
            social = header.get_by_role('link', name='소셜', exact=True).first
            social_visible = await social.is_visible()
            print(f"{'✅' if social_visible else '❌'} 소셜: {'노출' if social_visible else '미노출'}")
            assert social_visible, "소셜 메뉴가 노출되지 않음"

            # 7. 프리랜서 메뉴
            freelancer = header.get_by_role('link', name='프리랜서', exact=True).first
            freelancer_visible = await freelancer.is_visible()
            print(f"{'✅' if freelancer_visible else '❌'} 프리랜서: {'노출' if freelancer_visible else '미노출'}")
            assert freelancer_visible, "프리랜서 메뉴가 노출되지 않음"

            # 8. 더보기 메뉴
            more = header.locator('button, a').filter(has_text='더보기').first
            more_visible = await more.is_visible()
            print(f"{'✅' if more_visible else '❌'} 더보기: {'노출' if more_visible else '미노출'}")
            assert more_visible, "더보기 메뉴가 노출되지 않음"

            # 9. 검색 아이콘
            search = header.locator('button[aria-label*="검색"], a[aria-label*="검색"], button[class*="search"], a[class*="search"]').first
            search_visible = await search.is_visible()
            print(f"{'✅' if search_visible else '❌'} 검색 아이콘: {'노출' if search_visible else '미노출'}")
            assert search_visible, "검색 아이콘이 노출되지 않음"

            # 10. 회원가입/로그인
            login = header.locator('a, button').filter(has_text='회원가입').first
            login_visible = await login.is_visible()
            print(f"{'✅' if login_visible else '❌'} 회원가입/로그인: {'노출' if login_visible else '미노출'}")
            assert login_visible, "회원가입/로그인이 노출되지 않음"

            # 11. 기업 서비스
            corp = header.locator('a, button').filter(has_text='기업 서비스').first
            corp_visible = await corp.is_visible()
            print(f"{'✅' if corp_visible else '❌'} 기업 서비스: {'노출' if corp_visible else '미노출'}")
            assert corp_visible, "기업 서비스가 노출되지 않음"

            await page.screenshot(path='screenshots/test_12_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_12_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
