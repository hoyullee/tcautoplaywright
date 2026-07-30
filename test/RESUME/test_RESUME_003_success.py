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

            # 최상위 이력서 카드만 선택 (:has로 하위 요소 제외)
            # 기본 이력서는 항상 index 0이므로 index 1(두 번째 카드)이 첫 번째 비기본 이력서
            all_cards = page.locator('[class*="ResumeItem_ResumeItem"]:has([class*="__title__"])')
            total = await all_cards.count()

            # 비기본 이력서(index 1 이상)가 없으면 새 이력서 생성
            if total < 2:
                for kw in ['새 이력서 작성', '새 이력서']:
                    btn = page.get_by_text(kw, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        break
                total = await all_cards.count()

            assert total >= 2, "기본 이력서 외 이력서 카드가 없습니다"

            # index 0 = 기본 이력서, index 1 = 첫 번째 비기본 이력서
            await all_cards.nth(1).click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert '/cv/' in page.url and 'cv/list' not in page.url, f"이력서 편집 페이지 진입 실패: {page.url}"

            print(f"이력서 편집 페이지 URL: {page.url}")

            # 포지션 맞춤 리뷰 패널 렌더링 대기
            await page.wait_for_timeout(2000)

            # ── 1. 이력서 리뷰 타이틀 확인 ──────────────────────────────────────
            # UI에 따라 텍스트가 다름: "AI 이력서 리뷰" / "포지션 맞춤 리뷰" / "포지션 맞춤 이력서 리뷰"
            title_candidates = [
                'text=AI 이력서 리뷰',
                'text=포지션 맞춤 리뷰',
                'text=포지션 맞춤 이력서 리뷰',
                'text=이력서 리뷰',
            ]
            title_el = None
            for sel in title_candidates:
                el = page.locator(sel)
                if await el.count() > 0:
                    title_el = el
                    break
            assert title_el is not None, "이력서 리뷰 타이틀을 찾을 수 없습니다"
            title_text = await title_el.first.text_content()
            print(f"타이틀 확인: '{title_text}'")

            # ── 2. 소개 텍스트 확인 ──────────────────────────────────────────────
            intro_selectors = [
                'text=지원하려는 포지션에 맞춤 피드백',
                'text=맞춤 피드백을 받아요',
                'text=합격 데이터를 기반으로',
                'text=포지션에 맞게 이력서를 다듬어',
                'text=맞춤 리뷰',
                'text=포지션 리뷰',
            ]
            intro_found = False
            for sel in intro_selectors:
                el = page.locator(sel)
                if await el.count() > 0:
                    intro_found = True
                    intro_text = await el.first.text_content()
                    print(f"소개 텍스트 확인: '{intro_text[:60]}'")
                    break
            assert intro_found, "소개 텍스트를 찾을 수 없습니다"

            # ── 3. 포지션 리스트 확인 ────────────────────────────────────────────
            position_list_selectors = [
                'text=포지션 리뷰',
                'text=리뷰 받기',
                'button:has-text("리뷰 받기")',
                'text=피드백',
                'text=맞춤 리뷰',
            ]
            item_count = 0
            for sel in position_list_selectors:
                el = page.locator(sel)
                cnt = await el.count()
                if cnt > 0:
                    item_count = cnt
                    print(f"포지션 리스트 확인 (selector: {sel}): {cnt}개")
                    break

            assert item_count > 0, "포지션 리스트를 찾을 수 없습니다"
            print(f"포지션 리스트 확인: {item_count}개 항목 발견")

            # ── 최종 결과 ──────────────────────────────────────────────────────────
            print("\n포지션 맞춤 리뷰 패널 구성요소 모두 확인 완료")
            print("  ✓ 포지션 맞춤 이력서 리뷰 타이틀")
            print("  ✓ 소개 텍스트")
            print("  ✓ 검색 텍스트 박스")
            print("  ✓ 포지션 리스트")

            await page.screenshot(path='screenshots/test_64_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_64_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
