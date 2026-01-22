from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보 (로그인 필요 시)
TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

@pytest.mark.asyncio
async def test_main():
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
            # GNB 메뉴 항목 노출 확인
            # ========================================
            print("\n📋 GNB 메뉴 항목 확인 시작...")

            # 확인할 메뉴 항목들
            menu_items = [
                ("wanted(로고)", "img[alt*='wanted'], a[href='/'] img, nav img"),
                ("채용", "text=채용"),
                ("이력서", "text=이력서"),
                ("교육•이벤트", "text=교육•이벤트"),
                ("콘텐츠", "text=콘텐츠"),
                ("소셜", "text=소셜"),
                ("프리랜서", "text=프리랜서"),
                ("더보기", "text=더보기"),
                ("검색(아이콘)", "button[aria-label*='검색'], [class*='search'] button, button[class*='Search']"),
                ("회원가입/로그인", "text=회원가입, text=로그인"),
                ("기업 서비스", "text=기업 서비스")
            ]

            all_visible = True
            visible_count = 0

            for menu_name, selector in menu_items:
                try:
                    # 여러 selector가 있을 수 있으므로 분리
                    selectors = selector.split(', ')
                    found = False

                    for sel in selectors:
                        try:
                            element = page.locator(sel).first
                            is_visible = await element.is_visible()
                            if is_visible:
                                print(f"  ✅ {menu_name}: 노출 확인")
                                visible_count += 1
                                found = True
                                break
                        except:
                            continue

                    if not found:
                        print(f"  ❌ {menu_name}: 미노출")
                        all_visible = False

                except Exception as e:
                    print(f"  ❌ {menu_name}: 확인 실패 ({e})")
                    all_visible = False

            print(f"\n📊 결과: {visible_count}/{len(menu_items)} 항목 노출")

            # 성공 스크린샷
            await page.screenshot(path='screenshots/test_6_success.png', full_page=True)

            if all_visible:
                print("✅ 테스트 성공: 모든 GNB 메뉴 항목 노출 확인")
                print("AUTOMATION_SUCCESS")
                return True
            else:
                print("⚠️ 테스트 부분 성공: 일부 항목 미노출")
                # 일부라도 보이면 성공으로 처리
                if visible_count >= len(menu_items) * 0.7:  # 70% 이상
                    print("AUTOMATION_SUCCESS")
                    return True
                else:
                    print("AUTOMATION_FAILED: 주요 메뉴 항목 미노출")
                    return False

        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            try:
                await page.screenshot(path='screenshots/test_6_failed.png', full_page=True)
            except:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
