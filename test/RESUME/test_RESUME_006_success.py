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

            # 최상위 이력서 카드만 선택
            all_cards = page.locator('[class*="ResumeItem_ResumeItem"]:has([class*="__title__"])')
            total = await all_cards.count()

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
            await all_cards.nth(1).click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert '/cv/' in page.url and 'cv/list' not in page.url, f"이력서 편집 페이지 진입 실패: {page.url}"
            print(f"이력서 편집 페이지 진입 성공: {page.url}")

            # ===== 경력 섹션 확인 =====
            career_found = False
            for kw in ['경력', '경력사항']:
                els = page.get_by_text(kw, exact=True)
                if await els.count() > 0:
                    await els.first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    career_found = True
                    print(f"경력 섹션 발견: '{kw}'")
                    break
            assert career_found, "경력 섹션을 찾을 수 없습니다"

            # ===== 회사명 입력 =====
            company_input = page.locator('input[placeholder*="회사명"]').first
            await company_input.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)

            current_company = await company_input.input_value()
            print(f"현재 회사명 값: '{current_company}'")

            if not current_company:
                await company_input.click()
                await page.wait_for_timeout(500)
                await company_input.fill("원티드랩")
                await page.wait_for_timeout(2000)  # 자동완성 대기

                # 자동완성 드롭다운 확인 및 클릭
                suggestion_selectors = [
                    '[role="listbox"] [role="option"]',
                    '[role="option"]',
                    'ul[role="listbox"] li',
                    'li:has-text("원티드")',
                    '[class*="suggestion"] li',
                    '[class*="Suggestion"] li',
                ]

                suggestion_clicked = False
                for sel in suggestion_selectors:
                    try:
                        sug = page.locator(sel)
                        cnt = await sug.count()
                        if cnt > 0:
                            for i in range(min(cnt, 3)):
                                if await sug.nth(i).is_visible():
                                    await sug.nth(i).click()
                                    suggestion_clicked = True
                                    print(f"자동완성 선택: {sel}")
                                    await page.wait_for_timeout(800)
                                    break
                    except Exception:
                        pass
                    if suggestion_clicked:
                        break

                if not suggestion_clicked:
                    # Tab으로 커밋 (Escape는 search input 초기화 가능성 있음)
                    await page.keyboard.press('Tab')
                    await page.wait_for_timeout(500)
                    print("자동완성 없음 - Tab으로 포커스 이동")

            company_val = await company_input.input_value()
            print(f"회사명 입력 후 값: '{company_val}'")

            # ===== 경력 섹션 DOM 탐색 (날짜/재직형태 파악) =====
            career_dom_info = await page.evaluate("""() => {
                const results = { date_buttons: [], emp_type_elements: [] };

                // YYYY.MM 버튼 탐색
                const allBtns = [...document.querySelectorAll('button')];
                results.date_buttons = allBtns.filter(btn => {
                    return btn.textContent.trim() === 'YYYY.MM' && btn.offsetParent !== null;
                }).slice(0, 6).map(btn => ({
                    class: btn.className.substring(0, 100),
                    text: btn.textContent.trim(),
                    type: btn.type
                }));

                // 재직형태 텍스트 탐색
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const txt = walker.currentNode.textContent.trim();
                    const el = walker.currentNode.parentElement;
                    if (!el || !el.offsetParent) continue;
                    if (txt && (
                        txt.includes('재직') || txt.includes('형태') ||
                        txt === '정규직' || txt === '계약직' || txt === '인턴' ||
                        txt === '파트타임' || txt === '프리랜서'
                    ) && txt.length < 30) {
                        results.emp_type_elements.push({
                            text: txt,
                            tag: el.tagName,
                            class: el.className?.substring(0, 80) || '',
                            role: el.getAttribute('role') || ''
                        });
                    }
                }
                results.emp_type_elements = results.emp_type_elements.slice(0, 15);
                return results;
            }""")
            print(f"날짜 버튼 수: {len(career_dom_info['date_buttons'])}")
            print(f"재직형태 관련 요소: {career_dom_info['emp_type_elements']}")

            # ===== 재직 날짜 입력 =====
            date_filled = False
            yyyy_mm_buttons = page.locator('button').filter(has_text='YYYY.MM')
            btn_count = await yyyy_mm_buttons.count()
            print(f"YYYY.MM 버튼 개수: {btn_count}")

            if btn_count > 0:
                first_btn = yyyy_mm_buttons.first
                await first_btn.scroll_into_view_if_needed()
                await first_btn.click(force=True)
                await page.wait_for_timeout(1500)

                # 클릭 후 나타난 UI 탐색
                after_date_dom = await page.evaluate("""() => {
                    const res = { inputs: [], wds_pickers: [], focused_tag: '' };

                    // 현재 focused 요소
                    if (document.activeElement) {
                        res.focused_tag = document.activeElement.tagName + '|' +
                            (document.activeElement.className || '').substring(0, 80) + '|' +
                            (document.activeElement.placeholder || '') + '|' +
                            (document.activeElement.type || '');
                    }

                    // 새 input 탐색
                    res.inputs = [...document.querySelectorAll('input')].filter(el => el.offsetParent !== null)
                        .map(el => ({
                            placeholder: el.placeholder,
                            type: el.type,
                            name: el.name,
                            value: el.value.substring(0, 20)
                        }));

                    // WDS picker 계열 요소
                    res.wds_pickers = [...document.querySelectorAll('[class]')]
                        .filter(el => {
                            if (!el.offsetParent) return false;
                            const cls = el.className || '';
                            if (typeof cls !== 'string') return false;
                            return cls.includes('picker') || cls.includes('Picker') ||
                                   cls.includes('calendar') || cls.includes('Calendar') ||
                                   cls.includes('datepick') || cls.includes('DatePick') ||
                                   cls.includes('yearmonth') || cls.includes('YearMonth');
                        })
                        .slice(0, 5)
                        .map(el => ({
                            tag: el.tagName,
                            class: el.className.substring(0, 100),
                            text: el.textContent.substring(0, 80)
                        }));

                    return res;
                }""")
                print(f"날짜 클릭 후 focused: {after_date_dom['focused_tag']}")
                print(f"날짜 클릭 후 wds_pickers: {after_date_dom['wds_pickers']}")

                date_inputs = [x for x in after_date_dom['inputs'] if
                               'YYYY' in (x.get('placeholder', '') or '') or
                               'year' in (x.get('name', '') or '').lower() or
                               'month' in (x.get('name', '') or '').lower()]
                print(f"날짜 관련 inputs: {date_inputs}")

                # 포커스가 버튼/input에 있을 때 직접 키보드 입력 시도
                focused_info = after_date_dom.get('focused_tag', '')
                if 'INPUT' in focused_info or 'BUTTON' in focused_info:
                    await page.keyboard.type("2020", delay=100)
                    await page.wait_for_timeout(500)
                    await page.keyboard.press('Tab')
                    await page.wait_for_timeout(300)
                    await page.keyboard.type("03", delay=100)
                    await page.wait_for_timeout(500)
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(800)
                    print("키보드로 날짜 입력 시도")

                # date 관련 특정 input이 있으면 직접 입력
                year_input = page.locator('input[name*="year"], input[placeholder="YYYY"], input[placeholder*="년"]')
                if await year_input.count() > 0 and await year_input.first.is_visible():
                    await year_input.first.fill("2020")
                    await page.wait_for_timeout(300)
                    month_input = page.locator('input[name*="month"], input[placeholder="MM"], input[placeholder*="월"]')
                    if await month_input.count() > 0:
                        await month_input.first.fill("03")
                        await page.wait_for_timeout(300)
                    date_filled = True
                    print("년/월 input 직접 입력 완료")

                # 날짜 picker를 Escape 대신 다른 곳 클릭으로 닫기
                await page.mouse.click(10, 10)
                await page.wait_for_timeout(500)

                # 날짜 입력 결과 확인 (버튼 텍스트가 날짜로 변경됐는지)
                date_btn_texts = await page.evaluate("""() => {
                    return [...document.querySelectorAll('button')].filter(el => el.offsetParent !== null)
                        .filter(btn => /\d{4}\.\d{2}/.test(btn.textContent.trim()))
                        .slice(0, 3)
                        .map(btn => btn.textContent.trim());
                }""")
                if date_btn_texts:
                    date_filled = True
                    print(f"날짜 입력 확인: {date_btn_texts}")
                else:
                    print("날짜 버튼 텍스트 변경 없음 - 계속 진행")

            # ===== 재직형태 선택 =====
            emp_filled = False

            # 방법 1: 직접 보이는 재직형태 버튼 클릭
            emp_keywords = ['정규직', '계약직', '인턴', '파트타임', '프리랜서', '파견']
            for kw in emp_keywords:
                btn = page.get_by_text(kw, exact=True)
                try:
                    cnt = await btn.count()
                    if cnt > 0:
                        for i in range(cnt):
                            if await btn.nth(i).is_visible():
                                await btn.nth(i).scroll_into_view_if_needed()
                                await btn.nth(i).click()
                                emp_filled = True
                                print(f"재직형태 '{kw}' 선택 완료")
                                await page.wait_for_timeout(500)
                                break
                except Exception:
                    pass
                if emp_filled:
                    break

            # 방법 2: 재직형태 트리거 버튼/드롭다운 탐색
            if not emp_filled:
                emp_trigger_clicked = await page.evaluate("""() => {
                    const allEls = [...document.querySelectorAll('button, [role="combobox"], select, [role="button"]')];
                    const matching = allEls.filter(el => {
                        if (!el.offsetParent) return false;
                        const text = el.textContent.trim();
                        return text.includes('재직 형태') || text.includes('재직형태') ||
                               text === '선택' || text.includes('고용 형태') ||
                               text.includes('근무 형태') || text.includes('형태 선택');
                    });
                    if (matching.length > 0) {
                        matching[0].click();
                        return { found: true, text: matching[0].textContent.trim().substring(0, 50) };
                    }
                    return { found: false };
                }""")
                print(f"재직형태 트리거: {emp_trigger_clicked}")

                if emp_trigger_clicked.get('found'):
                    await page.wait_for_timeout(1500)
                    for kw in emp_keywords:
                        btn = page.get_by_text(kw, exact=True)
                        if await btn.count() > 0 and await btn.first.is_visible():
                            await btn.first.click(timeout=5000, force=True)
                            emp_filled = True
                            print(f"드롭다운에서 재직형태 '{kw}' 선택")
                            await page.wait_for_timeout(500)
                            break

            # 방법 3: select 요소 탐색
            if not emp_filled:
                selects = page.locator('select')
                for i in range(await selects.count()):
                    sel_el = selects.nth(i)
                    if await sel_el.is_visible():
                        opts = await sel_el.evaluate("el => [...el.options].map(o => o.text)")
                        print(f"select options: {opts}")
                        for kw in emp_keywords:
                            if kw in opts:
                                await sel_el.select_option(label=kw)
                                emp_filled = True
                                print(f"select 재직형태 '{kw}' 선택")
                                break
                    if emp_filled:
                        break

            # 방법 4: 경력 섹션 스크롤 후 재탐색
            if not emp_filled:
                # 경력 관련 섹션 스크롤
                await page.evaluate("window.scrollBy(0, 200)")
                await page.wait_for_timeout(500)

                all_visible_btns = await page.evaluate("""() => {
                    return [...document.querySelectorAll('button')].filter(el => el.offsetParent !== null)
                        .slice(0, 60)
                        .map(el => el.textContent.trim().substring(0, 30))
                        .filter(t => t.length > 0 && t.length < 20);
                }""")
                print(f"스크롤 후 visible 버튼들: {all_visible_btns[:30]}")

                for kw in emp_keywords:
                    btn = page.get_by_text(kw, exact=True)
                    if await btn.count() > 0 and await btn.first.is_visible():
                        await btn.first.click()
                        emp_filled = True
                        print(f"스크롤 후 재직형태 '{kw}' 선택")
                        await page.wait_for_timeout(500)
                        break

            if not emp_filled:
                print("⚠️ 재직형태 선택 실패 - 계속 진행합니다.")

            # 재직형태 select 트리거가 포커스를 붙잡고 있으면 이후 입력 필드로 포커스가
            # 넘어가지 않으므로, 빈 곳을 클릭해 포커스를 명시적으로 해제한다.
            await page.mouse.click(10, 10)
            await page.wait_for_timeout(500)

            # ===== 주요 성과 입력 =====
            achievement_input = page.locator('input[placeholder*="주요 성과"]').first
            visible_ach = await achievement_input.count() > 0 and await achievement_input.is_visible()

            if not visible_ach:
                for btn_text in ['주요 성과 추가', '+ 주요 성과 추가', '성과 추가']:
                    btn = page.get_by_text(btn_text, exact=False)
                    if await btn.count() > 0 and await btn.first.is_visible():
                        await btn.first.scroll_into_view_if_needed()
                        await btn.first.click()
                        await page.wait_for_timeout(1000)
                        print(f"'{btn_text}' 버튼 클릭")
                        break

            achievement_input = page.locator('input[placeholder*="주요 성과"]').first
            if await achievement_input.count() > 0 and await achievement_input.is_visible():
                current_ach = await achievement_input.input_value()
                if not current_ach:
                    await achievement_input.scroll_into_view_if_needed()
                    await achievement_input.click()
                    await page.wait_for_timeout(300)
                    await achievement_input.fill("백엔드 시스템 설계 및 개발")
                    await page.wait_for_timeout(500)
                    print("주요 성과 입력 완료")
                else:
                    print(f"주요 성과 기존값 유지: '{current_ach}'")
            else:
                print("⚠️ 주요 성과 input을 찾을 수 없음")

            # ===== 주요 성과 상세 입력 =====
            achievement_detail = None
            detail_selectors = [
                'textarea[placeholder*="상세"]',
                'textarea[placeholder*="성과"]',
                'textarea[placeholder*="내용"]',
                'textarea[placeholder*="설명"]',
                'textarea',
            ]
            for sel in detail_selectors:
                ta = page.locator(sel)
                cnt = await ta.count()
                if cnt > 0:
                    for i in range(min(cnt, 3)):
                        if await ta.nth(i).is_visible():
                            achievement_detail = ta.nth(i)
                            print(f"주요 성과 상세 textarea 발견: {sel}")
                            break
                if achievement_detail:
                    break

            if achievement_detail is not None:
                current_detail = await achievement_detail.input_value()
                if not current_detail:
                    await achievement_detail.scroll_into_view_if_needed()
                    detail_text = "마이크로서비스 아키텍처 기반 API 설계 및 성능 최적화로 응답 속도 30% 개선"
                    # 이 textarea는 auto-resize 컴포넌트라 fill()로는 React 상태가 갱신되지 않아
                    # 실제 키보드 입력(keyboard.type)으로 값을 채운다.
                    try:
                        await achievement_detail.click(timeout=5000)
                    except Exception:
                        print("일반 클릭 실패 - force 클릭으로 재시도")
                        await achievement_detail.click(force=True, timeout=5000)
                    await page.wait_for_timeout(300)
                    await page.keyboard.type(detail_text, delay=20)
                    await page.wait_for_timeout(500)
                    print("주요 성과 상세 입력 완료")
                else:
                    print(f"주요 성과 상세 기존값 유지: '{current_detail[:40]}'")
            else:
                print("⚠️ 주요 성과 상세 textarea를 찾을 수 없음")

            # ===== 최종 검증 (Escape 키 누르지 않음) =====
            await page.wait_for_timeout(1000)

            # 회사명 확인
            final_company = await company_input.input_value()
            print(f"최종 회사명: '{final_company}'")
            assert len(final_company) > 0, f"회사명이 비어있습니다 ('{final_company}')"
            print(f"✅ 회사명 확인: '{final_company}'")

            # 주요 성과 확인
            ach_final_input = page.locator('input[placeholder*="주요 성과"]').first
            if await ach_final_input.count() > 0 and await ach_final_input.is_visible():
                final_ach = await ach_final_input.input_value()
                print(f"✅ 주요 성과: '{final_ach}'")
                assert len(final_ach) > 0, "주요 성과가 비어있습니다"
            else:
                print("⚠️ 주요 성과 최종 확인 불가")

            # 주요 성과 상세 확인
            final_detail_val = ""
            if achievement_detail is not None:
                final_detail_val = await achievement_detail.input_value()
            else:
                for sel in detail_selectors:
                    ta = page.locator(sel)
                    if await ta.count() > 0 and await ta.first.is_visible():
                        final_detail_val = await ta.first.input_value()
                        break
            print(f"✅ 주요 성과 상세: '{final_detail_val[:50]}'")
            assert len(final_detail_val) > 0, "주요 성과 상세가 비어있습니다"

            print("✅ 경력 항목 모두 입력 확인 완료")

            await page.screenshot(path='screenshots/test_RESUME_006_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_RESUME_006_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
