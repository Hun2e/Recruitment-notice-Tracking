# 📋 자소설닷컴 공고 트래커

자소설닷컴(jasoseol.com)의 채용공고를 **자동으로 수집**하여 Notion 데이터베이스에 저장하는 자동화 시스템입니다.  
매시간 자동으로 실행되며, 공고별 작성자 수 변화와 마감일을 한눈에 확인할 수 있습니다.

---

## 🛠 사용 기술 스택

| 기술 | 역할 |
|------|------|
| Python | 웹 크롤링 및 데이터 처리 |
| GitHub Actions | 자동 스케줄링 (매시간 실행) |
| Notion API | 데이터베이스 자동 업데이트 |
| BeautifulSoup | HTML 파싱 |
| 정규표현식 (regex) | 텍스트에서 데이터 추출 |

---

## ⚙️ 전체 기능 설명

### 1. 웹 크롤링 (Python + BeautifulSoup)

> 크롤링이란, 웹사이트에 자동으로 접속해서 필요한 정보를 가져오는 기술입니다.

- `requests` 라이브러리로 자소설닷컴 공고 페이지에 HTTP 요청을 보냅니다
- 받아온 HTML을 `BeautifulSoup`으로 분석합니다
- 아래 정보를 자동으로 추출합니다
  - **회사명**: `<h2>` 태그에서 추출
  - **공고명**: `<h1>` 태그에서 추출
  - **마감일**: `~ 2026년 3월 17일` 형식의 텍스트를 정규표현식으로 추출
  - **직무별 작성자 수**: `N명 작성` 패턴을 가진 `<li>` 태그에서 추출

### 2. GitHub Actions - 자동 스케줄링

> GitHub Actions는 코드 저장소에서 특정 조건이 되면 자동으로 코드를 실행해주는 서비스입니다.

- `.github/workflows/tracker.yml` 파일에 스케줄을 설정합니다
- `cron: "0 * * * *"` → 매시간 정각에 자동 실행
- 내 컴퓨터가 꺼져 있어도 GitHub 서버가 알아서 실행합니다

### 3. GitHub Secrets - 보안 정보 관리

> API 키 같은 민감한 정보를 코드에 직접 넣지 않고 안전하게 보관하는 기능입니다.

| Secret 이름 | 내용 |
|------------|------|
| `NOTION_API_KEY` | Notion에 접근하기 위한 인증 키 |
| `NOTION_DB_ID` | 데이터를 저장할 Notion DB의 ID |
| `TRACK_URLS` | 추적할 공고 URL 목록 (JSON 배열) |

> ⚠️ API 키를 코드에 직접 쓰면 GitHub에 공개될 위험이 있습니다. Secrets를 사용하면 암호화되어 안전하게 보관됩니다.

### 4. Notion API - 데이터베이스 자동 업데이트

> API란, 두 프로그램이 서로 통신할 수 있게 해주는 인터페이스입니다. Notion API를 쓰면 코드로 Notion을 자동 제어할 수 있습니다.

- 크롤링한 데이터를 Notion API로 전송합니다
- **공고ID**로 기존 행이 있는지 검색합니다
  - 있으면 → **업데이트** (작성자 수, 마감 상태 갱신)
  - 없으면 → **새 행 추가**
- 마감일 기준으로 마감 상태를 자동 계산합니다
  - `진행중` / `D-3` / `D-2` / `D-1` / `오늘 마감` / `마감됨`

### 5. 정규표현식 (Regex)

> 텍스트에서 특정 패턴을 찾아내는 기술입니다.

- 마감일 추출: `~ 2026년 3월 17일` → `2026-03-17`로 변환
- 작성자 수 추출: `영업관리 69명 작성` → `{"job": "영업관리", "count": 69}`로 변환

---

## 🔄 전체 흐름

```
[매시간 정각]
      ↓
GitHub Actions 자동 실행
      ↓
tracker.py 실행
      ↓
TRACK_URLS의 공고들 순서대로 크롤링
      ↓
회사명 / 공고명 / 마감일 / 작성자 수 추출
      ↓
Notion API로 DB 업데이트 (upsert)
      ↓
Notion에서 최신 현황 확인 가능!
```

---

## 📁 파일 구조

```
Jasoseol-tracking/
├── .github/
│   └── workflows/
│       └── tracker.yml   ← GitHub Actions 스케줄 설정
└── scripts/
    └── tracker.py        ← 크롤링 + Notion 업데이트 코드
```

---

## 🚀 사용 방법

### 1. Notion 설정

1. [Notion Integrations](https://www.notion.so/my-integrations)에서 새 Integration 생성
2. Integration 토큰(`NOTION_API_KEY`) 복사
3. Notion에서 공고 트래커용 DB 생성 후 DB ID(`NOTION_DB_ID`) 복사
   - DB URL: `https://notion.so/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` → 뒤의 32자리가 DB ID
4. DB 페이지 우상단 **⋯ → Connections → 생성한 Integration 연결**

### 2. GitHub Secrets 등록

레포 **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 |
|------------|-----|
| `NOTION_API_KEY` | Notion Integration 토큰 |
| `NOTION_DB_ID` | Notion DB ID |
| `TRACK_URLS` | 추적할 공고 URL 목록 (JSON 배열, 한 줄로 입력) |

```json
["https://jasoseol.com/recruit/102910", "https://jasoseol.com/recruit/123456"]
```

> ⚠️ 반드시 한 줄로 입력해야 합니다.

### 3. 공고 추가 방법

`TRACK_URLS` Secret을 업데이트할 때 **기존 URL + 새 URL**을 합쳐서 저장합니다.

```json
["https://jasoseol.com/recruit/기존URL1", "https://jasoseol.com/recruit/기존URL2", "https://jasoseol.com/recruit/새URL"]
```

> ⚠️ 기존 URL을 빠뜨리면 해당 공고는 더 이상 업데이트되지 않습니다.

### 4. 수동 실행

GitHub **Actions 탭 → 자소설닷컴 공고 트래커 → Run workflow**
