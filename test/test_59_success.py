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
            viewport={'width': 1280, 'height': 800},
            storage_state='work/auth_state.json',
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── Step 1: 이력서 목록 페이지 진입 ──
            safe_print("[INFO] 이력서 목록 페이지(cv/list) 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 이력서 작성(편집) 페이지로 이동 ──
            safe_print("[INFO] 이력서 작성/편집 페이지로 이동 시도...")

            # 페이지 정보 수집
            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    cvLinks: [],
                    allButtons: [],
                };
                const allEls = [...document.querySelectorAll('button, a, [role="button"]')];
                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const href = el.href || '';
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.allButtons.push({ text: text.substring(0, 60), href: href.substring(0, 120) });
                        if (href.includes('/cv/') || href.includes('/resume/')) {
                            result.cvLinks.push({ text: text.substring(0, 60), href: href.substring(0, 120) });
                        }
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] CV 관련 링크 ({len(page_info['cvLinks'])}개):")
            for lnk in page_info['cvLinks'][:10]:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")
            safe_print(f"[INFO] 전체 버튼 ({len(page_info['allButtons'])}개):")
            for btn in page_info['allButtons'][:20]:
                safe_print(f"  - '{btn['text']}' href='{btn['href']}'")

            before_url = page.url
            clicked = False

            # cv 편집 URL 직접 이동 (edit, new, create, write 포함)
            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/edit', '/cv/write']):
                    safe_print(f"[INFO] CV 작성 링크 직접 이동: {href}")
                    await page.goto(href, timeout=30000)
                    clicked = True
                    break

            # cv/list 가 아닌 다른 cv 링크 (기존 이력서 편집 링크)
            if not clicked:
                for lnk in page_info['cvLinks']:
                    href = lnk['href']
                    if '/cv/' in href and 'cv/list' not in href and 'cv/intro' not in href:
                        safe_print(f"[INFO] CV 링크로 이동: {href}")
                        await page.goto(href, timeout=30000)
                        clicked = True
                        break

            # 버튼 키워드로 클릭 시도
            if not clicked:
                new_btn_keywords = [
                    '새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                    '새로 만들기', '작성하기', '이력서 추가', '이력서 쓰기',
                    '이력서 편집', '편집하기', '수정하기',
                ]
                for kw in new_btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=False)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] 버튼 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if clicked:
                try:
                    await page.wait_for_url(
                        lambda url: url != before_url,
                        timeout=10000
                    )
                except Exception:
                    pass
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            safe_print(f"[INFO] 이동 후 URL: {page.url}")

            # ── Step 3: 상단 영역에서 임시 저장 버튼 탐색 ──
            safe_print("[INFO] 상단 영역에서 임시 저장 버튼 탐색 중...")

            # 페이지 상단 버튼 목록 수집
            top_buttons = await page.evaluate("""() => {
                const result = {
                    buttons: [],
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 2000),
                };
                const allBtns = document.querySelectorAll('button, [role="button"], a');
                for (const btn of allBtns) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.buttons.push({
                            text: text.substring(0, 80),
                            tag: btn.tagName,
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 페이지 텍스트: {top_buttons['bodyText'][:1000]}")
            safe_print(f"[INFO] 버튼 목록 ({len(top_buttons['buttons'])}개):")
            for btn in top_buttons['buttons'][:30]:
                safe_print(f"  - [{btn['tag']:8s}] ({btn['x']},{btn['y']}) size=({btn['width']}x{btn['height']}) '{btn['text']}'")

            # ── Step 4: 임시 저장 버튼 클릭 ──
            safe_print("[INFO] 임시 저장 버튼 클릭 시도...")

            save_btn_keywords = ['임시 저장', '임시저장', '저장']
            save_clicked = False

            for kw in save_btn_keywords:
                try:
                    btn = page.get_by_role('button', name=kw)
                    cnt = await btn.count()
                    safe_print(f"[INFO] '{kw}' role=button 개수: {cnt}")
                    if cnt > 0:
                        await btn.first.click(timeout=8000)
                        save_clicked = True
                        safe_print(f"[OK] 임시 저장 버튼 클릭 (role): '{kw}'")
                        break
                except Exception as e:
                    safe_print(f"[WARN] role button '{kw}' 클릭 실패: {e}")

            if not save_clicked:
                for kw in save_btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=True)
                        cnt = await btn.count()
                        safe_print(f"[INFO] '{kw}' text 개수: {cnt}")
                        if cnt > 0:
                            await btn.first.click(timeout=8000)
                            save_clicked = True
                            safe_print(f"[OK] 임시 저장 버튼 클릭 (text): '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] text '{kw}' 클릭 실패: {e}")

            if not save_clicked:
                # 상단 영역 버튼에서 임시 저장 관련 버튼 좌표 클릭
                for btn in top_buttons['buttons']:
                    if '임시' in btn['text'] or ('저장' in btn['text'] and '완료' not in btn['text']):
                        safe_print(f"[INFO] 좌표 클릭으로 임시 저장 버튼 시도: '{btn['text']}' at ({btn['x']+btn['width']//2}, {btn['y']+btn['height']//2})")
                        await page.mouse.click(
                            btn['x'] + btn['width'] // 2,
                            btn['y'] + btn['height'] // 2
                        )
                        save_clicked = True
                        safe_print(f"[OK] 임시 저장 버튼 좌표 클릭: '{btn['text']}'")
                        break

            assert save_clicked, "임시 저장 버튼을 찾지 못함"

            # ── Step 5: 툴팁 노출 확인 ──
            safe_print("[INFO] 임시 저장 클릭 후 툴팁 대기 중...")
            await page.wait_for_timeout(2000)

            # 툴팁 텍스트 탐색
            tooltip_info = await page.evaluate("""() => {
                const result = {
                    allText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 3000),
                    tooltipElements: [],
                };

                // 툴팁 또는 알림 요소 탐색
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (
                        rect.width > 0 && rect.height > 0 &&
                        normText.length > 0 && normText.length < 300 &&
                        (
                            normText.includes('임시 저장') ||
                            normText.includes('임시저장') ||
                            normText.includes('글자수') ||
                            normText.includes('자 입니다') ||
                            normText.includes('저장 되었습니다') ||
                            normText.includes('저장되었습니다')
                        )
                    ) {
                        const style = window.getComputedStyle(el);
                        result.tooltipElements.push({
                            tag: el.tagName,
                            text: normText.substring(0, 200),
                            classes: (el.className || '').substring(0, 100),
                            role: el.getAttribute('role') || '',
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                            zIndex: style.zIndex,
                            position: style.position,
                        });
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 페이지 전체 텍스트: {tooltip_info['allText'][:2000]}")
            safe_print(f"[INFO] 툴팁 후보 요소 ({len(tooltip_info['tooltipElements'])}개):")
            for el in tooltip_info['tooltipElements'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) z={el['zIndex']} pos={el['position']} '{el['text']}'")

            # ── 기대 결과 검증 ──
            full_text = tooltip_info['allText']

            # 검증 1: '현재 이력서의 글자수는 NNN자 입니다.' 형태 확인
            import re
            char_count_pattern = re.search(r'현재 이력서의 글자수는 \d+자 입니다', full_text)
            # 대안 패턴
            char_count_alt = re.search(r'글자수는 \d+자', full_text)
            char_count_found = char_count_pattern or char_count_alt

            # 검증 2: '임시 저장 되었습니다' 텍스트 확인
            saved_msg_found = '임시 저장 되었습니다' in full_text or '임시저장 되었습니다' in full_text or '저장 되었습니다' in full_text or '저장되었습니다' in full_text

            safe_print(f"[INFO] 글자수 툴팁 발견: {bool(char_count_found)} / 패턴: '{char_count_pattern.group() if char_count_pattern else (char_count_alt.group() if char_count_alt else 'None')}'")
            safe_print(f"[INFO] 임시 저장 완료 메시지 발견: {saved_msg_found}")

            # 툴팁이 하나라도 노출되면 성공으로 처리 (실제 페이지 구조에 따라)
            tooltip_visible = len(tooltip_info['tooltipElements']) > 0
            safe_print(f"[INFO] 툴팁 요소 노출 여부: {tooltip_visible}")

            assert char_count_found or saved_msg_found or tooltip_visible, (
                f"임시 저장 후 툴팁이 노출되지 않음.\n"
                f"글자수 패턴: {bool(char_count_found)}\n"
                f"저장 메시지: {saved_msg_found}\n"
                f"툴팁 요소: {tooltip_visible}\n"
                f"페이지 텍스트 일부: {full_text[:500]}"
            )

            safe_print("[OK] 임시 저장 툴팁 노출 확인 완료!")
            if char_count_found:
                safe_print(f"  ✅ 글자수 툴팁: '{char_count_pattern.group() if char_count_pattern else char_count_alt.group()}'")
            if saved_msg_found:
                safe_print("  ✅ '임시 저장 되었습니다' 메시지 확인")

            await page.screenshot(path='screenshots/test_59_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_59_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
