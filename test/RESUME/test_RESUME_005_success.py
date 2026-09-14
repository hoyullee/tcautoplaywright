import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"
TEST_PASSWORD = ""

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

            print(f"이력서 편집 페이지 진입 성공: {page.url}")

            # 이력서 작성 영역 확인 - 간단 소개 항목 찾기
            # '간단 소개' 섹션 탐색
            intro_label = page.get_by_text('간단 소개', exact=True)
            if await intro_label.count() == 0:
                intro_label = page.get_by_text('간단소개', exact=True)

            assert await intro_label.count() > 0, "'간단 소개' 항목을 찾을 수 없습니다"
            print("'간단 소개' 항목 확인")

            # 간단 소개 영역이 보이도록 스크롤
            await intro_label.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 간단 소개 영역의 textarea 찾기
            intro_textarea = None

            # 방법 1: placeholder로 찾기
            placeholders = ['간단한 자기소개를', '자기소개', '소개', '간단 소개', '나를 소개']
            for ph in placeholders:
                ta = page.locator(f'textarea[placeholder*="{ph}"]')
                if await ta.count() > 0:
                    intro_textarea = ta.first
                    print(f"textarea 발견 (placeholder: {ph})")
                    break

            # 방법 2: 간단 소개 레이블 이후의 textarea (위치 기반)
            if intro_textarea is None:
                intro_label_box = await intro_label.first.bounding_box()
                all_textareas = page.locator('textarea')
                count = await all_textareas.count()
                print(f"전체 textarea 수: {count}")

                if intro_label_box:
                    for i in range(count):
                        ta = all_textareas.nth(i)
                        ta_box = await ta.bounding_box()
                        if ta_box and ta_box['y'] >= intro_label_box['y'] - 50:
                            intro_textarea = ta
                            print(f"textarea[{i}] 위치 기반 선택 (y={ta_box['y']} vs label y={intro_label_box['y']})")
                            break

            # 방법 3: 섹션 컨테이너 내 textarea
            if intro_textarea is None:
                selectors = [
                    '[class*="introduction"] textarea',
                    '[class*="Introduction"] textarea',
                    '[class*="intro"] textarea',
                    '[class*="summary"] textarea',
                    '[class*="Summary"] textarea',
                    '[class*="brief"] textarea',
                ]
                for sel in selectors:
                    ta = page.locator(sel)
                    if await ta.count() > 0:
                        intro_textarea = ta.first
                        print(f"컨테이너 셀렉터로 textarea 발견: {sel}")
                        break

            assert intro_textarea is not None, "간단 소개 textarea를 찾을 수 없습니다"

            # textarea가 보이도록 스크롤
            await intro_textarea.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # 기존 텍스트 클리어 후 임의의 소개 텍스트 작성
            test_text = "안녕하세요. 저는 5년 경력의 소프트웨어 엔지니어입니다."
            await intro_textarea.click()
            await page.wait_for_timeout(300)
            await intro_textarea.fill(test_text)
            await page.wait_for_timeout(1000)

            actual_count = len(test_text)
            print(f"작성한 텍스트: '{test_text}' (길이: {actual_count}자)")

            # 텍스트 카운팅 확인 - textarea 우측 하단의 카운터 찾기
            counter_found = False

            # 방법 1: 특정 클래스명으로 카운터 찾기
            counter_selectors = [
                '[class*="counter"]',
                '[class*="Counter"]',
                '[class*="count"]',
                '[class*="Count"]',
                '[class*="length"]',
                '[class*="Length"]',
                '[class*="char"]',
                '[class*="Char"]',
                '[class*="byte"]',
                '[class*="text-limit"]',
                '[class*="TextLimit"]',
            ]

            for sel in counter_selectors:
                el = page.locator(sel)
                if await el.count() > 0:
                    for i in range(min(await el.count(), 10)):
                        text = await el.nth(i).text_content()
                        if text and str(actual_count) in text:
                            counter_found = True
                            print(f"카운터 발견 (selector: {sel}): '{text.strip()}'")
                            break
                if counter_found:
                    break

            # 방법 2: textarea 주변 요소에서 카운터 숫자 탐색
            if not counter_found:
                parent_counters = await page.evaluate("""(count) => {
                    const allEls = document.querySelectorAll('span, p, div, em, small');
                    const results = [];
                    for (const el of Array.from(allEls).slice(0, 300)) {
                        const t = el.textContent.trim();
                        if (t && t.length < 20) {
                            // '숫자' 또는 '숫자/최대값' 패턴
                            if (t === String(count) || t.startsWith(String(count) + '/') || t.startsWith(String(count) + ' ')) {
                                results.push({text: t, class: el.className.substring(0, 80)});
                            }
                        }
                    }
                    return results;
                }""", actual_count)

                if parent_counters:
                    counter_found = True
                    print(f"카운터 요소 발견: {parent_counters[:3]}")

            # 방법 3: 더 넓은 패턴으로 탐색 (숫자가 포함된 짧은 텍스트)
            if not counter_found:
                broad_search = await page.evaluate("""(count) => {
                    const pattern = new RegExp('(^|\\D)' + count + '(\\D|$)');
                    const allEls = document.querySelectorAll('span, em, small, b, strong');
                    const results = [];
                    for (const el of Array.from(allEls).slice(0, 200)) {
                        const t = el.textContent.trim();
                        if (t && t.length < 30 && pattern.test(t)) {
                            results.push({text: t, class: el.className.substring(0, 80)});
                        }
                    }
                    return results;
                }""", actual_count)

                if broad_search:
                    counter_found = True
                    print(f"광범위 탐색으로 카운터 발견: {broad_search[:3]}")

            assert counter_found, f"텍스트박스 카운터를 찾을 수 없습니다 (작성 텍스트: {actual_count}자)"

            # textarea에 작성된 텍스트 최종 확인
            current_value = await intro_textarea.input_value()
            assert test_text in current_value or current_value == test_text, \
                f"작성된 텍스트가 일치하지 않습니다. 예상: '{test_text}', 실제: '{current_value}'"

            print(f"✅ 간단 소개 텍스트 작성 및 카운팅 확인 완료")
            print(f"   - 작성 텍스트: '{current_value}'")
            print(f"   - 텍스트 길이: {len(current_value)}자")

            await page.screenshot(path='screenshots/test_RESUME_005_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_005_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
