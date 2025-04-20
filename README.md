# threads2sheets

Threads API로 가져온 내 포스트와 인사이트를 Google Sheets에 동기화합니다.

## 기능

- 지정한 날짜 범위 내 Threads 포스트 조회  
- 조회수, 좋아요, 댓글, 리포스트, 인용, 공유 메트릭 수집  
- 기존 행 업데이트 또는 신규 행 추가  
- 시각적 가독성을 높이기 위한 포맷 자동 적용  
- 연도/월별 등으로 시트를 구분하여 탭 단위로 데이터 관리 가능

## 사용법

1. Repository Clone
   ```bash
   git clone https://github.com/GinaJihyeonLee/threads2sheets.git
   cd threads2sheets
   ```

2. Conda 환경 생성 및 활성화
   ```bash
   conda create -n threads python=3.10
   conda activate threads
   ```

3. 필수 package 설치  
   ```bash
   pip install -r requirements.txt
   ```

4. 실행 script 예시
   ```bash
   python threads_to_sheets.py \
     --access-token <THREADS_ACCESS_TOKEN> \
     --creds-json   /path/to/credentials.json \
     --spreadsheet-id <SPREADSHEET_ID> \
     --worksheet    <WORKSHEET_NAME> \
     --since        2025-01-01 \
     --until        2025-04-01 \
     --limit        100
   ```

## 파라미터 설명

- **`--access-token`**  
  Threads API를 사용하려면 Access Token이 필요합니다.  
  발급 과정이 다소 복잡할 수 있으나, 아래 블로그에 자세히 설명되어 있습니다:  
  👉 [https://carsleeper.tistory.com/5](https://carsleeper.tistory.com/5)

- **`--creds-json`**  
  Google Sheets API를 사용하기 위한 인증 정보가 담긴 파일입니다.  
  Google Cloud Console에서 서비스 계정을 생성하고 인증 정보를 발급받은 후, 사용하려는 Google Sheet 문서에 서비스 계정의 이메일을 **공유자**로 추가해야 합니다.  
  자세한 절차는 다음 블로그에서 확인할 수 있습니다.
  👉 [https://posbar.tistory.com/260](https://posbar.tistory.com/260)

- **`--spreadsheet-id`**  
  Google Spreadsheet의 고유 ID입니다.
  ```
  https://docs.google.com/spreadsheets/d/1234/edit#gid=567
  ```
  위 URL의 경우, `spreadsheet-id` 값은 `1234`입니다.  

- **`--worksheet`**  
  Google Sheet 문서 내 개별 탭(Tab)의 이름을 입력합니다.  

- **`--since`, `--until`**  
  Threads 포스트를 가져올 날짜 범위를 지정합니다.  
  `YYYY-MM-DD` 형식으로 입력해야 하며, `--until` 생략 시 최신 포스트까지 조회합니다.

- **`--limit`**  
  한 번에 가져올 최대 포스트 수를 지정합니다.  


## Scheduling

GitHub Actions로 자동화 가능


## License

MIT License © 2025 Gina Lee
