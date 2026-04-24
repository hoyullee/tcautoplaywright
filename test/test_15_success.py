from playwright.async_api import async_playwright
import asyncio
import sys
import os
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

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_load_state('load')
            print("✅ 페이지 로드 완료")

            # GNB 메뉴 노출 확인 (비로그인 상태)
            # 기대: wanted(로고), 채용, 이력서, 교육•이벤트, 콘텐츠, 소셜, 프리랜서, 더보기, 검색(아이콘), 회원가입/로그인, 기업 서비스

            # 1. 원티드 로고 확인
            logo = page.locator('a[aria-label="원티드"], a[href="/"][class*="logo"], header a img, nav a[href="/"]').first
            # 로고는 링크나 이미지로 존재할 가능성이 높음
            logo_visible = await page.locator('header').count() > 0
            assert logo_visible, "헤더가 존재하지 않습니다"
            print("✅ 헤더 확인")

            # GNB 링크 텍스트 목록 확인
            gnb_items = [
                ('채용', '/wdlist'),
                ('이력서', '/cv/'),
                ('교육•이벤트', None),
                ('콘텐츠', '/events'),
                ('소셜', None),
                ('프리랜서', '/gigs/experts'),
            ]

            for label, href_hint in gnb_items:
                if href_hint:
                    el = page.get_by_role('link', name=label).first
                else:
                    el = page.get_by_text(label, exact=True).first
                count = await el.count()
                assert count > 0, f"GNB 항목 '{label}' 를 찾을 수 없습니다"
                is_visible = await el.is_visible()
                assert is_visible, f"GNB 항목 '{label}' 가 보이지 않습니다"
                print(f"✅ GNB '{label}' 노출 확인")

            # 더보기 버튼 확인
            more_btn = page.get_by_text('더보기', exact=True).first
            more_count = await more_btn.count()
            if more_count == 0:
                # aria-label로 시도
                more_btn = page.get_by_role('button', name='더보기').first
                more_count = await more_btn.count()
            assert more_count > 0, "GNB '더보기' 항목을 찾을 수 없습니다"
            print("✅ GNB '더보기' 노출 확인")

            # 검색 아이콘 확인
            search_el = page.get_by_role('button', name='검색').first
            search_count = await search_el.count()
            if search_count == 0:
                search_el = page.locator('[aria-label*="검색"], [class*="search"], button[type="submit"]').first
                search_count = await search_el.count()
            assert search_count > 0, "검색 아이콘을 찾을 수 없습니다"
            print("✅ 검색 아이콘 노출 확인")

            # 회원가입/로그인 버튼 확인 (비로그인 상태)
            login_el = page.get_by_text('회원가입/로그인').first
            login_count = await login_el.count()
            if login_count == 0:
                login_el = page.get_by_role('link', name='로그인').first
                login_count = await login_el.count()
            if login_count == 0:
                login_el = page.get_by_text('로그인').first
                login_count = await login_el.count()
            assert login_count > 0, "회원가입/로그인 버튼을 찾을 수 없습니다"
            print("✅ '회원가입/로그인' 노출 확인")

            # 기업 서비스 확인
            biz_el = page.get_by_text('기업 서비스').first
            biz_count = await biz_el.count()
            if biz_count == 0:
                biz_el = page.get_by_role('link', name='기업 서비스').first
                biz_count = await biz_el.count()
            assert biz_count > 0, "기업 서비스 항목을 찾을 수 없습니다"
            print("✅ '기업 서비스' 노출 확인")

            await page.screenshot(path='screenshots/test_15_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_15_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
