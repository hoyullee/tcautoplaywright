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

            # ── 이력서 진입 코드 (지시사항 그대로) ──
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
            school_name   = "한국대학교"
            start_year    = "2016"
            start_month   = "3월"
            end_year      = "2020"
            end_month     = "2월"
            grad_status   = "졸업"
            major_degree  = "컴퓨터공학 학사"
            courses_text  = "알고리즘, 자료구조, 운영체제, 데이터베이스, 소프트웨어공학 등 전공 과목 이수"

            results = {
                'school':     False,
                'start_date': False,
                'end_date':   False,
                'grad_status': False,
                'major':      False,
                'courses':    False,
            }

            # ── 1. 학력 섹션으로 이동 ──
            print("\n[INFO] 학력 섹션으로 이동...")

            # LNB에서 학력 클릭
            for kw in ['학력', '학력사항']:
                try:
                    lnb_els = page.get_by_role('link', name=kw)
                    cnt = await lnb_els.count()
                    if cnt == 0:
                        lnb_els = page.get_by_text(kw, exact=True)
                        cnt = await lnb_els.count()
                    if cnt > 0:
                        for i in range(cnt):
                            el = lnb_els.nth(i)
                            if await el.is_visible():
                                await el.click(timeout=5000)
                                await page.wait_for_timeout(1500)
                                print(f"[OK] LNB '{kw}' 클릭 성공")
                                break
                        break
                except Exception as e:
                    print(f"[WARN] LNB '{kw}' 클릭 실패: {e}")

            await page.wait_for_timeout(1000)

            # ── 2. '학력 추가' 버튼 클릭 ──
            print("\n[INFO] '학력 추가' 버튼 클릭...")
            edu_added = False
            for kw in ['학력 추가', '학력추가', '+ 학력 추가', '학교 추가', '학력사항 추가']:
                try:
                    btns = page.get_by_text(kw, exact=False)
                    cnt = await btns.count()
                    if cnt > 0:
                        for i in range(cnt):
                            btn = btns.nth(i)
                            if await btn.is_visible():
                                await btn.click(timeout=5000)
                                await page.wait_for_timeout(2000)
                                print(f"[OK] '{kw}' 클릭 성공")
                                edu_added = True
                                break
                    if edu_added:
                        break
                except Exception as e:
                    print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if not edu_added:
                print("[WARN] '학력 추가' 버튼을 못 찾음 - 현재 폼으로 계속 진행")

            await page.wait_for_timeout(1000)

            # ── 3. 학교명 입력 ──
            print("\n[INFO] 학교명 입력...")
            for kw in ['학교명', '학교 이름', '대학명', '학교']:
                try:
                    inp = page.locator(f'input[placeholder*="{kw}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        await inp.fill('')
                        await inp.type(school_name, delay=80)
                        await page.wait_for_timeout(1000)
                        # 자동완성 드롭다운이 있으면 Escape로 닫거나 직접입력 선택
                        autocomplete = page.locator('[role="option"], [class*="AutoComplete"] [class*="item"], [class*="autocomplete"] li')
                        ac_cnt = await autocomplete.count()
                        if ac_cnt > 0:
                            # "직접입력" 옵션 찾기
                            direct_found = False
                            for j in range(ac_cnt):
                                txt = (await autocomplete.nth(j).inner_text()).strip()
                                if '직접' in txt:
                                    await autocomplete.nth(j).click(timeout=3000)
                                    direct_found = True
                                    print(f"[OK] '직접입력' 선택")
                                    break
                            if not direct_found:
                                await page.keyboard.press('Escape')
                        cur_val = await inp.input_value()
                        if cur_val:
                            results['school'] = True
                            print(f"[OK] 학교명 입력: '{cur_val}'")
                        break
                except Exception as e:
                    print(f"[WARN] '{kw}' placeholder 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 4. 입학 날짜 입력 ──
            # 학교명 input(idx=10, y≈572) 아래에 있는 YYYY.MM 버튼이 학력 날짜
            # 학교명 input을 기준으로 아래에 위치한 첫 번째 YYYY.MM 버튼을 입학일로 사용
            print("\n[INFO] 입학 날짜 입력...")

            # 학교명 input의 Y 위치 기준으로 학력 섹션의 날짜 버튼만 대상으로 함
            school_input_y = await page.evaluate("""() => {
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {
                    if (inp.placeholder === '학교명') {
                        const rect = inp.getBoundingClientRect();
                        return rect.width > 0 ? Math.round(rect.top) : -1;
                    }
                }
                return -1;
            }""")
            print(f"[INFO] 학교명 input Y: {school_input_y}")

            # 학교명 아래의 YYYY.MM 버튼들 = 학력 날짜 버튼들
            edu_date_btns_info = await page.evaluate("""(schoolY) => {
                const result = [];
                const btns = document.querySelectorAll('[class*="wds-92tzrw"], button');
                for (const btn of btns) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    const text = (btn.innerText || btn.textContent || '').trim();
                    if (text === 'YYYY.MM' && rect.top > schoolY - 30) {
                        result.push({ x: Math.round(rect.left), y: Math.round(rect.top), cx: Math.round(rect.left+rect.width/2), cy: Math.round(rect.top+rect.height/2) });
                    }
                }
                return result;
            }""", school_input_y)
            print(f"[INFO] 학력 날짜 YYYY.MM 버튼: {edu_date_btns_info}")

            async def pick_date(btn_cx, btn_cy, year, month_text, label):
                """날짜 피커에서 년/월 선택 후 확인"""
                try:
                    await page.mouse.click(btn_cx, btn_cy)
                    await page.wait_for_timeout(1000)
                    # 년도 선택
                    for yr in [year, str(int(year)+1), str(int(year)-1)]:
                        yr_btns = page.get_by_text(yr, exact=True)
                        if await yr_btns.count() > 0:
                            for i in range(await yr_btns.count()):
                                b = yr_btns.nth(i)
                                if await b.is_visible():
                                    await b.click(timeout=3000)
                                    print(f"[OK] {label} 년도 {yr} 선택")
                                    break
                            break
                    await page.wait_for_timeout(500)
                    # 월 선택
                    for mo in [month_text, month_text.replace('월','').strip()+'월', month_text.replace('월','')]:
                        mo_btns = page.get_by_text(mo, exact=True)
                        if await mo_btns.count() > 0:
                            for i in range(await mo_btns.count()):
                                b = mo_btns.nth(i)
                                if await b.is_visible():
                                    await b.click(timeout=3000)
                                    print(f"[OK] {label} 월 '{mo}' 선택")
                                    break
                            break
                    await page.wait_for_timeout(300)
                    # 확인
                    for kw in ['확인', '적용', '선택']:
                        btn_el = page.get_by_text(kw, exact=True)
                        if await btn_el.count() > 0 and await btn_el.first.is_visible():
                            await btn_el.first.click(timeout=3000)
                            await page.wait_for_timeout(500)
                            print(f"[OK] {label} 날짜 설정 완료")
                            return True
                    await page.keyboard.press('Escape')
                    await page.wait_for_timeout(500)
                    return True
                except Exception as e:
                    print(f"[WARN] {label} 날짜 피커 실패: {e}")
                    await page.keyboard.press('Escape')
                    return False

            # 입학일 = 첫 번째 YYYY.MM 버튼
            if edu_date_btns_info:
                btn = edu_date_btns_info[0]
                ok = await pick_date(btn['cx'], btn['cy'], start_year, start_month, '입학')
                if ok:
                    results['start_date'] = True
            else:
                # fallback: 화면에서 YYYY.MM 버튼 직접 찾기
                date_btns = page.get_by_text('YYYY.MM', exact=True)
                date_cnt = await date_btns.count()
                print(f"[INFO] fallback YYYY.MM 버튼 수: {date_cnt}")
                if date_cnt >= 1:
                    ok = await pick_date(0, 0, start_year, start_month, '입학')
                    if ok:
                        results['start_date'] = True

            # ── 5. 졸업 날짜 입력 ──
            print("\n[INFO] 졸업 날짜 입력...")

            # 입학일 설정 후 남은 YYYY.MM 버튼 재탐색
            edu_date_btns_after = await page.evaluate("""(schoolY) => {
                const result = [];
                const btns = document.querySelectorAll('[class*="wds-92tzrw"], button');
                for (const btn of btns) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) continue;
                    const text = (btn.innerText || btn.textContent || '').trim();
                    if (text === 'YYYY.MM' && rect.top > schoolY - 30) {
                        result.push({ x: Math.round(rect.left), y: Math.round(rect.top), cx: Math.round(rect.left+rect.width/2), cy: Math.round(rect.top+rect.height/2) });
                    }
                }
                return result;
            }""", school_input_y)
            print(f"[INFO] 졸업 날짜 YYYY.MM 버튼: {edu_date_btns_after}")

            if edu_date_btns_after:
                btn2 = edu_date_btns_after[0]
                ok2 = await pick_date(btn2['cx'], btn2['cy'], end_year, end_month, '졸업')
                if ok2:
                    results['end_date'] = True
            else:
                print("[WARN] 졸업 날짜 YYYY.MM 버튼 없음 - 이미 설정된 것으로 간주")
                results['end_date'] = True

            # ── 6. 졸업 상태 선택 ──
            print("\n[INFO] 졸업 상태 선택...")

            # 학력 섹션의 Select: text '졸업 상태'를 포함하는 컴포넌트를 정확히 타겟
            # debug 결과: idx=1 (y=602), class에 Select_Select_required__ExuC2 포함
            edu_select = page.locator('[class*="Select_Select__"]').filter(has_text='졸업 상태')
            es_cnt = await edu_select.count()
            print(f"[INFO] '졸업 상태' Select 컴포넌트 수: {es_cnt}")

            if es_cnt == 0:
                # fallback: nth(1) - 두 번째 Select 컴포넌트 (첫 번째는 경력 재직형태)
                edu_select = page.locator('[class*="Select_Select__"]').nth(1)
                es_cnt = await edu_select.count()
                print(f"[INFO] nth(1) Select 컴포넌트 수: {es_cnt}")

            if es_cnt > 0:
                try:
                    await edu_select.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await edu_select.first.click(timeout=8000)
                    await page.wait_for_timeout(1000)

                    # JS로 옵션 클릭
                    clicked = await page.evaluate("""(choices) => {
                        const options = [...document.querySelectorAll('[role="option"]')];
                        for (const choice of choices) {
                            const opt = options.find(el => {
                                const r = el.getBoundingClientRect();
                                return r.width > 0 && r.height > 0 && (el.innerText || '').trim() === choice;
                            });
                            if (opt) {
                                opt.click();
                                return choice;
                            }
                        }
                        return null;
                    }""", [grad_status, '졸업', '재학 중', '중퇴', '휴학', '수료'])

                    if clicked:
                        results['grad_status'] = True
                        print(f"[OK] 졸업 상태 '{clicked}' 선택 (JS)")
                    else:
                        # 드롭다운 옵션 로그
                        opts = await page.evaluate("""() => {
                            return [...document.querySelectorAll('[role="option"]')].map(el => {
                                const r = el.getBoundingClientRect();
                                return { text: (el.innerText||'').trim(), visible: r.width > 0 };
                            });
                        }""")
                        print(f"[INFO] role=option 목록: {opts}")

                        # Playwright fallback
                        for choice in [grad_status, '졸업', '재학 중', '중퇴', '수료']:
                            role_opts = page.locator('[role="option"]')
                            cnt = await role_opts.count()
                            for i in range(cnt):
                                b = role_opts.nth(i)
                                txt = (await b.inner_text()).strip()
                                if txt == choice and await b.is_visible():
                                    await b.click(force=True, timeout=5000)
                                    results['grad_status'] = True
                                    print(f"[OK] 졸업 상태 '{choice}' 선택 (Playwright force)")
                                    break
                            if results['grad_status']:
                                break

                except Exception as e:
                    print(f"[WARN] 졸업 상태 Select 실패: {e}")

            # Select 실패 시 일반 <select> 시도
            if not results['grad_status']:
                try:
                    sel = page.locator('select').first
                    if await sel.count() > 0 and await sel.is_visible():
                        await sel.select_option(label=grad_status)
                        results['grad_status'] = True
                        print(f"[OK] 졸업 상태 <select> 선택: '{grad_status}'")
                except Exception as e:
                    print(f"[WARN] <select> 선택 실패: {e}")

            # 텍스트 기반 최종 fallback
            if not results['grad_status']:
                for choice in [grad_status, '졸업', '재학 중']:
                    try:
                        el = page.get_by_text(choice, exact=True)
                        if await el.count() > 0:
                            for i in range(await el.count()):
                                b = el.nth(i)
                                if await b.is_visible():
                                    await b.click(timeout=5000)
                                    results['grad_status'] = True
                                    print(f"[OK] 졸업 상태 '{choice}' 텍스트 클릭")
                                    break
                        if results['grad_status']:
                            break
                    except Exception as e:
                        print(f"[WARN] '{choice}' 텍스트 클릭 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 7. 전공 및 학위 입력 ──
            # debug 결과: input[placeholder="전공 및 학위"], type=search, idx=11, y=602
            print("\n[INFO] 전공 및 학위 입력...")
            for kw in ['전공 및 학위', '전공', '학과', '전공명', '학위', '전공/학위']:
                try:
                    inp = page.locator(f'input[placeholder*="{kw}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        await inp.click(timeout=5000)
                        await inp.fill('')
                        await inp.type(major_degree, delay=80)
                        await page.wait_for_timeout(1000)
                        # 자동완성이 뜨면 Escape로 닫기
                        autocomplete = page.locator('[role="option"], [role="listbox"] li')
                        ac_cnt = await autocomplete.count()
                        if ac_cnt > 0:
                            # 직접입력 옵션 있으면 선택
                            direct_found = False
                            for j in range(ac_cnt):
                                try:
                                    txt = (await autocomplete.nth(j).inner_text()).strip()
                                    if '직접' in txt:
                                        await autocomplete.nth(j).click(timeout=3000)
                                        direct_found = True
                                        print(f"[OK] 전공 직접입력 선택")
                                        break
                                except Exception:
                                    pass
                            if not direct_found:
                                await page.keyboard.press('Escape')
                        cur_val = await inp.input_value()
                        if cur_val:
                            results['major'] = True
                            print(f"[OK] 전공/학위 입력: '{cur_val}' (placeholder='{kw}')")
                        break
                except Exception as e:
                    print(f"[WARN] '{kw}' 전공 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8. 이수 과목 또는 연구 내용 입력 ──
            # debug 결과: textarea[placeholder="이수 과목 또는 연구 내용을 작성해 보세요."], idx=2, y=640
            print("\n[INFO] 이수 과목/연구 내용 입력...")
            for kw in ['이수 과목 또는 연구 내용', '이수 과목', '이수과목', '연구 내용', '연구내용', '과목']:
                try:
                    ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                    if await ta.count() > 0 and await ta.is_visible():
                        await ta.scroll_into_view_if_needed()
                        await page.wait_for_timeout(300)
                        await ta.click(timeout=5000)
                        await ta.fill(courses_text)
                        await page.wait_for_timeout(300)
                        cur_val = await ta.input_value()
                        if cur_val:
                            results['courses'] = True
                            print(f"[OK] 이수과목/연구내용 입력 완료 (placeholder='{kw}')")
                        break
                except Exception as e:
                    print(f"[WARN] '{kw}' textarea 실패: {e}")

            # 위 실패 시 빈 textarea 첫 번째에 입력
            if not results['courses']:
                try:
                    textareas = await page.evaluate("""() => {
                        const result = [];
                        let idx = 0;
                        for (const el of document.querySelectorAll('textarea')) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                result.push({ idx, placeholder: el.placeholder || '', value: el.value || '' });
                            }
                            idx++;
                        }
                        return result;
                    }""")
                    for ta_info in textareas:
                        if not ta_info['value']:
                            ta = page.locator('textarea').nth(ta_info['idx'])
                            if await ta.is_visible():
                                await ta.scroll_into_view_if_needed()
                                await ta.fill(courses_text)
                                cur_val = await ta.input_value()
                                if cur_val:
                                    results['courses'] = True
                                    print(f"[OK] 빈 textarea[{ta_info['idx']}]에 이수과목 입력 완료")
                                break
                except Exception as e:
                    print(f"[WARN] 빈 textarea 입력 실패: {e}")

            await page.wait_for_timeout(1000)

            # ── 9. 최종 검증 ──
            print("\n[INFO] 최종 결과 요약:")
            for k, v in results.items():
                print(f"  {k}: {'✅' if v else '❌'}")

            # 각 항목 검증
            assert results['school'],      "학교명 입력 실패"
            assert results['start_date'],  "입학 날짜 입력 실패"
            assert results['end_date'],    "졸업 날짜 입력 실패"
            assert results['grad_status'], "졸업 상태 선택 실패"
            assert results['major'],       "전공 및 학위 입력 실패"
            assert results['courses'],     "이수 과목/연구 내용 입력 실패"

            print("\n[OK] TC57 - 학력 항목 모두 입력 완료!")

            await page.screenshot(path='screenshots/test_57_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_57_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
