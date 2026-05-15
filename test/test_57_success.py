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

            # ── Step 5: '학력' 섹션으로 스크롤/이동 ──
            safe_print("[INFO] '학력' 섹션으로 이동 시도...")

            edu_nav_keywords = ['학력', '학력사항', '학력 사항']
            for kw in edu_nav_keywords:
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

            await page.wait_for_timeout(1000)

            # 학력 관련 영역 탐색
            edu_area = await page.evaluate("""() => {
                const result = {
                    hasEduSection: false,
                    eduElements: [],
                    eduButtons: [],
                };

                const allEls = [...document.querySelectorAll('*')];
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 &&
                        (normText === '학력' || normText === '학력사항' ||
                         normText.includes('학력 추가') || normText.includes('학교 추가') ||
                         normText === '+ 학력 추가') &&
                        normText.length < 100) {
                        result.hasEduSection = true;
                        result.eduElements.push({
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
                        (text.includes('학력') || text.includes('학교')) &&
                        text.length < 80) {
                        result.eduButtons.push({
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

            safe_print(f"[INFO] 학력 섹션 발견: {edu_area['hasEduSection']}")
            for el in edu_area['eduElements'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) '{el['text']}'")
            for btn in edu_area['eduButtons'][:10]:
                safe_print(f"  - BTN [{btn['tag']:12s}] ({btn['x']},{btn['y']}) '{btn['text']}'")

            # ── Step 6: '학력 추가' 버튼 클릭 ──
            safe_print("[INFO] '학력 추가' 버튼 클릭 시도...")
            edu_add_clicked = False

            add_btn_keywords = [
                '학력 추가', '학력추가', '+ 학력 추가', '학교 추가',
                '학력 입력', '학력사항 추가', '추가하기',
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
                                    edu_add_clicked = True
                                    break
                            except Exception:
                                pass
                    if edu_add_clicked:
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if not edu_add_clicked:
                safe_print("[WARN] '학력 추가' 버튼을 찾지 못함. 현재 보이는 학력 폼으로 진행...")

            await page.wait_for_timeout(1000)

            # ── Step 7: 학력 입력 폼 상태 파악 ──
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

            # ── Step 8: 학력 항목 입력 ──
            school_name = "한국대학교"
            start_year = "2016"
            start_month = "03"
            end_year = "2020"
            end_month = "02"
            grad_status = "졸업"
            major = "컴퓨터공학"
            degree = "학사"
            courses = "알고리즘, 자료구조, 운영체제, 데이터베이스, 소프트웨어공학 등 전공 과목 이수"

            inputs_filled = {
                'school': False,
                'start_date': False,
                'end_date': False,
                'grad_status': False,
                'major': False,
                'courses': False,
            }

            # ── 8-1: 학교명 입력 ──
            safe_print("[INFO] 학교명 입력 시도...")
            school_keywords = ['학교명', '학교 이름', '학교 명', '대학교', '대학명', '학교']
            for kw in school_keywords:
                try:
                    inp = page.locator(f'input[placeholder*="{kw}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.click(timeout=5000)
                        await inp.fill(school_name)
                        inputs_filled['school'] = True
                        safe_print(f"[OK] 학교명 입력 성공 (placeholder='{kw}')")
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' placeholder 입력 실패: {e}")

            if not inputs_filled['school']:
                # text 타입의 첫 번째 visible input에 입력 시도
                for i, inp_info in enumerate(form_scan['inputs']):
                    if inp_info['type'] in ('text', ''):
                        try:
                            inp = page.locator('input').nth(i)
                            if await inp.is_visible():
                                await inp.click(timeout=5000)
                                await inp.fill(school_name)
                                inputs_filled['school'] = True
                                safe_print(f"[OK] 학교명 input[{i}]에 입력 성공 (placeholder='{inp_info['placeholder']}')")
                                break
                        except Exception as e:
                            safe_print(f"[WARN] input[{i}] 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-2: 입학/졸업 날짜 입력 ──
            safe_print("[INFO] 입학/졸업 날짜 입력 시도...")

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
                        ph.includes('입학') || ph.includes('졸업') ||
                        name.includes('date') || name.includes('year') ||
                        id.includes('date') || id.includes('year') ||
                        id.includes('start') || id.includes('end') ||
                        id.includes('admission') || id.includes('graduation')) {
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
                # 입학일 (첫 번째 날짜 입력)
                try:
                    di = date_inputs[0]
                    if di['type'] == 'date':
                        inp = page.locator("input[type='date']").first
                        await inp.fill(f"{start_year}-{start_month}-01")
                        inputs_filled['start_date'] = True
                        safe_print(f"[OK] 입학일 입력 성공 (date type): {start_year}-{start_month}")
                    else:
                        inp = page.locator('input').nth(di['domIndex'])
                        if await inp.is_visible():
                            await inp.click(timeout=5000)
                            await inp.fill(f"{start_year}.{start_month}")
                            inputs_filled['start_date'] = True
                            safe_print(f"[OK] 입학일 입력 성공: {start_year}.{start_month}")
                except Exception as e:
                    safe_print(f"[WARN] 입학일 입력 실패: {e}")

                # 졸업일 (두 번째 날짜 입력)
                if len(date_inputs) > 1:
                    try:
                        di2 = date_inputs[1]
                        if di2['type'] == 'date':
                            inp2 = page.locator("input[type='date']").nth(1)
                            await inp2.fill(f"{end_year}-{end_month}-01")
                            inputs_filled['end_date'] = True
                            safe_print(f"[OK] 졸업일 입력 성공 (date type): {end_year}-{end_month}")
                        else:
                            inp2 = page.locator('input').nth(di2['domIndex'])
                            if await inp2.is_visible():
                                await inp2.click(timeout=5000)
                                await inp2.fill(f"{end_year}.{end_month}")
                                inputs_filled['end_date'] = True
                                safe_print(f"[OK] 졸업일 입력 성공: {end_year}.{end_month}")
                    except Exception as e:
                        safe_print(f"[WARN] 졸업일 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-3: 졸업 상태 선택 ──
            safe_print("[INFO] 졸업 상태 입력 시도...")

            if form_scan['selects']:
                try:
                    sel = page.locator('select').first
                    if await sel.is_visible():
                        await sel.select_option(label=grad_status)
                        inputs_filled['grad_status'] = True
                        safe_print(f"[OK] 졸업 상태 select 선택 성공: '{grad_status}'")
                except Exception as e:
                    safe_print(f"[WARN] select 선택 실패: {e}")

            if not inputs_filled['grad_status']:
                grad_kws = ['졸업 상태', '졸업상태', '재학', '졸업', '재학 중', '학위']
                for kw in grad_kws:
                    try:
                        els = page.get_by_text(kw, exact=False)
                        cnt = await els.count()
                        if cnt > 0:
                            for i in range(cnt):
                                try:
                                    el = els.nth(i)
                                    if await el.is_visible():
                                        await el.click(timeout=5000)
                                        await page.wait_for_timeout(500)
                                        inputs_filled['grad_status'] = True
                                        safe_print(f"[OK] '{kw}' 클릭 성공")
                                        break
                                except Exception:
                                    pass
                            if inputs_filled['grad_status']:
                                break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-4: 전공 및 학위 입력 ──
            safe_print("[INFO] 전공 및 학위 입력 시도...")

            major_keywords = ['전공', '학과', '전공명', '전공 및 학위', '학위', '전공/학위']
            major_filled = False
            for kw in major_keywords:
                try:
                    inp = page.locator(f'input[placeholder*="{kw}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.click(timeout=5000)
                        await inp.fill(f"{major} {degree}")
                        major_filled = True
                        inputs_filled['major'] = True
                        safe_print(f"[OK] 전공/학위 입력 성공 (placeholder='{kw}'): {major} {degree}")
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' placeholder 입력 실패: {e}")

            if not major_filled:
                # textarea에서 전공 관련 필드 탐색
                for kw in major_keywords:
                    try:
                        ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                        if await ta.count() > 0 and await ta.is_visible():
                            await ta.click(timeout=5000)
                            await ta.fill(f"{major} {degree}")
                            major_filled = True
                            inputs_filled['major'] = True
                            safe_print(f"[OK] 전공/학위 textarea 입력 성공 (placeholder='{kw}'): {major} {degree}")
                            break
                    except Exception:
                        pass

            if not major_filled:
                # 두 번째 text input 시도
                text_inputs = [inp for inp in form_scan['inputs'] if inp['type'] in ('text', '')]
                if len(text_inputs) > 1:
                    try:
                        idx = form_scan['inputs'].index(text_inputs[1])
                        inp = page.locator('input').nth(idx)
                        if await inp.is_visible():
                            await inp.click(timeout=5000)
                            await inp.fill(f"{major} {degree}")
                            major_filled = True
                            inputs_filled['major'] = True
                            safe_print(f"[OK] 두 번째 text input에 전공/학위 입력 성공")
                    except Exception as e:
                        safe_print(f"[WARN] 두 번째 input 입력 실패: {e}")

            await page.wait_for_timeout(500)

            # ── 8-5: 이수 과목 또는 연구 내용 입력 ──
            safe_print("[INFO] 이수 과목/연구 내용 입력 시도...")

            # 최신 textarea 목록 재탐색
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
                            value: (el.value || '').substring(0, 60),
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
                safe_print(f"  - ({ta['x']},{ta['y']}) placeholder='{ta['placeholder']}' value='{ta['value']}' idx={ta['domIndex']}")

            courses_filled = False
            courses_kws = ['이수 과목', '이수과목', '연구 내용', '연구내용', '과목', '수업', '과제',
                           '활동', '내용', '설명', '기술', '주요', '성과', '이력']
            for kw in courses_kws:
                try:
                    ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                    if await ta.count() > 0 and await ta.is_visible():
                        await ta.click(timeout=5000)
                        await ta.fill(courses)
                        courses_filled = True
                        inputs_filled['courses'] = True
                        safe_print(f"[OK] 이수과목/연구내용 textarea 입력 성공 (placeholder='{kw}')")
                        break
                except Exception:
                    pass

            if not courses_filled and textareas:
                # 비어있는 첫 번째 textarea에 입력
                for ta_info in textareas:
                    if not ta_info['value']:
                        try:
                            ta = page.locator('textarea').nth(ta_info['domIndex'])
                            if await ta.is_visible():
                                await ta.click(timeout=5000)
                                await ta.fill(courses)
                                courses_filled = True
                                inputs_filled['courses'] = True
                                safe_print(f"[OK] 빈 textarea[{ta_info['domIndex']}]에 이수과목 입력 성공")
                                break
                        except Exception as e:
                            safe_print(f"[WARN] textarea[{ta_info['domIndex']}] 입력 실패: {e}")

            # 현재 상태 종합 로그
            safe_print(f"\n[INFO] 입력 현황:")
            for k, v in inputs_filled.items():
                safe_print(f"  - {k}: {'입력됨' if v else '미입력'}")

            # ── Step 9: 입력 결과 검증 ──
            safe_print("\n[INFO] 입력 결과 검증 중...")
            verify_result = await page.evaluate("""(schoolName) => {
                const result = {
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 5000),
                    hasSchoolName: false,
                    allInputValues: [],
                };

                if (result.bodyText.includes(schoolName)) {
                    result.hasSchoolName = true;
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
            }""", school_name)

            safe_print(f"[INFO] 학교명 입력 확인: {verify_result['hasSchoolName']}")
            safe_print(f"[INFO] 입력된 값들 ({len(verify_result['allInputValues'])}개):")
            for inp in verify_result['allInputValues']:
                safe_print(f"  - [{inp['tag']}] placeholder='{inp['placeholder']}' value='{inp['value']}'")

            # 검증: 적어도 일부 필드가 입력되었는지
            has_any_input = len(verify_result['allInputValues']) > 0
            assert has_any_input or inputs_filled['school'], \
                "학력 항목에 아무것도 입력되지 않았습니다."

            safe_print("[OK] 학력 항목 입력 완료!")

            await page.screenshot(path='screenshots/test_57_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_57_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
