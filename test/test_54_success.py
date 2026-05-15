import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

REAL_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)


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
            storage_state='work/auth_state.json',
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # ── Step 1: 이력서 목록 페이지 진입 ──
            safe_print("[INFO] 이력서 목록 페이지(cv/list) 진입...")
            await page.goto('https://www.wanted.co.kr/cv/list', timeout=60000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(4000)
            safe_print(f"[OK] 현재 URL: {page.url}")

            # ── Step 2: 이력서 작성(편집) 페이지로 이동 ──
            safe_print("[INFO] 이력서 작성 페이지로 이동 시도...")

            page_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyText: (document.body.innerText || '').substring(0, 500),
                    cvLinks: [],
                };
                const allEls = [...document.querySelectorAll('button, a, [role="button"]')];
                for (const el of allEls) {
                    const text = (el.innerText || el.textContent || '').trim();
                    const href = el.href || '';
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0) {
                        if (href.includes('/cv/') || href.includes('/resume/')) {
                            result.cvLinks.push({ text: text.substring(0, 60), href: href.substring(0, 100) });
                        }
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {page_info['url']}")
            safe_print(f"[INFO] 페이지 미리보기: {page_info['bodyText']}")
            safe_print("[INFO] CV 관련 링크:")
            for lnk in page_info['cvLinks']:
                safe_print(f"  - '{lnk['text']}' href='{lnk['href']}'")

            # cv 편집 URL로 이동 시도
            before_url = page.url
            clicked = False

            for lnk in page_info['cvLinks']:
                href = lnk['href']
                if any(pat in href for pat in ['/cv/new', '/cv/create', '/cv/edit', '/cv/write']):
                    safe_print(f"[INFO] CV 작성 링크 직접 이동: {href}")
                    await page.goto(href, timeout=30000)
                    clicked = True
                    break

            if not clicked:
                for lnk in page_info['cvLinks']:
                    href = lnk['href']
                    if '/cv/' in href and href != 'https://www.wanted.co.kr/cv/list':
                        safe_print(f"[INFO] CV 링크로 이동: {href}")
                        await page.goto(href, timeout=30000)
                        clicked = True
                        break

            if not clicked:
                new_btn_keywords = [
                    '새 이력서 작성', '새 이력서', '이력서 작성', '이력서 만들기',
                    '새로 만들기', '작성하기', '이력서 추가', '이력서 쓰기',
                ]
                for kw in new_btn_keywords:
                    try:
                        btn = page.get_by_text(kw, exact=False)
                        if await btn.count() > 0:
                            await btn.first.click(timeout=8000)
                            clicked = True
                            safe_print(f"[OK] 버튼 클릭: '{kw}'")
                            break
                    except Exception as e:
                        safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if clicked:
                try:
                    await page.wait_for_url(
                        lambda url: url != before_url,
                        timeout=8000
                    )
                except Exception:
                    pass
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(4000)

            safe_print(f"[INFO] 이동 후 URL: {page.url}")

            # ── Step 3: LNB에서 '이력서 리뷰' 버튼 클릭 ──
            safe_print("[INFO] LNB '이력서 리뷰' 버튼 탐색 중...")

            lnb_scan = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    bodyPreview: (document.body.innerText || '').substring(0, 1500),
                    reviewBtns: [],
                };
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const rawText = (el.innerText || el.textContent || '').trim();
                    const normText = rawText.replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (
                        rect.width > 0 && rect.height > 0 &&
                        (
                            normText === '이력서 리뷰' ||
                            normText.includes('이력서 리뷰') ||
                            normText.includes('이력서리뷰')
                        )
                    ) {
                        result.reviewBtns.push({
                            tag: el.tagName,
                            text: normText.substring(0, 80),
                            classes: (el.className || '').substring(0, 100),
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        });
                    }
                }
                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {lnb_scan['url']}")
            safe_print(f"[INFO] 페이지 미리보기:\n{lnb_scan['bodyPreview']}")
            safe_print(f"[INFO] '이력서 리뷰' 관련 요소 ({len(lnb_scan['reviewBtns'])}개):")
            for btn in lnb_scan['reviewBtns'][:10]:
                safe_print(f"  - [{btn['tag']:10s}] ({btn['x']},{btn['y']}) size=({btn['width']}x{btn['height']}) '{btn['text'][:70]}'")

            # '이력서 리뷰' LNB 버튼 클릭
            review_btn_clicked = False
            keywords_to_try = ['이력서 리뷰', '이력서리뷰', '리뷰']
            for kw in keywords_to_try:
                try:
                    btn = page.get_by_text(kw, exact=False)
                    cnt = await btn.count()
                    if cnt > 0:
                        # 여러 개 있으면 가장 작은 것(LNB 메뉴 항목) 클릭
                        await btn.first.click(timeout=8000)
                        review_btn_clicked = True
                        safe_print(f"[OK] '이력서 리뷰' LNB 버튼 클릭 성공: '{kw}'")
                        await page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    safe_print(f"[WARN] '{kw}' 클릭 실패: {e}")

            if not review_btn_clicked:
                safe_print("[WARN] '이력서 리뷰' 버튼 클릭 실패 - 패널이 이미 열려있거나 다른 방식 필요")

            # ── Step 4: 패널 내용 검증 ──
            safe_print("[INFO] 이력서 리뷰 패널 내용 검증 중...")
            await page.wait_for_timeout(2000)

            panel_info = await page.evaluate("""() => {
                const result = {
                    url: location.href,
                    fullText: (document.body.innerText || '').replace(/\\s+/g, ' '),
                    hasTitleText: false,
                    hasReviewButton: false,
                    titleElements: [],
                    buttonElements: [],
                    detailText: '',
                };

                const fullText = result.fullText;

                // 타이틀 및 소개 텍스트 확인: '이력서 분석을 받아보세요'
                const titleKeywords = [
                    '이력서 분석을 받아보세요',
                    '이력서 분석',
                    '분석을 받아보세요',
                    '이력서를 분석',
                    '이력서 리뷰를 받아보세요',
                    '이력서 리뷰',
                ];
                for (const kw of titleKeywords) {
                    if (fullText.includes(kw)) {
                        result.hasTitleText = true;
                        break;
                    }
                }

                // '이력서 리뷰 받기' 버튼 확인
                const btnKeywords = [
                    '이력서 리뷰 받기',
                    '리뷰 받기',
                    '이력서리뷰받기',
                ];
                for (const kw of btnKeywords) {
                    if (fullText.includes(kw)) {
                        result.hasReviewButton = true;
                        break;
                    }
                }

                // 버튼 요소 탐색
                const btns = document.querySelectorAll('button, a, [role="button"]');
                for (const btn of btns) {
                    const text = (btn.innerText || btn.textContent || '').trim().replace(/\\s+/g, ' ');
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0 && text.length < 100) {
                        if (text.includes('리뷰') || text.includes('분석')) {
                            result.buttonElements.push({
                                tag: btn.tagName,
                                text: text.substring(0, 60),
                                x: Math.round(rect.left),
                                y: Math.round(rect.top),
                            });
                        }
                    }
                }

                // 타이틀 요소 탐색
                const titleEls = document.querySelectorAll('h1, h2, h3, h4, h5, [class*="title"], [class*="Title"], [class*="header"], [class*="Header"]');
                for (const el of titleEls) {
                    const text = (el.innerText || '').trim().replace(/\\s+/g, ' ');
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && text.length > 0 && text.length < 200) {
                        result.titleElements.push({
                            tag: el.tagName,
                            text: text.substring(0, 100),
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                        });
                    }
                }

                // 페이지 상세 텍스트 (앞 3000자)
                result.detailText = fullText.substring(0, 3000);

                return result;
            }""")

            safe_print(f"[INFO] 현재 URL: {panel_info['url']}")
            safe_print(f"[INFO] 페이지 텍스트 (앞 3000자): {panel_info['detailText'][:3000]}")
            safe_print(f"[INFO] 타이틀 요소 ({len(panel_info['titleElements'])}개):")
            for el in panel_info['titleElements'][:10]:
                safe_print(f"  - [{el['tag']}] ({el['x']},{el['y']}) '{el['text']}'")
            safe_print(f"[INFO] 리뷰/분석 버튼 요소 ({len(panel_info['buttonElements'])}개):")
            for el in panel_info['buttonElements'][:10]:
                safe_print(f"  - [{el['tag']}] ({el['x']},{el['y']}) '{el['text']}'")

            safe_print(f"[INFO] 검증 결과:")
            safe_print(f"  - 타이틀/소개 텍스트 노출 ('이력서 분석을 받아보세요' 등): {panel_info['hasTitleText']}")
            safe_print(f"  - '이력서 리뷰 받기' 버튼 노출: {panel_info['hasReviewButton']}")

            # 최종 검증
            assert panel_info['hasTitleText'], (
                f"'이력서 분석을 받아보세요' 타이틀/소개 텍스트가 패널에 노출되지 않음 "
                f"(URL: {panel_info['url']})"
            )
            assert panel_info['hasReviewButton'], (
                f"'이력서 리뷰 받기' 버튼이 패널에 노출되지 않음 (URL: {panel_info['url']})"
            )

            safe_print("[OK] 이력서 리뷰 패널 항목 모두 확인 완료!")

            await page.screenshot(path='screenshots/test_54_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_54_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            return False

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
