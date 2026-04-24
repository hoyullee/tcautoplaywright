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
            storage_state='work/auth_state.json',
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

            # 1. 헤더 존재 확인
            assert await page.locator('header').count() > 0, "헤더가 존재하지 않습니다"
            print("✅ 헤더 확인")

            # 2. GNB 메뉴 텍스트 항목 확인
            gnb_items = ['채용', '이력서', '교육•이벤트', '콘텐츠', '소셜', '프리랜서']
            for label in gnb_items:
                el = page.get_by_role('link', name=label).first
                count = await el.count()
                if count == 0:
                    el = page.get_by_text(label, exact=True).first
                    count = await el.count()
                assert count > 0, f"GNB 항목 '{label}' 를 찾을 수 없습니다"
                assert await el.is_visible(), f"GNB 항목 '{label}' 가 보이지 않습니다"
                print(f"✅ GNB '{label}' 노출 확인")

            # 3. 더보기 버튼 확인
            more_btn = page.get_by_role('button', name='더보기').first
            more_count = await more_btn.count()
            if more_count == 0:
                more_btn = page.get_by_text('더보기', exact=True).first
                more_count = await more_btn.count()
            assert more_count > 0, "GNB '더보기' 항목을 찾을 수 없습니다"
            print("✅ GNB '더보기' 노출 확인")

            # 4. 검색 아이콘 확인
            search_el = page.get_by_role('button', name='검색').first
            search_count = await search_el.count()
            if search_count == 0:
                search_el = page.locator('[aria-label*="검색"], [class*="search"]').first
                search_count = await search_el.count()
            assert search_count > 0, "검색 아이콘을 찾을 수 없습니다"
            print("✅ 검색 아이콘 노출 확인")

            # 5. 알림센터 아이콘 확인 (로그인 상태)
            alarm_el = page.get_by_role('button', name='알림').first
            alarm_count = await alarm_el.count()
            if alarm_count == 0:
                alarm_el = page.locator('[aria-label*="알림"], [class*="alarm"], [class*="notification"]').first
                alarm_count = await alarm_el.count()
            assert alarm_count > 0, "알림센터 아이콘을 찾을 수 없습니다"
            print("✅ 알림센터 아이콘 노출 확인")

            # 6. 프로필 아이콘 확인 (로그인 상태 - aria-label: "MY 원티드")
            profile_el = page.get_by_role('link', name='MY 원티드').first
            profile_count = await profile_el.count()
            if profile_count == 0:
                profile_el = page.locator('[aria-label*="MY 원티드"], [aria-label*="프로필"], [class*="profile"], [class*="avatar"]').first
                profile_count = await profile_el.count()
            assert profile_count > 0, "프로필 아이콘을 찾을 수 없습니다"
            print("✅ 프로필 아이콘 노출 확인")

            # 7. 기업 서비스 확인
            biz_el = page.get_by_text('기업 서비스').first
            biz_count = await biz_el.count()
            if biz_count == 0:
                biz_el = page.get_by_role('link', name='기업 서비스').first
                biz_count = await biz_el.count()
            assert biz_count > 0, "기업 서비스 항목을 찾을 수 없습니다"
            print("✅ '기업 서비스' 노출 확인")

            await page.screenshot(path='screenshots/test_16_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_16_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
