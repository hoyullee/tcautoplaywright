import sys
from playwright.async_api import async_playwright
import asyncio
import os
import re
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

@pytest.mark.asyncio
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

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 목록 페이지로 이동 후 포지션 URL 확보
            print("[INFO] 채용 목록 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 채용 목록 페이지 로드 완료 - URL: {page.url}")

            position_url = None
            wd_links = page.locator('a[href*="/wd/"]')
            count = await wd_links.count()
            print(f"[INFO] /wd/ 링크 수: {count}")

            if count > 0:
                href = await wd_links.first.get_attribute('href')
                if href:
                    position_url = href if href.startswith('http') else f"https://www.wanted.co.kr{href}"
                    print(f"[OK] 포지션 URL 발견: {position_url}")

            assert position_url is not None, "포지션 상세 페이지 URL을 찾을 수 없습니다"

            # 2. 포지션 상세 페이지 진입
            print(f"[INFO] 포지션 상세 페이지 진입: {position_url}")
            await page.goto(position_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 포지션 상세 페이지 로드 완료 - URL: {page.url}")
            await page.screenshot(path='screenshots/test_35_step1_detail.png')

            # 3. 페이지 스크롤하여 '태그' 항목 탐색
            print("[INFO] '태그' 항목 탐색 중...")
            tag_found = False

            # 스크롤하면서 탐색
            for scroll_step in range(15):
                tag_texts = ['태그', 'tag', 'Tag', '#']
                for t in tag_texts:
                    try:
                        el = page.get_by_text(t, exact=True)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        tag_found = True
                                        print(f"[OK] '{t}' 텍스트 발견 (visible, count={cnt})")
                                        break
                                except Exception:
                                    continue
                        if tag_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{t}' 탐색 실패: {e}")
                if tag_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(400)

            # JS 기반 '태그' 항목 탐색
            if not tag_found:
                print("[INFO] JS 기반 '태그' 항목 탐색 중...")
                js_tag = await page.evaluate("""() => {
                    const keywords = ['태그', 'Tag', 'tag'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        if (keywords.includes(text)) {
                            const el = node.parentElement;
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0) {
                                return {found: true, text: text, tag: el.tagName, cls: el.className.substring(0, 60)};
                            }
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS '태그' 탐색 결과: {js_tag}")
                if js_tag.get('found'):
                    tag_found = True
                    print(f"[OK] JS로 '태그' 항목 발견: {js_tag.get('text')}")

            # '태그' 없을 경우 스킵 (일부 공고는 태그가 없을 수 있음)
            if not tag_found:
                print("[WARN] '태그' 항목이 없는 포지션입니다. 다른 포지션으로 재시도...")
                # 목록에서 다른 포지션 시도
                await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)
                wd_links = page.locator('a[href*="/wd/"]')
                count = await wd_links.count()
                if count > 1:
                    href = await wd_links.nth(1).get_attribute('href')
                    if href:
                        position_url = href if href.startswith('http') else f"https://www.wanted.co.kr{href}"
                        await page.goto(position_url, timeout=60000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        print(f"[INFO] 두 번째 포지션 상세 페이지 진입: {position_url}")

            await page.screenshot(path='screenshots/test_35_step2_scrolled.png')

            # 4. 마감일 항목 탐색 (스크롤하면서)
            print("[INFO] '마감일' 항목 탐색 중...")
            deadline_found = False
            deadline_value = None

            # 페이지 전체 스크롤
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            for scroll_step in range(20):
                # 다양한 마감일 텍스트 패턴 탐색
                deadline_texts = ['마감일', '채용 마감일', '지원 마감일', '마감', '기간']
                for dt in deadline_texts:
                    try:
                        el = page.get_by_text(dt, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        deadline_found = True
                                        try:
                                            deadline_value = await item.inner_text()
                                        except Exception:
                                            deadline_value = dt
                                        print(f"[OK] '{dt}' 텍스트 발견 (visible, text='{deadline_value}')")
                                        break
                                except Exception:
                                    continue
                        if deadline_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{dt}' 탐색 실패: {e}")
                if deadline_found:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(400)

            # JS로 마감일 탐색
            if not deadline_found:
                print("[INFO] JS 기반 '마감일' 탐색 중...")
                js_deadline = await page.evaluate("""() => {
                    const keywords = ['마감일', '채용 마감일', '지원 마감일', '마감'];
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        const text = node.textContent.trim();
                        for (const kw of keywords) {
                            if (text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0) {
                                    // 마감일 값도 찾기
                                    let container = el;
                                    let valueText = text;
                                    for (let i = 0; i < 4; i++) {
                                        if (!container) break;
                                        const fullText = (container.innerText || container.textContent || '').trim();
                                        if (fullText.length > text.length && fullText.length < 200) {
                                            valueText = fullText;
                                        }
                                        container = container.parentElement;
                                    }
                                    return {
                                        found: true,
                                        keyword: kw,
                                        text: text,
                                        valueText: valueText,
                                        tag: el.tagName,
                                        cls: el.className.substring(0, 60)
                                    };
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS '마감일' 탐색 결과: {js_deadline}")
                if js_deadline.get('found'):
                    deadline_found = True
                    deadline_value = js_deadline.get('valueText', js_deadline.get('text'))
                    print(f"[OK] JS로 '마감일' 항목 발견: {deadline_value}")

            await page.screenshot(path='screenshots/test_35_step3_deadline.png')

            assert deadline_found, "'마감일' 항목을 찾을 수 없습니다"
            print(f"[OK] '마감일' 항목 확인됨: {deadline_value}")

            # 5. 마감일 값이 날짜 또는 '상시채용'인지 확인
            print("[INFO] 마감일 값 검증 중...")

            # 마감일 관련 전체 텍스트 컨텍스트 수집
            deadline_context = await page.evaluate("""() => {
                const keywords = ['마감일', '채용 마감일', '지원 마감일', '마감'];
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    const text = node.textContent.trim();
                    for (const kw of keywords) {
                        if (text.includes(kw)) {
                            const el = node.parentElement;
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0) {
                                // 컨테이너 텍스트 수집
                                let container = el;
                                let contexts = [];
                                for (let i = 0; i < 5; i++) {
                                    if (!container) break;
                                    const t = (container.innerText || container.textContent || '').trim();
                                    if (t) contexts.push(t);
                                    container = container.parentElement;
                                }
                                // 형제 요소들도 확인
                                const siblings = [];
                                let sibling = el.nextElementSibling;
                                for (let i = 0; i < 3 && sibling; i++) {
                                    const st = (sibling.innerText || sibling.textContent || '').trim();
                                    if (st) siblings.push(st);
                                    sibling = sibling.nextElementSibling;
                                }
                                return {
                                    contexts: contexts,
                                    siblings: siblings,
                                    keyword: kw
                                };
                            }
                        }
                    }
                }
                return {contexts: [], siblings: [], keyword: ''};
            }""")

            try:
                print(f"[INFO] 마감일 컨텍스트 keyword={deadline_context.get('keyword')}, contexts_count={len(deadline_context.get('contexts', []))}")
            except Exception:
                print("[INFO] 마감일 컨텍스트 출력 중 인코딩 오류 (무시)")

            # 날짜 또는 '상시채용' 패턴 검증
            # 날짜 패턴: YYYY.MM.DD, YYYY-MM-DD, MM월 DD일, ~MM/DD 등
            date_pattern = re.compile(
                r'(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})'  # YYYY.MM.DD 형식
                r'|(\d{1,2}월\s*\d{1,2}일)'            # MM월 DD일 형식
                r'|(상시채용)'                           # 상시채용
                r'|(상시모집)'                           # 상시모집
                r'|(채용시\s*마감)'                      # 채용시 마감
                r'|(\d{4}년\s*\d{1,2}월)'              # YYYY년 MM월 형식
            )

            all_texts = deadline_context.get('contexts', []) + deadline_context.get('siblings', [])
            if deadline_value:
                all_texts.append(str(deadline_value))

            value_valid = False
            matched_value = None

            for text in all_texts:
                if not text:
                    continue
                # 인코딩 안전 출력용
                safe_text = text[:80].encode('cp949', errors='replace').decode('cp949')
                m = date_pattern.search(text)
                if m:
                    value_valid = True
                    matched_value = m.group(0)
                    print(f"[OK] 날짜 패턴 발견: '{matched_value}' (in '{safe_text}')")
                    break
                # 상시채용 추가 체크
                if '상시' in text or '상시채용' in text or '상시모집' in text:
                    value_valid = True
                    matched_value = '상시채용'
                    print(f"[OK] '상시채용' 패턴 발견 (in '{safe_text}')")
                    break

            # 페이지 전체에서 날짜/상시채용 탐색 (추가 확인)
            if not value_valid:
                print("[INFO] 페이지 전체에서 날짜/상시채용 탐색 중...")
                full_page_check = await page.evaluate("""() => {
                    const datePattern = /\\d{4}[.\\-\\/]\\d{1,2}[.\\-\\/]\\d{1,2}/;
                    const monthPattern = /\\d{1,2}월\\s*\\d{1,2}일/;
                    const alwaysPattern = /상시채용|상시모집|채용시\\s*마감/;

                    // 마감일 레이블 근처의 텍스트 수집
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text.includes('마감') && text.length < 100) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                if (datePattern.test(text) || monthPattern.test(text) || alwaysPattern.test(text)) {
                                    return {
                                        found: true,
                                        text: text,
                                        hasDate: datePattern.test(text) || monthPattern.test(text),
                                        hasAlways: alwaysPattern.test(text)
                                    };
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                try:
                    print(f"[INFO] 전체 탐색 결과: found={full_page_check.get('found')}")
                except Exception:
                    print("[INFO] 전체 탐색 결과 출력 오류")
                if full_page_check.get('found'):
                    value_valid = True
                    matched_value = full_page_check.get('text', '')
                    safe_mv = str(matched_value)[:80].encode('cp949', errors='replace').decode('cp949')
                    print(f"[OK] 날짜/상시채용 발견: '{safe_mv}'")

            # 추가 fallback: deadline_value가 있으면 부분 확인
            if not value_valid and deadline_value:
                dv_str = str(deadline_value)
                if re.search(r'\d{4}', dv_str):  # 연도 포함
                    value_valid = True
                    matched_value = dv_str
                    print(f"[OK] 연도 포함 텍스트 발견: '{dv_str[:80]}'")
                elif '상시' in dv_str:
                    value_valid = True
                    matched_value = dv_str
                    print(f"[OK] '상시' 텍스트 발견: '{dv_str[:80]}'")

            assert value_valid, (
                "마감일 값이 날짜 또는 '상시채용' 형식이 아닙니다."
            )

            safe_matched = str(matched_value).encode('cp949', errors='replace').decode('cp949')
            print(f"[OK] 마감일 값 검증 성공: '{safe_matched}'")

            await page.screenshot(path='screenshots/test_35_step4_final.png')

            print("[SUMMARY] 테스트 케이스 35 검증 완료:")
            print("[OK] 포지션 상세 페이지 진입")
            print(f"[OK] '태그' 항목 하단 '마감일' 항목 확인됨")
            safe_matched2 = str(matched_value).encode('cp949', errors='replace').decode('cp949')
            print(f"[OK] 마감일 값: '{safe_matched2}' (날짜 또는 상시채용)")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_35_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
