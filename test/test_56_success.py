import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json',
            viewport={'width': 1280, 'height': 1080},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── 이력서 진입 코드 ──
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            assert 'cv/list' in page.url, f"이력서 목록 페이지 진입 실패: {page.url}"

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

            print(f"[OK] 이력서 편집 페이지 진입: {page.url}")
            await page.wait_for_timeout(2000)

            # 테스트 데이터
            company_name = "원티드랩"
            achievement_title = "서비스 성능 개선"
            achievement_detail = "API 응답 속도를 30% 향상시켜 사용자 경험을 크게 개선하였습니다."

            results = {
                'company': False,
                'start_date': False,
                'employ_type': False,
                'achievement': False,
                'achievement_detail': False,
            }

            # ── 1. 회사명 입력 ──
            print("\n[INFO] 회사명 입력...")
            comp_inp = page.locator('input[placeholder*="회사명"]').first
            if await comp_inp.count() > 0:
                await comp_inp.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                await comp_inp.click()
                await page.wait_for_timeout(300)
                # 기존 내용 지우기
                await comp_inp.fill('')
                await page.wait_for_timeout(200)
                await comp_inp.type(company_name, delay=100)
                await page.wait_for_timeout(1200)  # 자동완성 대기

                # 자동완성 옵션 탐색
                all_options = page.locator('[class*="CompanyNameAutoComplete"][class*="option"]')
                opts_cnt = await all_options.count()
                print(f"[INFO] CompanyNameAutoComplete 옵션 수: {opts_cnt}")

                if opts_cnt > 0:
                    selected = False
                    for i in range(opts_cnt):
                        opt = all_options.nth(i)
                        try:
                            txt = await opt.inner_text()
                            txt = txt.strip()
                            print(f"  option[{i}]: '{txt}'")
                            # 원티드랩 정확히 매칭 (파트너스, 러닝, 커리어 등 제외)
                            if txt == '원티드랩':
                                await opt.click(timeout=5000)
                                selected = True
                                print(f"[OK] '원티드랩' 선택 (index={i})")
                                break
                        except Exception as e:
                            print(f"  option[{i}] 오류: {e}")

                    if not selected:
                        # 직접 입력하기 옵션 선택
                        for i in range(opts_cnt):
                            opt = all_options.nth(i)
                            try:
                                txt = (await opt.inner_text()).strip()
                                if '직접 입력' in txt:
                                    await opt.click(timeout=5000)
                                    selected = True
                                    print(f"[OK] '직접 입력하기' 선택")
                                    break
                            except Exception:
                                pass

                        if not selected:
                            # 첫 번째 옵션 선택 (fallback)
                            try:
                                await all_options.first.click(timeout=5000)
                                selected = True
                                print("[OK] fallback: 첫 번째 옵션 선택")
                            except Exception as e:
                                print(f"[WARN] fallback 실패: {e}")
                                await page.keyboard.press('Escape')
                else:
                    await page.keyboard.press('Escape')
                    print("[WARN] 자동완성 없음")

                await page.wait_for_timeout(500)
                cur_val = await comp_inp.input_value()
                print(f"[INFO] 회사명 현재 값: '{cur_val}'")
                results['company'] = bool(cur_val and cur_val != '회사명' and cur_val != '')
                if results['company']:
                    print(f"[OK] 회사명 입력 완료: '{cur_val}'")

            await page.wait_for_timeout(500)

            # ── 2. 재직 날짜 입력 ──
            print("\n[INFO] 재직 날짜 입력...")
            # 이미 설정된 날짜 확인
            date_els = page.locator('[class*="wds-92tzrw"]')
            d_cnt = await date_els.count()
            for i in range(d_cnt):
                txt = await date_els.nth(i).inner_text()
                if txt and 'YYYY' not in txt and '.' in txt:
                    results['start_date'] = True
                    print(f"[OK] 이미 날짜 설정됨: '{txt}'")
                    break

            if not results['start_date']:
                date_btns = page.get_by_text('YYYY.MM', exact=True)
                date_cnt = await date_btns.count()
                print(f"[INFO] YYYY.MM 버튼 수: {date_cnt}")

                if date_cnt >= 1:
                    try:
                        start_btn = date_btns.first
                        await start_btn.scroll_into_view_if_needed()
                        await start_btn.click(timeout=5000)
                        await page.wait_for_timeout(1000)

                        # 년도 선택
                        year_clicked = False
                        for yr in ['2022', '2021', '2023']:
                            yr_btns = page.get_by_text(yr, exact=True)
                            if await yr_btns.count() > 0:
                                for i in range(await yr_btns.count()):
                                    try:
                                        b = yr_btns.nth(i)
                                        if await b.is_visible():
                                            await b.click(timeout=3000)
                                            year_clicked = True
                                            print(f"[OK] {yr} 클릭")
                                            break
                                    except Exception:
                                        pass
                            if year_clicked:
                                break

                        await page.wait_for_timeout(500)

                        # 월 선택
                        for mo in ['1월', '1']:
                            mo_btns = page.get_by_text(mo, exact=True)
                            if await mo_btns.count() > 0:
                                for i in range(await mo_btns.count()):
                                    try:
                                        b = mo_btns.nth(i)
                                        if await b.is_visible():
                                            await b.click(timeout=3000)
                                            print(f"[OK] 월 '{mo}' 클릭")
                                            break
                                    except Exception:
                                        pass
                                break

                        await page.wait_for_timeout(300)

                        # 확인
                        for kw in ['확인', '적용']:
                            try:
                                btn = page.get_by_text(kw, exact=True)
                                if await btn.count() > 0 and await btn.first.is_visible():
                                    await btn.first.click(timeout=3000)
                                    await page.wait_for_timeout(500)
                                    results['start_date'] = True
                                    print(f"[OK] '{kw}' - 날짜 설정 완료")
                                    break
                            except Exception:
                                pass

                        await page.keyboard.press('Escape')
                        await page.wait_for_timeout(500)

                    except Exception as e:
                        print(f"[WARN] 날짜 피커 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 3. 재직형태 선택 (Select_Select 커스텀 드롭다운) ──
            print("\n[INFO] 재직형태 선택...")

            # 재직 형태 Select 컴포넌트 찾기
            # 클래스: Select_Select__fEsOi Select_Select_required__ExuC2
            # 또는 class*="Select_Select" 내 class*="Select_required"
            employ_select = page.locator('[class*="Select_Select__"]').first
            es_cnt = await employ_select.count()
            print(f"[INFO] Select_Select__ 컴포넌트 수: {es_cnt}")

            if es_cnt > 0:
                await employ_select.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                print("[INFO] Select 컴포넌트 클릭...")
                await employ_select.click(timeout=8000)
                await page.wait_for_timeout(1000)

                # 드롭다운 옵션 스캔
                dropdown_scan = await page.evaluate("""() => {
                    const res = [];
                    const selectors = [
                        '[role="option"]',
                        '[role="listbox"] [class*="item"]',
                        '[role="listbox"] li',
                        '[role="menu"] li',
                        '[class*="OptionItem"]',
                        '[class*="optionItem"]',
                        '[class*="SelectItem"]',
                        '[class*="selectItem"]',
                    ];
                    for (const sel of selectors) {
                        const items = [...document.querySelectorAll(sel)];
                        const visible = items.filter(el => {
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0;
                        });
                        if (visible.length > 0) {
                            visible.forEach(el => {
                                const text = (el.innerText||'').trim().replace(/\\s+/g,' ');
                                if (text.length > 0 && text.length < 60)
                                    res.push({ text: text.slice(0,50), sel,
                                        cls: (el.className||'').slice(0,60),
                                        x: Math.round(el.getBoundingClientRect().left),
                                        y: Math.round(el.getBoundingClientRect().top) });
                            });
                            break;
                        }
                    }
                    return res;
                }""")

                print(f"[INFO] 드롭다운 옵션 ({len(dropdown_scan)}개):")
                for opt in dropdown_scan:
                    print(f"  '{opt['text']}' ({opt['x']},{opt['y']}) sel={opt['sel']}")

                # 고용형태 옵션 선택 (드롭다운 열린 상태에서 클릭)
                employ_choices = ['정규직', '계약직', '인턴', '파견직', '프리랜서']

                # JS로 직접 클릭 (가장 안정적)
                clicked_by_js = await page.evaluate("""(choices) => {
                    const options = [...document.querySelectorAll('[role="option"]')];
                    for (const choice of choices) {
                        const opt = options.find(el => {
                            const r = el.getBoundingClientRect();
                            return r.width > 0 && r.height > 0 && (el.innerText||'').trim() === choice;
                        });
                        if (opt) {
                            opt.click();
                            return choice;
                        }
                    }
                    return null;
                }""", employ_choices)

                if clicked_by_js:
                    results['employ_type'] = True
                    print(f"[OK] 재직형태 '{clicked_by_js}' JS 클릭 완료")

                # JS 실패 시 Playwright로 재시도
                if not results['employ_type']:
                    for choice in employ_choices:
                        role_opts = page.locator('[role="option"]')
                        cnt = await role_opts.count()
                        for i in range(cnt):
                            b = role_opts.nth(i)
                            txt = (await b.inner_text()).strip()
                            if txt == choice:
                                try:
                                    await b.click(force=True, timeout=5000)
                                    results['employ_type'] = True
                                    print(f"[OK] 재직형태 '{choice}' force 클릭 완료")
                                    break
                                except Exception as ce:
                                    print(f"  force 클릭 실패: {ce}")
                        if results['employ_type']:
                            break

                # 텍스트 방식 최종 폴백
                if not results['employ_type']:
                    for choice in employ_choices:
                        el = page.get_by_text(choice, exact=True)
                        for i in range(await el.count()):
                            b = el.nth(i)
                            if await b.is_visible():
                                try:
                                    await b.click(timeout=5000)
                                    results['employ_type'] = True
                                    print(f"[OK] 재직형태 '{choice}' 직접 선택")
                                    break
                                except Exception:
                                    pass
                        if results['employ_type']:
                            break

            await page.wait_for_timeout(500)

            # 재직형태 여전히 실패시 CareerItem 내 Select 재시도
            if not results['employ_type']:
                print("[INFO] CareerItem 내 Select 재시도...")
                career_selects = page.locator('[class*="CareerItem"] [class*="Select_Select"]')
                cs_cnt = await career_selects.count()
                print(f"[INFO] CareerItem > Select 수: {cs_cnt}")
                if cs_cnt > 0:
                    await career_selects.first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await career_selects.first.click(timeout=8000)
                    await page.wait_for_timeout(1000)

                    for choice in ['정규직', '계약직', '인턴']:
                        el = page.get_by_text(choice, exact=True)
                        if await el.count() > 0:
                            for i in range(await el.count()):
                                b = el.nth(i)
                                if await b.is_visible():
                                    await b.click(timeout=5000)
                                    results['employ_type'] = True
                                    print(f"[OK] 재직형태 '{choice}' 재시도 성공")
                                    break
                        if results['employ_type']:
                            break

            await page.wait_for_timeout(500)

            # ── 4. 주요 성과 입력 ──
            print("\n[INFO] 주요 성과 입력...")
            achieve_input = page.locator('input[placeholder*="주요 성과"]').first
            if await achieve_input.count() > 0:
                try:
                    await achieve_input.scroll_into_view_if_needed()
                    await page.wait_for_timeout(300)
                    await achieve_input.fill(achievement_title)
                    await page.wait_for_timeout(300)
                    cur_val = await achieve_input.input_value()
                    if cur_val:
                        results['achievement'] = True
                        print(f"[OK] 주요 성과 입력 완료: '{cur_val}'")
                except Exception as e:
                    print(f"[WARN] 주요 성과 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 5. 주요 성과 상세 입력 ──
            print("\n[INFO] 주요 성과 상세 입력...")
            detail_ta = page.locator('textarea[placeholder*="업무 경험"]').first
            if await detail_ta.count() > 0:
                try:
                    await detail_ta.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await detail_ta.fill(achievement_detail)
                    await page.wait_for_timeout(300)
                    cur_val = await detail_ta.input_value()
                    if cur_val:
                        results['achievement_detail'] = True
                        print(f"[OK] 주요 성과 상세 입력 완료")
                except Exception as e:
                    print(f"[WARN] 주요 성과 상세 1차 실패: {e}")
                    try:
                        handle = await detail_ta.element_handle()
                        await page.evaluate("""([el, val]) => {
                            const setter = Object.getOwnPropertyDescriptor(
                                window.HTMLTextAreaElement.prototype, 'value').set;
                            setter.call(el, val);
                            el.dispatchEvent(new Event('input', {bubbles: true}));
                            el.dispatchEvent(new Event('change', {bubbles: true}));
                        }""", [handle, achievement_detail])
                        await page.wait_for_timeout(300)
                        cur_val = await detail_ta.input_value()
                        if cur_val:
                            results['achievement_detail'] = True
                            print("[OK] JS로 주요 성과 상세 입력 완료")
                    except Exception as e2:
                        print(f"[WARN] JS 방식도 실패: {e2}")

            await page.wait_for_timeout(1000)

            # ── 6. 최종 검증 ──
            print("\n[INFO] 최종 결과 요약:")
            for k, v in results.items():
                print(f"  {k}: {'✅' if v else '❌'}")

            assert results['company'], "회사명 입력 실패"
            assert results['start_date'], "재직 날짜 입력 실패"
            assert results['employ_type'], "재직형태 선택 실패"
            assert results['achievement'], "주요 성과 입력 실패"
            assert results['achievement_detail'], "주요 성과 상세 입력 실패"

            print("\n[OK] TC56 - 경력 항목 모두 입력 완료!")

            await page.screenshot(path='screenshots/test_56_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_56_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
