TC Playwright Code Conversion and Automated Execution
이 프로젝트는 작성된 TestCase를 자동으로 PlayWright Code로 변환, 실행, 수정, 결과 저장까지 실행합니다.
Playwright를 기반으로 하며, Mac OS 환경에서 구현되었으며 PC 환경에서 실행됩니다.

```text
SHEETS-AUTOMATION
python 3.11.14 를 사용합니다.
--dangerously-skip-permissions 옵션을 주어 claude에게 모든 권한을 주었으니 로컬에서 실행되어야 합니다.
실행 log는 logs 폴더 내에서 확인 가능합니다.
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

3. Claude Code 설치

4. Claude token 및 환경변수 설정
```shell
# 1회용
claude setup-token #token 복사
export CLAUDE_CODE_OAUTH_TOKEN=<token>

# 영구(1년)
claude setup-token #token 복사
nano ~/.zshrc

```
 
99. 실행
```shell
python run_automation.py
```