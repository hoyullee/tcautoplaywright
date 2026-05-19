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
            safe_print("[INFO] 이력서 목록 페이지 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] URL: {page.url}")
            assert 'cv/list' in page.url, f"로그인 세션 이상 - 리다이렉트: {page.url}"

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
                        before_url = page.url
                        await btn.first.click()
                        await page.wait_for_url(
                            lambda url: url != before_url, timeout=10000
                        )
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        # 뒤로 가기
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

            # ── Step 4: 카드를 뷰포트 상단으로 스크롤 후 hover ──
            # 드롭다운이 뷰포트 내에 들어오도록 카드를 상단으로 스크롤
            safe_print("[INFO] 카드를 뷰포트 상단으로 스크롤...")
            target_handle = await target.element_handle()
            await page.evaluate("""(el) => {
                el.scrollIntoView({ behavior: 'instant', block: 'start' });
            }""", target_handle)
            await page.wait_for_timeout(500)

            # 카드 위에 100px 여유 공간 확보
            card_box = await target.bounding_box()
            if card_box and card_box['y'] < 80:
                await page.evaluate("window.scrollBy(0, -120)")
                await page.wait_for_timeout(300)
                card_box = await target.bounding_box()

            safe_print(f"[INFO] 스크롤 후 카드 bounding box: {card_box}")

            await target.hover()
            await page.wait_for_timeout(800)
            safe_print("[OK] 카드 호버 완료")

            # ── Step 5: 3점(더보기) 버튼 클릭 ──
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

            # 전략 2: 카드 우측 하단 좌표 기반
            if not more_btn_clicked and card_box:
                cx = card_box['x'] + card_box['width'] - 20
                cy = card_box['y'] + card_box['height'] - 20
                await page.mouse.move(cx, cy)
                await page.wait_for_timeout(500)
                # 버튼 탐색
                btns = await page.evaluate(f"""() => {{
                    const result = [];
                    for (const btn of document.querySelectorAll('button, [role="button"]')) {{
                        const rect = btn.getBoundingClientRect();
                        if (rect.width < 1 || rect.height < 1) continue;
                        const inCard = (
                            rect.x >= {card_box['x'] - 5} && rect.x <= {card_box['x'] + card_box['width'] + 5} &&
                            rect.y >= {card_box['y'] - 5} && rect.y <= {card_box['y'] + card_box['height'] + 5}
                        );
                        if (inCard) {{
                            const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                            const cls = (btn.className || '').toLowerCase();
                            result.push({{
                                aria, cls: cls.substring(0, 80), txt: (btn.innerText||'').trim().substring(0,30),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            }});
                        }}
                    }}
                    return result;
                }}""")
                for b in btns:
                    is_more = ('더보기' in b['aria'] or 'more' in b['aria'] or
                               'kebab' in b['cls'] or 'more' in b['cls'] or 'menu' in b['cls'])
                    is_small = b['w'] <= 60 and b['h'] <= 60 and not b['txt']
                    if is_more or is_small:
                        safe_print(f"[INFO] 좌표 기반 더보기 클릭: ({b['x']},{b['y']}) aria='{b['aria']}'")
                        await page.mouse.click(b['x'] + b['w'] // 2, b['y'] + b['h'] // 2)
                        more_btn_clicked = True
                        safe_print("[OK] 좌표 기반 더보기 클릭!")
                        break

            assert more_btn_clicked, "더보기(3점) 버튼을 클릭할 수 없습니다"
            safe_print("[OK] '더보기' 클릭 성공!")
            await page.wait_for_timeout(1000)

            # ── Step 6: 드롭다운 메뉴에서 '이력서 삭제' 선택 ──
            safe_print("[INFO] '이력서 삭제' 메뉴 항목 탐색 및 클릭...")

            # 드롭다운 현황 확인
            dropdown_info = await page.evaluate("""() => {
                const result = [];
                for (const sel of ['li', 'button', '[role="menuitem"]', '[class*="DropDown"]']) {
                    for (const el of document.querySelectorAll(sel)) {
                        const text = (el.innerText || '').trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && text.includes('삭제')) {
                            result.push({
                                tag: el.tagName, text: text.substring(0, 60),
                                cls: (el.className || '').substring(0, 80),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    }
                }
                return result;
            }""")
            safe_print(f"[INFO] 삭제 관련 드롭다운 항목 ({len(dropdown_info)}개):")
            for d in dropdown_info:
                safe_print(f"  - [{d['tag']:8s}] ({d['x']},{d['y']}) '{d['text']}' cls='{d['cls'][:50]}'")

            delete_clicked = False

            # 방법 1: JS 직접 클릭 (스크롤 없이) - 뷰포트 밖 요소도 동작
            js_result = await page.evaluate("""() => {
                const allEls = Array.from(document.querySelectorAll(
                    'li, button, [role="menuitem"], [class*="DropDownItem"]'
                ));
                for (const el of allEls) {
                    const text = (el.innerText || '').trim();
                    if (text === '이력서 삭제') {
                        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                        el.click();
                        return `js_clicked: ${el.tagName} y=${Math.round(el.getBoundingClientRect().y)}`;
                    }
                }
                for (const el of allEls) {
                    const text = (el.innerText || '').trim();
                    if (text.includes('이력서 삭제')) {
                        el.click();
                        return `js_clicked_contains: ${el.tagName}`;
                    }
                }
                return 'not_found';
            }""")
            safe_print(f"[INFO] JS 클릭 결과: {js_result}")

            if js_result != 'not_found':
                delete_clicked = True
                safe_print("[OK] JS '이력서 삭제' 클릭!")

            # 방법 2: Playwright force 클릭
            if not delete_clicked:
                for selector in [
                    'li:has-text("이력서 삭제")',
                    'button:has-text("이력서 삭제")',
                    '[class*="DropDownItem"]:has-text("이력서 삭제")',
                ]:
                    try:
                        loc = page.locator(selector)
                        cnt = await loc.count()
                        if cnt > 0:
                            await loc.first.click(force=True)
                            delete_clicked = True
                            safe_print(f"[OK] '{selector}' 클릭!")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] {selector}: {e}")

            # 방법 3: Playwright get_by_role
            if not delete_clicked:
                try:
                    loc = page.get_by_role('button', name='이력서 삭제')
                    cnt = await loc.count()
                    if cnt > 0:
                        await loc.first.click(force=True)
                        delete_clicked = True
                        safe_print("[OK] role=button '이력서 삭제' force 클릭!")
                except Exception as e:
                    safe_print(f"[WARN] role=button: {e}")

            assert delete_clicked, "'이력서 삭제' 메뉴 항목을 클릭할 수 없습니다"
            safe_print("[OK] '이력서 삭제' 클릭 성공!")

            # ── Step 7: 삭제 확인 모달 대기 및 처리 ──
            safe_print("[INFO] 삭제 확인 모달 대기 중...")
            await page.wait_for_timeout(1500)

            # 모달 등장 대기 (DeleteModal 포함)
            modal_appeared = False
            modal_selectors = [
                '[class*="DeleteModal"]',
                '[class*="delete-modal"]',
                '[class*="deleteModal"]',
                '[role="dialog"]',
                '[class*="Modal"]',
                '[class*="modal"]',
                '[class*="Dialog"]',
                '[class*="Confirm"]',
                '[class*="overlay"]',
                '[class*="Overlay"]',
            ]

            for sel in modal_selectors:
                try:
                    loc = page.locator(sel)
                    cnt = await loc.count()
                    if cnt > 0:
                        safe_print(f"[OK] 모달 요소 발견: '{sel}' ({cnt}개)")
                        modal_appeared = True
                        break
                except Exception:
                    pass

            if not modal_appeared:
                # 추가 대기 후 재시도
                safe_print("[INFO] 모달 추가 대기 (2초)...")
                await page.wait_for_timeout(2000)
                for sel in modal_selectors:
                    try:
                        loc = page.locator(sel)
                        cnt = await loc.count()
                        if cnt > 0:
                            safe_print(f"[OK] 모달 요소 발견 (재시도): '{sel}' ({cnt}개)")
                            modal_appeared = True
                            break
                    except Exception:
                        pass

            # 현재 페이지 상태 디버그
            page_debug = await page.evaluate("""() => {
                const result = { modalEls: [], allBtns: [] };
                // 모달 탐색
                const modalSels = [
                    '[class*="DeleteModal"]', '[class*="Modal"]', '[role="dialog"]',
                    '[class*="overlay"]', '[class*="Overlay"]',
                ];
                for (const sel of modalSels) {
                    for (const el of document.querySelectorAll(sel)) {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || '').replace(/\\s+/g, ' ').trim();
                        if (rect.width > 50 && text.length > 0) {
                            result.modalEls.push({
                                sel, text: text.substring(0, 100),
                                cls: (el.className||'').substring(0, 100),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    }
                }
                // 모든 버튼 수집
                for (const btn of document.querySelectorAll('button')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 5 && rect.height > 5) {
                        const text = (btn.innerText || '').trim();
                        result.allBtns.push({
                            text: text.substring(0, 40),
                            cls: (btn.className||'').substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 모달 요소 ({len(page_debug['modalEls'])}개):")
            for m in page_debug['modalEls'][:10]:
                safe_print(f"  - ({m['x']},{m['y']}) '{m['text'][:60]}' cls='{m['cls'][:60]}'")
            safe_print(f"[INFO] 전체 버튼 ({len(page_debug['allBtns'])}개):")
            for b in page_debug['allBtns'][:20]:
                safe_print(f"  - ({b['x']},{b['y']}) '{b['text'][:40]}' cls='{b['cls'][:60]}'")

            # ── Step 8: 삭제 확인 버튼 클릭 ──
            safe_print("[INFO] 삭제 확인 버튼 클릭 시도...")
            confirm_clicked = False

            confirm_keywords = ['삭제', '삭제하기', '확인', '확인하기', '네', '예']
            cancel_keywords = ['취소', '아니오', '아니요', '닫기', '계속', '돌아가기', '이력서 삭제']

            # 방법 1: JS로 모달 내 삭제 버튼 클릭
            confirm_result = await page.evaluate("""() => {
                const confirmTexts = ['삭제', '삭제하기', '확인', '확인하기', '네', '예'];
                const cancelTexts = ['취소', '아니오', '아니요', '닫기', '이력서 삭제'];

                // Priority 1: DeleteModal 내부 버튼
                for (const btn of document.querySelectorAll('[class*="DeleteModal"] button')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) continue;
                    const text = (btn.innerText || '').trim();
                    const isConfirm = confirmTexts.some(kw => text === kw || text.startsWith(kw));
                    const isCancel = cancelTexts.some(kw => text.includes(kw));
                    if (isConfirm && !isCancel) {
                        btn.click();
                        return `delete_modal_btn: '${text}'`;
                    }
                }

                // Priority 2: role=dialog 내부 버튼
                for (const btn of document.querySelectorAll('[role="dialog"] button')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) continue;
                    const text = (btn.innerText || '').trim();
                    const isConfirm = confirmTexts.some(kw => text === kw);
                    const isCancel = cancelTexts.some(kw => text.includes(kw));
                    if (isConfirm && !isCancel) {
                        btn.click();
                        return `dialog_btn: '${text}'`;
                    }
                }

                // Priority 3: Modal 클래스 내부 버튼
                for (const btn of document.querySelectorAll('[class*="Modal"] button')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) continue;
                    const text = (btn.innerText || '').trim();
                    const isConfirm = text === '삭제' || text === '삭제하기' || text === '확인';
                    const isCancel = cancelTexts.some(kw => text.includes(kw));
                    if (isConfirm && !isCancel && text.length <= 10) {
                        btn.click();
                        return `modal_btn: '${text}'`;
                    }
                }

                // Priority 4: 전체 페이지에서 '삭제' 텍스트 버튼 (짧은 것만)
                for (const btn of document.querySelectorAll('button')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width < 5 || rect.height < 5) continue;
                    const text = (btn.innerText || '').trim();
                    if ((text === '삭제' || text === '삭제하기') && text !== '이력서 삭제') {
                        btn.click();
                        return `any_delete_btn: '${text}' cls='${(btn.className||'').substring(0,60)}'`;
                    }
                }

                return 'not_found';
            }""")
            safe_print(f"[INFO] JS 확인 클릭 결과: {confirm_result}")

            if confirm_result != 'not_found':
                confirm_clicked = True
                safe_print(f"[OK] JS로 확인 버튼 클릭!")

            # 방법 2: Playwright role=button으로 시도
            if not confirm_clicked:
                for kw in confirm_keywords:
                    try:
                        btn = page.get_by_role('button', name=kw, exact=True)
                        cnt = await btn.count()
                        if cnt > 0:
                            for i in range(cnt):
                                b = btn.nth(i)
                                btn_text = (await b.inner_text()).strip()
                                if not any(ck in btn_text for ck in cancel_keywords):
                                    await b.click(force=True)
                                    confirm_clicked = True
                                    safe_print(f"[OK] Playwright role=button '{kw}' 클릭!")
                                    break
                        if confirm_clicked:
                            break
                    except Exception as e:
                        safe_print(f"[WARN] role=button '{kw}': {e}")

            # 방법 3: 삭제 버튼 좌표 기반 클릭 (page_debug에서 수집한 버튼)
            if not confirm_clicked:
                for btn_info in page_debug['allBtns']:
                    text = btn_info['text'].strip()
                    cls = btn_info['cls'].lower()
                    is_confirm = any(text == kw for kw in ['삭제', '삭제하기', '확인'])
                    is_cancel = any(ck in text for ck in cancel_keywords)
                    is_modal = 'delete' in cls or 'modal' in cls or 'confirm' in cls
                    if is_confirm and not is_cancel and len(text) <= 10:
                        cx = btn_info['x'] + btn_info['w'] // 2
                        cy = btn_info['y'] + btn_info['h'] // 2
                        safe_print(f"[INFO] 좌표 클릭: '{text}' ({cx},{cy}) cls='{btn_info['cls'][:50]}'")
                        await page.mouse.click(cx, cy)
                        confirm_clicked = True
                        safe_print(f"[OK] 좌표 기반 확인 클릭: '{text}'")
                        break

            if not confirm_clicked:
                safe_print("[WARN] 삭제 확인 모달 또는 버튼을 찾지 못함 (삭제가 즉시 처리됐을 수 있음)")

            # 삭제 처리 대기
            await page.wait_for_timeout(2000)

            # ── Step 9: '삭제되었습니다.' 토스트 메시지 확인 ──
            safe_print("[INFO] '삭제되었습니다.' 토스트/툴팁 메시지 확인 중...")
            toast_found = False
            toast_text = ''

            for attempt in range(10):
                toast_info = await page.evaluate("""() => {
                    const result = { toasts: [], bodySnippet: '' };
                    const toastSels = [
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
                    for (const sel of toastSels) {
                        for (const el of document.querySelectorAll(sel)) {
                            const text = (el.innerText || el.textContent || '').trim();
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && text.length > 0 && text.length < 200) {
                                result.toasts.push({ text: text.substring(0, 80), sel });
                            }
                        }
                    }
                    result.bodySnippet = (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 3000);
                    return result;
                }""")

                for t in toast_info['toasts']:
                    if '삭제되었습니다' in t['text']:
                        toast_found = True
                        toast_text = t['text']
                        safe_print(f"[OK] 토스트 메시지: '{toast_text}' sel='{t['sel']}'")
                        break

                if not toast_found and '삭제되었습니다' in toast_info['bodySnippet']:
                    toast_found = True
                    toast_text = '삭제되었습니다.'
                    safe_print("[OK] 페이지 본문에서 '삭제되었습니다.' 확인")

                if toast_found:
                    break

                await page.wait_for_timeout(300)

            if not toast_found:
                safe_print("[WARN] '삭제되었습니다.' 토스트를 즉시 찾지 못함. 카드 수 감소로 검증 진행...")

            # ── Step 10: 카드 수 감소 검증 ──
            safe_print("[INFO] 삭제 결과 검증 (페이지 리로드)...")
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
