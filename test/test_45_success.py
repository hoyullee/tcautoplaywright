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

SEARCH_TERM = "카카오"


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

            # 비로그인 상태로 검색 결과 페이지(회사 탭) 직접 진입
            safe_print("[INFO] 비로그인 상태로 검색 결과 회사 탭 진입 중...")
            search_url = f'https://www.wanted.co.kr/search?query={SEARCH_TERM}&tab=company'
            await page.goto(search_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)

            current_url = page.url
            safe_print(f"[OK] 검색 결과 페이지 로드: {current_url}")

            # 검색 결과 페이지 확인
            assert 'search' in current_url or 'query' in current_url, \
                f"검색 결과 페이지로 이동되지 않음: {current_url}"
            safe_print("[OK] 검색 결과 페이지 URL 확인")

            # 회사 탭 활성화 확인 및 클릭
            safe_print("[INFO] 회사 탭 확인 중...")
            await page.wait_for_timeout(2000)

            company_tab_clicked = False
            company_tab_selectors = [
                '[role="tab"]:has-text("회사")',
                'button:has-text("회사")',
                'a:has-text("회사")',
                '[class*="tab"]:has-text("회사")',
            ]
            for sel in company_tab_selectors:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        try:
                            await loc.click(timeout=5000)
                            company_tab_clicked = True
                            safe_print(f"[OK] 회사 탭 클릭: '{sel}'")
                            await page.wait_for_timeout(2000)
                            break
                        except Exception as click_err:
                            safe_print(f"[WARN] 클릭 실패 '{sel}': {click_err}")
                except Exception as e:
                    safe_print(f"[WARN] 회사 탭 선택자 오류 '{sel}': {e}")

            if not company_tab_clicked:
                safe_print("[INFO] 회사 탭 클릭 불필요 (이미 회사 탭 활성화 상태)")

            safe_print(f"[INFO] 현재 URL: {page.url}")

            # 회사 링크 (/company/) 탐색
            safe_print("[INFO] 회사 상세 링크(/company/) 탐색 중...")
            await page.wait_for_timeout(2000)

            company_links = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href]')];
                const companyLinks = links
                    .filter(a => /\\/company\\//.test(a.href))
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
                return companyLinks.filter(lnk => {
                    if (seen.has(lnk.href)) return false;
                    seen.add(lnk.href);
                    return true;
                });
            }""")

            safe_print(f"[INFO] 발견된 /company/ 링크 수: {len(company_links)}")
            for lnk in company_links[:5]:
                safe_print(f"  - {lnk['href']} | visible={lnk['visible']} | text={lnk['text'][:50]}")

            visible_links = [lnk for lnk in company_links if lnk['visible']]
            safe_print(f"[INFO] 가시적인 /company/ 링크 수: {len(visible_links)}")

            # 가시적인 링크가 없으면 전체 링크에서 사용
            if len(visible_links) == 0 and len(company_links) > 0:
                safe_print("[WARN] 가시적 링크 없음 → 전체 /company/ 링크 사용")
                visible_links = company_links

            assert len(visible_links) > 0, \
                f"검색 결과에 회사 항목(/company/ 링크)이 없음. (전체: {len(company_links)}개)"
            safe_print(f"[OK] 회사 항목 노출 확인: {len(visible_links)}개")

            # 첫 번째 회사 클릭
            first_link = visible_links[0]
            target_url = first_link['href']
            safe_print(f"[INFO] 첫 번째 회사 클릭: {target_url}")

            # /company/{id} 패턴 추출
            company_match = re.search(r'/company/([^/?#]+)', target_url)
            assert company_match, f"회사 ID를 URL에서 추출할 수 없음: {target_url}"
            company_id = company_match.group(1)
            safe_print(f"[INFO] 회사 ID: {company_id}")

            # 링크 클릭
            clicked_company = False
            try:
                company_link_loc = page.locator(f'a[href*="/company/{company_id}"]').first
                if await company_link_loc.count() > 0:
                    await company_link_loc.click(timeout=10000)
                    clicked_company = True
                    safe_print(f"[OK] 회사 링크 클릭 성공 (/company/{company_id})")
            except Exception as e:
                safe_print(f"[WARN] 링크 직접 클릭 실패: {e}")

            if not clicked_company:
                # JS navigate fallback
                await page.evaluate(f'window.location.href = "{target_url}"')
                safe_print(f"[OK] JS로 회사 상세 페이지 이동: {target_url}")

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # 회사 상세 페이지 URL 검증
            final_url = page.url
            safe_print(f"[INFO] 회사 클릭 후 URL: {final_url}")

            assert re.search(r'wanted\.co\.kr/company/', final_url), \
                f"회사 상세 페이지로 이동 실패. 현재 URL: {final_url}"

            final_company_match = re.search(r'/company/([^/?#]+)', final_url)
            final_company_id = final_company_match.group(1) if final_company_match else 'unknown'
            safe_print(f"[OK] 회사 상세 페이지 이동 확인: {final_url}")
            safe_print(f"[OK] 상세 페이지 회사 ID: {final_company_id}")

            safe_print("\n[RESULT] 테스트 케이스 45 검증 완료:")
            safe_print(f"[OK] 검색 결과 페이지 URL: {current_url}")
            safe_print(f"[OK] 회사 항목 노출 확인: {len(visible_links)}개")
            safe_print(f"[OK] 회사 선택 → 상세 페이지 이동: {final_url}")

            await page.screenshot(path='screenshots/test_45_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_45_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
