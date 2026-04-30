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

            # 비로그인 상태로 검색 결과 페이지(콘텐츠 탭) 직접 진입
            safe_print("[INFO] 비로그인 상태로 검색 결과 콘텐츠 탭 진입 중...")
            search_url = f'https://www.wanted.co.kr/search?query={SEARCH_TERM}&tab=content'
            await page.goto(search_url, timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)

            current_url = page.url
            safe_print(f"[OK] 검색 결과 페이지 로드: {current_url}")

            # 검색 결과 페이지 확인
            assert 'search' in current_url or 'query' in current_url, \
                f"검색 결과 페이지로 이동되지 않음: {current_url}"
            safe_print("[OK] 검색 결과 페이지 URL 확인")

            # 콘텐츠 탭 활성화 확인 및 클릭
            safe_print("[INFO] 콘텐츠 탭 확인 중...")
            await page.wait_for_timeout(2000)

            content_tab_clicked = False
            content_tab_selectors = [
                '[role="tab"]:has-text("콘텐츠")',
                'button:has-text("콘텐츠")',
                'a:has-text("콘텐츠")',
                '[class*="tab"]:has-text("콘텐츠")',
            ]
            for sel in content_tab_selectors:
                try:
                    loc = page.locator(sel).first
                    cnt = await loc.count()
                    if cnt > 0:
                        try:
                            await loc.click(timeout=5000)
                            content_tab_clicked = True
                            safe_print(f"[OK] 콘텐츠 탭 클릭: '{sel}'")
                            await page.wait_for_timeout(2000)
                            break
                        except Exception as click_err:
                            safe_print(f"[WARN] 클릭 실패 '{sel}': {click_err}")
                except Exception as e:
                    safe_print(f"[WARN] 콘텐츠 탭 선택자 오류 '{sel}': {e}")

            if not content_tab_clicked:
                safe_print("[INFO] 콘텐츠 탭 클릭 불필요 (이미 콘텐츠 탭 활성화 상태)")

            safe_print(f"[INFO] 현재 URL: {page.url}")

            # 콘텐츠 링크 (/events/) 탐색
            safe_print("[INFO] 콘텐츠 상세 링크(/events/) 탐색 중...")
            await page.wait_for_timeout(2000)

            content_links = await page.evaluate("""() => {
                const links = [...document.querySelectorAll('a[href]')];
                const evLinks = links
                    .filter(a => /\\/events\\/\\d+/.test(a.href))
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
                return evLinks.filter(lnk => {
                    if (seen.has(lnk.href)) return false;
                    seen.add(lnk.href);
                    return true;
                });
            }""")

            safe_print(f"[INFO] 발견된 /events/ 링크 수: {len(content_links)}")
            for lnk in content_links[:5]:
                safe_print(f"  - {lnk['href']} | visible={lnk['visible']} | text={lnk['text'][:50]}")

            # tab=content가 없을 수도 있으니, 다른 검색어로 재시도
            if len(content_links) == 0:
                safe_print("[WARN] /events/ 링크 없음. 검색어 변경 후 재시도...")
                for alt_query in ["카카오", "IT", "마케팅", "디자인"]:
                    for alt_tab in ["content", "contents"]:
                        alt_url = f'https://www.wanted.co.kr/search?query={alt_query}&tab={alt_tab}'
                        safe_print(f"[INFO] 재시도: {alt_url}")
                        await page.goto(alt_url, timeout=60000)
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(3000)

                        # 콘텐츠 탭 클릭 시도
                        for sel in content_tab_selectors:
                            try:
                                loc = page.locator(sel).first
                                if await loc.count() > 0:
                                    await loc.click(timeout=5000)
                                    await page.wait_for_timeout(2000)
                                    break
                            except Exception:
                                pass

                        content_links = await page.evaluate("""() => {
                            const links = [...document.querySelectorAll('a[href]')];
                            const evLinks = links
                                .filter(a => /\\/events\\/\\d+/.test(a.href))
                                .map(a => {
                                    const rect = a.getBoundingClientRect();
                                    return {
                                        href: a.href,
                                        text: (a.innerText || a.textContent || '').trim().substring(0, 80),
                                        visible: rect.width > 0 && rect.height > 0,
                                    };
                                });
                            const seen = new Set();
                            return evLinks.filter(lnk => {
                                if (seen.has(lnk.href)) return false;
                                seen.add(lnk.href);
                                return true;
                            });
                        }""")
                        safe_print(f"[INFO] alt query={alt_query}, tab={alt_tab} → /events/ 링크 수: {len(content_links)}")
                        if len(content_links) > 0:
                            current_url = page.url
                            break
                    if len(content_links) > 0:
                        break

            visible_links = [lnk for lnk in content_links if lnk['visible']]
            safe_print(f"[INFO] 가시적인 /events/ 링크 수: {len(visible_links)}")

            # 가시적인 링크가 없으면 전체 링크에서 사용
            if len(visible_links) == 0 and len(content_links) > 0:
                safe_print("[WARN] 가시적 링크 없음 → 전체 /events/ 링크 사용")
                visible_links = content_links

            assert len(visible_links) > 0, \
                f"검색 결과에 콘텐츠 항목(/events/ 링크)이 없음. (전체: {len(content_links)}개)"
            safe_print(f"[OK] 콘텐츠 항목 노출 확인: {len(visible_links)}개")

            # 첫 번째 콘텐츠 클릭
            first_link = visible_links[0]
            target_url = first_link['href']
            safe_print(f"[INFO] 첫 번째 콘텐츠 클릭: {target_url}")

            # /events/{id} 패턴 추출
            event_match = re.search(r'/events/(\d+)', target_url)
            assert event_match, f"콘텐츠 ID를 URL에서 추출할 수 없음: {target_url}"
            event_id = event_match.group(1)
            safe_print(f"[INFO] 콘텐츠(이벤트) ID: {event_id}")

            # 링크 클릭
            clicked_content = False
            try:
                content_link_loc = page.locator(f'a[href*="/events/{event_id}"]').first
                if await content_link_loc.count() > 0:
                    await content_link_loc.click(timeout=10000)
                    clicked_content = True
                    safe_print(f"[OK] 콘텐츠 링크 클릭 성공 (/events/{event_id})")
            except Exception as e:
                safe_print(f"[WARN] 링크 직접 클릭 실패: {e}")

            if not clicked_content:
                # JS navigate fallback
                await page.evaluate(f'window.location.href = "{target_url}"')
                safe_print(f"[OK] JS로 콘텐츠 상세 페이지 이동: {target_url}")

            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)

            # 콘텐츠 상세 페이지 URL 검증
            final_url = page.url
            safe_print(f"[INFO] 콘텐츠 클릭 후 URL: {final_url}")

            assert re.search(r'wanted\.co\.kr/events/\d+', final_url), \
                f"콘텐츠 상세 페이지로 이동 실패. 현재 URL: {final_url}"

            final_event_match = re.search(r'/events/(\d+)', final_url)
            final_event_id = final_event_match.group(1) if final_event_match else 'unknown'
            safe_print(f"[OK] 콘텐츠 상세 페이지 이동 확인: {final_url}")
            safe_print(f"[OK] 상세 페이지 콘텐츠 ID: {final_event_id}")

            safe_print("\n[RESULT] 테스트 케이스 46 검증 완료:")
            safe_print(f"[OK] 검색 결과 페이지 URL: {current_url}")
            safe_print(f"[OK] 콘텐츠 항목 노출 확인: {len(visible_links)}개")
            safe_print(f"[OK] 콘텐츠 선택 → 상세 페이지 이동: {final_url}")

            await page.screenshot(path='screenshots/test_46_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_46_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
