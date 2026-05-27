"""
의정부도시공사 채용공고 일치 점검 스크립트
- 출처 A: 의정부도시공사 홈페이지 (uiuc.or.kr)
- 출처 B: 클린아이 경영공시 (cleaneye.go.kr)
두 사이트 채용공고 목록을 비교하여 불일치 시 이메일 발송
Playwright를 사용하여 JS 렌더링 및 403 차단 우회
"""

import os
import re
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── 환경변수 (GitHub Secrets) ──────────────────────────────────
EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO   = os.environ["EMAIL_TO"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
# ──────────────────────────────────────────────────────────────

def normalize(title: str) -> str:
    return re.sub(r"[\s\W_]+", "", title).lower()


# ─────────────────────────────────────────────
# 1. 의정부도시공사 홈페이지
# ─────────────────────────────────────────────
def fetch_uiuc_jobs(page):
    url = "https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do"
    jobs = []
    pg = 1

    while True:
        try:
            page.goto(f"{url}?pageIndex={pg}", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            print(f"[uiuc] 페이지 {pg} 타임아웃")
            break

        rows = page.query_selector_all("table tbody tr")
        if not rows:
            break

        new_found = False
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 2:
                continue
            a_tag = row.query_selector("a")
            title = (a_tag.inner_text().strip() if a_tag
                     else cells[1].inner_text().strip())
            date_text = ""
            for cell in cells:
                txt = cell.inner_text().strip()
                if re.match(r"\d{4}[.\-/]\d{2}[.\-/]\d{2}", txt):
                    date_text = txt
                    break
            if title:
                jobs.append({"title": title, "date": date_text})
                new_found = True

        if not new_found:
            break
        pg += 1

    print(f"[uiuc] 수집: {len(jobs)}건")
    return jobs


# ─────────────────────────────────────────────
# 2. 클린아이 (의정부도시공사 필터)
# ─────────────────────────────────────────────
def fetch_cleaneye_jobs(page):
    base = "https://www.cleaneye.go.kr/user/empInfoList.do"
    jobs = []
    pg = 1

    while True:
        url = f"{base}?pageIndex={pg}&searchCondition=organNm&searchKeyword=%EC%9D%98%EC%A0%95%EB%B6%80%EB%8F%84%EC%8B%9C%EA%B3%B5%EC%82%AC"
        try:
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
        except PWTimeout:
            print(f"[cleaneye] 페이지 {pg} 타임아웃")
            break

        rows = page.query_selector_all("table tbody tr")
        if not rows:
            break

        new_found = False
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 3:
                continue
            # 기관명 확인
            org = cells[1].inner_text().strip() if len(cells) > 1 else ""
            if "의정부도시공사" not in org:
                continue
            a_tag = row.query_selector("a")
            title = (a_tag.inner_text().strip() if a_tag
                     else cells[2].inner_text().strip())
            date_text = ""
            for cell in cells:
                txt = cell.inner_text().strip()
                if re.match(r"\d{4}[.\-/]\d{2}[.\-/]\d{2}", txt):
                    date_text = txt
                    break
            if title:
                jobs.append({"title": title, "date": date_text})
                new_found = True

        if not new_found:
            break
        pg += 1

    print(f"[cleaneye] 수집: {len(jobs)}건")
    return jobs


# ─────────────────────────────────────────────
# 3. 비교
# ─────────────────────────────────────────────
def compare_jobs(uiuc_jobs, cleaneye_jobs):
    uiuc_map     = {normalize(j["title"]): j for j in uiuc_jobs}
    cleaneye_map = {normalize(j["title"]): j for j in cleaneye_jobs}
    only_uiuc     = [v for k, v in uiuc_map.items() if k not in cleaneye_map]
    only_cleaneye = [v for k, v in cleaneye_map.items() if k not in uiuc_map]
    return only_uiuc, only_cleaneye


# ─────────────────────────────────────────────
# 4. 이메일 발송
# ─────────────────────────────────────────────
def send_email(only_uiuc, only_cleaneye):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[채용공고 불일치 감지] 의정부도시공사 – {now}"

    def make_rows(jobs):
        if not jobs:
            return "<tr><td colspan='2' style='padding:6px 8px;color:#888;border:1px solid #ddd'>없음</td></tr>"
        return "".join(
            f"<tr><td style='padding:5px 8px;border:1px solid #ddd'>{j['title']}</td>"
            f"<td style='padding:5px 8px;border:1px solid #ddd;white-space:nowrap'>{j['date']}</td></tr>"
            for j in jobs
        )

    html = f"""
<html><body style="font-family:sans-serif;font-size:14px;color:#333;line-height:1.6">
<h2 style="color:#c0392b">🚨 채용공고 불일치 감지</h2>
<p>점검 일시: <b>{now}</b></p><hr>

<h3 style="color:#e67e22">📌 홈페이지에만 있는 공고
  <small style="color:#888">({len(only_uiuc)}건) → 클린아이 등록 필요</small></h3>
<table style="border-collapse:collapse;width:100%">
  <thead><tr style="background:#fef9e7">
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">제목</th>
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">날짜</th>
  </tr></thead>
  <tbody>{make_rows(only_uiuc)}</tbody>
</table><br>

<h3 style="color:#2980b9">📌 클린아이에만 있는 공고
  <small style="color:#888">({len(only_cleaneye)}건) → 홈페이지 확인 필요</small></h3>
<table style="border-collapse:collapse;width:100%">
  <thead><tr style="background:#eaf4fb">
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">제목</th>
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">날짜</th>
  </tr></thead>
  <tbody>{make_rows(only_cleaneye)}</tbody>
</table><br><hr>
<p style="color:#aaa;font-size:12px">
  ▸ <a href="https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do">의정부도시공사 채용공고</a> &nbsp;|&nbsp;
  <a href="https://www.cleaneye.go.kr/user/empInfoList.do">클린아이 채용정보</a>
</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"이메일 발송 완료 → {EMAIL_TO}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"채용공고 점검 시작: {datetime.now()}")
    print("=" * 50)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        uiuc_jobs     = fetch_uiuc_jobs(page)
        cleaneye_jobs = fetch_cleaneye_jobs(page)
        browser.close()

    only_uiuc, only_cleaneye = compare_jobs(uiuc_jobs, cleaneye_jobs)

    report = {
        "checked_at": datetime.now().isoformat(),
        "uiuc_total": len(uiuc_jobs),
        "cleaneye_total": len(cleaneye_jobs),
        "only_in_uiuc": only_uiuc,
        "only_in_cleaneye": only_cleaneye,
        "is_match": len(only_uiuc) == 0 and len(only_cleaneye) == 0,
    }
    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n결과 요약")
    print(f"  홈페이지 공고: {len(uiuc_jobs)}건")
    print(f"  클린아이 공고: {len(cleaneye_jobs)}건")
    print(f"  홈페이지에만 있음: {len(only_uiuc)}건")
    print(f"  클린아이에만 있음: {len(only_cleaneye)}건")

    if report["is_match"]:
        print("\n✅ 두 사이트 공고가 일치합니다.")
    else:
        print("\n❌ 불일치 감지 → 이메일 발송 중...")
        send_email(only_uiuc, only_cleaneye)


if __name__ == "__main__":
    main()
