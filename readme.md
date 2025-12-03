TC Playwright Code Conversion and Automated Execution
이 프로젝트는 작성된 TestCase를 자동으로 PlayWright Code로 변환, 실행, 수정, 결과 저장까지 실행합니다.
Playwright를 기반으로 하며, PC 환경에서 실행됩니다.

프로젝트 구조

```text
SHEETS-AUTOMATION

```

## 설치 및 환경 구성

1. 의존성 설치

```shell
npm install
```

2. Playwright 브라우저 설치

```shell
npx playwright install
```

## 실행 방법

### 전체 실행

```shell
TEST_ENV=stage npx playwright test --grep-invert @skip
```

각 케이스는 stage 또는 live 환경에서 동작하도록 구현되어 있기 때문에 반드시 환경을 지정해주어야 하며, flaky한 테스트 스크립트를 제외하기 위해 @skip 태그를 반드시 사용해야합니다. --grep-invert 옵션을 사용하면 특정 태그를 포함한 시나리오를 제외하고 실행합니다.

### PC 환경

```shell
TEST_ENV=stage npx playwright test --grep-invert @skip --project=PC
```

### 특정 테스트 파일 실행

```shell
TEST_ENV=stage npx playwright test test/caseid_1.spec.js
```

### 최근 실행한 테스트에서 실패한 테스트 실행

```shell
TEST_ENV=stage npx playwright test --project=Mobile --last-failed
```

## 테스트 작성 가이드 (WIP)

### 1. 테스트 파일 형식

- 테스트 파일 이름은 caseid\_번호.spec.js 형식을 따름.
- PC / Mobile 디바이스 환경을 구분하여 작성함.
- 테스트 명은 Playwright test.describe()와 test()에 모두 명시함.
- 주요 태그:
  - @sanity: Sanity 테스트 케이스
  - @home, @store, @funding 등: 도메인 별 구분
  - @skip: 실행하지 않을 케이스
  - @payment: 결제가 포함된 테스트 시나리오

```javascript
test.describe('caseid_4 - 홈 > 프로젝트 만들기 진입 (로그인, 만든 프로젝트 존재)', () => {
  test('로그인 상태에서 프로젝트 만들기 진입 @sanity @home', async ({ page, isMobile }) => {
    if (isMobile) {
      // 모바일웹 전용 로직
      await closeAppBanner(page); // 모바일 앱 시작시 배너 닫기
      ...
    } else {
      // PC웹 전용 로직
      ...
    }
  });
});
```

### 2. 공통 유틸리티 및 헬퍼 사용

반복되는 로직은 helpers/ 디렉토리에 유틸로 정의되어 있고 이를 재사용합니다.

예시:

- closeAppBanner(page): 앱 설치 배너 제거
- signinWithAccount(page, account): global-setup에서 설정한 세션과 구분되는 별도의 계정 로그인 처리
- parsePrice(text): 금액 문자열에서 숫자만 추출
- payment 관련 로직은 helpers/payment/ 디렉토리 참조

### 3. Page Object 사용

모든 페이지는 page_objects/ 디렉토리 내에 정의된 **Page Object Model (POM)**을 따릅니다.
각 테스트에서 new HomePage(page, isMobile)처럼 생성하여 사용합니다.

내부 속성은 Locator 인스턴스이며, 테스트에서는 await pageObject.Element.click() 형태로 접근합니다.

예시:

```javascript
const homePage = new HomePage(page, isMobile);
await expect(homePage.MainBannerCarousel).toBeVisible();
```

### 4. 상대 경로 사용 (baseURL 기반)

테스트 코드는 항상 상대 경로(/web/main, /web/wstore)를 사용합니다.

환경별 접속 도메인은 playwright.config.js의 baseURL에서 자동 설정됩니다. 환경에 따라 자동으로 stage, live 혹은 rc 도메인으로 접근할 수 있습니다.

```javascript
await page.goto(`wreward/comingsoon`, { waitUntil: 'domcontentloaded', timeout: 5000 });
```

### 5. 로그인 세션 설정

global-setup.js를 통해 사전 로그인을 처리하고 해당 세션을 저장하여 추가적인 로그인 없이 재사용합니다. global-setup을 통하지 않고 별도의 계정이 필요한 경우, signinWithAccount 헬퍼 함수를 이용하고, 별도의 계정은 fixtures/accounts.js에서 정의합니다.

```javascript
const { accounts } = require('./fixtures/accounts');
await signinWithAccount(page, noWish); // 찜한 컨텐츠가 하나도 없는 계정
```
