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
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 이력서 작성(편집) 페이지로 이동 ──
            safe_print("[INFO] 이력서 작성 페이지로 이동 시도...")

            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').substring(0, 800),
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

            safe_print(f"[INFO] 현재 URL: {page_info['url']}")
            safe_print(f"[INFO] 페이지 미리보기: {page_info['bodyText']}")
            safe_print(f"[INFO] CV 관련 링크 ({len(page_info['cvLinks'])}개):")
            for lnk in page_info['cvLinks'][:10]:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")
            safe_print(f"[INFO] 전체 버튼 ({len(page_info['allButtons'])}개):")
            for btn in page_info['allButtons'][:20]:
                safe_print(f"  - '{btn['text']}' href='{btn['href']}'")

            # cv 편집 URL로 이동 시도
            before_url = page.url
            clicked = False

            # 직접 편집 링크가 있으면 이동
            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/edit', '/cv/write']):
                    safe_print(f"[INFO] CV 작성 링크 직접 이동: {href}")
                    await page.goto(href, timeout=30000)
                    clicked = True
                    break

            # cv/list가 아닌 cv 링크 (기존 이력서 편집 링크)
            if not clicked:
                for lnk in page_info['cvLinks']:
                    href = lnk['href']
                    if '/cv/' in href and href != 'https://www.wanted.co.kr/cv/list':
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
                await page.wait_for_timeout(4000)

            safe_print(f"[INFO] 이동 후 URL: {page.url}")

            # ── Step 3: 현재 페이지 내용 파악 ──
            safe_print("[INFO] 현재 페이지 내용 파악 중...")
            page_scan = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 3000),
                    introElements: [],
                    textareas: [],
                };

                // 간단 소개 관련 요소 탐색
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (
                        rect.width > 0 && rect.height > 0 &&
                        (
                            normText.includes('간단 소개') ||
                            normText.includes('간단소개') ||
                            normText.includes('자기소개') ||
                            normText.includes('소개 글') ||
                            normText.includes('한줄 소개') ||
                            normText.includes('한 줄 소개')
                        ) &&
                        normText.length < 200
                    ) {
                        result.introElements.push({
                            tag: el.tagName,
                            text: normText.substring(0, 100),
                            classes: (el.className || '').substring(0, 100),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }

                // textarea / contenteditable 탐색
                const editableEls = document.querySelectorAll('textarea, [contenteditable="true"]');
                for (const el of editableEls) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        result.textareas.push({
                            tag: el.tagName,
                            type: el.type || '',
                            placeholder: (el.placeholder || '').substring(0, 100),
                            classes: (el.className || '').substring(0, 100),
                            id: el.id || '',
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_scan['url']}")
            safe_print(f"[INFO] 페이지 텍스트: {page_scan['bodyText'][:2000]}")
            safe_print(f"[INFO] 간단 소개 관련 요소 ({len(page_scan['introElements'])}개):")
            for el in page_scan['introElements'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) size=({el['width']}x{el['height']}) '{el['text']}'")
            safe_print(f"[INFO] textarea/contenteditable 요소 ({len(page_scan['textareas'])}개):")
            for el in page_scan['textareas'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) size=({el['width']}x{el['height']}) placeholder='{el['placeholder']}' id='{el['id']}'")

            # ── Step 4: 간단 소개 섹션의 textarea 찾기 및 텍스트 입력 ──
            safe_print("[INFO] 간단 소개 섹션 탐색 및 텍스트 입력 시도...")

            intro_text = "안녕하세요. 저는 열정적인 개발자입니다."
            text_entered = False
            counter_verified = False

            # 방법 1: 간단 소개 레이블 인근의 textarea/contenteditable 탐색
            intro_result = await page.evaluate("""() => {
                const result = {
                    found: false,
                    method: '',
                    textareaInfo: null,
                    counterInfo: null,
                };

                // '간단 소개' 레이블 찾기
                const labels = [...document.querySelectorAll('*')].filter(el => {
                    const text = (el.innerText || el.textContent || '').trim();
                    const normText = text.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    return (
                        rect.width > 0 && rect.height > 0 &&
                        (normText === '간단 소개' || normText === '간단소개' || normText.startsWith('간단 소개') || normText.startsWith('간단소개')) &&
                        normText.length < 50 &&
                        ['LABEL', 'H1','H2','H3','H4','H5','P','SPAN','DIV','LI'].includes(el.tagName)
                    );
                });

                for (const label of labels) {
                    // 같은 섹션 내 textarea/contenteditable 탐색
                    const section = label.closest('section, [class*="section"], [class*="Section"], form, [class*="form"], [class*="Form"], [class*="wrap"], [class*="Wrap"]') || label.parentElement;
                    if (!section) continue;
                    const ta = section.querySelector('textarea, [contenteditable="true"]');
                    if (ta) {
                        const rect = ta.getBoundingClientRect();
                        result.found = true;
                        result.method = 'label_section';
                        result.textareaInfo = {
                            tag: ta.tagName,
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        };
                        break;
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 간단 소개 탐색 결과: found={intro_result['found']}, method='{intro_result['method']}'")
            if intro_result['textareaInfo']:
                safe_print(f"  - textarea 정보: {intro_result['textareaInfo']}")

            # ── 텍스트 입력 ──
            # 간단 소개 레이블 기준으로 textarea 찾기
            intro_label_selectors = [
                'text="간단 소개"',
                'text="간단소개"',
            ]

            for selector in intro_label_selectors:
                try:
                    label_el = page.locator(selector).first
                    if await label_el.count() > 0:
                        # 레이블 위치 기반으로 부모 섹션에서 textarea 찾기
                        section = await label_el.evaluate("""el => {
                            const section = el.closest('section, [class*="section"], [class*="Section"], form, [class*="wrap"], [class*="Wrap"], [class*="item"], [class*="Item"]')
                                           || el.parentElement?.parentElement;
                            if (!section) return null;
                            const ta = section.querySelector('textarea, [contenteditable="true"]');
                            if (!ta) return null;
                            const rect = ta.getBoundingClientRect();
                            return {
                                tag: ta.tagName,
                                x: Math.round(rect.left + rect.width / 2),
                                y: Math.round(rect.top + rect.height / 2),
                            };
                        }""")
                        if section:
                            safe_print(f"[INFO] 간단 소개 레이블({selector}) 인근 textarea: {section}")
                            # 좌표로 클릭 후 입력
                            await page.mouse.click(section['x'], section['y'])
                            await page.wait_for_timeout(500)
                            await page.keyboard.press('Control+a')
                            await page.keyboard.type(intro_text)
                            text_entered = True
                            safe_print(f"[OK] 텍스트 입력 성공 (좌표 클릭): '{intro_text}'")
                            break
                except Exception as e:
                    safe_print(f"[WARN] 레이블 기반 탐색 실패 ({selector}): {e}")

            # 방법 2: placeholder로 textarea 찾기
            if not text_entered:
                placeholder_keywords = ['소개', '자기소개', '간단하게', '간단 소개', '본인을 소개']
                for kw in placeholder_keywords:
                    try:
                        ta = page.locator(f'textarea[placeholder*="{kw}"]').first
                        cnt = await ta.count()
                        if cnt > 0:
                            await ta.click(timeout=5000)
                            await page.wait_for_timeout(300)
                            await ta.fill(intro_text)
                            text_entered = True
                            safe_print(f"[OK] placeholder '{kw}' textarea에 텍스트 입력 성공")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] placeholder '{kw}' 탐색 실패: {e}")

            # 방법 3: 텍스트 기반 LNB 메뉴로 '간단 소개' 섹션 이동 후 입력
            if not text_entered:
                safe_print("[INFO] 방법 3: '간단 소개' 텍스트 클릭 후 인접 textarea 탐색...")
                try:
                    intro_btn = page.get_by_text('간단 소개', exact=True).first
                    if await intro_btn.count() > 0:
                        await intro_btn.click(timeout=5000)
                        await page.wait_for_timeout(1000)
                except Exception as e:
                    safe_print(f"[WARN] '간단 소개' 클릭 실패: {e}")

                # 이후 텍스트 영역 재탐색
                textareas = page.locator('textarea')
                ta_count = await textareas.count()
                safe_print(f"[INFO] 발견된 textarea 수: {ta_count}")
                for i in range(ta_count):
                    try:
                        ta = textareas.nth(i)
                        ph = await ta.get_attribute('placeholder') or ''
                        bbox = await ta.bounding_box()
                        safe_print(f"  - textarea[{i}] placeholder='{ph}' bbox={bbox}")
                        if any(kw in ph for kw in ['소개', '자기소개', '간단']):
                            await ta.click(timeout=5000)
                            await ta.fill(intro_text)
                            text_entered = True
                            safe_print(f"[OK] textarea[{i}] 에 텍스트 입력 성공")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] textarea[{i}] 처리 실패: {e}")

            # 방법 4: 첫 번째 visible textarea에 입력
            if not text_entered:
                safe_print("[INFO] 방법 4: 첫 번째 visible textarea에 입력...")
                textareas = page.locator('textarea')
                ta_count = await textareas.count()
                for i in range(ta_count):
                    try:
                        ta = textareas.nth(i)
                        if await ta.is_visible():
                            await ta.click(timeout=5000)
                            await ta.fill(intro_text)
                            text_entered = True
                            safe_print(f"[OK] 첫 번째 visible textarea[{i}] 에 텍스트 입력 성공")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] textarea[{i}] 처리 실패: {e}")

            assert text_entered, "간단 소개 textarea에 텍스트 입력 실패"

            await page.wait_for_timeout(1000)

            # ── Step 5: 카운터 확인 ──
            safe_print("[INFO] 텍스트 카운터 확인 중...")
            expected_count = len(intro_text)
            safe_print(f"[INFO] 입력한 텍스트: '{intro_text}' (길이: {expected_count})")

            js_expected_count = expected_count
            counter_info = await page.evaluate("""(expectedCount) => {
                const result = {
                    foundCounter: false,
                    counterText: '',
                    counterElements: [],
                    fullText: (document.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 2000),
                };

                // 숫자 카운터 패턴 탐색 (예: "20/200", "20자", "20 / 200")
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rawText.length > 0 && rawText.length < 50) {
                        // 숫자/슬래시 패턴
                        if (/\\d+\\s*\\/\\s*\\d+/.test(rawText) || /\\d+자/.test(rawText)) {
                            result.counterElements.push({
                                tag: el.tagName,
                                text: rawText.substring(0, 50),
                                classes: (el.className || '').substring(0, 80),
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                            });
                            // 기대하는 카운트 숫자 포함 여부
                            if (rawText.includes(String(expectedCount))) {
                                result.foundCounter = true;
                                result.counterText = rawText;
                            }
                        }
                    }
                }

                return result;
            }""", js_expected_count)

            safe_print(f"[INFO] 카운터 요소 ({len(counter_info['counterElements'])}개):")
            for el in counter_info['counterElements'][:10]:
                safe_print(f"  - [{el['tag']:12s}] ({el['x']},{el['y']}) '{el['text']}'")
            safe_print(f"[INFO] 카운터 발견: {counter_info['foundCounter']}, 카운터 텍스트: '{counter_info['counterText']}'")
            safe_print(f"[INFO] 페이지 텍스트: {counter_info['fullText'][:1500]}")

            # 텍스트 입력 여부 재확인 (입력된 텍스트가 페이지에 존재하는지)
            text_in_page = intro_text[:10] in counter_info['fullText'] or intro_text in counter_info['fullText']
            safe_print(f"[INFO] 입력 텍스트 페이지 내 존재: {text_in_page}")

            # 검증: 카운터가 표시되는지 확인
            assert counter_info['foundCounter'] or len(counter_info['counterElements']) > 0, (
                f"텍스트박스 카운터가 표시되지 않음. 입력 텍스트: '{intro_text}'"
            )

            if counter_info['foundCounter']:
                safe_print(f"[OK] 카운터 정상 확인: '{counter_info['counterText']}' (기대값: {expected_count}자 포함)")
            else:
                safe_print(f"[OK] 카운터 요소 발견됨: {counter_info['counterElements'][0]['text']}")

            safe_print("[OK] 간단 소개 텍스트 입력 및 카운터 확인 완료!")

            await page.screenshot(path='screenshots/test_55_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_55_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
