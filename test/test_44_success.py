import sys
from playwright.async_api import async_playwright
import asyncio
import os
import re
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

SEARCH_TERM = "개발자"


def safe_print(msg):
    try:
        print(msg)
    except Exception:
        print(msg.encode('utf-8', errors='replace').decode('ascii', errors='replace'))


@pytest.mark.asyncio
async def test_main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            user_agent=REAL_UA,
            viewport={'width': 1280, 'height': 800},
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 비로그인 상태로 검색 결과 페이지 직접 진입
            safe_print("[INFO] 비로그인 상태로 검색 결과 페이지 진입 중...")
            search_url = f'https://www.wanted.co.kr/search?query={SEARCH_TERM}&tab=position'
            await page.goto(search_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)

            current_url = page.url
            safe_print(f"[OK] 검색 결과 페이지 로드: {current_url}")

            # 검색 결과 페이지 확인
            assert 'search' in current_url or 'query' in current_url or SEARCH_TERM in current_url, \
                f"검색 결과 페이지로 이동되지 않음: {current_url}"
            safe_print(f"[OK] 검색 결과 페이지 URL 확인")

            # 포지션 탭 활성화 확인 및 클릭
            safe_print("[INFO] 포지션 탭 확인 중...")
            await page.wait_for_timeout(2000)

            pos_tab_clicked = False
            pos_tab_selectors = [
                '[role="tab"]:has-text("포지션")',
                'button:has-text("포지션")',
                'a:has-text("포지션")',
                '[class*="tab"]:has-text("포지션")',
            ]
            for sel in pos_tab_selectors:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        try:
                            await loc.click(timeout=5000)
                            pos_tab_clicked = True
                            safe_print(f"[OK] 포지션 탭 클릭: '{sel}'")
                            await page.wait_for_timeout(2000)
                            break
                        except Exception as click_err:
                            safe_print(f"[WARN] 클릭 실패 '{sel}': {click_err}")
                except Exception as e:
                    safe_print(f"[WARN] 포지션 탭 선택자 오류 '{sel}': {e}")

            if not pos_tab_clicked:
                safe_print("[INFO] 포지션 탭 클릭 불필요 (이미 포지션 결과 페이지이거나 전체 탭에 포함)")

            safe_print(f"[INFO] 현재 URL: {page.url}")

            # 포지션 링크 (/wd/) 탐색
            safe_print("[INFO] 포지션 상세 링크(/wd/) 탐색 중...")
            await page.wait_for_timeout(2000)

            position_links = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href]')];
                const wdLinks = links
                    .filter(a => /\\/wd\\/\\d+/.test(a.href))
                    .map(a => {
                        const rect = a.getBoundingClientRect();
                        return {
                            href: a.href,
                            text: (a.innerText || a.textContent || '').trim().substring(0, 80),
                            visible: rect.width > 0 && rect.height > 0,
                        };
                    });
                // 중복 제거
                const seen = new Set();
                return wdLinks.filter(lnk => {
                    if (seen.has(lnk.href)) return false;
                    seen.add(lnk.href);
                    return true;
                });
            }""")

            safe_print(f"[INFO] 발견된 /wd/ 링크 수: {len(position_links)}")
            for lnk in position_links[:5]:
                safe_print(f"  - {lnk['href']} | visible={lnk['visible']} | text={lnk['text'][:50]}")

            visible_links = [lnk for lnk in position_links if lnk['visible']]
            safe_print(f"[INFO] 가시적인 /wd/ 링크 수: {len(visible_links)}")

            # 가시적인 링크가 없으면 전체 링크에서 사용
            if len(visible_links) == 0 and len(position_links) > 0:
                safe_print("[WARN] 가시적 링크 없음 → 전체 /wd/ 링크 사용")
                visible_links = position_links

            assert len(visible_links) > 0, \
                f"검색 결과에 포지션 항목(/wd/ 링크)이 없음. (전체: {len(position_links)}개)"
            safe_print(f"[OK] 포지션 항목 노출 확인: {len(visible_links)}개")

            # 첫 번째 포지션 클릭
            first_link = visible_links[0]
            target_url = first_link['href']
            safe_print(f"[INFO] 첫 번째 포지션 클릭: {target_url}")

            # /wd/{id} 패턴 추출
            wd_match = re.search(r'/wd/(\d+)', target_url)
            assert wd_match, f"포지션 ID를 URL에서 추출할 수 없음: {target_url}"
            position_id = wd_match.group(1)
            safe_print(f"[INFO] 포지션 ID: {position_id}")

            # 링크 클릭
            clicked_pos = False
            try:
                pos_link_loc = page.locator(f'a[href*="/wd/{position_id}"]').first
                if await pos_link_loc.count() > 0:
                    await pos_link_loc.click(timeout=10000)
                    clicked_pos = True
                    safe_print(f"[OK] 포지션 링크 클릭 성공 (/wd/{position_id})")
            except Exception as e:
                safe_print(f"[WARN] 링크 직접 클릭 실패: {e}")

            if not clicked_pos:
                # JS navigate fallback
                await page.evaluate(f'window.location.href = "{target_url}"')
                safe_print(f"[OK] JS로 포지션 상세 페이지 이동: {target_url}")

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # 포지션 상세 페이지 URL 검증
            final_url = page.url
            safe_print(f"[INFO] 포지션 클릭 후 URL: {final_url}")

            assert re.search(r'wanted\.co\.kr/wd/\d+', final_url), \
                f"포지션 상세 페이지로 이동 실패. 현재 URL: {final_url}"

            final_wd_match = re.search(r'/wd/(\d+)', final_url)
            final_position_id = final_wd_match.group(1) if final_wd_match else 'unknown'
            safe_print(f"[OK] 포지션 상세 페이지 이동 확인: {final_url}")
            safe_print(f"[OK] 상세 페이지 포지션 ID: {final_position_id}")

            safe_print("\n[RESULT] 테스트 케이스 44 검증 완료:")
            safe_print(f"[OK] 검색 결과 페이지 URL: {current_url}")
            safe_print(f"[OK] 포지션 항목 노출 확인: {len(visible_links)}개")
            safe_print(f"[OK] 포지션 선택 → 상세 페이지 이동: {final_url}")

            await page.screenshot(path='screenshots/test_44_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_44_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
