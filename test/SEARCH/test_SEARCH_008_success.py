import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest
import urllib.parse
import re

@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 1. 채용 홈 진입 (로그인 세션 사용)
            await page.goto('https://www.wanted.co.kr/', timeout=30000)
            await page.wait_for_load_state('load')
            await page.wait_for_timeout(2000)

            # 2. GNB 검색 버튼 클릭 → 검색 화면 전환
            search_btn = page.get_by_role('button', name='검색')
            await search_btn.wait_for(state='visible', timeout=10000)
            await search_btn.click()
            await page.wait_for_timeout(1500)

            # 3. 검색 입력창 확인
            search_input = page.locator('input[type="search"]')
            await search_input.wait_for(state='visible', timeout=10000)
            print("검색 화면 전환 확인 완료")

            # 4. 인기 검색어 항목 확인
            # evaluate() 대신 Playwright 로케이터 사용
            # 인기 검색어: 순위 번호가 포함된 a 태그들
            # 구조 탐색: "인기 검색어" 헤더 찾기
            popular_header = page.get_by_text('인기 검색어', exact=True)
            header_count = await popular_header.count()
            print(f"'인기 검색어' 헤더 수: {header_count}")

            if header_count == 0:
                popular_header = page.get_by_text('인기검색어', exact=True)
                header_count = await popular_header.count()
                print(f"'인기검색어' 헤더 수: {header_count}")

            assert header_count > 0, "'인기 검색어' 헤더를 찾을 수 없음"

            # 인기 검색어 목록 찾기 (a 태그들)
            # 검색 패널 내 모든 a 태그 수집
            all_links = page.locator('a').filter(has=page.locator(':visible'))
            link_count = await all_links.count()
            print(f"페이지 내 visible a 태그 수: {link_count}")

            # 인기 검색어 항목 찾기: href에 search 포함하고, 텍스트에 순위 숫자 포함
            popular_items = []
            for i in range(min(link_count, 100)):
                link = all_links.nth(i)
                try:
                    is_visible = await link.is_visible()
                    if not is_visible:
                        continue
                    link_text = (await link.inner_text()).strip()
                    link_href = await link.get_attribute('href') or ''
                    # 인기 검색어 패턴: 텍스트 첫 줄에 숫자(1-9)로 시작
                    lines = [l.strip() for l in link_text.split('\n') if l.strip()]
                    if lines and re.match(r'^[1-9]$', lines[0]):
                        popular_items.append({
                            'text': link_text,
                            'href': link_href,
                            'lines': lines,
                            'index': i
                        })
                except Exception:
                    continue

            print(f"인기 검색어 항목들: {popular_items[:5]}")
            assert len(popular_items) > 0, "인기 검색어 항목을 찾을 수 없음"
            print(f"✅ 인기 검색어 항목 확인 - {len(popular_items)}개 발견")

            # 첫 번째 인기 검색어 선택
            first_item = popular_items[0]
            lines = first_item['lines']
            # 순위(숫자)와 트렌드 기호 제거하고 검색어만 추출
            term_parts = [l for l in lines if not re.match(r'^[0-9]+$', l) and l not in ['-', '+', '↑', '↓', '→', '↔', 'NEW']]
            popular_term_text = term_parts[0] if term_parts else lines[1] if len(lines) > 1 else first_item['text']
            print(f"선택할 인기 검색어: rank={lines[0]}, term='{popular_term_text}'")

            # 5. 인기 검색어 클릭
            target_link = all_links.nth(first_item['index'])
            await target_link.click(timeout=10000)

            await page.wait_for_load_state('load', timeout=15000)
            await page.wait_for_timeout(2000)

            # 6. 검색 결과 페이지 확인
            final_url = page.url
            print(f"최종 URL: {final_url}")

            decoded_url = urllib.parse.unquote(final_url)
            is_search_result = (
                'search' in final_url.lower() or
                'query=' in final_url or
                'keyword=' in final_url or
                'q=' in final_url
            )

            is_term_in_url = (
                popular_term_text.lower() in decoded_url.lower() or
                urllib.parse.quote(popular_term_text) in final_url
            )

            print(f"검색 결과 URL 여부: {is_search_result}")
            print(f"검색어 URL 포함 여부: {is_term_in_url}")

            assert is_search_result, \
                f"검색 결과 페이지로 이동되지 않음. URL: {final_url}"

            print(f"✅ 인기 검색어 '{popular_term_text}'로 검색 결과 페이지 랜딩 확인: {final_url}")

            await page.screenshot(path='screenshots/test_60_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_60_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
