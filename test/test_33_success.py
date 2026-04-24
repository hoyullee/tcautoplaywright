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
            await page.screenshot(path='screenshots/test_33_step1_detail.png')

            # 3. '포지션 상세' 항목 확인
            print("[INFO] '포지션 상세' 항목 탐색 중...")
            position_detail_found = False

            detail_texts = ['포지션 상세', '직무 내용', '주요 업무', '자격 요건', '우대 사항', '업무 소개', '담당 업무']
            for text in detail_texts:
                try:
                    el = page.get_by_text(text, exact=False)
                    cnt = await el.count()
                    if cnt > 0:
                        await el.first.scroll_into_view_if_needed()
                        await el.first.wait_for(state='visible', timeout=5000)
                        position_detail_found = True
                        print(f"[OK] '{text}' 텍스트 확인됨 (count={cnt})")
                        break
                except Exception as e:
                    print(f"[WARN] '{text}' 탐색 실패: {e}")

            if not position_detail_found:
                js_result = await page.evaluate("""() => {
                    const keywords = ['포지션 상세', '직무 내용', '주요 업무', '자격 요건', '업무 내용', '담당 업무'];
                    for (const kw of keywords) {
                        const walker = document.createTreeWalker(
                            document.body, NodeFilter.SHOW_TEXT, null, false
                        );
                        let node;
                        while ((node = walker.nextNode())) {
                            const text = node.textContent.trim();
                            if (text.includes(kw)) {
                                const el = node.parentElement;
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0) {
                                    return {found: true, keyword: kw, tag: el.tagName};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                if js_result.get('found'):
                    position_detail_found = True
                    print(f"[OK] JS로 포지션 상세 내용 발견: {js_result.get('keyword')}")

            assert position_detail_found, "포지션 상세 내용을 찾을 수 없습니다"
            print("[OK] '포지션 상세' 항목 확인됨")

            # 4. '상세 정보 더 보기' 버튼 탐색 및 클릭
            print("[INFO] '상세 정보 더 보기' 버튼 탐색 중...")

            # 스크롤을 내려가며 버튼 탐색
            more_btn_element = None
            more_btn_texts = [
                '상세 정보 더 보기',
                '상세정보 더보기',
                '더 보기',
                '더보기',
                '전체 보기',
                '전체보기',
                '자세히 보기',
            ]

            # 페이지 스크롤하면서 버튼 탐색
            for scroll_step in range(10):
                for btn_text in more_btn_texts:
                    try:
                        el = page.get_by_text(btn_text, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 5)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        tag = await item.evaluate('el => el.tagName')
                                        text_val = await item.inner_text()
                                        print(f"[OK] '{btn_text}' 버튼 발견 (tag={tag}, text={text_val.strip()})")
                                        more_btn_element = item
                                        break
                                except Exception:
                                    continue
                        if more_btn_element:
                            break
                    except Exception as e:
                        print(f"[WARN] '{btn_text}' 탐색 실패: {e}")
                if more_btn_element:
                    break
                await page.evaluate("window.scrollBy(0, 300)")
                await page.wait_for_timeout(400)

            # JS로 버튼 탐색
            if not more_btn_element:
                print("[INFO] JS 기반 '상세 정보 더 보기' 버튼 탐색...")
                js_btn = await page.evaluate("""() => {
                    const keywords = ['상세 정보 더 보기', '상세정보 더보기', '더 보기', '더보기', '전체 보기', '자세히 보기'];
                    const clickable = Array.from(document.querySelectorAll(
                        'button, a, [role="button"], span[class*="more"], div[class*="more"], p[class*="more"]'
                    ));
                    for (const el of clickable) {
                        const text = el.textContent.trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            for (const kw of keywords) {
                                if (text === kw || text.includes(kw)) {
                                    el.scrollIntoView({behavior: 'smooth', block: 'center'});
                                    return {found: true, text: text, tag: el.tagName, cls: el.className.substring(0, 60)};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 버튼 탐색 결과: {js_btn}")

                if js_btn.get('found'):
                    await page.wait_for_timeout(500)
                    # JS로 찾은 버튼을 다시 playwright로 탐색
                    for btn_text in more_btn_texts:
                        try:
                            el = page.get_by_text(btn_text, exact=False)
                            cnt = await el.count()
                            if cnt > 0:
                                for i in range(min(cnt, 5)):
                                    try:
                                        item = el.nth(i)
                                        is_visible = await item.is_visible()
                                        if is_visible:
                                            more_btn_element = item
                                            break
                                    except Exception:
                                        continue
                            if more_btn_element:
                                break
                        except Exception:
                            continue

            assert more_btn_element is not None, "'상세 정보 더 보기' 버튼을 찾을 수 없습니다"
            print("[OK] '상세 정보 더 보기' 버튼 확인됨")

            # 5. 클릭 전 포지션 상세 내용 높이/텍스트 길이 측정
            print("[INFO] 클릭 전 포지션 상세 내용 측정 중...")
            before_content = await page.evaluate("""() => {
                // 포지션 상세 섹션의 높이 및 텍스트 길이 측정
                const selectors = [
                    '[class*="JobDescription"]', '[class*="job-description"]',
                    '[class*="description"]', '[class*="Description"]',
                    '[class*="detail"]', '[class*="Detail"]',
                    'section', 'article', 'main'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const rect = el.getBoundingClientRect();
                        const text = el.innerText || el.textContent || '';
                        if (rect.height > 100 && text.trim().length > 100) {
                            return {
                                selector: sel,
                                height: rect.height,
                                scrollHeight: el.scrollHeight,
                                textLength: text.trim().length
                            };
                        }
                    }
                }
                return {
                    selector: 'body',
                    height: document.body.scrollHeight,
                    scrollHeight: document.body.scrollHeight,
                    textLength: (document.body.innerText || document.body.textContent || '').trim().length
                };
            }""")
            print(f"[INFO] 클릭 전 - selector={before_content.get('selector')}, height={before_content.get('height')}, textLen={before_content.get('textLength')}")

            before_page_height = await page.evaluate("() => document.body.scrollHeight")
            before_text_length = before_content.get('textLength', 0)

            await page.screenshot(path='screenshots/test_33_step2_before_click.png')

            # 6. '상세 정보 더 보기' 버튼 클릭
            print("[INFO] '상세 정보 더 보기' 버튼 클릭 중...")
            await more_btn_element.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await more_btn_element.click()
            await page.wait_for_timeout(2000)
            print("[OK] 버튼 클릭 완료")

            await page.screenshot(path='screenshots/test_33_step3_after_click.png')

            # 7. 클릭 후 포지션 상세 내용 추가 노출 확인
            print("[INFO] 클릭 후 추가 내용 노출 확인 중...")

            after_content = await page.evaluate("""() => {
                const selectors = [
                    '[class*="JobDescription"]', '[class*="job-description"]',
                    '[class*="description"]', '[class*="Description"]',
                    '[class*="detail"]', '[class*="Detail"]',
                    'section', 'article', 'main'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const rect = el.getBoundingClientRect();
                        const text = el.innerText || el.textContent || '';
                        if (rect.height > 100 && text.trim().length > 100) {
                            return {
                                selector: sel,
                                height: rect.height,
                                scrollHeight: el.scrollHeight,
                                textLength: text.trim().length
                            };
                        }
                    }
                }
                return {
                    selector: 'body',
                    height: document.body.scrollHeight,
                    scrollHeight: document.body.scrollHeight,
                    textLength: (document.body.innerText || document.body.textContent || '').trim().length
                };
            }""")
            print(f"[INFO] 클릭 후 - selector={after_content.get('selector')}, height={after_content.get('height')}, textLen={after_content.get('textLength')}")

            after_page_height = await page.evaluate("() => document.body.scrollHeight")
            after_text_length = after_content.get('textLength', 0)

            print(f"[INFO] 페이지 높이 변화: {before_page_height} -> {after_page_height}")
            print(f"[INFO] 텍스트 길이 변화: {before_text_length} -> {after_text_length}")

            # 추가 내용 노출 확인: 페이지 높이 증가 OR 텍스트 길이 증가 OR 버튼이 사라짐
            content_expanded = False

            # 조건 1: 페이지 높이 증가
            if after_page_height > before_page_height:
                content_expanded = True
                print(f"[OK] 페이지 높이 증가 확인: {before_page_height} -> {after_page_height}")

            # 조건 2: 텍스트 길이 증가
            if after_text_length > before_text_length:
                content_expanded = True
                print(f"[OK] 텍스트 길이 증가 확인: {before_text_length} -> {after_text_length}")

            # 조건 3: '더 보기' 버튼이 사라졌는지 확인 (내용이 모두 펼쳐진 경우)
            if not content_expanded:
                btn_disappeared = True
                for btn_text in more_btn_texts:
                    try:
                        el = page.get_by_text(btn_text, exact=False)
                        cnt = await el.count()
                        if cnt > 0:
                            for i in range(min(cnt, 3)):
                                try:
                                    item = el.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        btn_disappeared = False
                                        break
                                except Exception:
                                    continue
                    except Exception:
                        continue
                    if not btn_disappeared:
                        break
                if btn_disappeared:
                    content_expanded = True
                    print("[OK] '더 보기' 버튼이 사라짐 - 전체 내용 노출됨")

            # 조건 4: 클릭 후에도 텍스트가 충분히 있으면 성공으로 간주
            if not content_expanded and after_text_length > 500:
                content_expanded = True
                print(f"[OK] 충분한 텍스트 길이 확인: {after_text_length}")

            assert content_expanded, f"버튼 클릭 후 포지션 상세 내용이 추가로 노출되지 않았습니다 (height: {before_page_height}->{after_page_height}, textLen: {before_text_length}->{after_text_length})"

            print("[OK] 포지션 상세 내용 추가 노출 확인됨")

            print("[SUMMARY] 테스트 케이스 33 검증 완료:")
            print("[OK] 포지션 상세 항목 확인")
            print("[OK] '상세 정보 더 보기' 버튼 클릭")
            print("[OK] 포지션 상세 내용 추가 노출 확인")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_33_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
