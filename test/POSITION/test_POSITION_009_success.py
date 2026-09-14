import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ui_helpers import dismiss_optional_popups
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

            # 탐색 페이지로 이동하여 첫 번째 포지션 카드 링크 추출
            await page.goto('https://www.wanted.co.kr/wdlist', timeout=30000)
            await page.wait_for_load_state('domcontentloaded')
            await dismiss_optional_popups(page)  # 검증 대상이 아닌 팝업 정리

            # 포지션 카드 링크 목록 수집 (최대 10개 순회하여 '지원하기' 버튼 있는 포지션 탐색)
            await page.wait_for_timeout(2000)
            position_cards = page.locator('a[href^="/wd/"]')
            card_count = await position_cards.count()
            print(f"포지션 카드 수: {card_count}")

            apply_btn = None
            found_url = None
            for i in range(min(card_count, 10)):
                href = await position_cards.nth(i).get_attribute('href')
                if not href:
                    continue
                position_url = f"https://www.wanted.co.kr{href}"
                await page.goto(position_url, timeout=30000)
                await page.wait_for_load_state('domcontentloaded')
                await page.wait_for_timeout(1500)
                print(f"포지션 상세 페이지 URL: {page.url}")

                btn = page.get_by_role('button', name='지원하기')
                if await btn.count() == 0:
                    btn = page.locator('button:has-text("지원하기")')
                if await btn.count() > 0:
                    apply_btn = btn
                    found_url = page.url
                    print(f"'지원하기' 버튼 발견: {found_url}")
                    break
                print(f"'지원하기' 버튼 없음, 다음 포지션 시도")

            assert apply_btn is not None, "10개 포지션 모두에서 '지원하기' 버튼을 찾을 수 없습니다"
            await apply_btn.first.wait_for(state='visible', timeout=10000)

            # 지원하기 버튼 클릭
            await apply_btn.first.click()
            await page.wait_for_timeout(2000)

            print(f"클릭 후 URL: {page.url}")

            # 지원 모달 탐색 - role="dialog" 또는 지원 관련 섹션
            # 모달이 열렸는지 확인
            modal = page.locator('[role="dialog"]')
            modal_count = await modal.count()
            print(f"다이얼로그 수: {modal_count}")

            # 지원 정보 섹션 확인 (이름/이메일/연락처/추천인)
            page_content = await page.evaluate("() => document.body.innerText || ''")

            # 필수 확인 항목들
            required_items = {
                '이름': False,
                '이메일': False,
                '연락처': False,
                '추천인': False,
                '첨부파일': False,
            }

            for item in required_items:
                if item in page_content:
                    required_items[item] = True
                    print(f"✓ '{item}' 항목 확인됨")
                else:
                    print(f"✗ '{item}' 항목 없음")

            # 버튼 확인: 파일 업로드 버튼, 새 이력서 작성 버튼
            # 파일 업로드 버튼 확인
            file_upload_btn = page.locator('button:has-text("파일 업로드"), button:has-text("업로드"), input[type="file"]')
            file_upload_count = await file_upload_btn.count()

            # 새 이력서 작성 버튼 확인
            new_resume_btn = page.get_by_role('button', name='새 이력서 작성')
            new_resume_count = await new_resume_btn.count()
            if new_resume_count == 0:
                new_resume_btn = page.locator('button:has-text("새 이력서 작성")')
                new_resume_count = await new_resume_btn.count()

            print(f"파일 업로드 관련 요소 수: {file_upload_count}")
            print(f"'새 이력서 작성' 버튼 수: {new_resume_count}")

            # 이력서 리스트 확인 (첨부파일 섹션)
            resume_list_present = '이력서' in page_content or '첨부파일' in page_content

            # 모달 내용 상세 확인
            if modal_count > 0:
                modal_text = await modal.first.inner_text()
                print(f"모달 텍스트 (첫 500자): {modal_text[:500]}")

                for item in required_items:
                    if item in modal_text:
                        required_items[item] = True
                        print(f"✓ 모달 내 '{item}' 항목 확인됨")

                # 모달 내 버튼 재확인
                modal_upload = modal.first.locator('button:has-text("파일 업로드"), button:has-text("업로드"), input[type="file"]')
                modal_upload_count = await modal_upload.count()

                modal_new_resume = modal.first.locator('button:has-text("새 이력서 작성")')
                modal_new_resume_count = await modal_new_resume.count()

                if modal_upload_count > 0:
                    file_upload_count = modal_upload_count
                if modal_new_resume_count > 0:
                    new_resume_count = modal_new_resume_count

                print(f"모달 내 파일 업로드 요소 수: {modal_upload_count}")
                print(f"모달 내 '새 이력서 작성' 버튼 수: {modal_new_resume_count}")

            # 검증: 지원 정보 항목들이 노출되어야 함
            missing_items = [item for item, found in required_items.items() if not found]
            if missing_items:
                # 추가 탐색: 페이지 전체 재확인
                full_content = await page.evaluate("""() => {
                    const all = document.querySelectorAll('label, h2, h3, h4, span, p, div');
                    return [...all].slice(0, 200).map(el => el.textContent?.trim()).filter(t => t).join('\\n');
                }""")
                for item in missing_items[:]:
                    if item in full_content:
                        required_items[item] = True
                        missing_items.remove(item)
                        print(f"✓ DOM 재탐색으로 '{item}' 항목 확인됨")

            missing_items = [item for item, found in required_items.items() if not found]
            assert len(missing_items) == 0, f"누락된 지원 정보 항목: {missing_items}"

            # 파일 업로드 버튼 또는 새 이력서 작성 버튼 중 하나 이상 확인
            assert file_upload_count > 0 or new_resume_count > 0, \
                "파일 업로드 버튼 또는 새 이력서 작성 버튼을 찾을 수 없습니다"

            print("✓ 지원 정보 섹션 (이름/이메일/연락처/추천인) 노출 확인")
            print("✓ 첨부파일 섹션 노출 확인")
            if file_upload_count > 0:
                print("✓ 파일 업로드 버튼 노출 확인")
            if new_resume_count > 0:
                print("✓ 새 이력서 작성 버튼 노출 확인")

            await page.screenshot(path='screenshots/test_POSITION_009_success.png')
            print("AUTOMATION_SUCCESS")
            return True

        except Exception as e:
            await page.screenshot(path='screenshots/test_POSITION_009_failed.png')
            print(f"AUTOMATION_FAILED: {e}")
            raise

        finally:
            await browser.close()

if __name__ == "__main__":
    result = asyncio.run(test_main())
    sys.exit(0 if result else 1)
