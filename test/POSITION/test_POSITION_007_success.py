import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = ""
TEST_PASSWORD = ""

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        # 비로그인 상태 - 세션 파일 로드 없이 새 컨텍스트 생성
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지로 이동하여 첫 번째 포지션 카드 링크 추출
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"첫 번째 포지션 링크: {href}")

            # 포지션 상세 페이지로 직접 이동
            position_url = f"https://www.wanted.co.kr{href}"
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            print(f"포지션 상세 페이지 URL: {page.url}")

            # 페이지 스크롤하여 모든 섹션 로딩 유도
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight * 2 / 3)')
            await page.wait_for_timeout(1000)
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(2000)

            # 1. '근무지역' 항목 확인
            work_area_found = False
            try:
                work_area_label = page.get_by_text('근무지역', exact=True)
                count = await work_area_label.count()
                if count > 0:
                    print(f"Found '근무지역' label, count={count}")
                    work_area_found = True
            except Exception as e:
                print(f"'근무지역' via get_by_text: {e}")

            if not work_area_found:
                result = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    return { found: body.includes('근무지역') };
                }""")
                if result.get('found'):
                    work_area_found = True
                    print("'근무지역' text found in page body via JS")

            assert work_area_found, "'근무지역' 항목이 페이지에서 노출되지 않았습니다"
            print("✓ '근무지역' 항목 확인 완료")

            # 2. '이 포지션을 찾고 계셨나요?' 텍스트 확인 (비로그인 상태 추천 포지션 섹션)
            target_text = '이 포지션을 찾고 계셨나요?'
            recommendation_found = False

            # 방법 1: get_by_text로 탐색
            try:
                rec_locator = page.get_by_text(target_text, exact=False)
                count = await rec_locator.count()
                if count > 0:
                    is_visible = await rec_locator.first.is_visible()
                    text = await rec_locator.first.inner_text()
                    print(f"Found recommendation section text: '{text}', count={count}, visible={is_visible}")
                    if is_visible:
                        recommendation_found = True
            except Exception as e:
                print(f"'{target_text}' not found via get_by_text: {e}")

            # 방법 2: JS로 텍스트 탐색
            if not recommendation_found:
                result = await page.evaluate("""() => {
                    const body = document.body.innerText || '';
                    const hasText = body.includes('이 포지션을 찾고 계셨나요?') ||
                                    body.includes('이 포지션을 찾고 계셨나요');
                    const allEls = [...document.querySelectorAll('h2, h3, h4, strong, span, div, p')].slice(0, 300);
                    const matchEl = allEls.find(el => {
                        const text = el.innerText ? el.innerText.trim() : '';
                        return text.includes('이 포지션을 찾고 계셨나요');
                    });
                    return {
                        found: hasText,
                        elementFound: !!matchEl,
                        elementText: matchEl ? matchEl.innerText.trim().slice(0, 100) : '',
                        bodySnippet: body.slice(-1000)
                    };
                }""")
                print(f"JS search result: found={result.get('found')}, elementFound={result.get('elementFound')}, text='{result.get('elementText')}'")
                if result.get('found') or result.get('elementFound'):
                    recommendation_found = True
                    print(f"Found '{target_text}' via JS")

            # 방법 3: 추가 스크롤 후 재시도
            if not recommendation_found:
                await page.evaluate('window.scrollTo(0, 0)')
                await page.wait_for_timeout(500)
                # 천천히 스크롤
                for ratio in [0.2, 0.4, 0.6, 0.8, 1.0]:
                    await page.evaluate(f'window.scrollTo(0, document.body.scrollHeight * {ratio})')
                    await page.wait_for_timeout(800)
                    try:
                        rec_locator = page.get_by_text(target_text, exact=False)
                        count = await rec_locator.count()
                        if count > 0:
                            is_visible = await rec_locator.first.is_visible()
                            if is_visible:
                                recommendation_found = True
                                print(f"Found '{target_text}' at scroll ratio {ratio}")
                                break
                    except Exception:
                        pass

            assert recommendation_found, f"'{target_text}' 텍스트가 페이지에서 노출되지 않았습니다"
            print(f"✓ '{target_text}' 항목 텍스트 노출 확인 완료")

            # 3. 포지션 리스트 노출 확인
            position_list_found = False
            current_position_id = page.url.split('/wd/')[-1].split('?')[0]
            print(f"현재 포지션 ID: {current_position_id}")

            # 방법 1: 포지션 링크 직접 탐색
            try:
                position_links = page.locator('a[href^="/wd/"]')
                total_count = await position_links.count()
                other_positions = []
                for j in range(min(total_count, 30)):
                    link_href = await position_links.nth(j).get_attribute('href')
                    if link_href and current_position_id not in link_href:
                        other_positions.append(link_href)
                print(f"전체 /wd/ 링크 수: {total_count}, 다른 포지션 수: {len(other_positions)}")
                if len(other_positions) > 0:
                    position_list_found = True
            except Exception as e:
                print(f"Position links check error: {e}")

            # 방법 2: JS로 포지션 카드 확인
            if not position_list_found:
                result = await page.evaluate(f"""() => {{
                    const links = [...document.querySelectorAll('a[href^="/wd/"]')];
                    const otherLinks = links.filter(a => !a.href.includes('{current_position_id}'));
                    return {{
                        total: links.length,
                        others: otherLinks.length,
                        hrefs: otherLinks.slice(0, 5).map(a => a.href)
                    }};
                }}""")
                print(f"JS position check: {result}")
                if result.get('others', 0) > 0:
                    position_list_found = True

            assert position_list_found, "추천 포지션 하단의 포지션 리스트가 노출되지 않았습니다"
            print("✓ 포지션 리스트 노출 확인 완료")

            await page.screenshot(path='screenshots/test_49_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_49_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
