import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"

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

            # 이력서 목록 페이지 진입
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert 'cv/list' in page.url, f"이력서 목록 페이지 진입 실패: {page.url}"

            # '작성 중' 상태이고 기본 이력서가 아닌 카드를 찾는 함수
            async def find_draft_non_basic_card():
                """'작성 중' 상태의 비기본 이력서 카드를 찾아 반환"""
                # 이력서 카드 전체 목록 가져오기
                cards = page.locator('[class*="ResumeItem_ResumeItem"]')
                count = await cards.count()
                print(f"총 이력서 카드 수: {count}")

                for i in range(count):
                    card = cards.nth(i)
                    card_text = await card.inner_text()
                    print(f"카드 {i}: {card_text[:100]}")

                    # 기본 이력서 태그가 있으면 제외
                    is_basic = False
                    basic_badges = [
                        '[class*="badge"][class*="basic"]',
                        '[class*="Badge"][class*="basic"]',
                        '[class*="basic"][class*="badge"]',
                    ]
                    for badge_sel in basic_badges:
                        badge = card.locator(badge_sel)
                        if await badge.count() > 0:
                            is_basic = True
                            break

                    # 텍스트에 '기본 이력서' 태그가 있는지도 확인
                    if '기본 이력서' in card_text and '기본' in card_text:
                        # 더 명확히 확인
                        basic_tag = card.get_by_text('기본 이력서', exact=True)
                        if await basic_tag.count() > 0:
                            is_basic = True

                    if is_basic:
                        print(f"카드 {i}: 기본 이력서 - 제외")
                        continue

                    # '작성 중' 상태 확인
                    is_draft = False
                    draft_indicators = ['작성 중', '작성중']
                    for indicator in draft_indicators:
                        if indicator in card_text:
                            is_draft = True
                            break

                    if is_draft:
                        print(f"카드 {i}: '작성 중' 상태 비기본 이력서 발견")
                        return card

                return None

            # 없으면 새 이력서 생성 (삭제 대상 확보)
            initial_card = await find_draft_non_basic_card()
            if initial_card is None:
                print("'작성 중' 비기본 이력서 없음 → 새 이력서 생성")
                new_btn = None
                for kw in ['새 이력서 작성', '새 이력서']:
                    btn = page.get_by_text(kw, exact=False)
                    if await btn.count() > 0:
                        new_btn = btn.first
                        break

                assert new_btn is not None, "'새 이력서 작성' 버튼을 찾을 수 없습니다"
                await new_btn.click()
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

                await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            # ===== 모든 '작성 중' 비기본 이력서를 루프로 삭제 =====
            more_selectors = [
                '[aria-label="더보기"]',
                '[aria-label="more"]',
                'button[class*="more"]',
                'button[class*="More"]',
                '[class*="more_btn"]',
                '[class*="moreBtn"]',
                '[class*="kebab"]',
                'button[class*="dot"]',
            ]
            delete_selectors = [
                'li:has-text("삭제")',
                'button:has-text("삭제")',
                '[role="menuitem"]:has-text("삭제")',
                'a:has-text("삭제")',
            ]
            confirm_selectors = [
                '[role="dialog"] button:has-text("삭제")',
                '[class*="modal"] button:has-text("삭제")',
                '[class*="popup"] button:has-text("삭제")',
                'button:has-text("삭제")',
            ]
            toast_selectors = [
                'text=삭제되었습니다',
                '[class*="toast"]:has-text("삭제되었습니다")',
                '[class*="Toast"]:has-text("삭제되었습니다")',
                '[class*="snackbar"]:has-text("삭제되었습니다")',
                '[role="alert"]:has-text("삭제되었습니다")',
            ]

            deleted_count = 0

            while True:
                await page.wait_for_timeout(1000)
                target_card = await find_draft_non_basic_card()
                if target_card is None:
                    print(f"더 이상 삭제할 '작성 중' 카드 없음 (총 {deleted_count}개 삭제)")
                    break

                # hover → 더보기 버튼 클릭
                await target_card.hover()
                await page.wait_for_timeout(700)

                more_btn = None
                for sel in more_selectors:
                    candidate = target_card.locator(sel)
                    if await candidate.count() > 0:
                        more_btn = candidate.first
                        print(f"더보기 버튼 발견 (selector: {sel})")
                        break

                if more_btn is not None:
                    await more_btn.wait_for(state='visible', timeout=5000)
                    await more_btn.click()
                else:
                    print("더보기 버튼 미발견 → JS hover 이벤트 강제 발생")
                    handle = await target_card.element_handle()
                    await page.evaluate("""(el) => {
                        el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
                        el.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true}));
                    }""", handle)
                    await page.wait_for_timeout(700)
                    for sel in more_selectors:
                        candidate = target_card.locator(sel)
                        if await candidate.count() > 0:
                            more_btn = candidate.first
                            break
                    assert more_btn is not None, "3점(더보기) 버튼을 찾을 수 없습니다"
                    await more_btn.click(force=True)

                await page.wait_for_timeout(500)

                # 드롭다운 → 삭제 클릭
                delete_btn = None
                for sel in delete_selectors:
                    candidate = page.locator(sel)
                    if await candidate.count() > 0:
                        delete_btn = candidate.first
                        print(f"삭제 버튼 발견 (selector: {sel})")
                        break
                assert delete_btn is not None, "이력서 삭제 버튼을 찾을 수 없습니다"
                await delete_btn.click()
                await page.wait_for_timeout(500)

                # 확인 팝업 → 삭제 클릭
                confirm_btn = None
                for sel in confirm_selectors:
                    candidate = page.locator(sel)
                    if await candidate.count() > 0:
                        confirm_btn = candidate.last
                        print(f"삭제 확인 버튼 발견 (selector: {sel})")
                        break
                assert confirm_btn is not None, "삭제 확인 팝업의 '삭제' 버튼을 찾을 수 없습니다"
                await confirm_btn.click()
                await page.wait_for_timeout(1500)

                # 토스트 확인
                toast_found = False
                for sel in toast_selectors:
                    try:
                        toast = page.locator(sel)
                        await toast.wait_for(state='visible', timeout=5000)
                        if await toast.count() > 0:
                            toast_found = True
                            print(f"토스트 확인 (selector: {sel})")
                            break
                    except Exception:
                        continue

                assert toast_found, "토스트 메시지 '삭제되었습니다.'가 표시되지 않았습니다"
                deleted_count += 1
                print(f"삭제 완료 ({deleted_count}번째)")

            assert deleted_count > 0, "삭제된 이력서가 없습니다"
            print(f"총 {deleted_count}개의 '작성 중' 이력서 삭제 완료")

            await page.screenshot(path='screenshots/test_72_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_72_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
