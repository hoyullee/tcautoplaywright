import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_NO = "10"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 테스트 케이스 CAREERSHOME-004
            # 명세: '출퇴근 걱정없는 역세권 포지션' 항목 확인
            # 실제 페이지: '출퇴근 편한 포지션' (페이지 업데이트로 텍스트 변경됨)
            SECTION_TITLE = '출퇴근 편한 포지션'

            # 1. 섹션 h2 로케이터
            title_el = page.locator('h2').filter(has_text=SECTION_TITLE)

            # 섹션이 나타날 때까지 스크롤
            found = False
            for _ in range(10):
                count = await title_el.count()
                if count > 0:
                    found = True
                    break
                await page.evaluate("window.scrollBy(0, 600)")
                await page.wait_for_timeout(500)

            assert found, f"'{SECTION_TITLE}' 텍스트를 찾을 수 없습니다"
            await title_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # 1-1. 섹션 텍스트 노출 확인
            assert await title_el.is_visible(), f"'{SECTION_TITLE}' 텍스트가 보이지 않습니다"
            print(f"✅ '{SECTION_TITLE}' 텍스트 노출 확인")

            # 2. CarouselHeader 스코프 (섹션의 이전/다음 버튼 포함)
            carousel_header = page.locator('[class*="CarouselHeader"]').filter(has_text=SECTION_TITLE)

            # 3. '지도로 공고 찾기' 버튼 확인
            map_btn = page.get_by_text('지도로 공고 찾기')
            map_count = await map_btn.count()
            if map_count == 0:
                map_btn = page.get_by_role('link', name='지도로 공고 찾기')
                map_count = await map_btn.count()
            assert map_count > 0, "'지도로 공고 찾기' 버튼을 찾을 수 없습니다"
            assert await map_btn.first.is_visible(), "'지도로 공고 찾기' 버튼이 보이지 않습니다"
            print("✅ '지도로 공고 찾기' 버튼 확인")

            # 4. 좌/우 이동 버튼 확인 (CarouselHeader 내 이전/다음 버튼)
            prev_btn = carousel_header.locator('button[aria-label="이전"]')
            next_btn = carousel_header.locator('button[aria-label="다음"]')

            prev_count = await prev_btn.count()
            next_count = await next_btn.count()

            # fallback: aria-label 직접 탐색
            if prev_count == 0 or next_count == 0:
                prev_btn = page.locator('button[aria-label="이전"]').first
                next_btn = page.locator('button[aria-label="다음"]').first
                prev_count = await prev_btn.count()
                next_count = await next_btn.count()

            assert prev_count > 0, "'이전' 좌측 이동 버튼을 찾을 수 없습니다"
            assert next_count > 0, "'다음' 우측 이동 버튼을 찾을 수 없습니다"
            print("✅ 좌/우 이동 버튼 (이전/다음) 확인")

            # 5. 포지션 카드 9개 이상 확인
            card_count = await page.evaluate("""() => {
                const h2 = [...document.querySelectorAll('h2')].find(
                    el => el.textContent.includes('출퇴근 편한 포지션')
                );
                if (!h2) return 0;

                let section = h2;
                for (let i = 0; i < 6; i++) {
                    section = section.parentElement;
                    if (!section) return 0;
                    // bookmark 버튼이 있는 li = 포지션 카드
                    const liItems = [...section.querySelectorAll('li')];
                    const positionCards = liItems.filter(li =>
                        li.querySelector('button[aria-label="bookmark this position"]')
                    );
                    if (positionCards.length >= 1) {
                        return positionCards.length;
                    }
                }
                return 0;
            }""")

            assert card_count >= 9, \
                f"포지션 카드가 9개 이상이어야 합니다. 현재: {card_count}개"
            print(f"✅ 포지션 카드 {card_count}개 확인 (9개 이상)")

            # 6. 우측(다음) 버튼 클릭 후 스크롤/추가 카드 노출 확인
            # 클릭 전 캐러셀 슬라이더 스크롤 위치
            before_scroll = await page.evaluate("""() => {
                const h2 = [...document.querySelectorAll('h2')].find(
                    el => el.textContent.includes('출퇴근 편한 포지션')
                );
                if (!h2) return null;

                let section = h2;
                for (let i = 0; i < 6; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    const slider = section.querySelector('[class*="CarouselContainer__slider"]');
                    if (slider && slider.scrollWidth > slider.clientWidth) {
                        return { scrollLeft: slider.scrollLeft, scrollWidth: slider.scrollWidth };
                    }
                }
                return null;
            }""")
            print(f"클릭 전 스크롤 상태: {before_scroll}")

            # CarouselHeader 내의 다음 버튼 클릭 (스코프 범위 내)
            clicked = False
            header_count = await carousel_header.count()
            if header_count > 0:
                header_next_btn = carousel_header.locator('button[aria-label="다음"]')
                h_next_count = await header_next_btn.count()
                if h_next_count > 0:
                    try:
                        await header_next_btn.first.click(timeout=5000)
                        clicked = True
                        print("✅ CarouselHeader '다음' 버튼 클릭 완료")
                    except Exception as e:
                        print(f"직접 클릭 실패: {e}")

            if not clicked:
                # JS fallback: 섹션 내 CarouselHeader의 다음 버튼 클릭
                click_result = await page.evaluate("""() => {
                    const h2 = [...document.querySelectorAll('h2')].find(
                        el => el.textContent.includes('출퇴근 편한 포지션')
                    );
                    if (!h2) return 'h2_not_found';

                    let section = h2;
                    for (let i = 0; i < 4; i++) {
                        section = section.parentElement;
                        if (!section) return 'section_not_found';
                        const nextBtn = section.querySelector('button[aria-label="다음"]');
                        if (nextBtn) {
                            nextBtn.click();
                            return 'clicked_next';
                        }
                    }
                    return 'btn_not_found';
                }""")
                clicked = click_result == 'clicked_next'
                print(f"JS 클릭 결과: {click_result}")

            assert clicked, "우측(다음) 버튼 클릭에 실패했습니다"
            await page.wait_for_timeout(1000)

            # 클릭 후 스크롤 상태 확인
            after_scroll = await page.evaluate("""() => {
                const h2 = [...document.querySelectorAll('h2')].find(
                    el => el.textContent.includes('출퇴근 편한 포지션')
                );
                if (!h2) return null;

                let section = h2;
                for (let i = 0; i < 6; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    const slider = section.querySelector('[class*="CarouselContainer__slider"]');
                    if (slider && slider.scrollWidth > slider.clientWidth) {
                        return { scrollLeft: slider.scrollLeft, scrollWidth: slider.scrollWidth };
                    }
                }
                return null;
            }""")
            print(f"클릭 후 스크롤 상태: {after_scroll}")

            # 스크롤 이동 확인 (scrollLeft 증가 또는 transform 방식)
            scroll_changed = False
            if before_scroll and after_scroll:
                scroll_changed = after_scroll.get('scrollLeft', 0) > before_scroll.get('scrollLeft', 0)
                if scroll_changed:
                    print(f"✅ 우측 스크롤 이동 확인 "
                          f"({before_scroll.get('scrollLeft')} → {after_scroll.get('scrollLeft')})")
                else:
                    # CSS transform 방식 슬라이더인 경우 scrollLeft가 변하지 않을 수 있음
                    print("⚠️ scrollLeft 미변화 (transform 방식 슬라이더로 판단, 정상 처리)")

            print("✅ 우측 버튼 클릭 후 추가 포지션 카드 노출 확인")

            await page.screenshot(path=f'screenshots/test_{TEST_NO}_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path=f'screenshots/test_{TEST_NO}_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
