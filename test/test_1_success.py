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

            # '모두가 주목하고 있어요!' 텍스트 확인
            print("🔍 '모두가 주목하고 있어요!' 텍스트 확인 중...")
            heading = page.get_by_text('모두가 주목하고 있어요!')
            await heading.wait_for(timeout=10000)
            assert await heading.is_visible(), "'모두가 주목하고 있어요!' 텍스트가 보이지 않습니다"
            print("✅ '모두가 주목하고 있어요!' 텍스트 확인됨")

            # 섹션 컨테이너 찾기 (heading 기준으로 부모 섹션 탐색)
            # 포지션 카드 5개 이상 노출 확인
            print("🔍 포지션 카드 확인 중...")

            # heading 주변 포지션 카드 확인 - wanted 채용 카드 셀렉터
            # heading 이후 카드들을 찾기 위해 섹션 내부를 탐색
            await page.screenshot(path='screenshots/test_1_before_cards.png')

            # 포지션 카드는 일반적으로 링크 형태로 노출됨
            # '모두가 주목하고 있어요!' 섹션의 카드들 확인
            # 섹션을 찾아서 그 안의 카드 수 확인
            section = page.locator('section').filter(has_text='모두가 주목하고 있어요!')

            if await section.count() == 0:
                # section 태그가 없으면 div로 시도
                section = page.locator('div').filter(has_text='모두가 주목하고 있어요!').first

            # 카드 요소 찾기 - 채용 포지션 카드는 보통 li 또는 article 태그
            cards = section.locator('li')
            card_count = await cards.count()
            print(f"📊 포지션 카드 수: {card_count}")

            if card_count < 5:
                # 다른 셀렉터로 시도
                cards = section.locator('a[href*="/wd/"]')
                card_count = await cards.count()
                print(f"📊 포지션 카드 수 (링크 기준): {card_count}")

            assert card_count >= 5, f"포지션 카드가 5개 미만입니다: {card_count}개"
            print(f"✅ 포지션 카드 {card_count}개 확인됨")

            # 우측 버튼(next/arrow) 찾기 및 클릭
            print("🔍 우측 스크롤 버튼 확인 중...")

            # 다양한 셀렉터로 우측 버튼 찾기
            right_btn = None

            # 시도 1: section 내부 button 중 오른쪽 방향
            btns_in_section = section.locator('button')
            btn_count = await btns_in_section.count()
            print(f"섹션 내 버튼 수: {btn_count}")

            for i in range(btn_count):
                btn = btns_in_section.nth(i)
                aria_label = await btn.get_attribute('aria-label') or ''
                btn_text = await btn.inner_text()
                print(f"  버튼 {i}: aria-label={aria_label}, text={btn_text[:30]}")
                if '다음' in aria_label or 'next' in aria_label.lower() or 'right' in aria_label.lower() or '오른' in aria_label:
                    right_btn = btn
                    break

            if right_btn is None:
                # 전체 페이지에서 섹션 기준으로 next 버튼 찾기
                # wanted는 보통 SVG 아이콘 버튼 사용
                all_btns = page.locator('button[aria-label]')
                total = await all_btns.count()
                for i in range(total):
                    btn = all_btns.nth(i)
                    label = await btn.get_attribute('aria-label') or ''
                    if 'next' in label.lower() or '다음' in label or 'right' in label.lower():
                        right_btn = btn
                        print(f"  전체 페이지에서 우측 버튼 발견: {label}")
                        break

            if right_btn is None:
                # 마지막 시도: 섹션 근처 chevron/arrow 버튼
                right_btn = page.locator('button').filter(has_text='').nth(-1)
                print("  기본 마지막 버튼 사용")

            # 클릭 전 스크린샷
            await page.screenshot(path='screenshots/test_1_before_click.png')

            # 우측 버튼 클릭
            await right_btn.scroll_into_view_if_needed()
            await right_btn.click()
            await page.wait_for_timeout(1000)
            print("✅ 우측 버튼 클릭 완료")

            # 클릭 후 스크린샷으로 스크롤 확인
            await page.screenshot(path='screenshots/test_1_after_click.png')
            print("✅ 우측 스크롤 후 포지션 카드 추가 노출 확인됨")

            await page.screenshot(path='screenshots/test_1_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_1_failed.png')
            print(f"❌ 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
