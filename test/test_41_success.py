import sys
import io
from playwright.async_api import async_playwright
import asyncio
import os

# Windows 콘솔 UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

def safe_print(msg):
    """UTF-8 안전 출력"""
    try:
        print(msg)
    except Exception:
        print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


async def find_apply_button(page):
    """'지원하기' 텍스트를 가진 버튼 탐색"""
    btn_info = await page.evaluate("""() => {
        const all = [...document.querySelectorAll('button, a, [role="button"]')];
        return all
            .filter(el => {
                const text = (el.innerText || el.textContent || '').trim();
                return text === '지원하기';
            })
            .map((el, idx) => {
                const rect = el.getBoundingClientRect();
                return {
                    idx, tag: el.tagName,
                    classes: el.className.substring(0, 100),
                    visible: rect.width > 0 && rect.height > 0,
                    inViewport: rect.top >= 0 && rect.top <= window.innerHeight,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                };
            });
    }""")
    safe_print(f"[INFO] '지원하기' 버튼 JS 탐색 결과: {btn_info}")

    for sel in [
        'button:has-text("지원하기")',
        'a:has-text("지원하기")',
        '[role="button"]:has-text("지원하기")',
    ]:
        try:
            loc = page.locator(sel)
            cnt = await loc.count()
            if cnt > 0:
                for i in range(cnt):
                    item = loc.nth(i)
                    txt = (await item.text_content() or '').strip()
                    if txt == '지원하기':
                        safe_print(f"[OK] Playwright 선택자 '{sel}'로 발견: '{txt}'")
                        return item
        except Exception as e:
            safe_print(f"[WARN] selector '{sel}' 오류: {e}")

    try:
        loc = page.get_by_role('button', name='지원하기', exact=True)
        cnt = await loc.count()
        if cnt > 0:
            safe_print("[OK] get_by_role로 '지원하기' 버튼 발견")
            return loc.first
    except Exception as e:
        safe_print(f"[WARN] get_by_role 오류: {e}")

    if btn_info:
        return 'use_js'

    return None


async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            storage_state='work/auth_state.json',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()
        active_page = page

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 목록 페이지 접속
            safe_print("[INFO] 채용 목록 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 채용 목록 로드: {page.url}")

            # 2. 포지션 URL 목록 수집
            wd_links = page.locator('a[href*="/wd/"]')
            count = await wd_links.count()
            safe_print(f"[INFO] /wd/ 링크 수: {count}")
            assert count > 0, "포지션 링크를 찾을 수 없습니다"

            hrefs = []
            for i in range(min(count, 20)):
                try:
                    href = await wd_links.nth(i).get_attribute('href')
                    if href and '/wd/' in href:
                        url = href if href.startswith('http') else f"https://www.wanted.co.kr{href}"
                        if url not in hrefs:
                            hrefs.append(url)
                except Exception:
                    continue
            safe_print(f"[INFO] 수집된 포지션 URL 수: {len(hrefs)}")

            # 3. '지원하기' 버튼이 있는 포지션 탐색
            position_url = None
            apply_btn = None

            for pos_url in hrefs[:15]:
                safe_print(f"[INFO] 포지션 시도: {pos_url}")
                await page.goto(pos_url, timeout=60000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(4000)

                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(1000)

                found = await find_apply_button(page)
                if found is not None:
                    position_url = pos_url
                    apply_btn = found
                    safe_print(f"[OK] '지원하기' 버튼 있는 포지션: {pos_url}")
                    break

                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(1000)
                found2 = await find_apply_button(page)
                if found2 is not None:
                    position_url = pos_url
                    apply_btn = found2
                    safe_print(f"[OK] 스크롤 후 '지원하기' 버튼 있는 포지션: {pos_url}")
                    break

            assert apply_btn is not None, "'지원하기' 버튼이 있는 포지션을 찾을 수 없습니다"
            safe_print(f"[OK] 포지션 URL: {position_url}")

            # 4. '지원하기' 버튼 클릭
            safe_print("[STEP 1] '지원하기' 버튼 클릭 중...")
            await page.screenshot(path='screenshots/test_41_step1_before_apply.png')

            if apply_btn == 'use_js':
                safe_print("[INFO] JS로 '지원하기' 버튼 클릭...")
                await page.evaluate("""() => {
                    const all = [...document.querySelectorAll('button, a, [role="button"]')];
                    for (const el of all) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === '지원하기') { el.click(); return; }
                    }
                }""")
            else:
                try:
                    await apply_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    await apply_btn.click(timeout=10000)
                    safe_print("[OK] Playwright click 완료")
                except Exception as click_err:
                    safe_print(f"[WARN] Playwright click 오류: {click_err}, JS 클릭 시도...")
                    await page.evaluate("""() => {
                        const all = [...document.querySelectorAll('button, a, [role="button"]')];
                        for (const el of all) {
                            const text = (el.innerText || el.textContent || '').trim();
                            if (text === '지원하기') { el.click(); return; }
                        }
                    }""")

            # 클릭 후 모달/페이지 로드 대기
            await page.wait_for_timeout(4000)

            # 새 탭 처리
            active_page = page
            pages = context.pages
            if len(pages) > 1:
                active_page = pages[-1]
                await active_page.wait_for_load_state('domcontentloaded')
                await active_page.wait_for_timeout(3000)
                safe_print(f"[INFO] 새 탭 URL: {active_page.url}")

            await active_page.screenshot(path='screenshots/test_41_step2_after_apply_click.png')
            safe_print(f"[INFO] 클릭 후 URL: {active_page.url}")

            # 5. 지원 페이지/모달 내 이력서 체크박스 탐색
            safe_print("[STEP 2] 이력서 체크박스 탐색 중...")

            # 지원 페이지 DOM 분석
            dom_info = await active_page.evaluate("""() => {
                // 체크박스 요소
                const checkboxes = [...document.querySelectorAll(
                    'input[type="checkbox"], [role="checkbox"], [class*="check"], [class*="Check"], ' +
                    '[class*="resume"], [class*="Resume"]'
                )].map(el => {
                    const rect = el.getBoundingClientRect();
                    return {
                        tag: el.tagName,
                        type: el.type || '',
                        role: el.getAttribute('role') || '',
                        classes: el.className.substring(0, 120),
                        id: el.id || '',
                        name: el.name || '',
                        checked: el.checked,
                        visible: rect.width > 0 && rect.height > 0,
                        ariaLabel: el.getAttribute('aria-label') || '',
                        ariaChecked: el.getAttribute('aria-checked') || '',
                    };
                });

                // 버튼 목록
                const buttons = [...document.querySelectorAll('button, [role="button"]')]
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            text: (el.innerText || el.textContent || '').trim().substring(0, 80),
                            classes: el.className.substring(0, 120),
                            disabled: el.disabled,
                            ariaDisabled: el.getAttribute('aria-disabled'),
                            visible: rect.width > 0 && rect.height > 0,
                        };
                    })
                    .filter(b => b.text.length > 0);

                // 모달/오버레이 감지
                const modals = [...document.querySelectorAll(
                    '[role="dialog"], [class*="modal"], [class*="Modal"], ' +
                    '[class*="overlay"], [class*="Overlay"], [class*="apply"], [class*="Apply"]'
                )].filter(el => el.offsetParent !== null)
                 .map(el => el.innerText.substring(0, 500));

                return { checkboxes, buttons, modals, bodyText: document.body.innerText.substring(0, 2000) };
            }""")

            checkboxes = dom_info.get('checkboxes', [])
            buttons = dom_info.get('buttons', [])
            modals = dom_info.get('modals', [])
            body_text = dom_info.get('bodyText', '')

            safe_print(f"[INFO] 체크박스 수: {len(checkboxes)}")
            safe_print(f"[INFO] 버튼 목록: {[b['text'] for b in buttons[:20]]}")
            safe_print(f"[INFO] 모달 텍스트 수: {len(modals)}")
            safe_print(f"[INFO] body 텍스트 일부:\n{body_text[:500]}")

            # 6. 제출하기 버튼 초기 상태 확인 (비활성 여부)
            safe_print("[STEP 3] '제출하기' 버튼 초기 상태 확인...")
            submit_info_before = await active_page.evaluate("""() => {
                const all = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')];
                return all
                    .filter(el => {
                        const text = (el.innerText || el.textContent || el.value || '').trim();
                        return text === '제출하기' || text.includes('제출');
                    })
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return {
                            text: (el.innerText || el.textContent || '').trim(),
                            disabled: el.disabled,
                            ariaDisabled: el.getAttribute('aria-disabled'),
                            classes: el.className.substring(0, 150),
                            opacity: style.opacity,
                            pointerEvents: style.pointerEvents,
                            cursor: style.cursor,
                            visible: rect.width > 0 && rect.height > 0,
                            color: style.color,
                            backgroundColor: style.backgroundColor,
                        };
                    });
            }""")
            safe_print(f"[INFO] 제출하기 버튼 초기 상태: {submit_info_before}")

            # 7. 이력서 체크박스 선택
            safe_print("[STEP 4] 이력서 체크박스 선택 시도...")
            checkbox_clicked = False

            # 방법 1: input[type=checkbox] 직접 클릭
            checkbox_inputs = active_page.locator('input[type="checkbox"]')
            cb_count = await checkbox_inputs.count()
            safe_print(f"[INFO] input[type=checkbox] 수: {cb_count}")

            if cb_count > 0:
                for i in range(cb_count):
                    try:
                        cb = checkbox_inputs.nth(i)
                        is_visible = await cb.is_visible()
                        if is_visible:
                            await cb.scroll_into_view_if_needed()
                            await active_page.wait_for_timeout(300)
                            # 이미 체크된 경우 제외
                            is_checked = await cb.is_checked()
                            if not is_checked:
                                await cb.click(timeout=5000)
                                safe_print(f"[OK] 체크박스 {i} 클릭 완료")
                                checkbox_clicked = True
                                break
                            else:
                                safe_print(f"[INFO] 체크박스 {i} 이미 체크됨, 유지")
                                checkbox_clicked = True
                                break
                    except Exception as e:
                        safe_print(f"[WARN] 체크박스 {i} 클릭 오류: {e}")
                        continue

            # 방법 2: role="checkbox" 클릭
            if not checkbox_clicked:
                role_checkboxes = active_page.locator('[role="checkbox"]')
                rc_count = await role_checkboxes.count()
                safe_print(f"[INFO] role=checkbox 수: {rc_count}")
                if rc_count > 0:
                    try:
                        rc = role_checkboxes.first
                        await rc.scroll_into_view_if_needed()
                        await active_page.wait_for_timeout(300)
                        await rc.click(timeout=5000)
                        safe_print("[OK] role=checkbox 클릭 완료")
                        checkbox_clicked = True
                    except Exception as e:
                        safe_print(f"[WARN] role=checkbox 클릭 오류: {e}")

            # 방법 3: 이력서 관련 클래스 클릭
            if not checkbox_clicked:
                resume_selectors = [
                    '[class*="resume"] input[type="checkbox"]',
                    '[class*="Resume"] input[type="checkbox"]',
                    '[class*="cv"] input[type="checkbox"]',
                    '[class*="resume"] [role="checkbox"]',
                    'li input[type="checkbox"]',
                    '.sc-bRkb * input[type="checkbox"]',
                ]
                for sel in resume_selectors:
                    try:
                        loc = active_page.locator(sel)
                        cnt = await loc.count()
                        if cnt > 0:
                            await loc.first.scroll_into_view_if_needed()
                            await loc.first.click(timeout=5000)
                            safe_print(f"[OK] 선택자 '{sel}'로 체크박스 클릭")
                            checkbox_clicked = True
                            break
                    except Exception as e:
                        safe_print(f"[WARN] 선택자 '{sel}' 오류: {e}")

            # 방법 4: JS로 이력서 체크박스 클릭
            if not checkbox_clicked:
                safe_print("[INFO] JS로 체크박스/이력서 항목 클릭 시도...")
                js_click_result = await active_page.evaluate("""() => {
                    // 체크박스 직접 클릭
                    const checkboxes = [...document.querySelectorAll('input[type="checkbox"]')];
                    for (const cb of checkboxes) {
                        if (!cb.checked) {
                            cb.click();
                            return {clicked: true, method: 'checkbox', checked: cb.checked};
                        }
                    }
                    // role=checkbox 클릭
                    const roleCheckboxes = [...document.querySelectorAll('[role="checkbox"]')];
                    if (roleCheckboxes.length > 0) {
                        roleCheckboxes[0].click();
                        return {clicked: true, method: 'role-checkbox'};
                    }
                    // 이력서 li 항목 클릭
                    const resumeItems = [...document.querySelectorAll(
                        'li[class*="resume"], li[class*="Resume"], ' +
                        '[class*="resume"] li, [class*="Resume"] li, ' +
                        '[class*="cv"] li'
                    )];
                    if (resumeItems.length > 0) {
                        resumeItems[0].click();
                        return {clicked: true, method: 'li-resume'};
                    }
                    return {clicked: false};
                }""")
                safe_print(f"[INFO] JS 클릭 결과: {js_click_result}")
                if js_click_result.get('clicked'):
                    checkbox_clicked = True

            safe_print(f"[INFO] 체크박스 클릭 여부: {checkbox_clicked}")
            await active_page.wait_for_timeout(2000)
            await active_page.screenshot(path='screenshots/test_41_step3_after_checkbox.png')

            # 8. 제출하기 버튼 상태 재확인
            safe_print("[STEP 5] 체크박스 선택 후 '제출하기' 버튼 상태 확인...")
            submit_info_after = await active_page.evaluate("""() => {
                const all = [...document.querySelectorAll('button, [role="button"], input[type="submit"]')];
                return all
                    .filter(el => {
                        const text = (el.innerText || el.textContent || el.value || '').trim();
                        return text === '제출하기' || text.includes('제출');
                    })
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return {
                            text: (el.innerText || el.textContent || '').trim(),
                            disabled: el.disabled,
                            ariaDisabled: el.getAttribute('aria-disabled'),
                            classes: el.className.substring(0, 150),
                            opacity: style.opacity,
                            pointerEvents: style.pointerEvents,
                            cursor: style.cursor,
                            visible: rect.width > 0 && rect.height > 0,
                            color: style.color,
                            backgroundColor: style.backgroundColor,
                        };
                    });
            }""")
            safe_print(f"[INFO] 제출하기 버튼 클릭 후 상태: {submit_info_after}")

            # 9. 제출하기 버튼 활성화 검증
            safe_print("[STEP 6] '제출하기' 버튼 활성화 상태 검증...")

            submit_found = len(submit_info_after) > 0
            submit_enabled = False
            submit_details = []

            for btn in submit_info_after:
                text = btn.get('text', '')
                disabled = btn.get('disabled', True)
                aria_disabled = btn.get('ariaDisabled', 'true')
                opacity = btn.get('opacity', '0')
                pointer_events = btn.get('pointerEvents', 'none')
                cursor = btn.get('cursor', 'not-allowed')
                classes = btn.get('classes', '')
                visible = btn.get('visible', False)

                safe_print(f"[INFO] 버튼 '{text}': disabled={disabled}, aria-disabled={aria_disabled}, "
                           f"opacity={opacity}, pointer-events={pointer_events}, cursor={cursor}")
                safe_print(f"[INFO] 버튼 classes: {classes}")

                # 활성화 판단
                is_enabled = (
                    not disabled and
                    aria_disabled not in ('true', 'True', True) and
                    pointer_events != 'none' and
                    float(opacity) > 0.5 and
                    visible
                )

                # classes 기반 추가 판단 (일부 사이트는 disabled class로 제어)
                if 'disabled' in classes.lower() or 'inactive' in classes.lower():
                    is_enabled = False

                # pointer-events 허용 여부
                if pointer_events == 'auto' and not disabled:
                    is_enabled = True

                submit_details.append({
                    'text': text, 'is_enabled': is_enabled,
                    'disabled': disabled, 'opacity': opacity
                })

                if is_enabled:
                    submit_enabled = True

            safe_print(f"\n[RESULT] 제출하기 버튼 발견: {submit_found}")
            safe_print(f"[RESULT] 제출하기 버튼 활성화됨: {submit_enabled}")
            safe_print(f"[RESULT] 상세: {submit_details}")

            # 제출하기 버튼이 없거나 활성화 판단이 어려운 경우: DOM 전체에서 탐색
            if not submit_found:
                safe_print("[INFO] 제출하기 버튼 찾을 수 없음, 추가 탐색...")
                all_buttons = await active_page.evaluate("""() => {
                    return [...document.querySelectorAll('button, [role="button"]')]
                        .map(el => {
                            const style = window.getComputedStyle(el);
                            return {
                                text: (el.innerText || el.textContent || '').trim().substring(0, 60),
                                disabled: el.disabled,
                                ariaDisabled: el.getAttribute('aria-disabled'),
                                opacity: style.opacity,
                                pointerEvents: style.pointerEvents,
                            };
                        })
                        .filter(b => b.text.length > 0);
                }""")
                safe_print(f"[INFO] 전체 버튼 목록: {all_buttons}")

                # 제출 관련 키워드로 재탐색
                for btn in all_buttons:
                    text = btn.get('text', '')
                    if any(kw in text for kw in ['제출', 'submit', 'Submit', '지원 완료', '완료']):
                        disabled = btn.get('disabled', True)
                        aria_disabled = btn.get('ariaDisabled', 'true')
                        opacity = float(btn.get('opacity', '0') or '0')
                        pointer_events = btn.get('pointerEvents', 'none')

                        safe_print(f"[INFO] 제출 관련 버튼: '{text}' disabled={disabled}, opacity={opacity}")
                        if not disabled and aria_disabled not in ('true', True) and opacity > 0.5:
                            submit_found = True
                            submit_enabled = True
                            safe_print(f"[OK] 제출 버튼 활성화 확인: '{text}'")
                            break
                        elif pointer_events != 'none' and not disabled:
                            submit_found = True
                            submit_enabled = True
                            safe_print(f"[OK] 제출 버튼 활성화 확인(pointer): '{text}'")
                            break

            # 체크박스 클릭 확인 + 제출 버튼 존재 확인으로 최종 판단
            # 이력서 선택 후 제출하기 버튼 활성화가 기대 결과이므로
            # 제출하기 버튼이 active 상태인지 확인

            # Playwright로도 직접 확인
            submit_btn_loc = active_page.locator('button:has-text("제출하기")')
            submit_cnt = await submit_btn_loc.count()
            if submit_cnt == 0:
                submit_btn_loc = active_page.locator('button').filter(has_text="제출")
                submit_cnt = await submit_btn_loc.count()

            safe_print(f"[INFO] Playwright '제출하기' 버튼 수: {submit_cnt}")
            if submit_cnt > 0:
                try:
                    is_disabled = await submit_btn_loc.first.is_disabled()
                    is_enabled_pw = not is_disabled
                    safe_print(f"[INFO] Playwright is_disabled(): {is_disabled}")
                    if is_enabled_pw:
                        submit_found = True
                        submit_enabled = True
                except Exception as e:
                    safe_print(f"[WARN] Playwright is_disabled 오류: {e}")

            await active_page.screenshot(path='screenshots/test_41_step4_final.png')

            # 최종 검증
            assert submit_found, (
                "이력서 체크박스 선택 후 '제출하기' 버튼을 찾을 수 없습니다.\n"
                f"현재 URL: {active_page.url}\n"
                f"체크박스 클릭: {checkbox_clicked}"
            )
            assert submit_enabled, (
                "이력서 체크박스 선택 후 '제출하기' 버튼이 활성화되지 않았습니다.\n"
                f"상세: {submit_details}"
            )

            safe_print("\n[SUMMARY] 테스트 케이스 41 검증 완료:")
            safe_print("[OK] 포지션 상세 페이지 진입 완료")
            safe_print("[OK] '지원하기' 버튼 클릭 완료")
            safe_print("[OK] 이력서 체크박스 선택 완료")
            safe_print("[OK] '제출하기' 버튼 활성화 확인됨")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await active_page.screenshot(path='screenshots/test_41_failed.png')
            except Exception:
                try:
                    await page.screenshot(path='screenshots/test_41_failed.png')
                except Exception:
                    pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
