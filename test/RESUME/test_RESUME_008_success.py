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

            # 스킬 섹션으로 스크롤
            await page.wait_for_timeout(2000)
            skill_header = page.locator('[data-header-label="스킬"]')
            await skill_header.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            print("스킬 헤더 발견")

            # 스킬 ActiveBox를 JS로 클릭하여 입력 활성화
            # (디버그에서 확인: JS 클릭 후 '보유 스킬을 검색해 보세요.' input이 활성화됨)
            await page.evaluate("""() => {
                const skillSpan = document.querySelector('[data-header-label="스킬"]');
                if (skillSpan) {
                    const sibling = skillSpan.nextElementSibling;
                    if (sibling) sibling.click();
                }
            }""")
            await page.wait_for_timeout(1500)

            # 스킬 검색 input 찾기 (placeholder: '보유 스킬을 검색해 보세요.')
            skill_input = page.get_by_placeholder('보유 스킬을 검색해 보세요.')
            skill_input_count = await skill_input.count()
            print(f"스킬 input 개수: {skill_input_count}")

            if skill_input_count == 0:
                # 폴백: ActiveBox 마우스 클릭으로 활성화
                skill_info = await page.evaluate("""() => {
                    const skillSpan = document.querySelector('[data-header-label="스킬"]');
                    if (!skillSpan) return null;
                    const sibling = skillSpan.nextElementSibling;
                    if (!sibling) return null;
                    const rect = sibling.getBoundingClientRect();
                    return { x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2) };
                }""")
                if skill_info:
                    await page.mouse.click(skill_info['x'], skill_info['y'])
                    await page.wait_for_timeout(1500)

                # ActiveBox 클래스로 직접 찾기
                active_box = page.locator('[class*="ActiveBox_ActiveBox"]').first
                if await active_box.count() > 0:
                    await active_box.click(force=True)
                    await page.wait_for_timeout(1500)

            # 스킬 input 다시 확인
            skill_input = page.get_by_placeholder('보유 스킬을 검색해 보세요.')
            skill_input_count = await skill_input.count()

            if skill_input_count == 0:
                # 스킬 관련 텍스트 input 전체 탐색
                all_inputs = await page.evaluate("""() => {
                    return [...document.querySelectorAll('input')].filter(el => el.offsetParent !== null)
                        .map(el => ({ placeholder: el.placeholder, type: el.type, class: (el.className||'').substring(0,60) }));
                }""")
                print(f"현재 visible inputs: {all_inputs}")

                # 보유 스킬 관련 input 찾기
                for inp_info in all_inputs:
                    ph = inp_info.get('placeholder', '')
                    if '스킬' in ph or 'skill' in ph.lower():
                        skill_input = page.get_by_placeholder(ph, exact=True)
                        if await skill_input.count() > 0:
                            print(f"폴백 스킬 input 발견: {ph}")
                            break

            assert await skill_input.count() > 0, "스킬 검색 input을 찾을 수 없습니다"

            # 'playwright' 입력
            await skill_input.first.scroll_into_view_if_needed()
            await skill_input.first.click()
            await page.wait_for_timeout(500)
            await skill_input.first.fill('playwright')
            await page.wait_for_timeout(2000)
            print("'playwright' 입력 완료")

            # 검색 결과 드롭다운에서 'Playwright' 선택
            playwright_option = None

            # 방법 1: role="option" 셀렉터 탐색
            for selector in ['[role="option"]', '[role="listbox"] li', 'li[class*="option"]', 'li[class*="Option"]']:
                options = page.locator(selector)
                cnt = await options.count()
                for i in range(min(cnt, 20)):
                    opt = options.nth(i)
                    try:
                        if await opt.is_visible():
                            text = await opt.inner_text()
                            if 'playwright' in text.lower():
                                playwright_option = opt
                                print(f"'Playwright' 옵션 발견: {selector}")
                                break
                    except:
                        pass
                if playwright_option:
                    break

            # 방법 2: 텍스트로 직접 찾기
            if playwright_option is None:
                for text_val in ['Playwright']:
                    opt = page.get_by_text(text_val, exact=True)
                    cnt = await opt.count()
                    if cnt > 0:
                        for i in range(cnt):
                            candidate = opt.nth(i)
                            try:
                                if await candidate.is_visible():
                                    playwright_option = candidate
                                    print(f"텍스트로 'Playwright' 옵션 발견")
                                    break
                            except:
                                pass
                    if playwright_option:
                        break

            # 방법 3: 드롭다운 리스트 요소 전체 탐색
            if playwright_option is None:
                dropdown_items = await page.evaluate("""() => {
                    const items = [...document.querySelectorAll('ul li, [role="listbox"] *, [class*="dropdown"] *')]
                        .filter(el => el.offsetParent !== null && el.textContent.trim().toLowerCase().includes('playwright'));
                    return items.slice(0, 10).map(el => ({
                        tag: el.tagName,
                        class: (el.className||'').substring(0,60),
                        text: el.textContent.trim().substring(0,60),
                        role: el.getAttribute('role')||''
                    }));
                }""")
                print(f"드롭다운 Playwright 아이템: {dropdown_items}")

                for item in dropdown_items:
                    candidate_class = item.get('class', '')
                    if candidate_class:
                        candidates = page.locator(f'[class="{candidate_class}"]')
                        cnt = await candidates.count()
                        for i in range(min(cnt, 5)):
                            c = candidates.nth(i)
                            try:
                                if await c.is_visible():
                                    text = await c.inner_text()
                                    if 'playwright' in text.lower():
                                        playwright_option = c
                                        break
                            except:
                                pass
                    if playwright_option:
                        break

            assert playwright_option is not None, "검색 결과에서 'Playwright' 옵션을 찾을 수 없습니다"

            await playwright_option.scroll_into_view_if_needed()
            await playwright_option.click(force=True)
            await page.wait_for_timeout(2000)
            print("'Playwright' 옵션 클릭 완료")

            # 검증: 스킬에 'Playwright'가 등록되었는지 확인
            skill_registered = False

            # 방법 1: 스킬 태그/칩 셀렉터로 확인
            for selector in [
                '[class*="SkillTag"]', '[class*="skill-tag"]', '[class*="SkillItem"]',
                '[class*="tag"]', '[class*="Tag"]', '[class*="badge"]', '[class*="Badge"]',
                '[class*="chip"]', '[class*="Chip"]', '[class*="selected"]', '[class*="Selected"]'
            ]:
                tags = page.locator(selector)
                cnt = await tags.count()
                for i in range(min(cnt, 30)):
                    tag = tags.nth(i)
                    try:
                        text = await tag.inner_text()
                        if 'playwright' in text.lower():
                            skill_registered = True
                            print(f"스킬 등록 확인 ({selector}): '{text.strip()}'")
                            break
                    except:
                        continue
                if skill_registered:
                    break

            # 방법 2: 스킬 컨테이너 텍스트에서 확인
            if not skill_registered:
                skill_area_text = await page.evaluate("""() => {
                    const skillSpan = document.querySelector('[data-header-label="스킬"]');
                    if (!skillSpan) return '';
                    const sibling = skillSpan.nextElementSibling;
                    if (!sibling) return '';
                    return sibling.textContent;
                }""")
                if 'playwright' in skill_area_text.lower():
                    skill_registered = True
                    print(f"스킬 컨테이너에서 확인: '{skill_area_text[:100]}'")

            # 방법 3: 스킬 영역 전체에서 확인
            if not skill_registered:
                skill_areas = page.locator('[class*="skill"], [class*="Skill"]')
                cnt = await skill_areas.count()
                for i in range(min(cnt, 20)):
                    area = skill_areas.nth(i)
                    try:
                        text = await area.inner_text()
                        tag_name = await area.evaluate('el => el.tagName.toLowerCase()')
                        if 'playwright' in text.lower() and tag_name != 'input':
                            skill_registered = True
                            print(f"스킬 영역에서 확인: '{text[:60]}'")
                            break
                    except:
                        continue

            assert skill_registered, "스킬에 'Playwright'가 등록되지 않았습니다"

            await page.screenshot(path='screenshots/test_69_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_69_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
