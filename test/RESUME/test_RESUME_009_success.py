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

            # 이력서 편집 페이지 상단 영역 확인 후 임시 저장 버튼 클릭
            # 임시 저장 버튼 찾기
            save_btn = None

            # 1순위: role=button, name 포함 '임시 저장'
            btn_candidate = page.get_by_role('button', name='임시 저장')
            if await btn_candidate.count() > 0:
                save_btn = btn_candidate.first

            # 2순위: 텍스트로 찾기
            if save_btn is None:
                btn_candidate = page.get_by_text('임시 저장', exact=True)
                if await btn_candidate.count() > 0:
                    save_btn = btn_candidate.first

            # 3순위: CSS selector로 찾기
            if save_btn is None:
                btn_candidate = page.locator('button:has-text("임시 저장")')
                if await btn_candidate.count() > 0:
                    save_btn = btn_candidate.first

            assert save_btn is not None, "임시 저장 버튼을 찾을 수 없습니다"

            # 임시 저장 버튼 클릭
            await save_btn.click()
            await page.wait_for_timeout(2000)

            # 툴팁 노출 확인
            # 기대결과 1: '현재 이력서의 글자수는 NNN자 입니다.'
            # 기대결과 2: '임시 저장 되었습니다. 작성 완료 후 기업 담당자에게 지원·면접 제안을 받을 수 있습니다.'

            # 글자수 툴팁 확인 (NNN자 패턴)
            char_count_visible = False
            saved_tooltip_visible = False

            # 툴팁/알림 영역에서 텍스트 확인
            # 글자수 관련 텍스트
            char_count_patterns = [
                '현재 이력서의 글자수는',
                '글자수',
                '자 입니다'
            ]

            for pattern in char_count_patterns:
                matching_elements = page.get_by_text(pattern, exact=False)
                count = await matching_elements.count()
                if count > 0:
                    char_count_visible = True
                    break

            # 임시 저장 완료 툴팁
            saved_patterns = [
                '임시 저장 되었습니다',
                '임시저장 되었습니다',
                '임시 저장되었습니다',
                '임시저장되었습니다'
            ]

            for pattern in saved_patterns:
                matching_elements = page.get_by_text(pattern, exact=False)
                count = await matching_elements.count()
                if count > 0:
                    saved_tooltip_visible = True
                    break

            # 툴팁이 바로 안 보이면 잠시 더 대기
            if not char_count_visible or not saved_tooltip_visible:
                await page.wait_for_timeout(2000)

                # 재확인
                for pattern in char_count_patterns:
                    matching_elements = page.get_by_text(pattern, exact=False)
                    count = await matching_elements.count()
                    if count > 0:
                        char_count_visible = True
                        break

                for pattern in saved_patterns:
                    matching_elements = page.get_by_text(pattern, exact=False)
                    count = await matching_elements.count()
                    if count > 0:
                        saved_tooltip_visible = True
                        break

            # 검증
            assert char_count_visible, "글자수 툴팁('현재 이력서의 글자수는 NNN자 입니다.')이 노출되지 않았습니다"
            assert saved_tooltip_visible, "임시 저장 툴팁('임시 저장 되었습니다...')이 노출되지 않았습니다"

            await page.screenshot(path='screenshots/test_70_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_70_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
