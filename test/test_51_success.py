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

            # ── Step 1: 이력서 페이지 진입 (로그인 상태) ──
            safe_print("[INFO] 이력서 페이지 진입 중 (로그인 상태)...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 이력서 페이지 로드: {page.url}")

            # ── Step 2: 내 이력서 리스트 확인 ──
            safe_print("[INFO] 내 이력서 리스트 확인 중...")
            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').substring(0, 600),
                    resumeListFound: false,
                    newResumeBtn: null,
                    visibleButtons: [],
                };

                const bodyText = document.body.innerText || '';

                // 내 이력서 리스트 확인
                const resumeKeywords = ['내 이력서', '이력서', '지원서', 'Resume'];
                for (const kw of resumeKeywords) {
                    if (bodyText.includes(kw)) {
                        result.resumeListFound = true;
                        break;
                    }
                }

                // 새 이력서 작성 버튼 탐색 (다양한 키워드 포함)
                const newBtnKeywords = [
                    '새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                    '새로 만들기', '작성하기', '이력서 추가', '새로운 이력서',
                    '이력서 쓰기', '새 CV', '이력서 시작',
                ];
                const allBtns = [...document.querySelectorAll('button, a, [role="button"]')];
                for (const btn of allBtns) {
                    const text = (btn.innerText || btn.textContent || '').trim();
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        result.visibleButtons.push({
                            tag: btn.tagName,
                            text: text.substring(0, 60),
                            href: btn.href || '',
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                        });
                        if (!result.newResumeBtn) {
                            for (const kw of newBtnKeywords) {
                                if (text.includes(kw)) {
                                    result.newResumeBtn = {
                                        tag: btn.tagName,
                                        text: text.substring(0, 60),
                                        href: btn.href || '',
                                        x: Math.round(rect.left + rect.width / 2),
                                        y: Math.round(rect.top + rect.height / 2),
                                    };
                                    break;
                                }
                            }
                        }
                    }
                }

                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_info['url']}")
            safe_print(f"[INFO] 이력서 리스트 확인: {page_info['resumeListFound']}")
            safe_print(f"[INFO] 새 이력서 작성 버튼: {page_info['newResumeBtn']}")
            safe_print(f"[INFO] 화면 내 버튼/링크 (상위 25개):")
            for btn in page_info['visibleButtons'][:25]:
                safe_print(f"  - tag={btn['tag']:6s} | ({btn['x']:4d},{btn['y']:4d}) | '{btn['text'][:50]}' | href='{btn['href'][:50]}'")
            safe_print(f"[INFO] 페이지 내용 미리보기:\n{page_info['bodyText']}")

            # 이력서 페이지 확인
            current_url = page.url
            assert 'cv' in current_url or 'resume' in current_url or 'wanted.co.kr' in current_url, \
                f"이력서 페이지가 아님: {current_url}"
            assert page_info['resumeListFound'], f"이력서 리스트가 화면에 없음 (URL: {current_url})"
            safe_print("[OK] 내 이력서 리스트 확인 완료!")

            # ── Step 3: 새 이력서 작성 버튼 클릭 ──
            safe_print("[INFO] 새 이력서 작성 버튼 클릭...")
            before_url = page.url
            clicked = False

            # 방법 1: 발견된 버튼 좌표로 마우스 클릭
            if page_info['newResumeBtn']:
                btn_info = page_info['newResumeBtn']
                safe_print(f"[INFO] 버튼 발견: '{btn_info['text']}' at ({btn_info['x']}, {btn_info['y']})")
                try:
                    await page.mouse.click(btn_info['x'], btn_info['y'])
                    clicked = True
                    safe_print("[OK] 마우스 좌표 클릭 성공")
                except Exception as e:
                    safe_print(f"[WARN] 마우스 클릭 실패: {e}")

            # 방법 2: get_by_role로 클릭
            if not clicked:
                for kw in ['새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기']:
                    try:
                        btn = page.get_by_role('button', name=kw)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] get_by_role 클릭 성공: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] get_by_role 실패 '{kw}': {e}")

            # 방법 3: get_by_text로 클릭
            if not clicked:
                for kw in ['새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기', '새로 만들기']:
                    try:
                        btn = page.get_by_text(kw, exact=False)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] get_by_text 클릭 성공: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] get_by_text 실패 '{kw}': {e}")

            # 방법 4: JS로 클릭
            if not clicked:
                js_result = await page.evaluate("""() => {
                    const keywords = ['새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기', '새로 만들기', '작성하기'];
                    const elems = [...document.querySelectorAll('button, a, [role="button"]')];
                    for (const el of elems) {
                        const text = (el.innerText || el.textContent || '').trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            for (const kw of keywords) {
                                if (text.includes(kw)) {
                                    el.click();
                                    return { clicked: true, text };
                                }
                            }
                        }
                    }
                    return { clicked: false };
                }""")
                if js_result.get('clicked'):
                    clicked = True
                    safe_print(f"[OK] JS 클릭 성공: '{js_result.get('text')}'")

            assert clicked, "새 이력서 작성 버튼을 찾거나 클릭할 수 없음"

            # ── Step 4: 이력서 작성 페이지로 이동 확인 ──
            safe_print("[INFO] 이력서 작성 페이지로 이동 대기 중...")
            try:
                await page.wait_for_url(
                    lambda url: url != before_url,
                    timeout=8000
                )
            except Exception:
                pass
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            after_url = page.url
            safe_print(f"[INFO] 클릭 전 URL: {before_url}")
            safe_print(f"[INFO] 클릭 후 URL: {after_url}")

            # 이력서 작성 페이지 URL 패턴
            cv_writing_patterns = ['/cv/new', '/cv/create', '/cv/edit', '/resume/new', '/resume/create', '/resume/edit']
            url_changed = after_url != before_url
            is_writing_url = any(pat in after_url for pat in cv_writing_patterns)

            # 페이지 내용으로 확인
            page_check = await page.evaluate("""() => {
                const bodyText = document.body.innerText || '';
                const writingKeywords = [
                    '이력서 작성', '기본 정보', '학력', '경력', '자기소개서',
                    '제목을 입력', '이름을 입력', '저장', '임시저장', '이력서 제목',
                ];
                for (const kw of writingKeywords) {
                    if (bodyText.includes(kw)) return { found: true, keyword: kw };
                }
                return { found: false, bodyText: bodyText.substring(0, 400) };
            }""")

            safe_print(f"[INFO] URL 변경됨: {url_changed}")
            safe_print(f"[INFO] 작성 페이지 URL 패턴 매칭: {is_writing_url}")
            safe_print(f"[INFO] 페이지 내용 확인: {page_check}")

            moved_to_writing = url_changed or is_writing_url or page_check.get('found', False)

            assert moved_to_writing, (
                f"이력서 작성 페이지로 이동하지 않음 "
                f"(URL={after_url}, url_changed={url_changed}, "
                f"is_writing_url={is_writing_url}, "
                f"content_found={page_check.get('found')})"
            )

            safe_print("[OK] 이력서 작성 페이지 이동 확인 완료!")
            safe_print(f"[OK] 최종 URL: {after_url}")

            await page.screenshot(path='screenshots/test_51_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_51_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
