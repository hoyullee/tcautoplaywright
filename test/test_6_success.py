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
            # wanted 로고
            logo = page.locator('a[aria-label="wanted"], a[href="/"][class*="logo"], header a img[alt*="wanted"], a[class*="logo"]')
            logo_visible = await logo.first.is_visible() if await logo.count() > 0 else False
            if not logo_visible:
                # 대안: 헤더 내 링크로 찾기
                logo_alt = page.locator('header').get_by_role('link', name='원티드')
                logo_visible = await logo_alt.is_visible() if await logo_alt.count() > 0 else False
            print(f"{'✅' if logo_visible else '❌'} wanted 로고: {'노출' if logo_visible else '미노출'}")

            # 채용
            menu_job = page.get_by_role('link', name='채용')
            job_visible = await menu_job.first.is_visible() if await menu_job.count() > 0 else False
            print(f"{'✅' if job_visible else '❌'} 채용: {'노출' if job_visible else '미노출'}")

            # 이력서
            menu_resume = page.get_by_role('link', name='이력서')
            resume_visible = await menu_resume.first.is_visible() if await menu_resume.count() > 0 else False
            print(f"{'✅' if resume_visible else '❌'} 이력서: {'노출' if resume_visible else '미노출'}")

            # 교육•이벤트
            menu_edu = page.get_by_role('link', name='교육•이벤트')
            edu_visible = await menu_edu.first.is_visible() if await menu_edu.count() > 0 else False
            if not edu_visible:
                menu_edu2 = page.get_by_text('교육', exact=False)
                edu_visible = await menu_edu2.first.is_visible() if await menu_edu2.count() > 0 else False
            print(f"{'✅' if edu_visible else '❌'} 교육•이벤트: {'노출' if edu_visible else '미노출'}")

            # 콘텐츠
            menu_content = page.get_by_role('link', name='콘텐츠')
            content_visible = await menu_content.first.is_visible() if await menu_content.count() > 0 else False
            print(f"{'✅' if content_visible else '❌'} 콘텐츠: {'노출' if content_visible else '미노출'}")

            # 소셜
            menu_social = page.get_by_role('link', name='소셜')
            social_visible = await menu_social.first.is_visible() if await menu_social.count() > 0 else False
            print(f"{'✅' if social_visible else '❌'} 소셜: {'노출' if social_visible else '미노출'}")

            # 프리랜서
            menu_freelancer = page.get_by_role('link', name='프리랜서')
            freelancer_visible = await menu_freelancer.first.is_visible() if await menu_freelancer.count() > 0 else False
            print(f"{'✅' if freelancer_visible else '❌'} 프리랜서: {'노출' if freelancer_visible else '미노출'}")

            # 더보기
            menu_more = page.get_by_role('button', name='더보기')
            more_visible = await menu_more.first.is_visible() if await menu_more.count() > 0 else False
            if not more_visible:
                menu_more2 = page.get_by_text('더보기')
                more_visible = await menu_more2.first.is_visible() if await menu_more2.count() > 0 else False
            print(f"{'✅' if more_visible else '❌'} 더보기: {'노출' if more_visible else '미노출'}")

            # 검색 아이콘
            search_icon = page.locator('button[aria-label*="검색"], button[class*="search"], [data-testid*="search"]')
            search_visible = await search_icon.first.is_visible() if await search_icon.count() > 0 else False
            if not search_visible:
                search_icon2 = page.get_by_role('button', name='검색')
                search_visible = await search_icon2.first.is_visible() if await search_icon2.count() > 0 else False
            print(f"{'✅' if search_visible else '❌'} 검색(아이콘): {'노출' if search_visible else '미노출'}")

            # 회원가입/로그인
            login_btn = page.get_by_role('link', name='회원가입/로그인')
            login_visible = await login_btn.first.is_visible() if await login_btn.count() > 0 else False
            if not login_visible:
                login_btn2 = page.get_by_text('로그인')
                login_visible = await login_btn2.first.is_visible() if await login_btn2.count() > 0 else False
            print(f"{'✅' if login_visible else '❌'} 회원가입/로그인: {'노출' if login_visible else '미노출'}")

            # 기업 서비스
            corp_btn = page.get_by_role('link', name='기업 서비스')
            corp_visible = await corp_btn.first.is_visible() if await corp_btn.count() > 0 else False
            if not corp_visible:
                corp_btn2 = page.get_by_text('기업 서비스')
                corp_visible = await corp_btn2.first.is_visible() if await corp_btn2.count() > 0 else False
            print(f"{'✅' if corp_visible else '❌'} 기업 서비스: {'노출' if corp_visible else '미노출'}")

            # 전체 결과 판정
            results = [job_visible, resume_visible, edu_visible, content_visible,
                       social_visible, freelancer_visible, more_visible,
                       search_visible, login_visible, corp_visible]
            all_passed = all(results)

            await page.screenshot(path='screenshots/test_6_success.png')

            if all_passed:
                print("✅ 테스트 성공 - 모든 GNB 메뉴 노출 확인")
                print("AUTOMATION_SUCCESS")
                return True
            else:
                failed_items = []
                labels = ['채용', '이력서', '교육•이벤트', '콘텐츠', '소셜', '프리랜서', '더보기', '검색', '회원가입/로그인', '기업 서비스']
                for label, result in zip(labels, results):
                    if not result:
                        failed_items.append(label)
                msg = f"일부 메뉴 미노출: {', '.join(failed_items)}"
                print(f"❌ 테스트 실패: {msg}")
                print(f"AUTOMATION_FAILED: {msg}")
                return False

        except Exception as e:
            await page.screenshot(path='screenshots/test_6_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
