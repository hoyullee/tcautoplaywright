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
            for _ in range(15):
                await page.evaluate("window.scrollBy(0, 400)")
                await page.wait_for_timeout(400)

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

            await page.screenshot(path='screenshots/test_13_step1_scroll.png')

            # '모두가 주목하고 있어요!' 섹션 비노출 확인
            target_text = '모두가 주목하고 있어요!'
            print(f"[INFO] 로그인 상태에서 '{target_text}' 섹션 비노출 확인 중...")

            found_in_dom = await page.evaluate("""(text) => {
                const walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                let node;
                while ((node = walker.nextNode())) {
                    if (node.textContent.includes(text)) {
                        const el = node.parentElement;
                        const rect = el.getBoundingClientRect();
                        return {
                            found: true,
                            visible: rect.width > 0 && rect.height > 0,
                            tag: el.tagName,
                            cls: el.className.substring(0, 80),
                        };
                    }
                }
                return {found: false};
            }""", target_text)

            print(f"[INFO] DOM 탐색 결과: {found_in_dom}")

            section_visible = False
            if found_in_dom.get('found'):
                if found_in_dom.get('visible'):
                    section_visible = True
                    print(f"[WARN] '{target_text}' 텍스트가 DOM에 존재하고 visible 상태")
                else:
                    print(f"[OK] '{target_text}' 텍스트가 DOM에 있으나 불가시 상태 (비노출 처리됨)")
            else:
                print(f"[OK] '{target_text}' 텍스트가 DOM에 존재하지 않음")

            # Playwright get_by_text로 이중 확인
            try:
                el = page.get_by_text(target_text, exact=True)
                count = await el.count()
                if count > 0:
                    is_visible = await el.first.is_visible()
                    print(f"[INFO] get_by_text 결과: count={count}, visible={is_visible}")
                    if is_visible:
                        section_visible = True
                        print(f"[WARN] '{target_text}' 섹션이 visible 상태로 감지됨")
                    else:
                        print(f"[OK] '{target_text}' 섹션 존재하나 비가시 상태 (비노출 처리됨)")
                else:
                    print(f"[OK] get_by_text: '{target_text}' 요소 없음 (비노출 확인)")
            except Exception as e:
                print(f"[INFO] get_by_text 예외: {e}")

            await page.screenshot(path='screenshots/test_13_step2_check.png')

            assert not section_visible, (
                f"'{target_text}' 섹션이 로그인 상태에서 노출되고 있습니다. "
                "기대결과: 비노출"
            )

            print(f"[OK] '{target_text}' 섹션이 로그인 상태에서 비노출 확인됨")

            await page.screenshot(path='screenshots/test_13_success.png')
            print("[OK] 테스트 성공")
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            try:
                await page.screenshot(path='screenshots/test_13_failed.png')
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
