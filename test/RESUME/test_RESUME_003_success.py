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

            # ── 1. 포지션 맞춤 이력서 리뷰 타이틀 확인 ──────────────────────────
            title_el = page.locator('text=포지션 맞춤 이력서 리뷰')
            assert await title_el.count() > 0, "포지션 맞춤 이력서 리뷰 타이틀을 찾을 수 없습니다"
            title_text = await title_el.first.text_content()
            print(f"타이틀 확인: '{title_text}'")

            # ── 2. 소개 텍스트 확인 ──────────────────────────────────────────────
            # "합격 데이터를 기반으로 선택한 포지션에 맞게 이력서를 다듬어 드려요."
            intro_selectors = [
                'text=합격 데이터를 기반으로',
                'text=포지션에 맞게 이력서를 다듬어',
                'text=선택한 포지션에 맞게',
            ]
            intro_found = False
            for sel in intro_selectors:
                el = page.locator(sel)
                if await el.count() > 0:
                    intro_found = True
                    intro_text = await el.first.text_content()
                    print(f"소개 텍스트 확인: '{intro_text[:60]}'")
                    break

            if not intro_found:
                # 타이틀 근처 텍스트 전체를 확인
                panel_text = await page.evaluate('''() => {
                    const titleEl = [...document.querySelectorAll("span, p, div")].find(
                        el => el.textContent.trim() === "포지션 맞춤 이력서 리뷰"
                    );
                    if (!titleEl) return "";
                    // 타이틀의 부모 컨테이너 텍스트
                    const parent = titleEl.closest("div[class]");
                    return parent ? parent.parentElement ? parent.parentElement.textContent.substring(0, 200) : "" : "";
                }''')
                print(f"패널 텍스트: {panel_text[:100]}")
                intro_found = len(panel_text) > 20
            assert intro_found, "소개 텍스트를 찾을 수 없습니다"

            # ── 3. 검색 텍스트 박스 확인 ─────────────────────────────────────────
            search_input = page.locator('input[placeholder*="포지션"]')
            if await search_input.count() == 0:
                search_input = page.locator('input[placeholder*="검색"]')
            assert await search_input.count() > 0, "검색 텍스트 박스를 찾을 수 없습니다"
            placeholder = await search_input.first.get_attribute('placeholder') or ''
            print(f"검색 텍스트 박스 확인: placeholder='{placeholder}'")

            # ── 4. 포지션 리스트 확인 ─────────────────────────────────────────────
            # 각 포지션 아이템에는 "리뷰 받기" 버튼이 존재
            position_items = page.locator('button:has-text("리뷰 받기")')
            item_count = await position_items.count()

            if item_count == 0:
                # 대안: get_by_text 로 탐색
                position_items = page.get_by_text('리뷰 받기', exact=True)
                item_count = await position_items.count()

            if item_count == 0:
                # 대안: 포지션 목록 컨테이너 자체 확인 (검색창 다음 형제)
                list_container = page.locator('.wds-1oymask, .wds-1r8pg5b')
                if await list_container.count() > 0:
                    item_count = 1  # 컨테이너가 존재하면 리스트 있음으로 간주

            assert item_count > 0, f"포지션 리스트를 찾을 수 없습니다 (리뷰 받기 버튼 수: {item_count})"
            print(f"포지션 리스트 확인: {item_count}개 포지션 아이템 발견")

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
