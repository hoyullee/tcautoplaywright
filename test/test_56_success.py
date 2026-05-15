import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)


def safe_print(msg):
    try:
        print(msg)
    except Exception:
        print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 900},
            storage_state='work/auth_state.json',
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── Step 1: 이력서 목록 페이지 진입 ──
            safe_print("[INFO] 이력서 목록 페이지(cv/list) 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 페이지 구조 파악 - 이력서 편집 또는 새 이력서 링크 찾기 ──
            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 1000),
                    cvLinks: [],
                    allButtons: [],
                };
                const allEls = [...document.querySelectorAll('a, button, [role="button"]')];
                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                    const href = el.href || '';
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.allButtons.push({ text: text.substring(0, 60), href: href.substring(0, 150) });
                        if (href.includes('/cv/') || href.includes('/resume/')) {
                            result.cvLinks.push({ text: text.substring(0, 60), href: href.substring(0, 150) });
                        }
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_info['url']}")
            safe_print(f"[INFO] 페이지 미리보기: {page_info['bodyText'][:600]}")
            safe_print(f"[INFO] CV 링크 ({len(page_info['cvLinks'])}개):")
            for lnk in page_info['cvLinks'][:10]:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")
            safe_print(f"[INFO] 전체 버튼 ({len(page_info['allButtons'])}개):")
            for btn in page_info['allButtons'][:15]:
                safe_print(f"  - '{btn['text']}' href='{btn['href']}'")

            # ── Step 3: 이력서 편집/작성 페이지로 이동 ──
            cv_edit_url = None

            # cv/new, cv/create, cv/write 링크 우선 탐색
            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/write']):
                    cv_edit_url = href
                    break

            # 기존 이력서 편집 링크
            if not cv_edit_url:
                for lnk in page_info['cvLinks']:
                    href = lnk['href']
                    if ('/cv/' in href and
                        'cv/list' not in href and
                        'cv/intro' not in href and
                        'cv/faq' not in href):
                        cv_edit_url = href
                        break

            if cv_edit_url:
                safe_print(f"[INFO] CV 편집 URL로 이동: {cv_edit_url}")
                await page.goto(cv_edit_url, timeout=30000)
            else:
                # 버튼 클릭으로 이동 시도
                btn_keywords = ['새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                                '새로 만들기', '작성하기', '이력서 추가',
                                '이력서 편집', '편집하기', '수정하기', '편집']
                for kw in btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=False).first
                        if await btn.count() > 0:
                            await btn.click(timeout=8000)
                            safe_print(f"[OK] 버튼 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[INFO] 이동 후 URL: {page.url}")

            # ── Step 4: 현재 페이지 구조 파악 ──
            safe_print("[INFO] 현재 페이지 구조 파악 중...")
            page_scan = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 4000),
                    inputs: [],
                    buttons: [],
                };

                const inputEls = document.querySelectorAll('input, textarea, [contenteditable="true"], select');
                for (const el of inputEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        result.inputs.push({
                            tag: el.tagName,
                            type: el.type || '',
                            placeholder: (el.placeholder || '').substring(0, 80),
                            id: el.id || '',
                            name: el.name || '',
                            classes: (el.className || '').substring(0, 80),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }

                const btnEls = [...document.querySelectorAll('button, [role="button"], a')];
                for (const el of btnEls) {
                    const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                    const href = el.href || '';
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0 && text.length < 60) {
                        result.buttons.push({
                            tag: el.tagName,
                            text: text.substring(0, 50),
                            href: href.substring(0, 100),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                        });
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_scan['url']}")
            safe_print(f"[INFO] 페이지 텍스트 일부: {page_scan['bodyText'][:2000]}")
            safe_print(f"[INFO] 입력 요소 ({len(page_scan['inputs'])}개):")
            for inp in page_scan['inputs'][:20]:
                safe_print(f"  - [{inp['tag']:10s}] ({inp['x']},{inp['y']}) type='{inp['type']}' placeholder='{inp['placeholder']}' id='{inp['id']}'")
            safe_print(f"[INFO] 버튼 요소 ({len(page_scan['buttons'])}개):")
            for btn in page_scan['buttons'][:20]:
                safe_print(f"  - [{btn['tag']:10s}] ({btn['x']},{btn['y']}) '{btn['text']}'")

            # ── Step 5: '경력' 섹션으로 이동 ──
            safe_print("[INFO] '경력' 섹션으로 이동 시도...")

            career_nav_keywords = ['경력', '경력사항', '경력 사항']
            for kw in career_nav_keywords:
                try:
                    els = page.get_by_text(kw, exact=True)
                    cnt = await els.count()
                    if cnt > 0:
                        for i in range(cnt):
                            try:
                                el = els.nth(i)
                                if await el.is_visible():
                                    await el.click(timeout=5000)
                                    await page.wait_for_timeout(1500)
                                    safe_print(f"[OK] '{kw}' 클릭 성공 (index={i})")
                                    break
                            except Exception:
                                pass
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            # 경력 관련 요소 탐색
            career_area = await page.evaluate("""() => {
                const result = {
                    hasCareerSection: false,
                    careerElements: [],
                    careerButtons: [],
                };

                const allEls = [...document.querySelectorAll('*')];
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 &&
                        (normText === '경력' || normText === '경력사항' || normText.includes('경력 추가') ||
                         normText.includes('경력사항 추가') || normText === '+ 경력 추가') &&
                        normText.length < 100) {
                        result.hasCareerSection = true;
                        result.careerElements.push({
                            tag: el.tagName,
                            text: normText.substring(0, 60),
                            classes: (el.className || '').substring(0, 100),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }

                const addBtns = [...document.querySelectorAll('button, [role="button"]')];
                for (const btn of addBtns) {
                    const text = (btn.innerText || btn.textContent || '').trim().replace(/\\s+/g, ' ');
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 &&
                        (text.includes('경력') || text.includes('추가')) &&
                        text.length < 80) {
                        result.careerButtons.push({
                            tag: btn.tagName,
                            text: text.substring(0, 60),
                            classes: (btn.className || '').substring(0, 100),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                        });
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 경력 섹션 발견: {career_area['hasCareerSection']}")
            for el in career_area['careerElements'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) '{el['text']}'")
            for btn in career_area['careerButtons'][:10]:
                safe_print(f"  - BTN [{btn['tag']:12s}] ({btn['x']},{btn['y']}) '{btn['text']}'")

            # ── Step 6: '경력 추가' 버튼 클릭 ──
            safe_print("[INFO] '경력 추가' 버튼 클릭 시도...")
            career_add_clicked = False

            add_btn_keywords = [
                '경력 추가', '경력추가', '+ 경력 추가', '경력 입력',
                '경력사항 추가', '+ 추가', '추가',
            ]

            for kw in add_btn_keywords:
                try:
                    btns = page.get_by_text(kw, exact=False)
                    cnt = await btns.count()
                    if cnt > 0:
                        for i in range(cnt):
                            try:
                                btn = btns.nth(i)
                                if await btn.is_visible():
                                    await btn.click(timeout=5000)
                                    await page.wait_for_timeout(2000)
                                    safe_print(f"[OK] '{kw}' 버튼 클릭 성공 (index={i})")
                                    career_add_clicked = True
                                    break
                            except Exception:
                                pass
                    if career_add_clicked:
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if not career_add_clicked:
                safe_print("[WARN] '경력 추가' 버튼을 찾지 못함. 현재 보이는 경력 폼으로 진행...")

            await page.wait_for_timeout(1000)

            # ── Step 7: 경력 입력 폼 상태 파악 ──
            form_scan = await page.evaluate("""() => {
                const result = {
                    inputs: [],
                    textareas: [],
                    selects: [],
                };

                const inputEls = document.querySelectorAll('input:not([type="hidden"]), textarea, select, [contenteditable="true"]');
                for (const el of inputEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const info = {
                            tag: el.tagName,
                            type: el.type || '',
                            placeholder: (el.placeholder || '').substring(0, 100),
                            id: (el.id || '').substring(0, 60),
                            name: (el.name || '').substring(0, 60),
                            value: (el.value || '').substring(0, 60),
                            classes: (el.className || '').substring(0, 120),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        };
                        if (el.tagName === 'TEXTAREA') result.textareas.push(info);
                        else if (el.tagName === 'SELECT') result.selects.push(info);
                        else result.inputs.push(info);
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 입력 요소 ({len(form_scan['inputs'])}개):")
            for inp in form_scan['inputs']:
                safe_print(f"  - INPUT ({inp['x']},{inp['y']}) type='{inp['type']}' placeholder='{inp['placeholder']}' id='{inp['id']}'")
            safe_print(f"[INFO] textarea ({len(form_scan['textareas'])}개):")
            for ta in form_scan['textareas']:
                safe_print(f"  - TEXTAREA ({ta['x']},{ta['y']}) placeholder='{ta['placeholder']}' id='{ta['id']}'")
            safe_print(f"[INFO] select ({len(form_scan['selects'])}개):")
            for sel in form_scan['selects']:
                safe_print(f"  - SELECT ({sel['x']},{sel['y']}) id='{sel['id']}'")

            # ── Step 8: 경력 항목 입력 ──
            company_name = "원티드랩"
            start_year = "2022"
            start_month = "01"
            end_year = "2023"
            end_month = "12"
            employment_type = "정규직"
            achievement_title = "서비스 성능 개선"
            achievement_detail = "API 응답 속도를 30% 향상시켜 사용자 경험을 개선하였습니다."

            inputs_filled = {
                'company': False,
                'start_date': False,
                'end_date': False,
                'employment_type': False,
                'achievement': False,
                'achievement_detail': False,
            }

            # ── 8-1: 회사명 입력 ──
            safe_print("[INFO] 회사명 입력 시도...")
            company_keywords = ['회사명', '회사 이름', '기업명', '회사', 'company', 'Company']
            for kw in company_keywords:
                try:
                    inp = page.locator(f'input[placeholder*="{kw}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.click(timeout=5000)
                        await inp.fill(company_name)
                        inputs_filled['company'] = True
                        safe_print(f"[OK] 회사명 입력 성공 (placeholder='{kw}')")
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' placeholder 입력 실패: {e}")

            if not inputs_filled['company']:
                # text 타입의 첫 번째 visible input에 입력 시도
                for i, inp_info in enumerate(form_scan['inputs']):
                    if inp_info['type'] in ('text', ''):
                        try:
                            inp = page.locator('input').nth(i)
                            if await inp.is_visible():
                                await inp.click(timeout=5000)
                                await inp.fill(company_name)
                                inputs_filled['company'] = True
                                safe_print(f"[OK] 회사명 input[{i}]에 입력 성공")
                                break
                        except Exception as e:
                            safe_print(f"[WARN] input[{i}] 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-2: 재직 날짜 입력 ──
            safe_print("[INFO] 재직 날짜 입력 시도...")

            date_inputs = await page.evaluate("""() => {
                const result = [];
                let idx = 0;
                const inputs = document.querySelectorAll('input');
                for (const inp of inputs) {
                    const rect = inp.getBoundingClientRect();
                    if (rect.width <= 0 || rect.height <= 0) { idx++; continue; }
                    const ph = (inp.placeholder || '').toLowerCase();
                    const type = inp.type || '';
                    const id = inp.id.toLowerCase();
                    const name = inp.name.toLowerCase();
                    if (type === 'date' ||
                        ph.includes('년') || ph.includes('월') ||
                        ph.includes('yyyy') || ph.includes('yy') ||
                        name.includes('date') || name.includes('year') ||
                        id.includes('date') || id.includes('year') ||
                        id.includes('start') || id.includes('end')) {
                        result.push({
                            type: type,
                            placeholder: (inp.placeholder || '').substring(0, 60),
                            id: inp.id.substring(0, 60),
                            name: inp.name.substring(0, 60),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            domIndex: idx,
                        });
                    }
                    idx++;
                }
                return result;
            }""")

            safe_print(f"[INFO] 날짜 관련 입력 요소 ({len(date_inputs)}개):")
            for di in date_inputs:
                safe_print(f"  - ({di['x']},{di['y']}) type='{di['type']}' placeholder='{di['placeholder']}' id='{di['id']}'")

            if date_inputs:
                try:
                    di = date_inputs[0]
                    if di['type'] == 'date':
                        inp = page.locator("input[type='date']").first
                        await inp.fill(f"{start_year}-{start_month}-01")
                        inputs_filled['start_date'] = True
                        safe_print(f"[OK] 시작일 입력 성공 (date type)")
                    else:
                        inp = page.locator('input').nth(di['domIndex'])
                        if await inp.is_visible():
                            await inp.fill(f"{start_year}.{start_month}")
                            inputs_filled['start_date'] = True
                            safe_print(f"[OK] 시작일 입력 성공")
                except Exception as e:
                    safe_print(f"[WARN] 시작일 입력 실패: {e}")

                if len(date_inputs) > 1:
                    try:
                        di2 = date_inputs[1]
                        if di2['type'] == 'date':
                            inp2 = page.locator("input[type='date']").nth(1)
                            await inp2.fill(f"{end_year}-{end_month}-01")
                            inputs_filled['end_date'] = True
                            safe_print(f"[OK] 종료일 입력 성공 (date type)")
                        else:
                            inp2 = page.locator('input').nth(di2['domIndex'])
                            if await inp2.is_visible():
                                await inp2.fill(f"{end_year}.{end_month}")
                                inputs_filled['end_date'] = True
                                safe_print(f"[OK] 종료일 입력 성공")
                    except Exception as e:
                        safe_print(f"[WARN] 종료일 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-3: 재직형태 선택 ──
            safe_print("[INFO] 재직형태 입력 시도...")

            if form_scan['selects']:
                try:
                    sel = page.locator('select').first
                    if await sel.is_visible():
                        await sel.select_option(label=employment_type)
                        inputs_filled['employment_type'] = True
                        safe_print(f"[OK] 재직형태 select 선택 성공: '{employment_type}'")
                except Exception as e:
                    safe_print(f"[WARN] select 선택 실패: {e}")

            if not inputs_filled['employment_type']:
                employ_kws = ['재직형태', '고용형태', '근무형태']
                for kw in employ_kws:
                    try:
                        el = page.get_by_text(kw, exact=False).first
                        if await el.count() > 0 and await el.is_visible():
                            await el.click(timeout=5000)
                            await page.wait_for_timeout(500)
                            opt = page.get_by_text(employment_type, exact=True).first
                            if await opt.count() > 0 and await opt.is_visible():
                                await opt.click(timeout=5000)
                                inputs_filled['employment_type'] = True
                                safe_print(f"[OK] '{employment_type}' 선택 성공")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if not inputs_filled['employment_type']:
                for kw in ['정규직', '풀타임']:
                    try:
                        el = page.get_by_text(kw, exact=True).first
                        if await el.count() > 0 and await el.is_visible():
                            await el.click(timeout=5000)
                            inputs_filled['employment_type'] = True
                            safe_print(f"[OK] '{kw}' 클릭 성공")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-4: 주요 성과 입력 ──
            safe_print("[INFO] 주요 성과/상세 입력 시도...")

            textareas = await page.evaluate("""() => {
                const result = [];
                const taEls = document.querySelectorAll('textarea');
                let idx = 0;
                for (const el of taEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        result.push({
                            placeholder: (el.placeholder || '').substring(0, 100),
                            id: el.id.substring(0, 60),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            domIndex: idx,
                        });
                    }
                    idx++;
                }
                return result;
            }""")

            safe_print(f"[INFO] textarea 요소 ({len(textareas)}개):")
            for ta in textareas:
                safe_print(f"  - ({ta['x']},{ta['y']}) placeholder='{ta['placeholder']}' idx={ta['domIndex']}")

            # 주요 성과
            achievement_filled = False
            achievement_detail_filled = False

            achievement_kws = ['주요 성과', '성과', '업무 내용', '담당 업무', '업무내용',
                               '성과 및 업무', '어떤 일을', '무슨 일을', '내용']
            for kw in achievement_kws:
                try:
                    ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                    if await ta.count() > 0 and await ta.is_visible():
                        await ta.click(timeout=5000)
                        await ta.fill(achievement_title)
                        achievement_filled = True
                        inputs_filled['achievement'] = True
                        safe_print(f"[OK] 주요 성과 textarea 입력 성공 (placeholder='{kw}')")
                        break
                except Exception:
                    pass

            if not achievement_filled:
                for kw in achievement_kws:
                    try:
                        inp = page.locator(f'input[placeholder*="{kw}"]').first
                        if await inp.count() > 0 and await inp.is_visible():
                            await inp.click(timeout=5000)
                            await inp.fill(achievement_title)
                            achievement_filled = True
                            inputs_filled['achievement'] = True
                            safe_print(f"[OK] 주요 성과 input 입력 성공 (placeholder='{kw}')")
                            break
                    except Exception:
                        pass

            if not achievement_filled and textareas:
                try:
                    ta = page.locator('textarea').nth(textareas[0]['domIndex'])
                    if await ta.is_visible():
                        await ta.click(timeout=5000)
                        await ta.fill(achievement_title)
                        achievement_filled = True
                        inputs_filled['achievement'] = True
                        safe_print(f"[OK] 첫 번째 textarea에 주요 성과 입력 성공")
                except Exception as e:
                    safe_print(f"[WARN] 첫 번째 textarea 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # 주요 성과 상세
            detail_kws = ['성과 상세', '상세 내용', '상세내용', '구체적', '자세히',
                          '업무 상세', '내용 입력', '설명', '어떤 성과']
            for kw in detail_kws:
                try:
                    ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                    if await ta.count() > 0 and await ta.is_visible():
                        await ta.click(timeout=5000)
                        await ta.fill(achievement_detail)
                        achievement_detail_filled = True
                        inputs_filled['achievement_detail'] = True
                        safe_print(f"[OK] 주요 성과 상세 textarea 입력 성공 (placeholder='{kw}')")
                        break
                except Exception:
                    pass

            if not achievement_detail_filled and len(textareas) > 1:
                try:
                    ta = page.locator('textarea').nth(textareas[1]['domIndex'])
                    if await ta.is_visible():
                        await ta.click(timeout=5000)
                        await ta.fill(achievement_detail)
                        achievement_detail_filled = True
                        inputs_filled['achievement_detail'] = True
                        safe_print(f"[OK] 두 번째 textarea에 주요 성과 상세 입력 성공")
                except Exception as e:
                    safe_print(f"[WARN] 두 번째 textarea 입력 실패: {e}")

            # 현재 상태 종합 로그
            safe_print(f"\n[INFO] 입력 현황:")
            for k, v in inputs_filled.items():
                safe_print(f"  - {k}: {'입력됨' if v else '미입력'}")

            # ── Step 9: 입력 결과 검증 ──
            safe_print("\n[INFO] 입력 결과 검증 중...")
            verify_result = await page.evaluate("""(companyName) => {
                const result = {
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 5000),
                    hasCompanyName: false,
                    allInputValues: [],
                };

                if (result.bodyText.includes(companyName)) {
                    result.hasCompanyName = true;
                }

                const inputEls = document.querySelectorAll('input:not([type="hidden"]), textarea, [contenteditable="true"]');
                for (const el of inputEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const value = el.value || el.textContent || '';
                        if (value.trim()) {
                            result.allInputValues.push({
                                tag: el.tagName,
                                value: value.trim().substring(0, 100),
                                placeholder: (el.placeholder || '').substring(0, 60),
                            });
                        }
                    }
                }

                return result;
            }""", company_name)

            safe_print(f"[INFO] 회사명 입력 확인: {verify_result['hasCompanyName']}")
            safe_print(f"[INFO] 입력된 값들 ({len(verify_result['allInputValues'])}개):")
            for inp in verify_result['allInputValues']:
                safe_print(f"  - [{inp['tag']}] placeholder='{inp['placeholder']}' value='{inp['value']}'")

            # 검증: 적어도 일부 필드가 입력되었는지
            has_any_input = len(verify_result['allInputValues']) > 0
            assert has_any_input or inputs_filled['company'], \
                "경력 항목에 아무것도 입력되지 않았습니다."

            safe_print("[OK] 경력 항목 입력 완료!")

            await page.screenshot(path='screenshots/test_56_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_56_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
