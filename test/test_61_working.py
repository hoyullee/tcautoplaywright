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


def is_main_card(text):
    """메인 카드 판별: '작성 중' 앞에 이름 등 선행 텍스트가 있는 경우"""
    if '작성 중' in text:
        text_before = text.split('작성 중')[0].strip()
        return len(text_before) > 2
    return False


def count_draft_non_basic_main_cards(items_texts):
    """비기본, 작성 중, 메인 카드 수 계산"""
    count = 0
    for text in items_texts:
        if '기본 이력서' in text:
            continue
        if ('작성 중' in text or '작성중' in text) and is_main_card(text):
            count += 1
    return count


@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel='chrome')
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
            safe_print("[INFO] 이력서 목록 페이지 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] URL: {page.url}")

            # ── Step 2: '작성 중' 비기본 이력서 카드 탐색 ──
            safe_print("[INFO] '작성 중' 비기본 이력서 메인 카드 탐색...")
            resume_items = page.locator('[class*="ResumeItem_ResumeItem"]')
            total = await resume_items.count()
            safe_print(f"[INFO] 전체 ResumeItem 수: {total}")

            before_texts = []
            target_idx = -1

            for i in range(total):
                item = resume_items.nth(i)
                try:
                    text = await item.inner_text(timeout=3000)
                    text_stripped = text.strip().replace('\n', ' ')
                    is_basic = '기본 이력서' in text
                    is_draft = '작성 중' in text or '작성중' in text
                    is_mc = is_main_card(text)
                    safe_print(f"  [{i}] isBasic={is_basic} isDraft={is_draft} isMain={is_mc} '{text_stripped[:60]}'")
                    before_texts.append(text)
                    if is_draft and not is_basic and is_mc and target_idx == -1:
                        target_idx = i
                except Exception as e:
                    safe_print(f"  [{i}] 오류: {e}")
                    before_texts.append('')

            before_count = count_draft_non_basic_main_cards(before_texts)
            safe_print(f"[INFO] 비기본 '작성 중' 메인 카드: {before_count}개, 대상 인덱스: {target_idx}")

            # ── Step 3: 없으면 새 이력서 생성 ──
            if target_idx == -1:
                safe_print("[INFO] '작성 중' 비기본 이력서 없음. 새 이력서 생성...")
                for kw in ['새 이력서 작성', '새 이력서']:
                    btn = page.get_by_text(kw, exact=False)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        await page.go_back()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        if 'cv/list' not in page.url:
                            await page.goto('https://www.wanted.co.kr/cv/list', timeout=30000)
                            await page.wait_for_load_state('domcontentloaded')
                            await page.wait_for_timeout(3000)
                        break

                total = await resume_items.count()
                before_texts = []
                target_idx = -1
                for i in range(total):
                    item = resume_items.nth(i)
                    try:
                        text = await item.inner_text(timeout=3000)
                        before_texts.append(text)
                        is_basic = '기본 이력서' in text
                        is_draft = '작성 중' in text or '작성중' in text
                        is_mc = is_main_card(text)
                        if is_draft and not is_basic and is_mc and target_idx == -1:
                            target_idx = i
                    except Exception:
                        before_texts.append('')

                before_count = count_draft_non_basic_main_cards(before_texts)

            assert target_idx >= 0, "작성 중 비기본 메인 이력서 카드를 찾을 수 없습니다"
            safe_print(f"[OK] 대상 메인 카드 인덱스: {target_idx}, before_count={before_count}")

            target = resume_items.nth(target_idx)

            # ── Step 4: 카드 hover 후 더보기 버튼 클릭 ──
            await target.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            card_box = await target.bounding_box()
            safe_print(f"[INFO] 카드 bounding box: {card_box}")

            await target.hover()
            await page.wait_for_timeout(800)
            safe_print("[OK] 카드 호버 완료")

            more_btn_clicked = False

            # 전략 1: target 내부 aria-label 더보기 버튼
            for aria_kw in ['더보기', 'more', '더 보기', '옵션']:
                try:
                    mb = target.locator(f'button[aria-label*="{aria_kw}"]')
                    cnt = await mb.count()
                    safe_print(f"[INFO] 카드 내 aria-label*='{aria_kw}': {cnt}개")
                    if cnt > 0:
                        await mb.first.click(force=True)
                        more_btn_clicked = True
                        safe_print(f"[OK] aria-label '{aria_kw}' 더보기 클릭!")
                        break
                except Exception as e:
                    safe_print(f"[WARN] {e}")

            # 전략 2: 카드 영역 내 좌표 기반 버튼 탐색
            if not more_btn_clicked and card_box:
                card_right = card_box['x'] + card_box['width']
                card_bottom = card_box['y'] + card_box['height']
                card_top = card_box['y']
                card_left = card_box['x']

                all_btns_info = await page.evaluate("""() => {
                    const result = [];
                    for (const btn of document.querySelectorAll('button, [role="button"]')) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width < 1 || rect.height < 1) continue;
                        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                        const cls = (btn.className || '').toLowerCase();
                        const txt = (btn.innerText || '').trim();
                        result.push({
                            aria, cls, txt: txt.substring(0, 60),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                    return result;
                }""")

                for btn in all_btns_info:
                    bx, by, bw, bh = btn['x'], btn['y'], btn['w'], btn['h']
                    in_card = (card_left <= bx <= card_right and card_top <= by <= card_bottom)
                    aria = btn['aria'].lower()
                    cls = btn['cls'].lower()
                    is_more = ('더보기' in aria or 'more' in aria or 'option' in aria or
                               'kebab' in cls or 'more' in cls or 'dot' in cls)
                    is_small = bw <= 60 and bh <= 60
                    is_right_bottom = (bx + bw > card_left + card_box['width'] * 0.5 and
                                       by + bh > card_top + card_box['height'] * 0.4)
                    if in_card and (is_more or (is_right_bottom and is_small and not btn['txt'])):
                        safe_print(f"[INFO] 좌표 더보기 클릭: ({bx},{by}) aria='{btn['aria']}'")
                        await page.mouse.click(bx + bw // 2, by + bh // 2)
                        more_btn_clicked = True
                        safe_print("[OK] 더보기 버튼 좌표 클릭!")
                        break

            # 전략 3: JS hover 후 버튼 탐색
            if not more_btn_clicked and card_box:
                safe_print("[INFO] JS 이벤트로 hover 후 버튼 재탐색...")
                cx = card_box['x'] + card_box['width'] - 20
                cy = card_box['y'] + card_box['height'] - 20
                await page.mouse.move(cx, cy)
                await page.wait_for_timeout(800)

                btns_after_hover = await page.evaluate(f"""() => {{
                    const result = [];
                    for (const btn of document.querySelectorAll('button, [role="button"]')) {{
                        const rect = btn.getBoundingClientRect();
                        if (rect.width < 1 || rect.height < 1) continue;
                        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                        const cls = (btn.className || '').toLowerCase();
                        const txt = (btn.innerText || '').trim();
                        const inCard = (rect.x >= {card_box['x'] - 5} && rect.x <= {card_box['x'] + card_box['width'] + 5} &&
                                        rect.y >= {card_box['y'] - 5} && rect.y <= {card_box['y'] + card_box['height'] + 5});
                        if (inCard) {{
                            result.push({{
                                aria, cls: cls.substring(0, 120),
                                txt: txt.substring(0, 60),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            }});
                        }}
                    }}
                    return result;
                }}""")

                for b in btns_after_hover:
                    aria = b['aria']
                    cls = b['cls']
                    is_more = ('더보기' in aria or 'more' in aria or 'option' in aria or
                               'kebab' in cls or 'more' in cls)
                    is_small_no_txt = b['w'] <= 50 and not b['txt']
                    if is_more or is_small_no_txt:
                        safe_print(f"[INFO] hover 후 더보기 버튼 클릭: ({b['x']},{b['y']}) aria='{b['aria']}'")
                        await page.mouse.click(b['x'] + b['w'] // 2, b['y'] + b['h'] // 2)
                        more_btn_clicked = True
                        safe_print("[OK] hover 후 더보기 버튼 클릭!")
                        break

            assert more_btn_clicked, "더보기(3점) 버튼을 클릭할 수 없습니다"
            safe_print("[OK] '더보기' 클릭 성공!")
            await page.wait_for_timeout(1000)

            # ── Step 5: 드롭다운 메뉴에서 '이력서 삭제' 선택 ──
            safe_print("[INFO] '이력서 삭제' 메뉴 항목 탐색...")

            # 드롭다운 메뉴 디버깅
            dropdown_info = await page.evaluate("""() => {
                const result = [];
                const selectors = [
                    'li', 'button', '[role="menuitem"]', '[role="option"]',
                    '[class*="menu"]', '[class*="Menu"]', '[class*="dropdown"]',
                    '[class*="Dropdown"]', '[class*="popup"]', '[class*="Popup"]',
                ];
                const seen = new Set();
                for (const sel of selectors) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = (el.innerText || '').trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width < 1 || rect.height < 1) continue;
                        const key = `${Math.round(rect.x)},${Math.round(rect.y)},${text.substring(0,20)}`;
                        if (seen.has(key)) continue;
                        seen.add(key);
                        result.push({
                            tag: el.tagName, text: text.substring(0, 60),
                            cls: (el.className || '').substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
                return result;
            }""")
            safe_print(f"[INFO] 드롭다운 후 메뉴 항목 ({len(dropdown_info)}개):")
            for d in dropdown_info[:30]:
                safe_print(f"  - [{d['tag']:8s}] ({d['x']},{d['y']}) '{d['text'][:50]}' cls='{d['cls'][:50]}'")

            delete_clicked = False

            # 1순위: text-is 정확 매칭
            for selector in [
                'li:text-is("이력서 삭제")',
                'button:text-is("이력서 삭제")',
                '[role="menuitem"]:text-is("이력서 삭제")',
            ]:
                try:
                    loc = page.locator(selector)
                    cnt = await loc.count()
                    safe_print(f"  '{selector}' → {cnt}개")
                    if cnt > 0:
                        await loc.first.click()
                        delete_clicked = True
                        safe_print(f"[OK] '{selector}' 클릭!")
                        break
                except Exception as e:
                    safe_print(f"  '{selector}' 오류: {e}")

            # 2순위: role=button name='이력서 삭제'
            if not delete_clicked:
                try:
                    loc = page.get_by_role('button', name='이력서 삭제')
                    cnt = await loc.count()
                    safe_print(f"  role=button '이력서 삭제' → {cnt}개")
                    if cnt > 0:
                        await loc.first.click()
                        delete_clicked = True
                        safe_print("[OK] role=button '이력서 삭제' 클릭!")
                except Exception as e:
                    safe_print(f"  role=button 오류: {e}")

            # 3순위: get_by_text
            if not delete_clicked:
                try:
                    loc = page.get_by_text('이력서 삭제', exact=True)
                    cnt = await loc.count()
                    safe_print(f"  get_by_text '이력서 삭제' → {cnt}개")
                    if cnt > 0:
                        await loc.first.click()
                        delete_clicked = True
                        safe_print("[OK] get_by_text 클릭!")
                except Exception as e:
                    safe_print(f"  get_by_text 오류: {e}")

            # 4순위: JS click
            if not delete_clicked:
                safe_print("[INFO] JS scrollIntoView + click 시도...")
                result = await page.evaluate("""() => {
                    const allEls = Array.from(document.querySelectorAll('li, button, [role="menuitem"], [role="option"]'));
                    for (const el of allEls) {
                        const t = (el.innerText || '').trim();
                        if (t === '이력서 삭제') {
                            el.scrollIntoView({ behavior: 'instant', block: 'center' });
                            el.click();
                            return `clicked: ${el.tagName} cls='${el.className}'`;
                        }
                    }
                    for (const el of allEls) {
                        const t = (el.innerText || '').trim();
                        if (t.includes('이력서 삭제') && t.length < 20) {
                            el.scrollIntoView({ behavior: 'instant', block: 'center' });
                            el.click();
                            return `clicked_contains: ${el.tagName} text='${t}'`;
                        }
                    }
                    return 'not_found';
                }""")
                safe_print(f"  JS 결과: {result}")
                if result != 'not_found':
                    delete_clicked = True
                    safe_print("[OK] JS click 성공!")

            assert delete_clicked, "'이력서 삭제' 메뉴 항목을 찾아 클릭할 수 없습니다"
            safe_print("[OK] '이력서 삭제' 클릭 성공!")

            # ── Step 6: 삭제 확인 모달 대기 및 처리 ──
            safe_print("[INFO] 삭제 확인 모달 대기 중...")
            await page.wait_for_timeout(500)

            # 모달 등장 대기 (최대 5초)
            modal_appeared = False
            modal_selectors = [
                '[role="dialog"]',
                '[class*="Modal"]',
                '[class*="modal"]',
                '[class*="Dialog"]',
                '[class*="dialog"]',
                '[class*="Confirm"]',
                '[class*="confirm"]',
                '[class*="Alert"]',
                '[class*="alert"]',
            ]

            for sel in modal_selectors:
                try:
                    loc = page.locator(sel)
                    await loc.first.wait_for(state='visible', timeout=3000)
                    cnt = await loc.count()
                    safe_print(f"[OK] 모달 발견: '{sel}' ({cnt}개)")
                    modal_appeared = True
                    break
                except Exception:
                    pass

            if not modal_appeared:
                safe_print("[INFO] 명시적 모달 없음 - 버튼 직접 탐색")

            await page.wait_for_timeout(500)

            # 현재 보이는 버튼 전체 수집 (디버깅)
            visible_btns = await page.evaluate("""() => {
                const result = [];
                for (const el of document.querySelectorAll('button, [role="button"]')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) continue;
                    const text = (el.innerText || '').trim();
                    if (!text) continue;
                    result.push({
                        text: text.substring(0, 60),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                        cls: (el.className || '').substring(0, 80),
                    });
                }
                return result;
            }""")

            safe_print(f"[INFO] 현재 버튼 ({len(visible_btns)}개):")
            for b in visible_btns:
                safe_print(f"  - ({b['x']},{b['y']}) '{b['text'][:40]}' cls='{b['cls'][:50]}'")

            confirm_clicked = False
            confirm_keywords = ['삭제', '확인', '삭제하기', '네', '예', 'OK', '확인하기']
            cancel_keywords = ['취소', '아니오', '아니요', '닫기', '계속', '돌아가기']

            # 방법 1: role=dialog 내부 버튼
            if not confirm_clicked:
                try:
                    dialog = page.get_by_role('dialog')
                    if await dialog.count() > 0:
                        safe_print("[INFO] role=dialog 발견!")
                        for kw in confirm_keywords:
                            d_btn = dialog.get_by_role('button', name=kw)
                            if await d_btn.count() > 0:
                                btn_text = (await d_btn.first.inner_text() or '').strip()
                                if not any(ck in btn_text for ck in cancel_keywords):
                                    await d_btn.first.click()
                                    confirm_clicked = True
                                    safe_print(f"[OK] dialog 내 '{kw}' 클릭!")
                                    break
                            # exact=False 시도
                            d_btn2 = dialog.get_by_role('button', name=kw, exact=False)
                            if await d_btn2.count() > 0:
                                btn_text = (await d_btn2.first.inner_text() or '').strip()
                                if not any(ck in btn_text for ck in cancel_keywords):
                                    await d_btn2.first.click()
                                    confirm_clicked = True
                                    safe_print(f"[OK] dialog 내 '{kw}' (exact=False) 클릭!")
                                    break
                except Exception as e:
                    safe_print(f"[WARN] dialog 탐색 오류: {e}")

            # 방법 2: 전체 페이지 role=button exact match
            if not confirm_clicked:
                for kw in confirm_keywords:
                    try:
                        btn = page.get_by_role('button', name=kw, exact=True)
                        cnt = await btn.count()
                        if cnt > 0:
                            btn_text = (await btn.first.inner_text() or '').strip()
                            if not any(ck in btn_text for ck in cancel_keywords):
                                safe_print(f"[INFO] role=button exact='{kw}' {cnt}개 → 클릭")
                                await btn.first.click()
                                confirm_clicked = True
                                safe_print(f"[OK] 확인 클릭: '{kw}'")
                                break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 탐색 오류: {e}")

            # 방법 3: visible_btns 좌표 기반 클릭 (확인 버튼 패턴)
            if not confirm_clicked:
                for btn_info in visible_btns:
                    text = btn_info['text'].strip()
                    is_confirm = any(text == kw or text.startswith(kw) for kw in confirm_keywords)
                    is_cancel = any(ck in text for ck in cancel_keywords)
                    cls = btn_info['cls'].lower()
                    # 모달 내부 확인 버튼은 보통 짧은 텍스트, 취소 아님
                    if is_confirm and not is_cancel and len(text) <= 15:
                        cx = btn_info['x'] + btn_info['w'] // 2
                        cy = btn_info['y'] + btn_info['h'] // 2
                        safe_print(f"[INFO] 좌표 클릭: '{text}' ({cx},{cy})")
                        await page.mouse.click(cx, cy)
                        confirm_clicked = True
                        safe_print(f"[OK] 확인 클릭 (좌표): '{text}'")
                        break

            # 방법 4: JS로 모달 내부 버튼 탐색
            if not confirm_clicked:
                safe_print("[INFO] JS로 확인 버튼 탐색...")
                result = await page.evaluate("""() => {
                    const confirmTexts = ['삭제', '확인', '삭제하기', '네', '예'];
                    const cancelTexts = ['취소', '아니오', '아니요', '닫기'];
                    const allBtns = Array.from(document.querySelectorAll('button, [role="button"]'));
                    for (const btn of allBtns) {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width < 5 || rect.height < 5) continue;
                        const text = (btn.innerText || '').trim();
                        const isConfirm = confirmTexts.some(kw => text === kw || text.startsWith(kw));
                        const isCancel = cancelTexts.some(kw => text.includes(kw));
                        if (isConfirm && !isCancel && text.length <= 15) {
                            btn.click();
                            return `clicked: '${text}' at (${Math.round(rect.x)}, ${Math.round(rect.y)})`;
                        }
                    }
                    return 'not_found';
                }""")
                safe_print(f"  JS 확인 버튼: {result}")
                if result != 'not_found':
                    confirm_clicked = True
                    safe_print("[OK] JS 확인 버튼 클릭 성공!")

            if confirm_clicked:
                safe_print("[INFO] 확인 클릭 완료, 삭제 처리 대기 중...")
                await page.wait_for_timeout(2000)
            else:
                safe_print("[INFO] 확인 다이얼로그 없음 (삭제가 즉시 처리됐을 수 있음)")
                await page.wait_for_timeout(1500)

            # ── Step 7: '삭제되었습니다.' 토스트 메시지 확인 ──
            safe_print("[INFO] '삭제되었습니다.' 토스트/툴팁 메시지 확인 중...")
            toast_found = False
            toast_text = ''

            for attempt in range(8):
                toast_info = await page.evaluate("""() => {
                    const result = { toasts: [], bodyText: '' };
                    const toastSelectors = [
                        '[class*="toast"]', '[class*="Toast"]',
                        '[class*="snack"]', '[class*="Snack"]',
                        '[class*="alert"]', '[class*="Alert"]',
                        '[class*="notification"]', '[class*="Notification"]',
                        '[class*="tooltip"]', '[class*="Tooltip"]',
                        '[class*="message"]', '[class*="Message"]',
                        '[role="alert"]', '[role="status"]',
                        '[class*="success"]', '[class*="Success"]',
                        '[class*="Toastify"]',
                    ];
                    for (const sel of toastSelectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const text = (el.innerText || el.textContent || '').trim();
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && text.length > 0 && text.length < 200) {
                                result.toasts.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 80),
                                    sel: sel,
                                    x: Math.round(rect.left),
                                    y: Math.round(rect.top),
                                });
                            }
                        }
                    }
                    result.bodyText = (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 2000);
                    return result;
                }""")

                if attempt == 0 or attempt == 3:
                    safe_print(f"[INFO] 시도 {attempt+1} - 토스트 ({len(toast_info['toasts'])}개):")
                    for t in toast_info['toasts'][:5]:
                        safe_print(f"  - [{t['tag']}] ({t['x']},{t['y']}) '{t['text'][:60]}' sel='{t['sel']}'")

                for t in toast_info['toasts']:
                    if '삭제되었습니다' in t['text']:
                        toast_found = True
                        toast_text = t['text']
                        safe_print(f"[OK] 토스트 메시지 확인: '{toast_text}'")
                        break

                if not toast_found and '삭제되었습니다' in toast_info['bodyText']:
                    toast_found = True
                    toast_text = '삭제되었습니다.'
                    safe_print(f"[OK] 페이지 본문에서 '삭제되었습니다.' 확인")

                if toast_found:
                    break

                await page.wait_for_timeout(400)

            if not toast_found:
                safe_print("[WARN] '삭제되었습니다.' 토스트 메시지를 직접 찾지 못함. 카드 수 감소로 검증 진행...")

            # ── Step 8: 카드 수 감소 검증 ──
            safe_print("[INFO] 삭제 결과 검증...")

            # 페이지 리로드하여 최신 상태 확인
            await page.reload()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            total_after = await resume_items.count()
            after_texts = []
            for i in range(total_after):
                item = resume_items.nth(i)
                try:
                    text = await item.inner_text(timeout=3000)
                    after_texts.append(text)
                except Exception:
                    after_texts.append('')

            after_count = count_draft_non_basic_main_cards(after_texts)

            safe_print(f"[INFO] 삭제 전: {before_count}개 → 삭제 후: {after_count}개")
            # 카드 수 감소 또는 토스트 메시지 확인 중 하나는 반드시 성공해야 함
            card_deleted = after_count < before_count
            assert card_deleted or toast_found, (
                f"이력서 삭제 실패! 삭제 전: {before_count}개, 삭제 후: {after_count}개, toast='{toast_text}'"
            )
            if toast_found:
                safe_print(f"[OK] '삭제되었습니다.' 툴팁 확인: '{toast_text}'")
            if card_deleted:
                safe_print(f"[OK] 이력서 카드 수 감소 확인: {before_count} → {after_count}")

            await page.screenshot(path='screenshots/test_61_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_61_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
