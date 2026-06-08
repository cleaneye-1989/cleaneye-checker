"""
의정부도시공사 채용공고 일치 점검 스크립트
2026-01-01 이후 게시글만 비교
"""

import os
import re
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

EMAIL_FROM  = os.environ["EMAIL_FROM"]
EMAIL_TO    = os.environ["EMAIL_TO"]
EMAIL_PASS  = os.environ["EMAIL_PASS"]

FILTER_FROM = datetime(2026, 6, 1).date()

def normalize(title):
    title = re.sub(r"\s+", "", title)
    title = re.sub(r"[^\w가-힣]", "", title)
    return title.lower()

def parse_date(text):
    try:
        return datetime.strptime(re.sub(r"[./]", "-", text.strip()), "%Y-%m-%d").date()
    except Exception:
        return None


# ─────────────────────────────────────────────
# 1. 의정부도시공사 홈페이지 (POST 방식)
# ─────────────────────────────────────────────
def fetch_uiuc_jobs():
    url = "https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do"
    jobs = []
    seen_titles = set()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": url,
    })

    for pg in range(1, 20):
        data = {
            "controller": "",
            "isDesc": "false",
            "sortField": "a.SORT_ORDR DESC, NTT_NO",
            "view": "",
            "pageNum": pg,
            "baseAction": "/companyNotice/employmentPage/employment/list.do",
            "searchField0": "a.BBS_ID",
            "searchKeyword0": "BBSMSTR_000000000079",
            "searchField1": "NTT_SJ",
            "searchKeyword1": "",
        }
        try:
            res = session.post(url, data=data, timeout=20)
            res.raise_for_status()
        except Exception as e:
            print(f"[uiuc] 오류: {e}")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        if not rows:
            break

        stop = False
        page_new = 0
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            a_tag = row.find("a")
            title = a_tag.get_text(strip=True) if a_tag else cols[1].get_text(strip=True)
            date_text = ""
            for col in cols:
                txt = col.get_text(strip=True)
                if re.match(r"\d{4}[.\-/]\d{2}[.\-/]\d{2}", txt):
                    date_text = txt
                    break

            post_date = parse_date(date_text)
            if post_date and post_date < FILTER_FROM:
                stop = True
                break

            key = normalize(title)
            if title and key not in seen_titles:
                seen_titles.add(key)
                jobs.append({"title": title.strip(), "date": date_text})
                page_new += 1

        if stop or page_new == 0:
            break

    print(f"[uiuc] 수집: {len(jobs)}건 (2026-01-01 이후)")
    for j in jobs:
        print(f"  [uiuc] {j['title']}")
    return jobs


# ─────────────────────────────────────────────
# 2. 클린아이 (POST HTML 방식)
# ─────────────────────────────────────────────
def fetch_cleaneye_jobs():
    url = "https://www.cleaneye.go.kr/user/empHireInfo.do"
    jobs = []
    seen_titles = set()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Origin": "https://www.cleaneye.go.kr",
        "Referer": "https://www.cleaneye.go.kr/user/itemGongsi.do",
        "Content-Type": "application/x-www-form-urlencoded",
    })

    try:
        session.get("https://www.cleaneye.go.kr/user/itemGongsi.do", timeout=15)
    except Exception as e:
        print(f"[cleaneye] 메인 접근 오류: {e}")

    for pg in range(1, 20):
        data = {
            "pageIndex": pg,
            "entId": "2024000003",
            "entName": "의정부도시공사",
            "fixedYear": "",
            "num": "",
        }
        try:
            res = session.post(url, data=data, timeout=20)
            res.raise_for_status()
        except Exception as e:
            print(f"[cleaneye] 페이지 {pg} 오류: {e}")
            break

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("table tbody tr")
        if not rows:
            break

        stop = False
        page_new = 0
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            a_tag = row.find("a")
            title = a_tag.get_text(strip=True) if a_tag else cols[1].get_text(strip=True)
            date_text = ""
            for col in cols:
                txt = col.get_text(strip=True)
                if re.match(r"\d{4}[.\-/]\d{2}[.\-/]\d{2}", txt):
                    date_text = txt
                    break

            post_date = parse_date(date_text)
            if post_date and post_date < FILTER_FROM:
                stop = True
                break

            key = normalize(title)
            if title and key not in seen_titles:
                seen_titles.add(key)
                jobs.append({"title": title.strip(), "date": date_text})
                page_new += 1

        if stop or page_new == 0:
            break

    print(f"[cleaneye] 수집: {len(jobs)}건 (2026-01-01 이후)")
    for j in jobs:
        print(f"  [cleaneye] {j['title']}")
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
<p>점검 일시: <b>{now}</b> / 비교 기간: 2026-01-01 이후</p><hr>
<h3 style="color:#e67e22">📌 홈페이지에만 있는 공고 ({len(only_uiuc)}건) → 클린아이 등록 필요</h3>
<table style="border-collapse:collapse;width:100%">
  <thead><tr style="background:#fef9e7">
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">제목</th>
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">날짜</th>
  </tr></thead>
  <tbody>{make_rows(only_uiuc)}</tbody>
</table><br>
<h3 style="color:#2980b9">📌 클린아이에만 있는 공고 ({len(only_cleaneye)}건) → 홈페이지 확인 필요</h3>
<table style="border-collapse:collapse;width:100%">
  <thead><tr style="background:#eaf4fb">
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">제목</th>
    <th style="padding:6px 8px;border:1px solid #ddd;text-align:left">날짜</th>
  </tr></thead>
  <tbody>{make_rows(only_cleaneye)}</tbody>
</table><br><hr>
<p style="color:#aaa;font-size:12px">
  ▸ <a href="https://www.uiuc.or.kr/companyNotice/employmentPage/employment/list.do">의정부도시공사 채용공고</a> &nbsp;|&nbsp;
  <a href="https://www.cleaneye.go.kr/user/itemGongsi.do">클린아이 채용정보</a>
</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.daum.net", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"이메일 발송 완료 → {EMAIL_TO}")



# ─────────────────────────────────────────────
# 4-2. 오류 알림 이메일
# ─────────────────────────────────────────────
def send_error_email():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[점검 오류] 클린아이 접속 실패 – {now}"
    html = f"""
<html><body style="font-family:sans-serif;font-size:14px;color:#333">
<h2 style="color:#e67e22">⚠️ 클린아이 접속 오류</h2>
<p>점검 일시: <b>{now}</b></p>
<p>클린아이(cleaneye.go.kr) 서버 접속이 실패하여 채용공고 비교를 수행하지 못했습니다.</p>
<p>잠시 후 수동으로 확인해주세요.</p>
</body></html>"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.daum.net", 465) as s:
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"오류 알림 발송 완료 → {EMAIL_TO}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"채용공고 점검 시작: {datetime.now()}")
    print(f"비교 기준: {FILTER_FROM} 이후")
    print("=" * 50)

    uiuc_jobs     = fetch_uiuc_jobs()
    cleaneye_jobs = fetch_cleaneye_jobs()

    # 클린아이 접속 실패 시 이메일 발송 중단
    if len(cleaneye_jobs) == 0 and len(uiuc_jobs) > 0:
        print("\n⚠️ 클린아이 접속 오류 → 비교 중단")
        send_error_email()
        return

    only_uiuc, only_cleaneye = compare_jobs(uiuc_jobs, cleaneye_jobs)

    report = {
        "checked_at": datetime.now().isoformat(),
        "filter_from": str(FILTER_FROM),
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
