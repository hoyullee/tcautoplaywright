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
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 접속
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(1500)

            # 인앱 메시지(브레이즈) 팝업이 뜨는 경우 화면을 가려 클릭이 막히므로 닫기 처리
            if await page.locator('iframe.ab-in-app-message').count() > 0:
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(500)

            # '지금 주목할 소식' 섹션(article) 찾기 - 해당 heading을 포함하는 article 컨테이너
            section = page.locator('article').filter(
                has=page.get_by_role('heading', name='지금 주목할 소식')
            ).first
            await section.wait_for(state='visible', timeout=15000)
            await section.scroll_into_view_if_needed()
            await page.wait_for_timeout(800)

            print("1. '지금 주목할 소식' 텍스트 노출 확인 완료")

            # 좌/우 이동 버튼 확인 (섹션 내 '이전'/'다음' 버튼)
            prev_btn = section.get_by_role('button', name='이전')
            next_btn = section.get_by_role('button', name='다음')

            await next_btn.wait_for(state='visible', timeout=10000)
            prev_count = await prev_btn.count()
            next_count = await next_btn.count()

            if prev_count == 0 or next_count == 0:
                raise Exception(f"좌/우 이동 버튼을 찾을 수 없습니다. 이전 버튼: {prev_count}개, 다음 버튼: {next_count}개")

            print("2. 좌/우 이동 버튼 노출 확인 완료 (이전/다음)")

            # 컨텐츠 카드 3개 이상 확인 (ul > li 구조)
            cards = section.locator('ul > li')
            cards_count = await cards.count()
            print(f"Cards count: {cards_count}")

            if cards_count < 3:
                raise Exception(f"컨텐츠 카드가 3개 미만입니다. 발견된 카드 수: {cards_count}")

            print(f"3. 컨텐츠 카드 {cards_count}개 확인 완료 (3개 이상)")

            # '다음' 버튼이 비활성화 상태이면 클릭 불가하므로 확인
            next_disabled = await next_btn.is_disabled()
            print(f"'다음' 버튼 disabled 상태: {next_disabled}")

            if next_disabled:
                raise Exception("'다음' 버튼이 비활성화 상태입니다 - 클릭 불가")

            # 클릭 전 첫 번째 카드 위치 및 '이전' 버튼 활성화 상태 기록
            first_card_x_before = (await cards.first.bounding_box())['x']
            prev_disabled_before = await prev_btn.is_disabled()
            print(f"First card x before: {first_card_x_before}, prev disabled before: {prev_disabled_before}")

            # '다음' 버튼 클릭 (우측 이동)
            await next_btn.scroll_into_view_if_needed()
            await next_btn.click()
            await page.wait_for_timeout(1200)

            # 클릭 후 첫 번째 카드 위치 및 '이전' 버튼 활성화 상태 확인
            first_card_x_after = (await cards.first.bounding_box())['x']
            prev_disabled_after = await prev_btn.is_disabled()
            print(f"First card x after: {first_card_x_after}, prev disabled after: {prev_disabled_after}")

            x_diff = abs(first_card_x_after - first_card_x_before)
            scroll_verified = x_diff > 5 or (prev_disabled_before and not prev_disabled_after)

            if not scroll_verified:
                raise Exception(
                    f"우측 버튼 클릭 후 슬라이드 이동을 확인할 수 없습니다. "
                    f"x 이동량: {x_diff}, 이전 버튼 disabled 변화: {prev_disabled_before} -> {prev_disabled_after}"
                )

            print(f"4. 우측 버튼 클릭 후 카드가 우측으로 이동하며 추가 컨텐츠 카드 노출 확인 완료 (x 이동량: {x_diff}px)")

            await page.screenshot(path='screenshots/test_CAREERSHOME_014_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_014_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
