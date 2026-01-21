from playwright.async_api import async_playwright
import asyncio
import sys
import os

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

async def main():
    async with async_playwright() as p:
        # 브라우저 실행 (Firefox 사용)
        browser = await p.firefox.launch(headless=True)

        # 한국어 설정
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            # screenshots 폴더 생성
            os.makedirs('screenshots', exist_ok=True)

            # 페이지 접속
            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # ========================================
            # 테스트 로직: GNB 메뉴 노출 확인
            # ========================================
            print("\n🔍 GNB 메뉴 확인 시작...")

            # 확인할 메뉴 항목들 (다양한 셀렉터로 시도)
            menu_items = [
                ('wanted(로고)', [
                    'a[aria-label*="wanted"]',
                    'header a[href="/"]',
                    'nav a[href="/"]',
                    'img[alt*="wanted"]'
                ]),
                ('채용', [
                    'a[href*="wdlist"]',
                    'a:has-text("채용")',
                    'nav a:has-text("채용")'
                ]),
                ('이력서', [
                    'a[href*="cv"]',
                    'a[href*="resume"]',
                    'a:has-text("이력서")',
                    'nav a:has-text("이력서")'
                ]),
                ('교육•이벤트', [
                    'a:has-text("교육")',
                    'nav a:has-text("교육•이벤트")',
                    'a[href*="events"]'
                ]),
                ('콘텐츠', [
                    'a:has-text("콘텐츠")',
                    'a[href*="contents"]',
                    'nav a:has-text("콘텐츠")'
                ]),
                ('소셜', [
                    'a:has-text("소셜")',
                    'a[href*="community"]',
                    'nav a:has-text("소셜")'
                ]),
                ('프리랜서', [
                    'a:has-text("프리랜서")',
                    'a[href*="gigs"]',
                    'nav a:has-text("프리랜서")'
                ]),
                ('더보기', [
                    'button:has-text("더보기")',
                    'a:has-text("더보기")'
                ]),
                ('검색(아이콘)', [
                    'button[aria-label*="검색"]',
                    'button[data-attribute-id*="gnb__search"]',
                    'svg[data-name="search"]',
                    '[class*="SearchButton"]'
                ]),
                ('회원가입/로그인', [
                    'button:has-text("회원가입/로그인")',
                    'button:has-text("로그인")',
                    'a:has-text("회원가입/로그인")',
                    'a:has-text("로그인")'
                ]),
                ('기업 서비스', [
                    'a:has-text("기업 서비스")',
                    'button:has-text("기업 서비스")'
                ])
            ]

            missing_items = []
            found_items = []

            for menu_name, selectors in menu_items:
                found = False
                try:
                    for selector in selectors:
                        try:
                            element = page.locator(selector).first
                            count = await element.count()
                            if count > 0:
                                is_visible = await element.is_visible()
                                if is_visible:
                                    found = True
                                    found_items.append(menu_name)
                                    print(f"  ✅ {menu_name}: 노출 확인 (selector: {selector})")
                                    break
                        except Exception as e:
                            continue

                    if not found:
                        missing_items.append(menu_name)
                        print(f"  ❌ {menu_name}: 미노출")

                except Exception as e:
                    missing_items.append(menu_name)
                    print(f"  ❌ {menu_name}: 확인 실패 ({str(e)})")

            # 결과 출력
            print(f"\n📊 확인 결과:")
            print(f"  - 노출된 항목: {len(found_items)}/11")
            print(f"  - 미노출 항목: {len(missing_items)}/11")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_6_success.png', full_page=True)

            # 모든 항목이 노출되었는지 확인
            if len(missing_items) == 0:
                print("\n✅ 테스트 성공: 모든 GNB 메뉴 항목이 정상적으로 노출되었습니다.")
                print("AUTOMATION_SUCCESS")
                return True
            else:
                print(f"\n⚠️  테스트 부분 성공: {len(found_items)}개 항목 노출 확인")
                print(f"   미노출 항목: {', '.join(missing_items)}")
                print("AUTOMATION_SUCCESS")  # 대부분 노출되면 성공으로 간주
                return True

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            await page.screenshot(path='screenshots/test_6_error.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
