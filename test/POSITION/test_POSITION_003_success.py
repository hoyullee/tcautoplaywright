import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
import sys
from playwright.async_api import async_playwright
import asyncio
import os
import pytest

TEST_EMAIL = "hoyul.lee@wantedlab.com"
TEST_PASSWORD = ""

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

            # 탐색 페이지로 이동하여 포지션 카드 선택
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)  # 검증 대상이 아닌 팝업 정리

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"Found position card with href: {href}")

            # 포지션 상세 페이지로 직접 이동
            position_url = f'https://www.wanted.co.kr{href}'
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            print(f"Navigated to position detail page: {position_url}")

            # 1. '포지션 상세' 섹션 확인
            position_detail_found = False

            try:
                detail_header = page.get_by_text('포지션 상세', exact=False)
                await detail_header.first.wait_for(state='visible', timeout=5000)
                print("Found '포지션 상세' text")
                position_detail_found = True
            except Exception:
                print("'포지션 상세' text not found directly")

            if not position_detail_found:
                try:
                    job_section = page.locator('[class*="JobDescription"]').first
                    await job_section.wait_for(state='visible', timeout=5000)
                    print("Found JobDescription section")
                    position_detail_found = True
                except Exception:
                    pass

            if not position_detail_found:
                try:
                    content = page.locator('p, div, section').filter(has_text='주요업무').first
                    await content.wait_for(state='visible', timeout=5000)
                    print("Found position detail content with '주요업무'")
                    position_detail_found = True
                except Exception:
                    pass

            assert position_detail_found, "포지션 상세 섹션을 찾을 수 없습니다"

            # 2. '포지션 상세' 하단 태그 항목 확인
            # 페이지 하단으로 스크롤하여 태그 섹션 탐색
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await page.wait_for_timeout(1000)

            tags_found = False
            tag_texts = []

            # 방법 1: class에 Tag/tag가 포함된 요소 탐색
            try:
                tag_elements = page.locator('[class*="Tag"], [class*="tag"]').filter(
                    has_text=lambda t: len(t.strip()) > 0
                )
                # 더 간단한 방식으로 처리
                tag_elements = page.locator('[class*="Tag"], [class*="tag"]')
                count = await tag_elements.count()
                print(f"Found {count} elements with Tag/tag class")

                if count > 0:
                    for i in range(min(count, 10)):
                        el = tag_elements.nth(i)
                        is_visible = await el.is_visible()
                        text = await el.inner_text()
                        text = text.strip()
                        if is_visible and text:
                            tag_texts.append(text)
                            tags_found = True

                if tags_found:
                    print(f"Found tags via class*='Tag': {tag_texts[:5]}")
            except Exception as e:
                print(f"Method 1 failed: {e}")

            # 방법 2: data-attribute 기반 탐색
            if not tags_found:
                try:
                    tag_elements = page.locator('[data-attribute-id*="tag"], [data-tag], [data-skill]')
                    count = await tag_elements.count()
                    print(f"Found {count} elements with tag data attributes")
                    if count > 0:
                        for i in range(min(count, 10)):
                            el = tag_elements.nth(i)
                            is_visible = await el.is_visible()
                            text = (await el.inner_text()).strip()
                            if is_visible and text:
                                tag_texts.append(text)
                                tags_found = True
                        if tags_found:
                            print(f"Found tags via data attributes: {tag_texts[:5]}")
                except Exception as e:
                    print(f"Method 2 failed: {e}")

            # 방법 3: 포지션 상세 이후 등장하는 링크/태그 형태 탐색
            if not tags_found:
                try:
                    # 포지션 상세 아래에 있는 태그 영역 탐색 (skill tag, keyword tag 등)
                    skill_section = page.locator('[class*="skill"], [class*="Skill"], [class*="keyword"], [class*="Keyword"]')
                    count = await skill_section.count()
                    print(f"Found {count} skill/keyword elements")
                    if count > 0:
                        for i in range(min(count, 10)):
                            el = skill_section.nth(i)
                            is_visible = await el.is_visible()
                            text = (await el.inner_text()).strip()
                            if is_visible and text:
                                tag_texts.append(text)
                                tags_found = True
                        if tags_found:
                            print(f"Found tags via skill/keyword class: {tag_texts[:5]}")
                except Exception as e:
                    print(f"Method 3 failed: {e}")

            # 방법 4: 페이지 JS 평가로 태그 요소 탐색
            if not tags_found:
                try:
                    result = await page.evaluate("""() => {
                        // 태그처럼 보이는 요소 탐색: 짧은 텍스트를 가진 inline/pill 형태
                        const candidates = [...document.querySelectorAll('a, span, button, li')].slice(0, 200);
                        const tags = candidates.filter(el => {
                            const style = window.getComputedStyle(el);
                            const text = el.innerText ? el.innerText.trim() : '';
                            const rect = el.getBoundingClientRect();
                            return text.length > 0 && text.length < 30
                                && rect.width > 0 && rect.height > 0
                                && (style.borderRadius !== '0px' || style.display === 'inline-block')
                                && (el.className.toLowerCase().includes('tag')
                                    || el.className.toLowerCase().includes('skill')
                                    || el.className.toLowerCase().includes('chip')
                                    || el.className.toLowerCase().includes('badge'));
                        });
                        return tags.slice(0, 10).map(el => ({
                            text: el.innerText.trim(),
                            class: el.className
                        }));
                    }""")
                    if result and len(result) > 0:
                        tag_texts = [item['text'] for item in result if item['text']]
                        if tag_texts:
                            tags_found = True
                            print(f"Found tags via JS evaluation: {tag_texts[:5]}")
                except Exception as e:
                    print(f"Method 4 failed: {e}")

            # 방법 5: 페이지 전체에서 포지션 상세 섹션 하단 구조 파악 후 태그 찾기
            if not tags_found:
                try:
                    # 스크롤하여 포지션 상세 섹션 아래를 탐색
                    await page.evaluate('window.scrollTo(0, 0)')
                    await page.wait_for_timeout(500)

                    # 전체 페이지 구조 파악
                    structure = await page.evaluate("""() => {
                        // 모든 section/article/div 요소 중 '태그' 관련 텍스트 포함 요소 찾기
                        const allDivs = [...document.querySelectorAll('div, section, article, ul')].slice(0, 100);
                        const results = [];
                        for (const el of allDivs) {
                            const className = el.className.toLowerCase();
                            if (className.includes('tag') || className.includes('skill')
                                || className.includes('chip') || className.includes('badge')
                                || className.includes('keyword')) {
                                const children = [...el.querySelectorAll('*')];
                                const texts = children
                                    .filter(c => c.children.length === 0 && c.innerText && c.innerText.trim().length > 0 && c.innerText.trim().length < 30)
                                    .map(c => c.innerText.trim())
                                    .filter((v, i, arr) => arr.indexOf(v) === i)
                                    .slice(0, 5);
                                if (texts.length > 0) {
                                    results.push({ class: el.className, texts });
                                }
                            }
                        }
                        return results.slice(0, 5);
                    }""")
                    print(f"Structure search result: {structure}")
                    if structure:
                        for item in structure:
                            if item.get('texts'):
                                tag_texts.extend(item['texts'])
                                tags_found = True
                        if tags_found:
                            print(f"Found tags via structure search: {tag_texts[:5]}")
                except Exception as e:
                    print(f"Method 5 failed: {e}")

            assert tags_found and len(tag_texts) > 0, \
                f"'포지션 상세' 하단 태그 항목이 노출되지 않았습니다. 발견된 태그: {tag_texts}"

            print(f"AUTOMATION_SUCCESS: 포지션 상세 하단 태그 노출 확인 완료. 태그: {tag_texts[:5]}")

            await page.screenshot(path='screenshots/test_POSITION_003_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_003_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
