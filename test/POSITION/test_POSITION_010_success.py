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
        context = await browser.new_context(
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            storage_state='work/auth_state.json'
        )
        page = await context.new_page()

        try:
            os.makedirs('screenshots', exist_ok=True)

            # 탐색 페이지에서 포지션 카드 링크 추출
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)

            # 첫 번째 포지션 카드 링크 찾기
            position_card = page.locator('a[href^="/wd/"]').first
            await position_card.wait_for(state='visible', timeout=10000)
            href = await position_card.get_attribute('href')
            print(f"포지션 링크: {href}")

            # 포지션 상세 페이지로 이동
            position_url = f"https://www.wanted.co.kr{href}"
            await page.goto(position_url, timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(3000)
            print(f"포지션 상세 페이지 URL: {page.url}")

            # 1. 지원하기 버튼 찾기 및 클릭
            apply_btn = page.locator('button:has-text("지원하기")')
            apply_btn_count = await apply_btn.count()
            print(f"'지원하기' 버튼 수: {apply_btn_count}")

            if apply_btn_count > 0:
                await apply_btn.first.wait_for(state='visible', timeout=5000)
                await apply_btn.first.click()
                await page.wait_for_timeout(2000)
                print("✓ 지원하기 버튼 클릭 완료")
            else:
                # 지원 섹션이 이미 임베딩된 상태 확인
                apply_section = page.locator('h2:has-text("지원하기"), [class*="Applying_header"]')
                apply_section_count = await apply_section.count()
                assert apply_section_count > 0, "'지원하기' 버튼 또는 지원 섹션을 찾을 수 없습니다"
                print("✓ 지원하기 섹션이 이미 표시됨")

            # 2. 이력서 체크박스 선택
            # 다양한 방법으로 이력서 체크박스 탐색
            await page.wait_for_timeout(1000)

            # label[for^="resume-"] 로케이터
            resume_labels = page.locator('label[for^="resume-"]')
            resume_label_count = await resume_labels.count()
            print(f"이력서 label[for^='resume-'] 수: {resume_label_count}")

            # label이 없으면 다른 방식 시도
            if resume_label_count == 0:
                # input[type="checkbox"] + label 또는 체크박스 기반 찾기
                resume_labels = page.locator('input[type="checkbox"][id^="resume-"]')
                resume_label_count = await resume_labels.count()
                print(f"체크박스 input[id^='resume-'] 수: {resume_label_count}")

            assert resume_label_count > 0, "이력서 체크박스/레이블을 찾을 수 없습니다"

            # 첫 번째 이력서 선택 (기본 이력서 여부와 무관하게 임의 선택)
            target_label = resume_labels.nth(0)
            print(f"선택할 이력서: 첫 번째 (index=0)")

            # 스크롤하여 뷰포트 내로 이동
            await target_label.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)

            # label이면 클릭, checkbox input이면 클릭
            tag_name = await target_label.evaluate("el => el.tagName.toLowerCase()")
            print(f"요소 태그: {tag_name}")

            if tag_name == 'label':
                # label 클릭으로 checkbox 토글
                try:
                    await target_label.click(timeout=10000)
                except Exception:
                    # 실패 시 force 클릭 시도
                    await target_label.click(force=True, timeout=10000)
                await page.wait_for_timeout(500)

                # 연결된 checkbox id 확인
                for_attr = await target_label.get_attribute('for')
                if for_attr:
                    checkbox = page.locator(f'input#{for_attr}')
                    cb_count = await checkbox.count()
                    if cb_count > 0:
                        is_checked = await checkbox.is_checked()
                        print(f"이력서 체크박스 상태 (id={for_attr}): {'체크됨' if is_checked else '미체크'}")
                        if not is_checked:
                            # JS로 강제 클릭
                            await page.evaluate(f"() => document.getElementById('{for_attr}')?.click()")
                            await page.wait_for_timeout(500)
                            is_checked = await checkbox.is_checked()
                            print(f"JS 클릭 후 체크박스 상태: {'체크됨' if is_checked else '미체크'}")
                        assert is_checked, "이력서 체크박스를 선택할 수 없습니다"
                    else:
                        print(f"체크박스 input (id={for_attr})을 찾을 수 없음, 상태 확인 생략")
                else:
                    print("label의 for 속성 없음, 상태 확인 생략")
            else:
                # checkbox input 직접 클릭
                await page.evaluate("(el) => el.click()", await target_label.element_handle())
                await page.wait_for_timeout(500)
                is_checked = await target_label.is_checked()
                print(f"체크박스 상태: {'체크됨' if is_checked else '미체크'}")
                assert is_checked, "이력서 체크박스를 선택할 수 없습니다"

            print("✓ 이력서 체크박스 선택 완료")

            # 3. 제출하기 버튼 활성화 여부 확인
            await page.wait_for_timeout(500)

            submit_btn = page.locator('button:has-text("제출하기")')
            submit_btn_count = await submit_btn.count()
            print(f"'제출하기' 버튼 수: {submit_btn_count}")

            assert submit_btn_count > 0, "'제출하기' 버튼을 찾을 수 없습니다"

            submit_element = submit_btn.first
            await submit_element.wait_for(state='visible', timeout=5000)

            is_disabled = await submit_element.is_disabled()
            disabled_attr = await submit_element.get_attribute('disabled')
            aria_disabled = await submit_element.get_attribute('aria-disabled')
            print(f"'제출하기' 버튼 - disabled: {is_disabled}, disabled attr: {disabled_attr}, aria-disabled: {aria_disabled}")

            assert not is_disabled, \
                f"'제출하기' 버튼이 비활성화 상태입니다 (disabled={disabled_attr})"
            print("✓ 제출하기 버튼 활성화 확인")

            await page.screenshot(path='screenshots/test_52_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_52_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
