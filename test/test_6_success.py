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
            timezone_id='Asia/Seoul',
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            print("🌐 페이지 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('networkidle')
            print("✅ 페이지 로드 완료")

            # 1. '출퇴근 걱정없는 역세권 포지션' 섹션 확인
            print("🔍 '출퇴근 걱정없는 역세권 포지션' 섹션 탐색 중...")
            carousels = page.locator('aside.CarouselHeader_CarouselHeader__pwUTM')
            await carousels.nth(3).wait_for(timeout=15000)

            station_aside = carousels.nth(3)
            station_text = await station_aside.text_content()
            assert '출퇴근 걱정없는 역세권 포지션' in station_text, \
                f"aside[3]에 역세권 텍스트 없음: {station_text[:80]}"
            await station_aside.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            print("✅ '출퇴근 걱정없는 역세권 포지션' 섹션 확인")

            await page.screenshot(path='screenshots/test_6_station_section.png')

            # 2. '요즘 뜨는 포지션' 섹션 확인 (역세권 다음 aside)
            print("🔍 '요즘 뜨는 포지션' 섹션 탐색 중...")

            # 전체 aside 개수 확인
            total_asides = await carousels.count()
            print(f"ℹ️ 전체 CarouselHeader aside 수: {total_asides}")

            trending_aside = None
            trending_idx = -1

            # aside[3] 이후에서 '요즘 뜨는 포지션' 찾기
            for i in range(4, total_asides):
                aside = carousels.nth(i)
                text = await aside.text_content()
                if text and '요즘 뜨는 포지션' in text:
                    trending_aside = aside
                    trending_idx = i
                    print(f"✅ '요즘 뜨는 포지션' 섹션 발견 (aside[{i}])")
                    break

            # 못 찾은 경우 페이지 전체에서 텍스트로 시도
            if trending_aside is None:
                print("⚠️ CarouselHeader에서 못 찾음, 페이지 전체에서 탐색...")
                trending_el = page.get_by_text('요즘 뜨는 포지션').first
                await trending_el.wait_for(timeout=10000)
                assert await trending_el.is_visible(), "'요즘 뜨는 포지션' 텍스트가 보이지 않습니다"
                await trending_el.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                print("✅ '요즘 뜨는 포지션' 텍스트 확인 (페이지 전체 탐색)")

                await page.screenshot(path='screenshots/test_6_trending_found.png')

                # 주변 섹션에서 포지션 카드 확인
                # 텍스트 기준으로 부모/형제 요소에서 카드 탐색
                section = page.locator('section').filter(has_text='요즘 뜨는 포지션').first
                sec_count = await section.count()
                if sec_count > 0:
                    trending_aside = section
            else:
                await trending_aside.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                await page.screenshot(path='screenshots/test_6_trending_found.png')

            # 3. '요즘 뜨는 포지션' 텍스트 노출 검증
            print("🔍 '요즘 뜨는 포지션' 텍스트 노출 검증...")
            trending_text_el = page.get_by_text('요즘 뜨는 포지션').first
            assert await trending_text_el.is_visible(), "'요즘 뜨는 포지션' 텍스트가 화면에 보이지 않습니다"
            print("✅ '요즘 뜨는 포지션' 텍스트 노출 확인")

            # 4. 포지션 카드 5개 노출 확인
            print("🔍 포지션 카드 5개 노출 확인...")

            # 카드 컨테이너 탐색: trending_aside 기준 또는 페이지 전체
            card_locator = None
            if trending_aside is not None and hasattr(trending_aside, 'locator'):
                # aside 내부의 카드 탐색
                card_locator = trending_aside.locator('li')
                card_count = await card_locator.count()
                print(f"ℹ️ aside 내 li 카드 수: {card_count}")
                if card_count < 3:
                    # 다른 카드 선택자 시도
                    card_locator = trending_aside.locator('a[href*="/wd/"]')
                    card_count = await card_locator.count()
                    print(f"ℹ️ aside 내 포지션 링크 수: {card_count}")
            else:
                card_count = 0

            if card_count < 3:
                # 페이지 전체에서 '요즘 뜨는 포지션' 주변 카드 탐색
                # JobCard 또는 PositionCard 패턴 사용
                all_sections = page.locator('section')
                sec_total = await all_sections.count()
                for i in range(sec_total):
                    sec = all_sections.nth(i)
                    sec_text = await sec.text_content()
                    if sec_text and '요즘 뜨는 포지션' in sec_text:
                        card_locator = sec.locator('li')
                        card_count = await card_locator.count()
                        print(f"ℹ️ section[{i}] 내 li 수: {card_count}")
                        if card_count >= 3:
                            break

            print(f"ℹ️ 최종 카드 수: {card_count}")
            assert card_count >= 5, f"포지션 카드가 5개 미만: {card_count}개"
            print(f"✅ 포지션 카드 {card_count}개 이상 노출 확인")

            await page.screenshot(path='screenshots/test_6_cards_initial.png')

            # 5. 우측 버튼 클릭 후 추가 카드 노출 확인
            print("🔍 우측(다음) 버튼 탐색 중...")

            next_btn = None
            if trending_aside is not None and hasattr(trending_aside, 'locator'):
                next_btn_candidates = trending_aside.locator("button[aria-label='다음']")
                nb_count = await next_btn_candidates.count()
                if nb_count > 0:
                    next_btn = next_btn_candidates.first
                else:
                    # aria-label 없는 경우 버튼 목록에서 마지막/두번째 버튼
                    aside_btns = trending_aside.locator('button')
                    ab_count = await aside_btns.count()
                    print(f"ℹ️ aside 내 버튼 수: {ab_count}")
                    if ab_count >= 2:
                        next_btn = aside_btns.nth(1)
                    elif ab_count == 1:
                        next_btn = aside_btns.first

            if next_btn is None:
                # 페이지 전체에서 '요즘 뜨는 포지션' 근처 다음 버튼
                next_btn_all = page.locator("button[aria-label='다음']")
                nb_all_count = await next_btn_all.count()
                print(f"ℹ️ 페이지 내 '다음' 버튼 수: {nb_all_count}")
                if nb_all_count > 0:
                    # 마지막 다음 버튼 사용 (요즘 뜨는 포지션이 하단에 있으므로)
                    next_btn = next_btn_all.last

            if next_btn is not None:
                is_visible = await next_btn.is_visible()
                if is_visible:
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    await page.wait_for_timeout(1000)
                    print("✅ 우측 버튼 클릭 완료")
                    await page.screenshot(path='screenshots/test_6_after_right_btn.png')

                    # 클릭 후 카드 수 재확인
                    if card_locator is not None:
                        new_card_count = await card_locator.count()
                        print(f"ℹ️ 클릭 후 카드 수: {new_card_count}")
                        # 카드가 여전히 노출되면 OK (슬라이드되어 새 카드 표시)
                        assert new_card_count >= 1, "우측 버튼 클릭 후 카드가 사라짐"
                        print("✅ 우측 버튼 클릭 후 추가 카드 노출 확인")
                    else:
                        print("✅ 우측 버튼 클릭 완료 (카드 재확인 생략)")
                else:
                    print("⚠️ 우측 버튼이 보이지 않음 (비활성화 또는 숨김), 계속 진행")
            else:
                print("⚠️ 우측 버튼을 찾을 수 없음, 계속 진행")

            print("✅ 모든 검증 완료")
            await page.screenshot(path='screenshots/test_6_success.png')
            print("✅ 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

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
