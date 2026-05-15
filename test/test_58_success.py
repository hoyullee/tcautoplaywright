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

            # ── Step 2: 이력서 편집 페이지 진입 ──
            cv_edit_url = await page.evaluate("""() => {
                const allLinks = document.querySelectorAll('a');
                for (const a of allLinks) {
                    const href = a.href || '';
                    if (/\/cv\/[A-Za-z0-9+=/]{6,}/.test(href) &&
                        !href.includes('/cv/list') &&
                        !href.includes('/cv/intro') &&
                        !href.includes('/cv/faq') &&
                        !href.includes('/cv/matchup') &&
                        !href.includes('/cv/coach')) {
                        return href;
                    }
                }
                return null;
            }""")

            if not cv_edit_url:
                safe_print("[INFO] 새 이력서 작성 버튼 클릭...")
                for kw in ['새 이력서 작성', '새 이력서', '이력서 작성']:
                    try:
                        btn = page.get_by_text(kw, exact=False).first
                        if await btn.count() > 0 and await btn.is_visible():
                            await btn.click(timeout=8000)
                            await page.wait_for_load_state('domcontentloaded')
                            await page.wait_for_timeout(3000)
                            safe_print(f"[OK] '{kw}' 클릭 성공, URL: {page.url}")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")
            else:
                safe_print(f"[INFO] 이력서 편집 URL 발견: {cv_edit_url}")
                await page.goto(cv_edit_url, timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            safe_print(f"[INFO] 이력서 편집 페이지 URL: {page.url}")

            # ── Step 3: 스킬 섹션 찾기 및 스크롤 ──
            safe_print("[INFO] 스킬 섹션 찾기 및 스크롤...")

            # 스킬 섹션 헤더를 찾아서 스크롤
            skill_header_found = await page.evaluate("""() => {
                const allEls = [...document.querySelectorAll('span, h2, h3, h4, label, div, p')];
                for (const el of allEls) {
                    const children = el.children.length;
                    if (children > 5) continue;
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text === '스킬' || text === 'Skills') {
                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                        return true;
                    }
                }
                return false;
            }""")
            safe_print(f"[INFO] 스킬 헤더 스크롤: {skill_header_found}")
            await page.wait_for_timeout(1500)

            # ── Step 4: 스킬 섹션 전체 DOM 구조 파악 ──
            safe_print("[INFO] 스킬 섹션 전체 DOM 구조 파악...")
            skill_dom = await page.evaluate("""() => {
                const result = {
                    skillHeaderY: -1,
                    allVisibleElements: [],
                    skillSectionHTML: '',
                };

                // 스킬 헤더 위치 파악
                const allEls = [...document.querySelectorAll('*')];
                let skillHeaderEl = null;
                for (const el of allEls) {
                    const children = el.children.length;
                    if (children > 5) continue;
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text === '스킬' || text === 'Skills') {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.skillHeaderY = Math.round(rect.top);
                            skillHeaderEl = el;
                            break;
                        }
                    }
                }

                // 스킬 섹션 HTML (부모 컨테이너)
                if (skillHeaderEl) {
                    let parent = skillHeaderEl;
                    for (let i = 0; i < 5; i++) {
                        if (parent.parentElement) parent = parent.parentElement;
                        const rect = parent.getBoundingClientRect();
                        if (rect.height > 100) {
                            result.skillSectionHTML = parent.innerHTML.substring(0, 3000);
                            break;
                        }
                    }
                }

                // 뷰포트 내 모든 visible 요소 탐색 (Y: skillHeaderY-50 ~ skillHeaderY+400)
                const skillY = result.skillHeaderY;
                if (skillY > 0) {
                    for (const el of allEls) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) continue;
                        if (rect.top < skillY - 50 || rect.top > skillY + 400) continue;

                        const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                        if (text.length > 200) continue;

                        const isClickable = el.tagName === 'INPUT' ||
                            el.tagName === 'BUTTON' ||
                            el.tagName === 'A' ||
                            el.getAttribute('role') === 'button' ||
                            el.getAttribute('contenteditable') === 'true' ||
                            (el.style && el.style.cursor === 'pointer') ||
                            window.getComputedStyle(el).cursor === 'pointer';

                        const clsStr = typeof el.className === 'string' ? el.className : (el.className.baseVal || '');
                        result.allVisibleElements.push({
                            tag: el.tagName,
                            text: text.substring(0, 80),
                            id: (el.id || '').substring(0, 50),
                            cls: clsStr.substring(0, 100),
                            placeholder: (el.placeholder || '').substring(0, 60),
                            contenteditable: el.getAttribute('contenteditable') || '',
                            role: el.getAttribute('role') || '',
                            cursor: window.getComputedStyle(el).cursor,
                            isClickable,
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            cx: Math.round(rect.left + rect.width / 2),
                            cy: Math.round(rect.top + rect.height / 2),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                        });
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 스킬 헤더 Y: {skill_dom['skillHeaderY']}")
            safe_print(f"[INFO] 스킬 섹션 근처 요소 ({len(skill_dom['allVisibleElements'])}개):")
            for el in skill_dom['allVisibleElements'][:30]:
                safe_print(f"  - [{el['tag']:8s}] ({el['x']},{el['y']}) cursor='{el['cursor']}' ce='{el['contenteditable']}' role='{el['role']}' placeholder='{el['placeholder']}' text='{el['text'][:50]}'")

            safe_print(f"[INFO] 스킬 섹션 HTML(일부): {skill_dom['skillSectionHTML'][:1000]}")

            # ── Step 5: 스킬 입력 클릭 ──
            safe_print("[INFO] 스킬 입력 영역 클릭 시도...")
            skill_typed = False
            skill_keyword = 'playwright'

            # 방법 1: contenteditable 요소
            ce_els = [el for el in skill_dom['allVisibleElements'] if el['contenteditable'] in ['true', '']]
            safe_print(f"[INFO] contenteditable 요소: {len([el for el in skill_dom['allVisibleElements'] if el['contenteditable'] == 'true'])}개")

            # 방법 2: placeholder 포함 input
            ph_els = [el for el in skill_dom['allVisibleElements']
                      if any(k in el['placeholder'].lower() for k in ['스킬', '기술', 'skill', 'tool', '검색', '입력'])
                      and '포지션' not in el['placeholder']]
            safe_print(f"[INFO] 스킬 관련 placeholder input: {len(ph_els)}개")
            for el in ph_els:
                safe_print(f"  - [{el['tag']}] placeholder='{el['placeholder']}'")

            # 방법 3: cursor=pointer인 요소
            clickable_els = [el for el in skill_dom['allVisibleElements']
                             if el['cursor'] in ['pointer', 'text']
                             and el['tag'] not in ['A']
                             and '포지션' not in el['text']
                             and '포지션' not in el['placeholder']]
            safe_print(f"[INFO] cursor 기반 클릭 가능 요소: {len(clickable_els)}개")
            for el in clickable_els[:10]:
                safe_print(f"  - [{el['tag']}] ({el['x']},{el['y']}) cursor='{el['cursor']}' text='{el['text'][:40]}'")

            # 스킬 입력 시도: placeholder 있는 input 먼저
            for el in ph_els:
                try:
                    inp = page.locator('input').filter(has_not_text='포지션').nth(0)
                    # 더 정확하게: placeholder 값으로 찾기
                    if el['placeholder']:
                        inp = page.locator(f'input[placeholder="{el["placeholder"]}"]').first
                    if await inp.count() > 0 and await inp.is_visible():
                        await inp.click(timeout=5000)
                        await page.wait_for_timeout(500)
                        await inp.type(skill_keyword, delay=80)
                        skill_typed = True
                        safe_print(f"[OK] placeholder input에 '{skill_keyword}' 입력: '{el['placeholder']}'")
                        break
                except Exception as e:
                    safe_print(f"[WARN] placeholder input 클릭 실패: {e}")

            # 방법: 스킬 헤더 아래 영역 클릭 시도
            if not skill_typed:
                safe_print("[INFO] 스킬 헤더 Y 기반 클릭 시도...")
                skill_y = skill_dom['skillHeaderY']
                if skill_y > 0:
                    # 스킬 헤더 아래 여러 Y 위치 클릭 시도
                    for dy in [40, 60, 80, 100, 120, 150]:
                        try:
                            target_y = skill_y + dy
                            await page.mouse.click(700, target_y)
                            await page.wait_for_timeout(800)

                            active = await page.evaluate("""() => {
                                const a = document.activeElement;
                                if (!a) return { found: false };
                                return {
                                    found: true,
                                    tag: a.tagName,
                                    placeholder: a.placeholder || '',
                                    contenteditable: a.getAttribute('contenteditable') || '',
                                    id: a.id || '',
                                };
                            }""")

                            if active['found'] and active['tag'] in ['INPUT', 'TEXTAREA'] and '포지션' not in active['placeholder']:
                                await page.keyboard.type(skill_keyword, delay=80)
                                skill_typed = True
                                safe_print(f"[OK] y={target_y} 클릭 후 {active['tag']} 활성화, '{skill_keyword}' 입력")
                                break
                        except Exception as e:
                            safe_print(f"[WARN] y={skill_y + dy} 클릭 실패: {e}")

            # 방법: 커서=text인 DIV 클릭 (커스텀 입력 컴포넌트)
            if not skill_typed:
                safe_print("[INFO] cursor=text 또는 cursor=pointer DIV 클릭 시도...")
                for el in clickable_els:
                    if el['tag'] == 'DIV' and el['cursor'] in ['text', 'pointer']:
                        if '포지션' in el['text'] or el['h'] < 20 or el['w'] < 50:
                            continue
                        try:
                            await page.mouse.click(el['cx'], el['cy'])
                            await page.wait_for_timeout(1000)

                            active = await page.evaluate("""() => {
                                const a = document.activeElement;
                                if (!a) return { found: false };
                                return {
                                    found: true,
                                    tag: a.tagName,
                                    placeholder: a.placeholder || '',
                                    contenteditable: a.getAttribute('contenteditable') || '',
                                };
                            }""")

                            if active['found'] and '포지션' not in active['placeholder']:
                                if active['tag'] in ['INPUT', 'TEXTAREA'] or active['contenteditable'] == 'true':
                                    await page.keyboard.type(skill_keyword, delay=80)
                                    skill_typed = True
                                    safe_print(f"[OK] DIV 클릭 후 {active['tag']} 활성화 ({el['cx']},{el['cy']}), '{skill_keyword}' 입력")
                                    break
                        except Exception as e:
                            safe_print(f"[WARN] DIV 클릭 실패: {e}")

            # 방법: 페이지 전체 스크롤 후 재탐색
            if not skill_typed:
                safe_print("[INFO] 페이지 전체 스크롤 후 스킬 섹션 재탐색...")
                await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(1500)

                # 스킬 섹션 헤더 다시 찾기
                skill_header_scroll = await page.evaluate("""() => {
                    const allEls = [...document.querySelectorAll('*')];
                    for (const el of allEls) {
                        const children = el.children.length;
                        if (children > 5) continue;
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === '스킬' || text === 'Skills') {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.top > 0 && rect.top < window.innerHeight) {
                                el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                return { found: true, x: Math.round(rect.left), y: Math.round(rect.top) };
                            }
                        }
                    }
                    return { found: false };
                }""")
                safe_print(f"[INFO] 스킬 헤더 재스크롤: {skill_header_scroll}")
                await page.wait_for_timeout(1500)

                # 스킬 섹션 내 '내가 가진 직무 스킬을 입력해 주세요.' 텍스트 찾기
                skill_input_area = await page.evaluate("""() => {
                    const result = { found: false, elements: [] };
                    const allEls = [...document.querySelectorAll('*')];
                    for (const el of allEls) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text.includes('내가 가진') || text.includes('직무 스킬') ||
                            text.includes('스킬을 추가') || text.includes('스킬 추가') ||
                            text.includes('스킬을 입력') || (text.includes('스킬') && text.length < 30)) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.top < window.innerHeight + 100) {
                                result.found = true;
                                result.elements.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 80),
                                    cls: (el.className || '').substring(0, 100),
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    cx: Math.round(rect.left + rect.width / 2),
                                    cy: Math.round(rect.top + rect.height / 2),
                                    w: Math.round(rect.width),
                                    h: Math.round(rect.height),
                                });
                            }
                        }
                    }
                    return result;
                }""")

                safe_print(f"[INFO] 스킬 입력 영역 요소 ({len(skill_input_area['elements'])}개):")
                for el in skill_input_area['elements'][:20]:
                    safe_print(f"  - [{el['tag']:8s}] ({el['x']},{el['y']}) cls='{el['cls'][:60]}' text='{el['text'][:50]}'")

                for el in skill_input_area['elements']:
                    if el['tag'] in ['DIV', 'SPAN', 'P', 'BUTTON', 'INPUT']:
                        try:
                            await page.mouse.click(el['cx'], el['cy'])
                            await page.wait_for_timeout(1500)

                            active = await page.evaluate("""() => {
                                const a = document.activeElement;
                                if (!a) return { found: false };
                                return {
                                    found: true,
                                    tag: a.tagName,
                                    placeholder: a.placeholder || '',
                                    ce: a.getAttribute('contenteditable') || '',
                                };
                            }""")

                            if active['found'] and '포지션' not in active['placeholder']:
                                if active['tag'] in ['INPUT', 'TEXTAREA'] or active['ce'] == 'true':
                                    await page.keyboard.type(skill_keyword, delay=80)
                                    skill_typed = True
                                    safe_print(f"[OK] 스킬 영역 클릭 후 입력 성공 ({el['cx']},{el['cy']})")
                                    break
                        except Exception as e:
                            safe_print(f"[WARN] 클릭 실패: {e}")
                    if skill_typed:
                        break

            # 방법: LNB 스킬 링크 클릭 후 재시도
            if not skill_typed:
                safe_print("[INFO] LNB에서 '스킬' 링크 클릭 시도...")
                lnb_skill_clicked = False
                for kw in ['스킬', 'Skills', '기술스택', '기술 스택']:
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
                                    safe_print(f"[OK] LNB '{kw}' 클릭 성공 (index={i})")
                                    lnb_skill_clicked = True
                                    break
                        if lnb_skill_clicked:
                            break
                    except Exception as e:
                        safe_print(f"[WARN] LNB '{kw}' 클릭 실패: {e}")

                if lnb_skill_clicked:
                    await page.wait_for_timeout(2000)

                    # 스킬 섹션 내 입력 필드 재탐색
                    all_visible = await page.evaluate("""() => {
                        const result = [];
                        const inputs = [...document.querySelectorAll('input:not([type="hidden"])')];
                        inputs.forEach((inp, i) => {
                            const rect = inp.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.top < window.innerHeight) {
                                const ph = (inp.placeholder || '').toLowerCase();
                                if (!ph.includes('포지션')) {
                                    result.push({
                                        i, placeholder: inp.placeholder || '',
                                        x: Math.round(rect.left), y: Math.round(rect.top),
                                    });
                                }
                            }
                        });
                        return result;
                    }""")
                    safe_print(f"[INFO] LNB 클릭 후 visible input ({len(all_visible)}개):")
                    for vi in all_visible[:10]:
                        safe_print(f"  - [idx={vi['i']}] ({vi['x']},{vi['y']}) placeholder='{vi['placeholder']}'")

                    for vi in all_visible:
                        ph = vi['placeholder'].lower()
                        if any(k in ph for k in ['스킬', '기술', 'skill', 'tool', '검색', '입력']):
                            try:
                                inp = page.locator('input').nth(vi['i'])
                                await inp.click(timeout=5000)
                                await inp.type(skill_keyword, delay=80)
                                skill_typed = True
                                safe_print(f"[OK] input[{vi['i']}]에 '{skill_keyword}' 입력")
                                break
                            except Exception as e:
                                safe_print(f"[WARN] input 입력 실패: {e}")

            safe_print(f"[INFO] 스킬 입력 여부: {skill_typed}")

            # ── Step 6: 자동완성에서 'Playwright' 선택 ──
            if skill_typed:
                safe_print("[INFO] 자동완성 목록 대기 중 (3초)...")
                await page.wait_for_timeout(3000)

                page_text = await page.evaluate("() => (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 3000)")
                safe_print(f"[INFO] 입력 후 페이지 텍스트(일부): {page_text[:800]}")

                playwright_selected = False

                # 자동완성 목록에서 Playwright 탐색
                autocomplete_items = await page.evaluate("""() => {
                    const result = [];
                    const seen = new Set();
                    const selectors = [
                        '[role="option"]',
                        '[role="listbox"] *',
                        '[role="listbox"]',
                        'ul[class*="list"] li',
                        'ul[class*="suggest"] li',
                        '[class*="dropdown"] li',
                        '[class*="dropdown"] [class*="item"]',
                        '[class*="option"]',
                        '[class*="autocomplete"] li',
                        '[class*="autocomplete"] div',
                        '[class*="suggest"] div',
                        '[class*="result"] li',
                        '[class*="result"] div',
                        'li',
                    ];

                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width <= 0 || rect.height <= 0) continue;
                            const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                            if (!text || text.length > 100) continue;
                            if (text.toLowerCase().includes('playwright') && !seen.has(text)) {
                                seen.add(text);
                                result.push({
                                    sel: sel.substring(0, 60),
                                    text: text.substring(0, 60),
                                    tag: el.tagName,
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                    cx: Math.round(rect.left + rect.width / 2),
                                    cy: Math.round(rect.top + rect.height / 2),
                                });
                            }
                        }
                    }

                    // 전체 visible 요소에서 Playwright 포함 텍스트 탐색
                    const allEls = [...document.querySelectorAll('*')];
                    for (const el of allEls) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) continue;
                        const directText = Array.from(el.childNodes)
                            .filter(n => n.nodeType === 3)
                            .map(n => n.textContent.trim())
                            .join('').trim();
                        if (directText.toLowerCase().includes('playwright') && !seen.has(directText) && directText.length < 100) {
                            seen.add(directText);
                            result.push({
                                sel: 'DIRECT_TEXT',
                                text: directText.substring(0, 60),
                                tag: el.tagName,
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                                cx: Math.round(rect.left + rect.width / 2),
                                cy: Math.round(rect.top + rect.height / 2),
                            });
                        }
                    }
                    return result;
                }""")

                safe_print(f"[INFO] Playwright 자동완성 항목 ({len(autocomplete_items)}개):")
                for item in autocomplete_items[:10]:
                    safe_print(f"  - [{item['tag']}] ({item['x']},{item['y']}) text='{item['text']}' sel='{item['sel']}'")

                # Playwright 항목 클릭
                for item in autocomplete_items:
                    if 'playwright' in item['text'].lower():
                        try:
                            await page.mouse.click(item['cx'], item['cy'])
                            await page.wait_for_timeout(2000)
                            playwright_selected = True
                            safe_print(f"[OK] Playwright 항목 클릭 성공 ({item['cx']},{item['cy']}) '{item['text']}'")
                            break
                        except Exception as e:
                            safe_print(f"[WARN] 마우스 클릭 실패: {e}")

                if not playwright_selected:
                    try:
                        option = page.get_by_role('option', name='Playwright')
                        if await option.count() > 0 and await option.first.is_visible():
                            await option.first.click(timeout=5000)
                            playwright_selected = True
                            safe_print("[OK] get_by_role option 'Playwright' 클릭 성공")
                            await page.wait_for_timeout(2000)
                    except Exception as e:
                        safe_print(f"[WARN] get_by_role option 실패: {e}")

                if not playwright_selected:
                    for kw in ['Playwright', 'playwright']:
                        try:
                            items = page.get_by_text(kw, exact=True)
                            cnt = await items.count()
                            if cnt > 0:
                                for i in range(min(cnt, 5)):
                                    item_el = items.nth(i)
                                    if await item_el.is_visible():
                                        await item_el.click(timeout=5000)
                                        playwright_selected = True
                                        safe_print(f"[OK] get_by_text '{kw}' 클릭 성공 (index={i})")
                                        await page.wait_for_timeout(2000)
                                        break
                            if playwright_selected:
                                break
                        except Exception as e:
                            safe_print(f"[WARN] get_by_text 실패: {e}")

                safe_print(f"[INFO] Playwright 선택 여부: {playwright_selected}")
            else:
                playwright_selected = False

            # ── Step 7: 검증 ──
            safe_print("[INFO] 스킬 등록 결과 확인...")
            await page.wait_for_timeout(2000)

            verify_result = await page.evaluate("""() => {
                const bodyText = (document.body.innerText || '').replace(/\\s+/g, ' ');
                const hasPlaywright = bodyText.toLowerCase().includes('playwright');

                const skillTags = [];
                const seen = new Set();
                const tagSelectors = [
                    '[class*="Skill"] *', '[class*="skill"] *',
                    '[class*="tag"]', '[class*="chip"]',
                    '[class*="badge"]', '[class*="keyword"]',
                    'li', 'span',
                ];
                for (const sel of tagSelectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) continue;
                        const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
                        if (!text || text.length > 60 || seen.has(text)) continue;
                        if (text.toLowerCase().includes('playwright')) {
                            seen.add(text);
                            skillTags.push({ sel, text: text.substring(0, 60) });
                        }
                    }
                }

                return { hasPlaywright, skillTags };
            }""")

            safe_print(f"[INFO] 페이지에서 Playwright 발견: {verify_result['hasPlaywright']}")
            safe_print(f"[INFO] Playwright 스킬 태그 ({len(verify_result['skillTags'])}개):")
            for tag in verify_result['skillTags'][:5]:
                safe_print(f"  - '{tag['text']}' sel='{tag['sel']}'")

            assert skill_typed, "스킬 입력 필드를 찾지 못했습니다."
            assert verify_result['hasPlaywright'], "'playwright' 스킬이 페이지에서 확인되지 않습니다."

            safe_print("[OK] 'playwright' 스킬 등록 확인 완료!")

            await page.screenshot(path='screenshots/test_58_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_58_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
