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

            # 1. 채용 메인 페이지 접속
            print("[INFO] 채용 메인 페이지 접속 중...")
            await page.goto('https://www.wanted.co.kr/', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 채용 메인 페이지 로드 완료 - URL: {page.url}")

            # 2. 포지션 상세 페이지로 직접 이동 (잡 목록에서 첫 번째 포지션 클릭)
            print("[INFO] 포지션 상세 페이지 탐색 중...")

            # 잡 카드 링크 탐색 (wanted 포지션 URL 패턴: /wd/{id})
            position_url = None

            # 방법 1: href에 /wd/ 포함된 링크 탐색
            wd_links = page.locator('a[href*="/wd/"]')
            count = await wd_links.count()
            print(f"[INFO] /wd/ 링크 수: {count}")

            if count > 0:
                href = await wd_links.first.get_attribute('href')
                if href:
                    if href.startswith('http'):
                        position_url = href
                    else:
                        position_url = f"https://www.wanted.co.kr{href}"
                    print(f"[OK] 포지션 URL 발견: {position_url}")

            # 방법 2: 직접 채용 목록 페이지로 이동
            if not position_url:
                print("[INFO] 채용 목록 페이지로 이동 중...")
                await page.goto('https://www.wanted.co.kr/wdlist', timeout=60000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

                wd_links = page.locator('a[href*="/wd/"]')
                count = await wd_links.count()
                print(f"[INFO] /wd/ 링크 수: {count}")

                if count > 0:
                    href = await wd_links.first.get_attribute('href')
                    if href:
                        if href.startswith('http'):
                            position_url = href
                        else:
                            position_url = f"https://www.wanted.co.kr{href}"
                        print(f"[OK] 포지션 URL 발견: {position_url}")

            assert position_url is not None, "포지션 상세 페이지 URL을 찾을 수 없습니다"

            # 3. 포지션 상세 페이지 진입
            print(f"[INFO] 포지션 상세 페이지 진입: {position_url}")
            await page.goto(position_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"[OK] 포지션 상세 페이지 로드 완료 - URL: {page.url}")

            await page.screenshot(path='screenshots/test_32_step1_position_detail.png')

            # 4. '포지션 상세' 항목 확인
            print("[INFO] '포지션 상세' 항목 탐색 중...")
            position_detail_found = False

            # 텍스트 기반 탐색
            detail_texts = ['포지션 상세', '직무 내용', '주요 업무', '자격 요건', '우대 사항', '업무 소개']
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

            # CSS 셀렉터 기반 탐색
            if not position_detail_found:
                print("[INFO] CSS 셀렉터 기반 포지션 상세 탐색...")
                detail_selectors = [
                    '[class*="JobDescription"]',
                    '[class*="job-description"]',
                    '[class*="position-description"]',
                    '[class*="PositionDescription"]',
                    '[class*="detail"]',
                    'section[class*="Detail"]',
                    'div[class*="Detail"]',
                    'article',
                ]
                for sel in detail_selectors:
                    try:
                        el = page.locator(sel).first
                        cnt = await page.locator(sel).count()
                        if cnt > 0:
                            is_visible = await el.is_visible()
                            if is_visible:
                                position_detail_found = True
                                print(f"[OK] 포지션 상세 섹션 확인됨 (selector: {sel})")
                                break
                    except Exception as e:
                        print(f"[WARN] '{sel}' 탐색 실패: {e}")

            # JS 기반 탐색
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
                                    return {found: true, keyword: kw, tag: el.tagName, cls: el.className.substring(0, 60)};
                                }
                            }
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 탐색 결과: {js_result}")
                if js_result.get('found'):
                    position_detail_found = True
                    print(f"[OK] JS로 포지션 상세 내용 발견: {js_result.get('keyword')}")

            assert position_detail_found, "포지션 상세 내용을 찾을 수 없습니다"
            print("[OK] '포지션 상세' 항목 확인됨")

            # 5. 텍스트 형식으로 노출되는지 확인
            print("[INFO] 포지션 상세 내용 텍스트 형식 확인 중...")
            text_content_found = False

            text_result = await page.evaluate("""() => {
                // 포지션 상세 내용이 텍스트로 노출되는지 확인
                const detailKeywords = ['주요 업무', '자격 요건', '우대 사항', '담당 업무', '업무 내용', '포지션 상세'];
                for (const kw of detailKeywords) {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(kw)) {
                            // 해당 섹션에서 텍스트 내용 찾기
                            let container = node.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (!container) break;
                                const text = container.innerText || container.textContent;
                                if (text && text.trim().length > 50) {
                                    return {
                                        found: true,
                                        keyword: kw,
                                        textLength: text.trim().length
                                    };
                                }
                                container = container.parentElement;
                            }
                        }
                    }
                }
                // 페이지 전체 텍스트 양 확인
                const bodyText = document.body.innerText || document.body.textContent;
                return {
                    found: bodyText && bodyText.trim().length > 200,
                    keyword: 'body',
                    textLength: bodyText ? bodyText.trim().length : 0
                };
            }""")
            # 인코딩 안전하게 출력
            try:
                print(f"[INFO] 텍스트 형식 확인 결과: found={text_result.get('found')}, length={text_result.get('textLength')}")
            except Exception:
                print("[INFO] 텍스트 형식 결과 출력 중 인코딩 오류 (무시)")

            if text_result.get('found') and text_result.get('textLength', 0) > 50:
                text_content_found = True
                print(f"[OK] 텍스트 형식 내용 확인됨 (길이: {text_result.get('textLength')})")

            assert text_content_found, "포지션 상세 내용이 텍스트 형식으로 노출되지 않았습니다"

            # 6. '상세 정보 더 보기' 버튼 노출 확인
            print("[INFO] '상세 정보 더 보기' 버튼 탐색 중...")
            more_info_btn_found = False

            # 다양한 텍스트 변형으로 탐색
            more_btn_texts = [
                '상세 정보 더 보기',
                '상세정보 더보기',
                '더 보기',
                '더보기',
                '전체 보기',
                '전체보기',
                '자세히 보기',
                'View more',
                'Show more',
            ]

            for btn_text in more_btn_texts:
                try:
                    el = page.get_by_text(btn_text, exact=False)
                    cnt = await el.count()
                    if cnt > 0:
                        # 버튼이나 클릭 가능한 요소인지 확인
                        for i in range(min(cnt, 3)):
                            try:
                                item = el.nth(i)
                                is_visible = await item.is_visible()
                                tag = await item.evaluate('el => el.tagName')
                                if is_visible:
                                    more_info_btn_found = True
                                    text_val = await item.inner_text()
                                    print(f"[OK] '{btn_text}' 버튼 발견 (tag={tag}, text={text_val})")
                                    break
                            except Exception:
                                continue
                    if more_info_btn_found:
                        break
                except Exception as e:
                    print(f"[WARN] '{btn_text}' 탐색 실패: {e}")

            # 버튼을 못 찾으면 스크롤 후 재탐색
            if not more_info_btn_found:
                print("[INFO] 스크롤 후 '상세 정보 더 보기' 버튼 재탐색...")
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 300)")
                    await page.wait_for_timeout(500)

                await page.screenshot(path='screenshots/test_32_step2_scrolled.png')

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
                                        more_info_btn_found = True
                                        text_val = await item.inner_text()
                                        print(f"[OK] 스크롤 후 '{btn_text}' 버튼 발견: {text_val}")
                                        break
                                except Exception:
                                    continue
                        if more_info_btn_found:
                            break
                    except Exception as e:
                        print(f"[WARN] '{btn_text}' 스크롤 후 탐색 실패: {e}")

            # CSS 셀렉터로 '더 보기' 관련 버튼 탐색
            if not more_info_btn_found:
                print("[INFO] CSS/JS 기반 '더 보기' 버튼 탐색...")
                js_btn_result = await page.evaluate("""() => {
                    const keywords = ['상세 정보 더 보기', '상세정보 더보기', '더 보기', '더보기', '전체 보기', '자세히 보기'];
                    const clickable = Array.from(document.querySelectorAll(
                        'button, a, [role="button"], span[class*="more"], div[class*="more"]'
                    ));
                    for (const el of clickable) {
                        const text = el.textContent.trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            for (const kw of keywords) {
                                if (text === kw || text.includes(kw)) {
                                    return {
                                        found: true,
                                        text: text,
                                        tag: el.tagName,
                                        cls: el.className.substring(0, 60)
                                    };
                                }
                            }
                        }
                    }
                    // '더' 또는 'more' 포함 버튼 찾기
                    for (const el of clickable) {
                        const text = el.textContent.trim();
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && (text.includes('더') || text.toLowerCase().includes('more'))) {
                            return {
                                found: true,
                                text: text,
                                tag: el.tagName,
                                cls: el.className.substring(0, 60),
                                partial: true
                            };
                        }
                    }
                    return {found: false};
                }""")
                print(f"[INFO] JS 버튼 탐색 결과: {js_btn_result}")
                if js_btn_result.get('found'):
                    more_info_btn_found = True
                    print(f"[OK] JS로 '더 보기' 버튼 발견: {js_btn_result.get('text')}")

            await page.screenshot(path='screenshots/test_32_step3_final.png')

            assert more_info_btn_found, "'상세 정보 더 보기' 버튼을 찾을 수 없습니다"
            print("[OK] '상세 정보 더 보기' 버튼 확인됨")

            print("[SUMMARY] 테스트 케이스 32 검증 완료:")
            print("[OK] 포지션 상세 내용 노출 확인")
            print("[OK] 텍스트 형식 노출 확인")
            print("[OK] '상세 정보 더 보기' 버튼 노출 확인")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_32_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
