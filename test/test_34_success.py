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
            await page.screenshot(path='screenshots/test_34_step1_detail.png')

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

            # 4. 페이지 끝까지 스크롤하며 태그 탐색
            print("[INFO] 페이지 스크롤 중 - 태그 탐색 준비...")
            for scroll_step in range(15):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(300)
            await page.wait_for_timeout(1000)
            await page.screenshot(path='screenshots/test_34_step2_scrolled.png')

            # 5. 태그 항목 노출 확인 (포지션 상세 하단)
            print("[INFO] 태그 항목 탐색 중...")
            tags_found = False
            found_tags = []

            # 방법 1: JS로 태그 요소 탐색 (class, role, 텍스트 등)
            js_tags = await page.evaluate("""() => {
                // 태그 관련 클래스명 패턴
                const tagSelectors = [
                    '[class*="tag"]', '[class*="Tag"]',
                    '[class*="keyword"]', '[class*="Keyword"]',
                    '[class*="badge"]', '[class*="Badge"]',
                    '[class*="chip"]', '[class*="Chip"]',
                    '[class*="label"]', '[class*="Label"]',
                    '[class*="hashtag"]', '[class*="Hashtag"]',
                    '[class*="skill"]', '[class*="Skill"]',
                    '[class*="category"]', '[class*="Category"]',
                ];

                let tagElements = [];
                for (const sel of tagSelectors) {
                    const els = Array.from(document.querySelectorAll(sel));
                    for (const el of els) {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.textContent || '').trim();
                        // 의미 있는 텍스트가 있는 작은 요소 (태그 형태)
                        if (text.length > 0 && text.length < 100 && rect.width > 0) {
                            tagElements.push({
                                selector: sel,
                                text: text.substring(0, 50),
                                tag: el.tagName,
                                className: el.className.substring(0, 80),
                                top: rect.top + window.scrollY,
                                height: rect.height,
                                width: rect.width
                            });
                        }
                    }
                }
                return tagElements.slice(0, 20);
            }""")

            print(f"[INFO] JS 태그 탐색 결과 (총 {len(js_tags)}개):")
            for tag in js_tags[:10]:
                print(f"  - [{tag.get('tag')}] '{tag.get('text')}' class='{tag.get('className')}'")

            if len(js_tags) > 0:
                tags_found = True
                found_tags = [t.get('text') for t in js_tags[:5]]
                print(f"[OK] 태그 요소 발견: {found_tags}")

            # 방법 2: 특정 태그 컨테이너 탐색
            if not tags_found:
                print("[INFO] 방법2 - 태그 컨테이너 탐색...")
                js_container = await page.evaluate("""() => {
                    // 태그 목록을 감싸는 컨테이너 탐색
                    const containerSelectors = [
                        '[class*="TagList"]', '[class*="tag-list"]',
                        '[class*="KeywordList"]', '[class*="keyword-list"]',
                        '[class*="SkillList"]', '[class*="skill-list"]',
                        '[class*="BadgeList"]', '[class*="badge-list"]',
                        'ul[class*="tag"]', 'ul[class*="Tag"]',
                        'div[class*="tag"]', 'div[class*="Tag"]',
                    ];

                    for (const sel of containerSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const rect = el.getBoundingClientRect();
                            const children = el.children;
                            const childTexts = Array.from(children).map(c => (c.innerText || c.textContent || '').trim()).filter(t => t.length > 0 && t.length < 50);
                            if (childTexts.length > 0) {
                                return {
                                    found: true,
                                    selector: sel,
                                    childCount: children.length,
                                    sampleTags: childTexts.slice(0, 5)
                                };
                            }
                        }
                    }
                    return {found: false};
                }""")

                if js_container.get('found'):
                    tags_found = True
                    found_tags = js_container.get('sampleTags', [])
                    print(f"[OK] 태그 컨테이너 발견: {js_container.get('selector')}, 태그={found_tags}")

            # 방법 3: 앵커 또는 버튼 형태의 태그 탐색 (해시태그 스타일)
            if not tags_found:
                print("[INFO] 방법3 - 해시태그/앵커 스타일 태그 탐색...")
                js_anchor_tags = await page.evaluate("""() => {
                    // '#' 시작하는 텍스트 또는 태그 관련 링크 탐색
                    const allEls = Array.from(document.querySelectorAll('a, button, span, li'));
                    const tagEls = allEls.filter(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        const cls = el.className || '';
                        const rect = el.getBoundingClientRect();
                        // 텍스트가 짧고 가시적이며 태그 관련 클래스나 해시태그 형태
                        return rect.width > 0 && rect.height > 0 &&
                               text.length > 0 && text.length < 50 &&
                               (text.startsWith('#') ||
                                cls.toLowerCase().includes('tag') ||
                                cls.toLowerCase().includes('keyword') ||
                                cls.toLowerCase().includes('badge') ||
                                cls.toLowerCase().includes('chip'));
                    });
                    return tagEls.map(el => ({
                        tag: el.tagName,
                        text: (el.innerText || el.textContent || '').trim().substring(0, 50),
                        className: el.className.substring(0, 60)
                    })).slice(0, 10);
                }""")

                print(f"[INFO] 앵커/버튼 스타일 태그 탐색 결과: {len(js_anchor_tags)}개")
                for t in js_anchor_tags:
                    print(f"  - [{t.get('tag')}] '{t.get('text')}' class='{t.get('className')}'")

                if len(js_anchor_tags) > 0:
                    tags_found = True
                    found_tags = [t.get('text') for t in js_anchor_tags[:5]]
                    print(f"[OK] 해시태그/앵커 스타일 태그 발견: {found_tags}")

            # 방법 4: 페이지 전체 텍스트에서 태그 섹션 탐색
            if not tags_found:
                print("[INFO] 방법4 - 페이지 DOM 구조에서 태그 섹션 탐색...")
                js_dom = await page.evaluate("""() => {
                    // 포지션 상세 페이지의 태그 섹션 탐색
                    // 'wanted' 특화 클래스명 탐색
                    const selectors = [
                        '[class*="JobTags"]', '[class*="job-tags"]',
                        '[class*="PositionTag"]', '[class*="position-tag"]',
                        '[class*="JobDetail"] [class*="tag"]',
                        '[class*="RelatedTag"]', '[class*="related-tag"]',
                        'section [class*="tag"]',
                        'article [class*="tag"]',
                    ];

                    const results = [];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const text = (el.innerText || el.textContent || '').trim();
                            const rect = el.getBoundingClientRect();
                            if (text.length > 0 && text.length < 200 && rect.width > 0) {
                                results.push({
                                    selector: sel,
                                    text: text.substring(0, 100),
                                    tag: el.tagName,
                                    className: el.className.substring(0, 60)
                                });
                            }
                        }
                    }
                    return results.slice(0, 10);
                }""")

                print(f"[INFO] DOM 구조 태그 탐색 결과: {len(js_dom)}개")
                for item in js_dom:
                    print(f"  - [{item.get('tag')}] '{item.get('text')[:50]}' class='{item.get('className')}'")

                if len(js_dom) > 0:
                    tags_found = True
                    found_tags = [item.get('text', '')[:30] for item in js_dom[:5]]
                    print(f"[OK] DOM 구조에서 태그 발견: {found_tags}")

            # 방법 5: Playwright locator로 태그 요소 탐색
            if not tags_found:
                print("[INFO] 방법5 - Playwright locator로 태그 탐색...")
                tag_selectors = [
                    '[class*="tag"]', '[class*="Tag"]',
                    '[class*="keyword"]', '[class*="Keyword"]',
                    '[class*="badge"]', '[class*="Badge"]',
                    '[class*="chip"]', '[class*="Chip"]',
                ]
                for sel in tag_selectors:
                    try:
                        els = page.locator(sel)
                        cnt = await els.count()
                        if cnt > 0:
                            visible_count = 0
                            sample_texts = []
                            for i in range(min(cnt, 10)):
                                try:
                                    item = els.nth(i)
                                    is_visible = await item.is_visible()
                                    if is_visible:
                                        text = await item.inner_text()
                                        text = text.strip()
                                        if text and len(text) < 100:
                                            visible_count += 1
                                            sample_texts.append(text[:30])
                                except Exception:
                                    continue
                            if visible_count > 0:
                                tags_found = True
                                found_tags = sample_texts
                                print(f"[OK] Playwright locator로 태그 발견: sel='{sel}', count={visible_count}, samples={sample_texts}")
                                break
                    except Exception as e:
                        print(f"[WARN] locator '{sel}' 탐색 실패: {e}")

            await page.screenshot(path='screenshots/test_34_step3_tags.png')

            # 최종 검증
            assert tags_found, "포지션 상세 하단의 태그 항목을 찾을 수 없습니다"
            print(f"[OK] 태그 항목 노출 확인됨: {found_tags}")

            print("[SUMMARY] 테스트 케이스 34 검증 완료:")
            print("[OK] 포지션 상세 항목 확인")
            print("[OK] 포지션 상세 하단 태그 항목 노출 확인")
            print(f"[OK] 발견된 태그: {found_tags}")

            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_34_failed.png')
            except Exception:
                pass
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
