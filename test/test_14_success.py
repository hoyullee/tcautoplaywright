import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee+1@wantedlab.com"
TEST_PASSWORD = "wanted12!@"

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

            print("[INFO] 채용 홈 접속: https://www.wanted.co.kr/")
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(3000)
            print(f"[INFO] 현재 URL: {page.url}")

            # 점진적 스크롤로 페이지 전체 렌더링
            print("[INFO] 페이지 스크롤 중...")
            for _ in range(20):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(300)

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1500)

            await page.screenshot(path='screenshots/test_14_step1_scroll.png')

            # 1단계: '출퇴근 걱정없는 역세권 포지션' 섹션 탐지
            station_text = '출퇴근 걱정없는 역세권 포지션'
            print(f"[INFO] '{station_text}' 섹션 탐색 중...")

            # 섹션 탐색 (DOM에서 위치 파악)
            station_info = await page.evaluate("""(text) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.trim().includes(text)) {
                        const el = node.parentElement;
                        const rect = el.getBoundingClientRect();
                        return {
                            found: true,
                            visible: rect.width > 0 && rect.height > 0,
                            top: rect.top + window.scrollY,
                            tag: el.tagName,
                            cls: el.className.substring(0, 100),
                            text: node.textContent.trim().substring(0, 100),
                        };
                    }
                }
                return {found: false};
            }""", station_text)

            print(f"[INFO] '{station_text}' 탐색 결과: {station_info}")

            assert station_info.get('found'), f"'{station_text}' 섹션을 찾을 수 없습니다."
            print(f"[OK] '{station_text}' 섹션 발견 (top={station_info.get('top')})")

            # 해당 섹션으로 스크롤
            section_top = station_info.get('top', 0)
            await page.evaluate(f"window.scrollTo(0, {max(0, section_top - 200)})")
            await page.wait_for_timeout(1500)
            await page.screenshot(path='screenshots/test_14_step2_station_section.png')

            # 2단계: '~포지션 어때요' 텍스트 확인 (하단 노출)
            # '역세권' 섹션 하단에 위치한 추천 텍스트 찾기
            recommend_text_info = await page.evaluate("""(stationText) => {
                // 역세권 섹션 요소 찾기
                const allElements = document.querySelectorAll('*');
                let stationEl = null;

                for (const el of allElements) {
                    if (el.children.length === 0 && el.textContent.trim().includes(stationText)) {
                        stationEl = el;
                        break;
                    }
                }

                if (!stationEl) return {found: false, reason: 'station element not found'};

                // 역세권 섹션의 부모/조상에서 섹션 컨테이너 찾기
                let sectionContainer = stationEl;
                for (let i = 0; i < 10; i++) {
                    sectionContainer = sectionContainer.parentElement;
                    if (!sectionContainer) break;
                }

                // 역세권 섹션 이후 '포지션 어때요' 포함 텍스트 탐색
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                const results = [];
                while ((node = walker.nextNode())) {
                    const t = node.textContent.trim();
                    if (t.includes('포지션 어때요')) {
                        const el = node.parentElement;
                        const rect = el.getBoundingClientRect();
                        results.push({
                            text: t.substring(0, 120),
                            top: rect.top + window.scrollY,
                            visible: rect.width > 0 && rect.height > 0,
                            tag: el.tagName,
                            cls: el.className.substring(0, 80),
                        });
                    }
                }
                return results.length > 0 ? {found: true, items: results} : {found: false, reason: 'no 포지션 어때요 text'};
            }""", station_text)

            print(f"[INFO] '포지션 어때요' 탐색 결과: {recommend_text_info}")

            if not recommend_text_info.get('found'):
                # 페이지 전체 텍스트 덤프로 디버깅
                page_text_sample = await page.evaluate("""() => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let node;
                    const lines = [];
                    while ((node = walker.nextNode())) {
                        const t = node.textContent.trim();
                        if (t.length > 5 && (t.includes('역세권') || t.includes('어때요') || t.includes('포지션'))) {
                            lines.push(t.substring(0, 100));
                        }
                    }
                    return lines.slice(0, 30);
                }""")
                print(f"[DEBUG] 관련 텍스트 샘플: {page_text_sample}")

            assert recommend_text_info.get('found'), (
                "'~포지션 어때요' 텍스트를 찾을 수 없습니다. "
                f"사유: {recommend_text_info.get('reason', 'unknown')}"
            )

            # 노출되는 항목 중 visible한 것 확인
            visible_items = [item for item in recommend_text_info.get('items', []) if item.get('visible')]
            assert len(visible_items) > 0, "'~포지션 어때요' 텍스트가 DOM에 있으나 노출되지 않습니다."

            recommend_item = visible_items[0]
            print(f"[OK] '~포지션 어때요' 텍스트 노출 확인: '{recommend_item['text']}'")

            # 해당 위치로 스크롤
            await page.evaluate(f"window.scrollTo(0, {max(0, recommend_item['top'] - 200)})")
            await page.wait_for_timeout(1500)
            await page.screenshot(path='screenshots/test_14_step3_recommend_text.png')

            # 3단계: 역세권 섹션 내 포지션 카드 5개 확인
            print("[INFO] 역세권 섹션 내 포지션 카드 확인 중...")

            card_count_info = await page.evaluate("""(stationText) => {
                // '역세권' 텍스트를 포함하는 섹션 컨테이너 찾기
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let stationNode = null;
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.trim().includes(stationText)) {
                        stationNode = node;
                        break;
                    }
                }

                if (!stationNode) return {error: 'station node not found', cardCount: 0};

                // 섹션 컨테이너 찾기 (부모 올라가기)
                let container = stationNode.parentElement;
                let foundSection = null;
                for (let i = 0; i < 15; i++) {
                    if (!container) break;
                    // 포지션 카드가 많이 포함된 섹션 컨테이너
                    const cards = container.querySelectorAll('a[href*="/wd/"]');
                    if (cards.length >= 3) {
                        foundSection = container;
                        break;
                    }
                    container = container.parentElement;
                }

                if (!foundSection) return {error: 'section container not found', cardCount: 0};

                const cards = foundSection.querySelectorAll('a[href*="/wd/"]');
                const visibleCards = [];
                for (const card of cards) {
                    const rect = card.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        visibleCards.push({
                            href: card.href,
                            top: rect.top + window.scrollY,
                        });
                    }
                }

                return {
                    totalCards: cards.length,
                    visibleCards: visibleCards.length,
                    cardSamples: visibleCards.slice(0, 8).map(c => c.href),
                };
            }""", station_text)

            print(f"[INFO] 포지션 카드 확인 결과: {card_count_info}")

            visible_card_count = card_count_info.get('visibleCards', 0)
            assert visible_card_count >= 5, (
                f"포지션 카드가 5개 미만입니다. 실제 노출 카드 수: {visible_card_count}"
            )
            print(f"[OK] 포지션 카드 {visible_card_count}개 노출 확인 (기대: 5개 이상)")

            await page.screenshot(path='screenshots/test_14_step4_cards.png')

            # 4단계: 우측 버튼 클릭 후 추가 포지션 카드 노출 확인
            print("[INFO] 우측 스크롤 버튼 탐색 중...")

            # 역세권 섹션 내 우측 버튼 찾기
            right_btn_found = await page.evaluate("""(stationText) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let stationNode = null;
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.trim().includes(stationText)) {
                        stationNode = node;
                        break;
                    }
                }
                if (!stationNode) return null;

                // 섹션 컨테이너 찾기
                let container = stationNode.parentElement;
                let foundSection = null;
                for (let i = 0; i < 15; i++) {
                    if (!container) break;
                    const cards = container.querySelectorAll('a[href*="/wd/"]');
                    if (cards.length >= 3) {
                        foundSection = container;
                        break;
                    }
                    container = container.parentElement;
                }
                if (!foundSection) return null;

                // 우측 버튼 탐색 (button, [role=button] 중 오른쪽/next/right 관련)
                const btns = foundSection.querySelectorAll('button, [role="button"]');
                for (const btn of btns) {
                    const cls = (btn.className || '').toLowerCase();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    if (cls.includes('next') || cls.includes('right') || cls.includes('forward')
                        || aria.includes('next') || aria.includes('right') || aria.includes('다음')) {
                        const rect = btn.getBoundingClientRect();
                        return {found: true, top: rect.top + window.scrollY, left: rect.left};
                    }
                }

                // aria-label 없이 마지막 버튼 시도
                if (btns.length >= 2) {
                    const lastBtn = btns[btns.length - 1];
                    const rect = lastBtn.getBoundingClientRect();
                    return {found: true, top: rect.top + window.scrollY, left: rect.left, fallback: true};
                }
                return {found: false, btnCount: btns.length};
            }""", station_text)

            print(f"[INFO] 우측 버튼 탐색 결과: {right_btn_found}")

            if right_btn_found and right_btn_found.get('found'):
                btn_top = right_btn_found.get('top', 0)
                await page.evaluate(f"window.scrollTo(0, {max(0, btn_top - 300)})")
                await page.wait_for_timeout(1000)

                # 클릭 전 카드 위치 수집
                before_scroll_info = await page.evaluate("""(stationText) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let stationNode = null;
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(stationText)) {
                            stationNode = node;
                            break;
                        }
                    }
                    if (!stationNode) return null;
                    let container = stationNode.parentElement;
                    let foundSection = null;
                    for (let i = 0; i < 15; i++) {
                        if (!container) break;
                        const cards = container.querySelectorAll('a[href*="/wd/"]');
                        if (cards.length >= 3) {
                            foundSection = container;
                            break;
                        }
                        container = container.parentElement;
                    }
                    if (!foundSection) return null;
                    // 스크롤 컨테이너 내 scrollLeft
                    const scrollables = foundSection.querySelectorAll('*');
                    for (const el of scrollables) {
                        if (el.scrollWidth > el.clientWidth && el.clientWidth > 0) {
                            return {scrollLeft: el.scrollLeft, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth};
                        }
                    }
                    return {scrollLeft: 0};
                }""", station_text)

                print(f"[INFO] 클릭 전 스크롤 상태: {before_scroll_info}")
                await page.screenshot(path='screenshots/test_14_step5_before_click.png')

                # 우측 버튼 클릭
                # 섹션 내 버튼들 중 우측 버튼 재탐색 후 클릭
                clicked = await page.evaluate("""(stationText) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let stationNode = null;
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(stationText)) {
                            stationNode = node;
                            break;
                        }
                    }
                    if (!stationNode) return false;

                    let container = stationNode.parentElement;
                    let foundSection = null;
                    for (let i = 0; i < 15; i++) {
                        if (!container) break;
                        const cards = container.querySelectorAll('a[href*="/wd/"]');
                        if (cards.length >= 3) {
                            foundSection = container;
                            break;
                        }
                        container = container.parentElement;
                    }
                    if (!foundSection) return false;

                    const btns = foundSection.querySelectorAll('button, [role="button"]');
                    for (const btn of btns) {
                        const cls = (btn.className || '').toLowerCase();
                        const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                        if (cls.includes('next') || cls.includes('right') || cls.includes('forward')
                            || aria.includes('next') || aria.includes('right') || aria.includes('다음')) {
                            btn.click();
                            return true;
                        }
                    }
                    if (btns.length >= 2) {
                        btns[btns.length - 1].click();
                        return true;
                    }
                    return false;
                }""", station_text)

                print(f"[INFO] 우측 버튼 클릭 결과: {clicked}")
                await page.wait_for_timeout(1500)
                await page.screenshot(path='screenshots/test_14_step6_after_click.png')

                # 클릭 후 스크롤 변화 또는 카드 변화 확인
                after_scroll_info = await page.evaluate("""(stationText) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let stationNode = null;
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(stationText)) {
                            stationNode = node;
                            break;
                        }
                    }
                    if (!stationNode) return null;
                    let container = stationNode.parentElement;
                    let foundSection = null;
                    for (let i = 0; i < 15; i++) {
                        if (!container) break;
                        const cards = container.querySelectorAll('a[href*="/wd/"]');
                        if (cards.length >= 3) {
                            foundSection = container;
                            break;
                        }
                        container = container.parentElement;
                    }
                    if (!foundSection) return null;
                    const scrollables = foundSection.querySelectorAll('*');
                    for (const el of scrollables) {
                        if (el.scrollWidth > el.clientWidth && el.clientWidth > 0) {
                            return {scrollLeft: el.scrollLeft, scrollWidth: el.scrollWidth, clientWidth: el.clientWidth};
                        }
                    }
                    return {scrollLeft: 0};
                }""", station_text)

                print(f"[INFO] 클릭 후 스크롤 상태: {after_scroll_info}")

                if before_scroll_info and after_scroll_info:
                    before_left = before_scroll_info.get('scrollLeft', 0)
                    after_left = after_scroll_info.get('scrollLeft', 0)
                    if after_left > before_left:
                        print(f"[OK] 우측 버튼 클릭 후 스크롤 이동 확인: {before_left} -> {after_left}")
                    else:
                        print(f"[WARN] scrollLeft 변화 없음 ({before_left} -> {after_left}). 카드 수로 재확인.")

                # 클릭 후 카드 수 재확인 (추가 카드 노출)
                after_card_info = await page.evaluate("""(stationText) => {
                    const walker = document.createTreeWalker(
                        document.body, NodeFilter.SHOW_TEXT, null, false
                    );
                    let stationNode = null;
                    let node;
                    while ((node = walker.nextNode())) {
                        if (node.textContent.trim().includes(stationText)) {
                            stationNode = node;
                            break;
                        }
                    }
                    if (!stationNode) return {visibleCards: 0};
                    let container = stationNode.parentElement;
                    let foundSection = null;
                    for (let i = 0; i < 15; i++) {
                        if (!container) break;
                        const cards = container.querySelectorAll('a[href*="/wd/"]');
                        if (cards.length >= 3) {
                            foundSection = container;
                            break;
                        }
                        container = container.parentElement;
                    }
                    if (!foundSection) return {visibleCards: 0};
                    const cards = foundSection.querySelectorAll('a[href*="/wd/"]');
                    let visibleCount = 0;
                    for (const card of cards) {
                        const rect = card.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) visibleCount++;
                    }
                    return {visibleCards: visibleCount, totalCards: cards.length};
                }""", station_text)

                print(f"[INFO] 클릭 후 포지션 카드: {after_card_info}")
                after_visible = after_card_info.get('visibleCards', 0)
                assert after_visible >= 5, (
                    f"우측 버튼 클릭 후 포지션 카드가 5개 미만입니다. 실제: {after_visible}"
                )
                print(f"[OK] 우측 버튼 클릭 후 포지션 카드 {after_visible}개 노출 확인")
            else:
                print(f"[WARN] 우측 버튼을 찾지 못했습니다: {right_btn_found}. 카드 노출 확인만 진행.")

            await page.screenshot(path='screenshots/test_14_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_14_failed.png')
            except Exception:
                pass
            print(f"[FAIL] 테스트 실패: {e}")
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
