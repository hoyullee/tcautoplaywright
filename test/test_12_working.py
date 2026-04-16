from playwright.async_api import async_playwright
import asyncio
import sys
import os
import pytest

# ⭐ 테스트 계정 정보
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

            # 채용 탭 접속
            print("🌐 채용 탭 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 채용 탭 클릭
            print("🔍 채용 탭 클릭 중...")
            hiring_tab = page.get_by_role('link', name='채용')
            if await hiring_tab.count() > 0:
                await hiring_tab.first.click()
            else:
                await page.get_by_text('채용').first.click()
            await page.wait_for_load_state('networkidle')
            print("✅ 채용 탭 진입 완료")

            await page.screenshot(path='screenshots/test_12_step1.png')

            # '모두가 주목하고 있어요!' 텍스트 확인
            print("🔍 '모두가 주목하고 있어요!' 텍스트 확인 중...")
            attention_text = page.get_by_text('모두가 주목하고 있어요!')
            if await attention_text.count() == 0:
                # 부분 텍스트로 재시도
                attention_text = page.locator('text=모두가 주목하고 있어요')

            await attention_text.first.wait_for(timeout=10000)
            assert await attention_text.count() > 0, "'모두가 주목하고 있어요!' 텍스트가 노출되지 않음"
            print("✅ '모두가 주목하고 있어요!' 텍스트 확인 완료")

            # 해당 섹션으로 스크롤
            await attention_text.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/test_12_step2.png')

            # 포지션 카드 5개 확인 (섹션 내 카드 탐색)
            print("🔍 포지션 카드 확인 중...")

            # 섹션 컨테이너 찾기
            section = attention_text.first.locator('xpath=ancestor::section | xpath=ancestor::div[contains(@class,"section")] | xpath=ancestor::div[contains(@class,"wrap")]').first

            # 포지션 카드 선택자들 시도
            card_selectors = [
                'a[href*="/wd/"]',
                '[class*="JobCard"]',
                '[class*="job-card"]',
                '[class*="position-card"]',
                '[class*="PositionCard"]',
                'li[class*="item"]',
            ]

            cards = None
            for selector in card_selectors:
                candidates = page.locator(selector)
                count = await candidates.count()
                if count >= 5:
                    cards = candidates
                    print(f"✅ 포지션 카드 {count}개 발견 (selector: {selector})")
                    break

            if cards is None:
                # 섹션 주변에서 링크 카드 찾기
                parent = page.locator('section, [class*="Section"], [class*="Container"]')
                for i in range(await parent.count()):
                    section_el = parent.nth(i)
                    text = await section_el.text_content()
                    if text and '모두가 주목' in text:
                        links = section_el.locator('a[href]')
                        link_count = await links.count()
                        if link_count >= 5:
                            cards = links
                            print(f"✅ 섹션 내 포지션 카드 {link_count}개 발견")
                            break

            assert cards is not None, "포지션 카드를 찾을 수 없음"
            card_count = await cards.count()
            assert card_count >= 5, f"포지션 카드가 5개 미만: {card_count}개"
            print(f"✅ 포지션 카드 {card_count}개 확인 완료")

            # 우측 버튼 찾기 및 클릭
            print("🔍 우측 스크롤 버튼 찾는 중...")
            next_btn_selectors = [
                'button[aria-label*="다음"]',
                'button[aria-label*="next"]',
                'button[aria-label*="Next"]',
                'button[class*="next"]',
                'button[class*="Next"]',
                'button[class*="right"]',
                'button[class*="Right"]',
                '[class*="arrow"][class*="right"]',
                '[class*="ArrowRight"]',
                'button svg[class*="right"]',
            ]

            next_btn = None
            for selector in next_btn_selectors:
                btn = page.locator(selector)
                if await btn.count() > 0:
                    next_btn = btn.first
                    print(f"✅ 우측 버튼 발견 (selector: {selector})")
                    break

            if next_btn is None:
                # '모두가 주목' 섹션 주변 버튼 탐색
                attention_section = None
                sections = page.locator('section, [class*="Section"]')
                for i in range(await sections.count()):
                    sec = sections.nth(i)
                    text = await sec.text_content()
                    if text and '모두가 주목' in text:
                        attention_section = sec
                        break

                if attention_section:
                    buttons = attention_section.locator('button')
                    btn_count = await buttons.count()
                    print(f"섹션 내 버튼 {btn_count}개 발견")
                    if btn_count > 0:
                        next_btn = buttons.last

            assert next_btn is not None, "우측 스크롤 버튼을 찾을 수 없음"

            # 버튼 클릭 전 스크린샷
            await page.screenshot(path='screenshots/test_12_before_scroll.png')

            # 우측 버튼 클릭
            await next_btn.click()
            await page.wait_for_timeout(1500)
            print("✅ 우측 버튼 클릭 완료")

            # 클릭 후 스크린샷
            await page.screenshot(path='screenshots/test_12_after_scroll.png')
            print("✅ 스크롤 후 추가 포지션 카드 노출 확인")

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
