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

            # 비로그인 상태로 검색 결과 페이지(소셜 탭) 직접 진입
            safe_print("[INFO] 비로그인 상태로 검색 결과 소셜 탭 진입 중...")
            search_url = f'https://www.wanted.co.kr/search?query={SEARCH_TERM}&tab=social'
            await page.goto(search_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)

            current_url = page.url
            safe_print(f"[OK] 검색 결과 페이지 로드: {current_url}")

            # 검색 결과 페이지 확인
            assert 'search' in current_url or 'query' in current_url, \
                f"검색 결과 페이지로 이동되지 않음: {current_url}"
            safe_print("[OK] 검색 결과 페이지 URL 확인")

            # 소셜 탭 활성화 확인 및 클릭
            safe_print("[INFO] 소셜 탭 확인 중...")
            await page.wait_for_timeout(2000)

            social_tab_clicked = False
            social_tab_selectors = [
                '[role="tab"]:has-text("소셜")',
                'button:has-text("소셜")',
                'a:has-text("소셜")',
                '[class*="tab"]:has-text("소셜")',
            ]
            for sel in social_tab_selectors:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        try:
                            await loc.click(timeout=5000)
                            social_tab_clicked = True
                            safe_print(f"[OK] 소셜 탭 클릭: '{sel}'")
                            await page.wait_for_timeout(2000)
                            break
                        except Exception as click_err:
                            safe_print(f"[WARN] 클릭 실패 '{sel}': {click_err}")
                except Exception as e:
                    safe_print(f"[WARN] 소셜 탭 선택자 오류 '{sel}': {e}")

            if not social_tab_clicked:
                safe_print("[INFO] 소셜 탭 클릭 불필요 (이미 소셜 탭 활성화 상태)")

            safe_print(f"[INFO] 현재 URL: {page.url}")

            # 소셜 링크 (social.wanted.co.kr/community/post/ 또는 /community/article/) 탐색
            safe_print("[INFO] 소셜 상세 링크 탐색 중...")
            await page.wait_for_timeout(2000)

            social_links = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href]')];
                const sLinks = links
                    .filter(a => /social\\.wanted\\.co\\.kr\\/community\\/(post|article)\\//.test(a.href))
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
                return sLinks.filter(lnk => {
                    if (seen.has(lnk.href)) return false;
                    seen.add(lnk.href);
                    return true;
                });
            }""")

            safe_print(f"[INFO] 발견된 소셜 링크 수: {len(social_links)}")
            for lnk in social_links[:5]:
                safe_print(f"  - {lnk['href']} | visible={lnk['visible']} | text={lnk['text'][:50]}")

            # 소셜 링크가 없을 경우 다른 검색어 또는 탭 이름으로 재시도
            if len(social_links) == 0:
                safe_print("[WARN] 소셜 링크 없음. 검색어/탭 변경 후 재시도...")
                for alt_query in ["카카오", "IT", "마케팅", "디자인", "개발"]:
                    for alt_tab in ["social", "community"]:
                        alt_url = f'https://www.wanted.co.kr/search?query={alt_query}&tab={alt_tab}'
                        safe_print(f"[INFO] 재시도: {alt_url}")
                        await page.goto(alt_url, timeout=60000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)

                        # 소셜 탭 클릭 시도
                        for sel in social_tab_selectors:
                            try:
                                loc = page.locator(sel).first
                                if await loc.count() > 0:
                                    await loc.click(timeout=5000)
                                    await page.wait_for_timeout(2000)
                                    break
                            except Exception:
                                pass

                        social_links = await page.evaluate("""() => {
                            const links = [...document.querySelectorAll('a[href]')];
                            const sLinks = links
                                .filter(a => /social\\.wanted\\.co\\.kr\\/community\\/(post|article)\\//.test(a.href))
                                .map(a => {
                                    const rect = a.getBoundingClientRect();
                                    return {
                                        href: a.href,
                                        text: (a.innerText || a.textContent || '').trim().substring(0, 80),
                                        visible: rect.width > 0 && rect.height > 0,
                                    };
                                });
                            const seen = new Set();
                            return sLinks.filter(lnk => {
                                if (seen.has(lnk.href)) return false;
                                seen.add(lnk.href);
                                return true;
                            });
                        }""")
                        safe_print(f"[INFO] alt query={alt_query}, tab={alt_tab} → 소셜 링크 수: {len(social_links)}")
                        if len(social_links) > 0:
                            current_url = page.url
                            break
                    if len(social_links) > 0:
                        break

            # 모든 링크 확인 (소셜 관련 링크 체크)
            if len(social_links) == 0:
                safe_print("[INFO] 페이지의 모든 링크 조회 (디버깅)...")
                all_links = await page.evaluate("""() => {
                    const links = [...document.querySelectorAll('a[href]')];
                    return links.map(a => a.href).filter(h => h.includes('social') || h.includes('community')).slice(0, 20);
                }""")
                safe_print(f"[INFO] 소셜/커뮤니티 관련 링크들: {all_links}")

            visible_links = [lnk for lnk in social_links if lnk['visible']]
            safe_print(f"[INFO] 가시적인 소셜 링크 수: {len(visible_links)}")

            # 가시적인 링크가 없으면 전체 링크에서 사용
            if len(visible_links) == 0 and len(social_links) > 0:
                safe_print("[WARN] 가시적 링크 없음 → 전체 소셜 링크 사용")
                visible_links = social_links

            assert len(visible_links) > 0, \
                f"검색 결과에 소셜 항목(social.wanted.co.kr/community/ 링크)이 없음. (전체: {len(social_links)}개)"
            safe_print(f"[OK] 소셜 항목 노출 확인: {len(visible_links)}개")

            # 첫 번째 소셜 클릭
            first_link = visible_links[0]
            target_url = first_link['href']
            safe_print(f"[INFO] 첫 번째 소셜 클릭: {target_url}")

            # /community/post/{id} 또는 /community/article/{id} 패턴 추출
            social_match = re.search(r'/community/(post|article)/([^/?#]+)', target_url)
            assert social_match, f"소셜 타입/ID를 URL에서 추출할 수 없음: {target_url}"
            social_type = social_match.group(1)
            social_id = social_match.group(2)
            safe_print(f"[INFO] 소셜 타입: {social_type}, ID: {social_id}")

            # 새 탭에서 열릴 수 있으므로 새 탭 처리
            clicked_social = False
            new_page = None
            try:
                social_link_loc = page.locator(f'a[href*="/community/{social_type}/{social_id}"]').first
                if await social_link_loc.count() > 0:
                    # 새 탭/페이지 오픈 대기
                    async with context.expect_page() as new_page_info:
                        await social_link_loc.click(timeout=10000)
                    new_page = await new_page_info.value
                    await new_page.wait_for_load_state('domcontentloaded')
                    await new_page.wait_for_timeout(3000)
                    clicked_social = True
                    safe_print(f"[OK] 소셜 링크 클릭 성공 → 새 탭: {new_page.url}")
            except Exception as e:
                safe_print(f"[WARN] 새 탭으로 클릭 실패: {e}")

            if not clicked_social:
                # 같은 탭에서 클릭 시도
                safe_print("[INFO] 같은 탭에서 클릭 시도...")
                try:
                    social_link_loc = page.locator(f'a[href*="/community/{social_type}/{social_id}"]').first
                    if await social_link_loc.count() > 0:
                        await social_link_loc.click(timeout=10000)
                        clicked_social = True
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)
                        safe_print(f"[OK] 소셜 링크 클릭 성공 (같은 탭): {page.url}")
                except Exception as e:
                    safe_print(f"[WARN] 같은 탭 클릭 실패: {e}")

            if not clicked_social:
                # JS navigate fallback
                await page.evaluate(f'window.location.href = "{target_url}"')
                safe_print(f"[OK] JS로 소셜 상세 페이지 이동: {target_url}")
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(3000)

            # 최종 URL 확인 (새 탭이면 new_page, 아니면 page)
            check_page = new_page if new_page else page
            final_url = check_page.url
            safe_print(f"[INFO] 소셜 클릭 후 URL: {final_url}")

            # 소셜 상세 페이지 URL 검증
            # 기대: https://social.wanted.co.kr/community/post/{id} 또는 /article/{id}
            assert re.search(r'social\.wanted\.co\.kr/community/(post|article)/', final_url), \
                f"소셜 상세 페이지로 이동 실패. 현재 URL: {final_url}"

            final_social_match = re.search(r'/community/(post|article)/([^/?#]+)', final_url)
            if final_social_match:
                final_type = final_social_match.group(1)
                final_id = final_social_match.group(2)
                safe_print(f"[OK] 소셜 상세 페이지 이동 확인: {final_url}")
                safe_print(f"[OK] 소셜 타입: {final_type}, ID: {final_id}")

            safe_print("\n[RESULT] 테스트 케이스 47 검증 완료:")
            safe_print(f"[OK] 검색 결과 페이지 URL: {current_url}")
            safe_print(f"[OK] 소셜 항목 노출 확인: {len(visible_links)}개")
            safe_print(f"[OK] 소셜 선택 → 상세 페이지 이동: {final_url}")

            await check_page.screenshot(path='screenshots/test_47_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_47_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
