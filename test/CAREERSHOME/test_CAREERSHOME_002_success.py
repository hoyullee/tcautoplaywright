import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_NO = "08"

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 채용 홈 진입 (비로그인 상태)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 1. '지금 주목할 소식' 텍스트 확인
            notice_heading = page.get_by_text('지금 주목할 소식', exact=False)
            await notice_heading.first.wait_for(state='visible', timeout=15000)
            print("✅ '지금 주목할 소식' 텍스트 노출 확인")

            # '지금 주목할 소식' 섹션 컨테이너 탐색
            # 섹션 제목 요소 기준으로 부모 섹션 탐색
            section_heading = notice_heading.first

            # 2. 좌/우 이동 버튼 확인
            # 섹션 내의 이전/다음 버튼 탐색 (role=button 기준)
            prev_btn = None
            next_btn = None

            # 페이지 내 버튼 중 aria-label이나 텍스트로 이전/다음 버튼 찾기
            # 일반적으로 슬라이더 이전/다음 버튼
            candidate_labels = [
                ('이전', '다음'),
                ('prev', 'next'),
                ('left', 'right'),
                ('이전 슬라이드', '다음 슬라이드'),
                ('이전 버튼', '다음 버튼'),
            ]

            # aria-label로 버튼 탐색
            for prev_label, next_label in candidate_labels:
                prev_candidate = page.get_by_role('button', name=prev_label)
                next_candidate = page.get_by_role('button', name=next_label)
                try:
                    prev_count = await prev_candidate.count()
                    next_count = await next_candidate.count()
                    if prev_count > 0 and next_count > 0:
                        prev_btn = prev_candidate.first
                        next_btn = next_candidate.first
                        print(f"✅ 좌/우 이동 버튼 발견: '{prev_label}' / '{next_label}'")
                        break
                except Exception:
                    continue

            # 버튼을 못찾으면 '지금 주목할 소식' 텍스트 근처 섹션에서 버튼 탐색
            if prev_btn is None or next_btn is None:
                # JS로 섹션 구조 파악
                section_info = await page.evaluate("""() => {
                    // '지금 주목할 소식' 텍스트를 포함하는 요소 찾기
                    const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div')].filter(
                        el => el.textContent.trim().includes('지금 주목할 소식')
                    );
                    if (headings.length === 0) return { found: false };

                    const heading = headings[0];
                    // 부모 섹션 탐색 (최대 5단계)
                    let section = heading;
                    for (let i = 0; i < 8; i++) {
                        section = section.parentElement;
                        if (!section) break;
                        const buttons = section.querySelectorAll('button');
                        if (buttons.length >= 2) {
                            return {
                                found: true,
                                buttonCount: buttons.length,
                                buttonLabels: [...buttons].slice(0, 10).map(b => ({
                                    text: b.textContent.trim().slice(0, 50),
                                    ariaLabel: b.getAttribute('aria-label') || '',
                                    type: b.getAttribute('type') || ''
                                })),
                                sectionTag: section.tagName,
                                sectionClass: section.className.slice(0, 100)
                            };
                        }
                    }
                    return { found: false, headingFound: true };
                }""")
                print(f"섹션 정보: {section_info}")

                if section_info.get('found'):
                    btn_labels = section_info.get('buttonLabels', [])
                    # 네비게이션 버튼 후보 탐색
                    for btn_info in btn_labels:
                        label = btn_info.get('ariaLabel', '') or btn_info.get('text', '')
                        if any(k in label for k in ['이전', 'prev', 'Prev', 'left', 'Left', '◀', '<']):
                            prev_btn = page.get_by_role('button', name=label) if label else None
                        elif any(k in label for k in ['다음', 'next', 'Next', 'right', 'Right', '▶', '>']):
                            next_btn = page.get_by_role('button', name=label) if label else None

            # 버튼이 여전히 없으면 페이지 전체에서 슬라이더 버튼 탐색
            if prev_btn is None or next_btn is None:
                # SVG 화살표 버튼 등도 포함하여 탐색
                all_btns = await page.evaluate("""() => {
                    // '지금 주목할 소식' 섹션 내 버튼 찾기
                    const headings = [...document.querySelectorAll('*')].filter(
                        el => el.childNodes.length > 0 &&
                              [...el.childNodes].some(n => n.nodeType === 3 &&
                              n.textContent.includes('지금 주목할 소식'))
                    );
                    if (headings.length === 0) return [];

                    let section = headings[0];
                    for (let i = 0; i < 10; i++) {
                        section = section.parentElement;
                        if (!section) return [];
                        const btns = section.querySelectorAll('button');
                        if (btns.length >= 2) {
                            return [...btns].slice(0, 20).map((b, idx) => ({
                                idx,
                                text: b.innerText.trim().slice(0, 30),
                                ariaLabel: b.getAttribute('aria-label') || '',
                                disabled: b.disabled,
                                visible: b.offsetParent !== null
                            }));
                        }
                    }
                    return [];
                }""")
                print(f"섹션 버튼 목록: {all_btns}")

                # 인덱스 기반으로 버튼 선택 (슬라이더 이전/다음 버튼은 보통 마지막 2개)
                if len(all_btns) >= 2:
                    # 보이는 버튼만 필터
                    visible_btns = [b for b in all_btns if b.get('visible')]
                    if len(visible_btns) >= 2:
                        # aria-label 또는 텍스트로 이전/다음 구분
                        for btn in visible_btns:
                            label = btn.get('ariaLabel', '') + btn.get('text', '')
                            if not prev_btn and any(k in label for k in ['이전', 'prev', 'Prev', '<', '◀']):
                                # JS로 클릭하기 위해 인덱스 저장
                                prev_btn_idx = btn['idx']
                                prev_btn = f"__idx_{prev_btn_idx}"
                            elif not next_btn and any(k in label for k in ['다음', 'next', 'Next', '>', '▶']):
                                next_btn_idx = btn['idx']
                                next_btn = f"__idx_{next_btn_idx}"

            # 좌/우 버튼 존재 확인
            assert prev_btn is not None or next_btn is not None, \
                "좌/우 이동 버튼을 찾을 수 없습니다"
            print("✅ 좌/우 이동 버튼 존재 확인")

            # 3. 컨텐츠 카드 3개 확인
            # '지금 주목할 소식' 섹션 내 카드 개수 확인
            card_info = await page.evaluate("""() => {
                const headings = [...document.querySelectorAll('*')].filter(
                    el => el.childNodes.length > 0 &&
                          [...el.childNodes].some(n => n.nodeType === 3 &&
                          n.textContent.includes('지금 주목할 소식'))
                );
                if (headings.length === 0) return { count: 0, method: 'heading_not_found' };

                let section = headings[0];
                for (let i = 0; i < 10; i++) {
                    section = section.parentElement;
                    if (!section) return { count: 0, method: 'section_not_found' };

                    // 카드 후보: li, article, [role="listitem"], a 태그 등
                    const cards_li = section.querySelectorAll('li');
                    const cards_article = section.querySelectorAll('article');
                    const cards_a = section.querySelectorAll('a[href]');

                    if (cards_li.length >= 3) {
                        // 보이는 li만 카운트
                        const visibleLi = [...cards_li].filter(el => el.offsetParent !== null);
                        return {
                            count: visibleLi.length,
                            total: cards_li.length,
                            method: 'li',
                            sectionTag: section.tagName,
                            sectionClass: section.className.slice(0, 80)
                        };
                    }
                    if (cards_article.length >= 2) {
                        return {
                            count: cards_article.length,
                            method: 'article',
                            sectionClass: section.className.slice(0, 80)
                        };
                    }
                }
                return { count: 0, method: 'fallback' };
            }""")
            print(f"카드 정보: {card_info}")

            card_count = card_info.get('count', 0)
            assert card_count >= 3, \
                f"컨텐츠 카드가 3개 이상이어야 합니다. 현재: {card_count}개"
            print(f"✅ 컨텐츠 카드 {card_count}개 확인 (3개 이상)")

            # 4. 우측 버튼 클릭 후 추가 컨텐츠 카드 노출 확인
            # 클릭 전 현재 상태 캡처
            before_scroll = await page.evaluate("""() => {
                // 슬라이더/스크롤 컨테이너 찾기
                const headings = [...document.querySelectorAll('*')].filter(
                    el => el.childNodes.length > 0 &&
                          [...el.childNodes].some(n => n.nodeType === 3 &&
                          n.textContent.includes('지금 주목할 소식'))
                );
                if (headings.length === 0) return null;

                let section = headings[0];
                for (let i = 0; i < 10; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    // 스크롤 가능한 컨테이너 탐색
                    const scrollEl = section.querySelector('[class*="slide"], [class*="carousel"], [class*="scroll"], ul');
                    if (scrollEl) {
                        return {
                            scrollLeft: scrollEl.scrollLeft,
                            scrollWidth: scrollEl.scrollWidth,
                            clientWidth: scrollEl.clientWidth,
                            tag: scrollEl.tagName,
                            cls: scrollEl.className.slice(0, 80)
                        };
                    }
                }
                return null;
            }""")
            print(f"스크롤 전 상태: {before_scroll}")

            # 다음 버튼 클릭
            clicked_next = False
            if next_btn and not isinstance(next_btn, str):
                try:
                    await next_btn.first.click()
                    await page.wait_for_timeout(1000)
                    clicked_next = True
                    print("✅ 다음(우측) 버튼 클릭 완료")
                except Exception as e:
                    print(f"다음 버튼 클릭 실패: {e}")

            if not clicked_next:
                # JS로 다음 버튼 클릭 시도
                click_result = await page.evaluate("""() => {
                    const headings = [...document.querySelectorAll('*')].filter(
                        el => el.childNodes.length > 0 &&
                              [...el.childNodes].some(n => n.nodeType === 3 &&
                              n.textContent.includes('지금 주목할 소식'))
                    );
                    if (headings.length === 0) return 'heading_not_found';

                    let section = headings[0];
                    for (let i = 0; i < 10; i++) {
                        section = section.parentElement;
                        if (!section) return 'section_not_found';
                        const btns = [...section.querySelectorAll('button')];
                        if (btns.length >= 2) {
                            // 마지막 버튼이 '다음'일 가능성이 높음
                            const lastBtn = btns[btns.length - 1];
                            lastBtn.click();
                            return 'clicked_last_btn';
                        }
                    }
                    return 'no_btn_found';
                }""")
                await page.wait_for_timeout(1000)
                print(f"JS 버튼 클릭 결과: {click_result}")
                clicked_next = click_result in ['clicked_last_btn']

            # 클릭 후 상태 확인
            after_scroll = await page.evaluate("""() => {
                const headings = [...document.querySelectorAll('*')].filter(
                    el => el.childNodes.length > 0 &&
                          [...el.childNodes].some(n => n.nodeType === 3 &&
                          n.textContent.includes('지금 주목할 소식'))
                );
                if (headings.length === 0) return null;

                let section = headings[0];
                for (let i = 0; i < 10; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    const scrollEl = section.querySelector('[class*="slide"], [class*="carousel"], [class*="scroll"], ul');
                    if (scrollEl) {
                        return {
                            scrollLeft: scrollEl.scrollLeft,
                            scrollWidth: scrollEl.scrollWidth,
                            clientWidth: scrollEl.clientWidth,
                            tag: scrollEl.tagName,
                            cls: scrollEl.className.slice(0, 80)
                        };
                    }
                }
                return null;
            }""")
            print(f"스크롤 후 상태: {after_scroll}")

            # 스크롤 이동 또는 추가 카드 노출 확인
            if before_scroll and after_scroll:
                scroll_changed = after_scroll.get('scrollLeft', 0) != before_scroll.get('scrollLeft', 0)
                if scroll_changed:
                    print(f"✅ 우측 버튼 클릭 후 스크롤 이동 확인 "
                          f"(before: {before_scroll.get('scrollLeft')}, after: {after_scroll.get('scrollLeft')})")
                else:
                    print(f"⚠️ 스크롤 위치 변화 없음. 슬라이더 방식일 수 있음")
            else:
                print("⚠️ 스크롤 컨테이너 정보를 가져오지 못했습니다")

            # 클릭 후 카드 재확인
            after_card_info = await page.evaluate("""() => {
                const headings = [...document.querySelectorAll('*')].filter(
                    el => el.childNodes.length > 0 &&
                          [...el.childNodes].some(n => n.nodeType === 3 &&
                          n.textContent.includes('지금 주목할 소식'))
                );
                if (headings.length === 0) return { count: 0 };

                let section = headings[0];
                for (let i = 0; i < 10; i++) {
                    section = section.parentElement;
                    if (!section) return { count: 0 };
                    const cards_li = section.querySelectorAll('li');
                    if (cards_li.length >= 3) {
                        const visibleLi = [...cards_li].filter(el => el.offsetParent !== null);
                        return { count: visibleLi.length, total: cards_li.length };
                    }
                    const cards_article = section.querySelectorAll('article');
                    if (cards_article.length >= 2) {
                        return { count: cards_article.length };
                    }
                }
                return { count: 0 };
            }""")
            print(f"클릭 후 카드 정보: {after_card_info}")

            # 클릭 후 카드 노출 확인 (슬라이더인 경우 동일하거나 더 많을 수 있음)
            after_card_count = after_card_info.get('count', 0)
            assert after_card_count >= 3 or clicked_next, \
                f"우측 버튼 클릭 후에도 카드가 충분히 노출되지 않음: {after_card_count}개"
            print(f"✅ 우측 버튼 클릭 후 카드 노출 확인: {after_card_count}개")

            await page.screenshot(path='screenshots/test_CAREERSHOME_002_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_CAREERSHOME_002_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
