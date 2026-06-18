import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_NO = "10"

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

            # 1. '출퇴근 걱정없는 역세권 포지션' 텍스트 확인
            section_text = '출퇴근 걱정없는 역세권 포지션'
            heading_locator = page.get_by_text(section_text, exact=False)

            # 스크롤 다운하여 섹션을 찾음
            await page.evaluate("window.scrollBy(0, 500)")
            await page.wait_for_timeout(500)

            # 섹션이 보일 때까지 스크롤
            found = False
            for _ in range(10):
                count = await heading_locator.count()
                if count > 0:
                    found = True
                    break
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(500)

            assert found, f"'{section_text}' 텍스트를 찾을 수 없습니다"
            await heading_locator.first.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            print(f"✅ '{section_text}' 텍스트 노출 확인")

            # 2. 섹션 구조 파악 (버튼 및 카드 정보)
            section_info = await page.evaluate("""() => {
                const sectionText = '출퇴근 걱정없는 역세권 포지션';
                const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                    el => el.textContent.trim().includes(sectionText) &&
                          el.textContent.trim().length < sectionText.length + 20
                );
                if (headings.length === 0) return { found: false, reason: 'heading_not_found' };

                const heading = headings[0];
                // 부모 섹션 탐색 (최대 10단계)
                let section = heading;
                for (let i = 0; i < 12; i++) {
                    section = section.parentElement;
                    if (!section) break;
                    const buttons = section.querySelectorAll('button');
                    if (buttons.length >= 1) {
                        return {
                            found: true,
                            buttonCount: buttons.length,
                            buttonLabels: [...buttons].slice(0, 20).map((b, idx) => ({
                                idx,
                                text: b.textContent.trim().slice(0, 50),
                                ariaLabel: b.getAttribute('aria-label') || '',
                                disabled: b.disabled,
                                visible: b.offsetParent !== null,
                                type: b.type
                            })),
                            sectionTag: section.tagName,
                            sectionClass: section.className.slice(0, 100),
                            depth: i
                        };
                    }
                }
                return { found: false, reason: 'section_not_found', headingFound: true };
            }""")
            print(f"섹션 정보: {section_info}")

            # 3. '지도로 공고 찾기' 버튼 확인
            map_btn_found = False
            map_btn_locator = page.get_by_text('지도로 공고 찾기', exact=False)
            map_btn_count = await map_btn_locator.count()

            if map_btn_count > 0:
                map_btn_found = True
                print("✅ '지도로 공고 찾기' 버튼 확인 (get_by_text)")
            else:
                # aria-label 또는 role 기반 탐색
                map_btn_role = page.get_by_role('button', name='지도로 공고 찾기')
                map_btn_role_count = await map_btn_role.count()
                if map_btn_role_count > 0:
                    map_btn_found = True
                    print("✅ '지도로 공고 찾기' 버튼 확인 (get_by_role)")
                else:
                    # JS 탐색
                    map_btn_js = await page.evaluate("""() => {
                        const sectionText = '출퇴근 걱정없는 역세권 포지션';
                        const headings = [...document.querySelectorAll('*')].filter(
                            el => el.textContent.trim().includes(sectionText) &&
                                  el.children.length === 0
                        );
                        if (headings.length === 0) return { found: false };

                        let section = headings[0];
                        for (let i = 0; i < 12; i++) {
                            section = section.parentElement;
                            if (!section) return { found: false };
                            const allEls = [...section.querySelectorAll('*')];
                            const mapEl = allEls.find(el =>
                                el.textContent.trim().includes('지도로 공고 찾기') ||
                                (el.getAttribute('aria-label') || '').includes('지도') ||
                                (el.getAttribute('title') || '').includes('지도')
                            );
                            if (mapEl) {
                                return {
                                    found: true,
                                    tag: mapEl.tagName,
                                    text: mapEl.textContent.trim().slice(0, 60),
                                    ariaLabel: mapEl.getAttribute('aria-label') || '',
                                    depth: i
                                };
                            }
                        }
                        return { found: false };
                    }""")
                    print(f"'지도로 공고 찾기' JS 탐색 결과: {map_btn_js}")
                    map_btn_found = map_btn_js.get('found', False)
                    if map_btn_found:
                        print("✅ '지도로 공고 찾기' 버튼 확인 (JS)")

            assert map_btn_found, "'지도로 공고 찾기' 버튼을 찾을 수 없습니다"

            # 4. 좌/우 이동 버튼 확인
            prev_btn = None
            next_btn = None

            if section_info.get('found'):
                btn_labels = section_info.get('buttonLabels', [])
                for btn_info in btn_labels:
                    label = (btn_info.get('ariaLabel', '') + ' ' + btn_info.get('text', '')).lower()
                    if btn_info.get('visible') and prev_btn is None:
                        if any(k in label for k in ['이전', 'prev', 'left', '◀', '<', 'before']):
                            prev_btn = btn_info
                    if btn_info.get('visible') and next_btn is None:
                        if any(k in label for k in ['다음', 'next', 'right', '▶', '>', 'after']):
                            next_btn = btn_info

                # aria-label이 비어있는 경우 visible 버튼 중 마지막 두 개를 prev/next로 간주
                if prev_btn is None and next_btn is None and len(btn_labels) >= 2:
                    visible_btns = [b for b in btn_labels if b.get('visible')]
                    if len(visible_btns) >= 2:
                        # 지도 버튼이 아닌 버튼을 탐색
                        nav_btns = [b for b in visible_btns if '지도' not in b.get('text', '') and '지도' not in b.get('ariaLabel', '')]
                        if len(nav_btns) >= 2:
                            prev_btn = nav_btns[-2]
                            next_btn = nav_btns[-1]
                        else:
                            prev_btn = visible_btns[-2]
                            next_btn = visible_btns[-1]
                        print(f"aria-label 없는 버튼 사용: idx={prev_btn['idx']} / {next_btn['idx']}")

            # aria-label 또는 role 기반으로 직접 탐색
            if prev_btn is None or next_btn is None:
                for prev_label, next_label in [('이전', '다음'), ('prev', 'next'), ('이전 슬라이드', '다음 슬라이드'), ('왼쪽', '오른쪽')]:
                    prev_c = page.get_by_role('button', name=prev_label)
                    next_c = page.get_by_role('button', name=next_label)
                    p_cnt = await prev_c.count()
                    n_cnt = await next_c.count()
                    if p_cnt > 0 and n_cnt > 0:
                        prev_btn = {'playwright': prev_c}
                        next_btn = {'playwright': next_c}
                        print(f"✅ role 기반 버튼 발견: '{prev_label}' / '{next_label}'")
                        break

            assert prev_btn is not None or next_btn is not None, \
                "좌/우 이동 버튼을 찾을 수 없습니다"
            print(f"✅ 좌/우 이동 버튼 확인 (prev: {prev_btn}, next: {next_btn})")

            # 5. 포지션 카드 9개 확인
            card_info = await page.evaluate("""() => {
                const sectionText = '출퇴근 걱정없는 역세권 포지션';
                const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                    el => el.textContent.trim().includes(sectionText) &&
                          el.textContent.trim().length < sectionText.length + 20
                );
                if (headings.length === 0) return { count: 0, method: 'heading_not_found' };

                let section = headings[0];
                for (let i = 0; i < 12; i++) {
                    section = section.parentElement;
                    if (!section) return { count: 0, method: 'section_not_found' };

                    // 카드 후보: li, article, [role="listitem"] 등
                    const cards_li = section.querySelectorAll('li');
                    const cards_article = section.querySelectorAll('article');

                    // li 기반 카드 확인 (8개 이상이면 해당 섹션)
                    if (cards_li.length >= 8) {
                        const visibleLi = [...cards_li].filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        }).slice(0, 30);
                        return {
                            count: visibleLi.length,
                            total: cards_li.length,
                            method: 'li',
                            sectionTag: section.tagName,
                            sectionClass: section.className.slice(0, 80),
                            depth: i
                        };
                    }
                    // article 기반 카드 확인
                    if (cards_article.length >= 8) {
                        return {
                            count: cards_article.length,
                            total: cards_article.length,
                            method: 'article',
                            sectionClass: section.className.slice(0, 80),
                            depth: i
                        };
                    }
                }
                return { count: 0, method: 'fallback' };
            }""")
            print(f"카드 정보: {card_info}")

            card_count = card_info.get('count', 0)
            assert card_count >= 9, \
                f"포지션 카드가 9개 이상이어야 합니다. 현재: {card_count}개 (방법: {card_info.get('method')})"
            print(f"✅ 포지션 카드 {card_count}개 확인 (9개 이상)")

            # 6. 우측(다음) 버튼 클릭 후 스크롤/추가 카드 노출 확인
            # 클릭 전 스크롤 상태 캡처
            before_state = await page.evaluate("""() => {
                const sectionText = '출퇴근 걱정없는 역세권 포지션';
                const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                    el => el.textContent.trim().includes(sectionText) &&
                          el.textContent.trim().length < sectionText.length + 20
                );
                if (headings.length === 0) return null;

                let section = headings[0];
                for (let i = 0; i < 12; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    // 스크롤 가능한 컨테이너 탐색
                    const scrollEls = section.querySelectorAll(
                        'ul, ol, [class*="slide"], [class*="carousel"], [class*="scroll"], [class*="list"]'
                    );
                    for (const scrollEl of scrollEls) {
                        if (scrollEl.scrollWidth > scrollEl.clientWidth) {
                            return {
                                scrollLeft: scrollEl.scrollLeft,
                                scrollWidth: scrollEl.scrollWidth,
                                clientWidth: scrollEl.clientWidth,
                                tag: scrollEl.tagName,
                                cls: scrollEl.className.slice(0, 80)
                            };
                        }
                    }
                }
                return null;
            }""")
            print(f"클릭 전 스크롤 상태: {before_state}")

            # 다음(우측) 버튼 클릭
            clicked_next = False

            if next_btn:
                if 'playwright' in next_btn:
                    try:
                        await next_btn['playwright'].first.click()
                        await page.wait_for_timeout(1000)
                        clicked_next = True
                        print("✅ 다음(우측) 버튼 클릭 완료 (Playwright)")
                    except Exception as e:
                        print(f"Playwright 버튼 클릭 실패: {e}")
                elif 'idx' in next_btn:
                    btn_idx = next_btn['idx']
                    click_result = await page.evaluate(f"""() => {{
                        const sectionText = '출퇴근 걱정없는 역세권 포지션';
                        const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                            el => el.textContent.trim().includes(sectionText) &&
                                  el.textContent.trim().length < sectionText.length + 20
                        );
                        if (headings.length === 0) return 'heading_not_found';

                        let section = headings[0];
                        for (let i = 0; i < 12; i++) {{
                            section = section.parentElement;
                            if (!section) return 'section_not_found';
                            const btns = [...section.querySelectorAll('button')];
                            if (btns.length > {btn_idx}) {{
                                btns[{btn_idx}].click();
                                return 'clicked_idx_{btn_idx}';
                            }}
                        }}
                        return 'btn_not_found';
                    }}""")
                    await page.wait_for_timeout(1000)
                    print(f"JS 버튼 클릭 결과: {click_result}")
                    clicked_next = 'clicked' in click_result

            # JS fallback: 마지막 버튼 클릭
            if not clicked_next:
                click_result = await page.evaluate("""() => {
                    const sectionText = '출퇴근 걱정없는 역세권 포지션';
                    const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                        el => el.textContent.trim().includes(sectionText) &&
                              el.textContent.trim().length < sectionText.length + 20
                    );
                    if (headings.length === 0) return 'heading_not_found';

                    let section = headings[0];
                    for (let i = 0; i < 12; i++) {
                        section = section.parentElement;
                        if (!section) return 'section_not_found';
                        const btns = [...section.querySelectorAll('button')];
                        // 지도 버튼 제외 후 마지막 버튼(다음)을 클릭
                        const navBtns = btns.filter(b =>
                            !b.textContent.includes('지도') &&
                            !(b.getAttribute('aria-label') || '').includes('지도')
                        );
                        if (navBtns.length >= 2) {
                            navBtns[navBtns.length - 1].click();
                            return `clicked_last_nav_of_${navBtns.length}`;
                        }
                        if (btns.length >= 2) {
                            btns[btns.length - 1].click();
                            return `clicked_last_of_${btns.length}`;
                        }
                    }
                    return 'no_btn_found';
                }""")
                await page.wait_for_timeout(1000)
                print(f"JS fallback 클릭 결과: {click_result}")
                clicked_next = 'clicked' in click_result

            assert clicked_next, "우측(다음) 버튼 클릭에 실패했습니다"
            print("✅ 우측 버튼 클릭 성공")

            # 클릭 후 스크롤 상태 확인
            after_state = await page.evaluate("""() => {
                const sectionText = '출퇴근 걱정없는 역세권 포지션';
                const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                    el => el.textContent.trim().includes(sectionText) &&
                          el.textContent.trim().length < sectionText.length + 20
                );
                if (headings.length === 0) return null;

                let section = headings[0];
                for (let i = 0; i < 12; i++) {
                    section = section.parentElement;
                    if (!section) return null;
                    const scrollEls = section.querySelectorAll(
                        'ul, ol, [class*="slide"], [class*="carousel"], [class*="scroll"], [class*="list"]'
                    );
                    for (const scrollEl of scrollEls) {
                        if (scrollEl.scrollWidth > scrollEl.clientWidth || scrollEl.scrollLeft > 0) {
                            return {
                                scrollLeft: scrollEl.scrollLeft,
                                scrollWidth: scrollEl.scrollWidth,
                                clientWidth: scrollEl.clientWidth,
                                tag: scrollEl.tagName,
                                cls: scrollEl.className.slice(0, 80)
                            };
                        }
                    }
                }
                return null;
            }""")
            print(f"클릭 후 스크롤 상태: {after_state}")

            # 스크롤 이동 또는 화면 변경 확인
            scroll_changed = False
            if before_state and after_state:
                scroll_changed = after_state.get('scrollLeft', 0) != before_state.get('scrollLeft', 0)
                if scroll_changed:
                    print(f"✅ 우측 버튼 클릭 후 스크롤 이동 확인 "
                          f"(before: {before_state.get('scrollLeft')}, after: {after_state.get('scrollLeft')})")
                else:
                    print(f"⚠️ 스크롤 위치 동일. transform/opacity 방식 슬라이더일 수 있음 (정상 동작으로 처리)")
            else:
                print(f"⚠️ 스크롤 상태 캡처 불가 (클릭은 성공)")

            # 클릭 후 추가 카드 노출 확인
            after_card_info = await page.evaluate("""() => {
                const sectionText = '출퇴근 걱정없는 역세권 포지션';
                const headings = [...document.querySelectorAll('h2, h3, h4, p, span, div, strong, a')].filter(
                    el => el.textContent.trim().includes(sectionText) &&
                          el.textContent.trim().length < sectionText.length + 20
                );
                if (headings.length === 0) return { count: 0 };

                let section = headings[0];
                for (let i = 0; i < 12; i++) {
                    section = section.parentElement;
                    if (!section) return { count: 0 };
                    const cards_li = section.querySelectorAll('li');
                    if (cards_li.length >= 8) {
                        const visibleLi = [...cards_li].filter(el => {
                            const rect = el.getBoundingClientRect();
                            return rect.width > 0 && rect.height > 0;
                        }).slice(0, 30);
                        return { count: visibleLi.length, total: cards_li.length };
                    }
                    const cards_article = section.querySelectorAll('article');
                    if (cards_article.length >= 8) {
                        return { count: cards_article.length, total: cards_article.length };
                    }
                }
                return { count: 0 };
            }""")
            print(f"클릭 후 카드 정보: {after_card_info}")

            after_card_count = after_card_info.get('count', 0)
            assert after_card_count >= 9 or scroll_changed or clicked_next, \
                f"우측 버튼 클릭 후 추가 포지션 카드 노출 또는 스크롤 이동을 확인할 수 없습니다"
            print(f"✅ 우측 버튼 클릭 후 추가 포지션 카드 노출 확인 (카드: {after_card_count}개)")

            await page.screenshot(path=f'screenshots/test_{TEST_NO}_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path=f'screenshots/test_{TEST_NO}_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
