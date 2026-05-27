# 의정부도시공사 채용공고 자동 점검

의정부도시공사 홈페이지와 클린아이 경영공시의 채용공고를 매일 자동 비교하여
불일치 시 이메일로 알림을 발송합니다.

---

## 📁 파일 구조

```
job-checker/
├── check_jobs.py                    # 메인 점검 스크립트
├── .github/
│   └── workflows/
│       └── check.yml                # GitHub Actions 스케줄러
└── README.md
```

---

## 🚀 설치 방법 (5단계)

### 1단계 — GitHub 저장소 생성

1. https://github.com 접속 후 로그인
2. 우상단 **[+] → New repository** 클릭
3. 이름 예: `job-checker` / **Private** 선택 권장
4. **Create repository**

---

### 2단계 — 파일 업로드

터미널(또는 GitHub 웹 편집기)에서:

```bash
git clone https://github.com/[내계정]/job-checker.git
cd job-checker

# 이 프로젝트 파일들을 복사한 뒤
git add .
git commit -m "초기 설정"
git push
```

---

### 3단계 — Gmail 앱 비밀번호 발급

> 일반 Gmail 비밀번호가 아닌 **앱 비밀번호**가 필요합니다.

1. https://myaccount.google.com 접속
2. **보안 → 2단계 인증** 활성화 (필수)
3. **보안 → 앱 비밀번호** 클릭
4. 앱: "메일" / 기기: "기타(직접 입력)" → `job-checker` 입력
5. 생성된 **16자리 비밀번호** 복사 (공백 제거: `xxxx xxxx xxxx xxxx` → `xxxxxxxxxxxxxxxx`)

---

### 4단계 — GitHub Secrets 등록

1. 저장소 → **Settings → Secrets and variables → Actions**
2. **New repository secret** 을 눌러 아래 3개 등록:

| Secret 이름  | 값 예시                         | 설명               |
|-------------|--------------------------------|--------------------|
| `EMAIL_FROM` | `myaccount@gmail.com`          | 발송 Gmail 주소    |
| `EMAIL_TO`   | `receiver@example.com`         | 수신 이메일 주소   |
| `EMAIL_PASS` | `abcdabcdabcdabcd`             | Gmail 앱 비밀번호  |

---

### 5단계 — 첫 실행 테스트

1. GitHub 저장소 → **Actions** 탭
2. 좌측 `채용공고 일치 점검` 클릭
3. 우측 **Run workflow → Run workflow** 클릭
4. 실행 결과 확인 (초록 체크 = 성공)
5. 불일치 시 이메일이 도착하는지 확인

---

## ⏰ 실행 스케줄

기본 설정: **매일 오전 9시 (KST)** 자동 실행

변경하려면 `check.yml`의 cron 값을 수정:

```yaml
- cron: "0 0 * * *"   # 매일 오전 9시 KST
- cron: "0 0 * * 1"   # 매주 월요일 오전 9시
- cron: "0 0 * * 1,4" # 매주 월/목 오전 9시
```

---

## 📧 이메일 알림 예시

불일치 감지 시 아래와 같은 이메일이 발송됩니다:

```
제목: [채용공고 불일치 감지] 의정부도시공사 – 2026-05-27 09:00

🚨 채용공고 불일치 감지

📌 의정부도시공사 홈페이지에만 있는 공고 (1건)
→ 클린아이에 등록 필요
┌────────────────────────────┬────────────┐
│ 2026년 정규직 공개채용 공고 │ 2026-05-26 │
└────────────────────────────┴────────────┘

📌 클린아이에만 있는 공고 (0건)
→ 없음
```

---

## ✅ 일치 시 동작

두 사이트 공고가 완전히 일치하면 이메일이 발송되지 않습니다.
Actions 실행 내역 및 `report.json` 아티팩트에서 결과를 확인할 수 있습니다.

---

## 🔧 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 이메일 미수신 | Gmail 보안 설정 | 앱 비밀번호 재발급 |
| 공고 0건 수집 | 사이트 HTML 구조 변경 | `check_jobs.py`의 CSS 선택자 수정 |
| Actions 오류 | Secrets 미등록 | 4단계 다시 확인 |

---

## 📋 수집 대상

| 항목 | 의정부도시공사 | 클린아이 |
|------|-------------|---------|
| URL | `uiuc.or.kr/...employment/list.do` | `cleaneye.go.kr/user/empInfoList.do` |
| 필터 | 전체 목록 | 기관명 = 의정부도시공사 |
| 비교 기준 | 공고 제목 (정규화 후 비교) | 동일 |
