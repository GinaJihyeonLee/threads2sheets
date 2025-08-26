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

5. Customization
- Topic 종류 및 개수, filtering range, background color 등은 선호에 맞게 수정하여 사용하시면 됩니다.

## 파라미터 설명

- **`--access-token`**  
  Threads API를 사용하기 위해 필요한 인증 토큰입니다.  
  발급 절차가 다소 복잡하지만, 아래 블로그에 상세히 안내되어 있습니다:  
  👉 [https://carsleeper.tistory.com/5](https://carsleeper.tistory.com/5)

- **`--creds-json`**  
  Google Sheets API를 사용하기 위한 인증 정보입니다.  
  Google Cloud Console에서 서비스 계정을 생성하고 인증 파일을 발급받은 뒤, 사용하려는 Google Sheet 문서에 해당 서비스 계정 이메일을 **공유자**로 추가해야 합니다.  
  자세한 과정은 아래 블로그를 참고하세요:  
  👉 [https://posbar.tistory.com/260](https://posbar.tistory.com/260)

- **`--spreadsheet-id`**  
  Google Spreadsheet의 고유 ID입니다. 아래 URL의 경우, `spreadsheet-id` 값은 `1234`입니다.
  ```
  https://docs.google.com/spreadsheets/d/1234/edit#gid=567
  ```

- **`--worksheet`**  
  Google Sheet 문서 내 개별 탭(Tab)의 이름을 입력합니다.  

- **`--since`, `--until`**  
  Threads 포스트를 가져올 날짜 범위를 지정합니다.  
  `YYYY-MM-DD` 형식으로 입력해야 하며, `--until` 생략 시 최신 포스트까지 조회합니다.

- **`--limit`**  
  한 번에 가져올 최대 포스트 수를 지정합니다.  


## Scheduling (자동화)

매일 자동으로 Threads 데이터를 업데이트하려면 cron job을 설정할 수 있습니다.

### 1. 실행 스크립트 준비

`run_threads_update.sh` 파일을 생성하고 실행 권한을 부여합니다:

```bash
chmod +x run_threads_update_daily.sh
```

### 2. Cron Job 설정

#### 매일 오전 7시 자동 실행 등록
```bash
# Cron job 추가
(crontab -l 2>/dev/null; echo "0 7 * * * /path/to/run_threads_update.sh") | crontab -

# 등록 확인
crontab -l
```

#### Cron 시간 형식
```
분 시 일 월 요일
0  7  *  *  *    # 매일 오전 7시
0  */6 * * *     # 6시간마다
0  9  *  *  1-5  # 평일 오전 9시
```

### 3. 관리 명령어

```bash
# 등록된 작업 확인
crontab -l

# 작업 편집
crontab -e

# 모든 작업 삭제
crontab -r

# 로그 확인
tail -f /path/to/threads2sheets/logs/threads_update_*.log
```

### 4. 문제 해결

Cron이 실행되지 않을 때:
1. 스크립트 권한 확인: `ls -l run_threads_update.sh`
2. 스크립트 직접 테스트: `./run_threads_update.sh`
3. 시스템 시간대 확인: `date`
4. Python 경로 확인: `which python`

**주의**: Cron은 시스템 시간대를 따르며, 컴퓨터가 켜져 있어야 실행됩니다.

## License

MIT License © 2025 Gina Lee
