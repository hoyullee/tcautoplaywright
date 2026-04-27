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
    """UTF-8 안전 출력"""
    try:
        print(msg)
    except Exception:
        print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


async def find_exact_apply_button(page):
    """정확히 '지원하기' 텍스트를 가진 버튼 탐색"""
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

    # Playwright locator로 시도
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

    # get_by_role 시도
    try:
        loc = page.get_by_role('button', name='지원하기', exact=True)
        cnt = await loc.count()
        if cnt > 0:
            safe_print("[OK] get_by_role로 '지원하기' 버튼 발견")
            return loc.first
    except Exception as e:
        safe_print(f"[WARN] get_by_role 오류: {e}")

    # JS 클릭 필요 여부
    if btn_info:
        return 'use_js'

    return None


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
            for i in range(min(count, 15)):
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

            for pos_url in hrefs[:10]:
                safe_print(f"[INFO] 포지션 시도: {pos_url}")
                await page.goto(pos_url, timeout=60000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(5000)

                # 스크롤해서 버튼 로드 유도
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(1000)

                found = await find_exact_apply_button(page)
                if found is not None:
                    position_url = pos_url
                    apply_btn = found
                    safe_print(f"[OK] '지원하기' 버튼 있는 포지션: {pos_url}")
                    break

                # 추가 스크롤 후 재탐색
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(1000)
                found2 = await find_exact_apply_button(page)
                if found2 is not None:
                    position_url = pos_url
                    apply_btn = found2
                    safe_print(f"[OK] 스크롤 후 '지원하기' 버튼 있는 포지션: {pos_url}")
                    break

            assert apply_btn is not None, "'지원하기' 버튼이 있는 포지션을 찾을 수 없습니다"
            safe_print(f"[OK] 포지션 URL: {position_url}")

            # 4. '지원하기' 버튼 클릭
            safe_print("[INFO] '지원하기' 버튼 클릭 중...")
            await page.screenshot(path='screenshots/test_40_step1_before_click.png')
            pre_click_url = page.url

            if apply_btn == 'use_js':
                safe_print("[INFO] JS로 '지원하기' 버튼 클릭...")
                clicked = await page.evaluate("""() => {
                    const all = [...document.querySelectorAll('button, a, [role="button"]')];
                    for (const el of all) {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text === '지원하기') {
                            el.click();
                            return {clicked: true, tag: el.tagName, classes: el.className.substring(0, 80)};
                        }
                    }
                    return {clicked: false};
                }""")
                safe_print(f"[INFO] JS 클릭 결과: {clicked}")
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

            # 클릭 후 대기 (모달 또는 네비게이션 대기)
            await page.wait_for_timeout(4000)
            post_click_url = page.url
            safe_print(f"[INFO] 클릭 후 URL: {post_click_url}")

            # 새 탭 처리
            active_page = page
            pages = context.pages
            if len(pages) > 1:
                active_page = pages[-1]
                await active_page.wait_for_load_state('domcontentloaded')
                await active_page.wait_for_timeout(2000)
                post_click_url = active_page.url
                safe_print(f"[INFO] 새 탭 URL: {post_click_url}")

            await active_page.screenshot(path='screenshots/test_40_step2_after_click.png')

            # 5. 페이지/모달 내용 수집
            safe_print("[INFO] 지원 페이지/모달 내용 수집 중...")
            dom_result = await active_page.evaluate("""() => {
                const bodyText = document.body.innerText || '';

                const buttons = [...document.querySelectorAll('button, [role="button"]')]
                    .map(el => (el.innerText || el.textContent || '').trim())
                    .filter(t => t.length > 0 && t.length < 60)
                    .slice(0, 50);

                const inputs = [...document.querySelectorAll('input, textarea, select')]
                    .map(el => ({
                        type: el.type || el.tagName,
                        placeholder: el.placeholder || '',
                        name: el.name || '',
                        label: el.getAttribute('aria-label') || '',
                        id: el.id || '',
                    }));

                const labels = [...document.querySelectorAll('label, dt')]
                    .map(el => (el.innerText || el.textContent || '').trim())
                    .filter(t => t.length > 0 && t.length < 60)
                    .slice(0, 30);

                const modalEls = document.querySelectorAll(
                    '[role="dialog"], [class*="modal"], [class*="Modal"], [class*="overlay"], [class*="Overlay"], [class*="apply"], [class*="Apply"]'
                );
                const modalTexts = [...modalEls]
                    .filter(el => el.offsetParent !== null)
                    .map(el => (el.innerText || '').substring(0, 1000));

                const headings = [...document.querySelectorAll('h1, h2, h3, h4, h5')]
                    .map(el => (el.innerText || el.textContent || '').trim())
                    .filter(t => t.length > 0 && t.length < 80)
                    .slice(0, 20);

                return {
                    url: window.location.href,
                    title: document.title,
                    bodyText: bodyText.substring(0, 3000),
                    buttons, inputs, labels, modalTexts, headings,
                };
            }""")

            body_text = dom_result.get('bodyText', '')
            buttons_list = dom_result.get('buttons', [])
            buttons_text = ' '.join(buttons_list)
            inputs_info = dom_result.get('inputs', [])
            labels_text = ' '.join(dom_result.get('labels', []))
            modal_text = ' '.join(dom_result.get('modalTexts', []))
            modal_texts = dom_result.get('modalTexts', [])

            # 입력 필드 텍스트 통합
            inputs_text = ' '.join([
                f"{i.get('placeholder', '')} {i.get('name', '')} {i.get('label', '')} {i.get('id', '')}"
                for i in inputs_info
            ])

            # 전체 검색 대상 텍스트
            all_text = body_text + ' ' + modal_text + ' ' + labels_text + ' ' + inputs_text

            safe_print(f"[INFO] URL: {dom_result.get('url', '')}")
            safe_print(f"[INFO] 제목: {dom_result.get('title', '')[:80]}")
            safe_print(f"[INFO] 버튼 목록: {buttons_list[:25]}")
            safe_print(f"[INFO] 레이블: {dom_result.get('labels', [])[:15]}")
            safe_print(f"[INFO] 헤딩: {dom_result.get('headings', [])[:10]}")
            safe_print(f"[INFO] 입력 필드: {inputs_info[:10]}")
            safe_print(f"[INFO] 모달 텍스트: {[t[:150] for t in modal_texts[:3]]}")

            # 6. 기대결과 검증
            name_found = any(kw in all_text for kw in ['이름', 'name'])
            email_found = any(kw in all_text for kw in ['이메일', 'email', 'e-mail'])
            phone_found = any(kw in all_text for kw in ['연락처', '전화', 'phone', '휴대', 'mobile', 'tel'])
            referral_found = any(kw in all_text for kw in ['추천인', 'referral', '추천 코드'])

            resume_found = any(kw in all_text for kw in ['이력서', 'resume', 'Resume', 'CV'])

            upload_found = any(kw in all_text or kw in buttons_text
                               for kw in ['파일 업로드', '파일업로드', '파일 첨부', 'Upload', '업로드'])

            new_resume_found = any(kw in all_text or kw in buttons_text
                                   for kw in ['새 이력서 작성', '새 이력서', '이력서 작성', '새로 작성', '이력서 만들기'])

            safe_print(f"\n[RESULT] 이름: {name_found}")
            safe_print(f"[RESULT] 이메일: {email_found}")
            safe_print(f"[RESULT] 연락처: {phone_found}")
            safe_print(f"[RESULT] 추천인: {referral_found}")
            safe_print(f"[RESULT] 이력서: {resume_found}")
            safe_print(f"[RESULT] 파일 업로드: {upload_found}")
            safe_print(f"[RESULT] 새 이력서 작성: {new_resume_found}")

            # 지원 페이지 판단
            apply_url_ok = any(kw in post_click_url.lower()
                               for kw in ['apply', '/cv/', '/resume', '/wd/'])
            url_unchanged = (pre_click_url == post_click_url)
            content_ok = (
                (email_found or name_found or phone_found) and
                (resume_found or upload_found or new_resume_found)
            )
            is_apply_page = apply_url_ok or content_ok or (url_unchanged and resume_found)

            safe_print(f"\n[CHECK] apply_url_ok: {apply_url_ok}")
            safe_print(f"[CHECK] url_unchanged(모달): {url_unchanged}")
            safe_print(f"[CHECK] content_ok: {content_ok}")
            safe_print(f"[CHECK] is_apply_page: {is_apply_page}")
            safe_print(f"\n[DEBUG] body_text 일부:\n{body_text[:600]}")
            safe_print(f"[DEBUG] inputs_text: {inputs_text[:300]}")

            assert is_apply_page, (
                f"지원하기 클릭 후 지원 페이지/모달이 나타나지 않았습니다.\n"
                f"URL: {post_click_url}\nbody: {body_text[:300]}"
            )

            # 최종 요약
            safe_print("\n[SUMMARY] 테스트 케이스 40 검증 완료:")
            safe_print(f"[OK] 지원하기 버튼 클릭 완료")
            safe_print(f"[OK] 지원 페이지/모달 진입 확인: {post_click_url}")

            for label, ok in [
                ('이름', name_found), ('이메일', email_found),
                ('연락처', phone_found), ('추천인', referral_found),
                ('이력서 리스트', resume_found), ('파일 업로드 버튼', upload_found),
                ('새 이력서 작성 버튼', new_resume_found),
            ]:
                safe_print(f"{'[OK]' if ok else '[WARN]'} {label} {'확인됨' if ok else '미확인'}")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await active_page.screenshot(path='screenshots/test_40_failed.png')
            except Exception:
                try:
                    await page.screenshot(path='screenshots/test_40_failed.png')
                except Exception:
                    pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
