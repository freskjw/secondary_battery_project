"""
AI Reporter v1.2  (Dual-DB + KPI 강조 + 주간/월간 + 이상탐지 + LLM요약[Gemini])
- REPORT_DB_* 설정 시 그 DB 사용, 없으면 DB_* 로 폴백
- 기간: 자동(D 매일, W 월요일, M 매월 1일) 또는 REPORT_PERIODS 지정
- 이상탐지:
  * OK률: 14일 baseline 대비 z<-2(WARN)/z<-3(CRIT) + KPI 임계 비교
  * CPK: KPI 임계 비교
  * 결함코드: 기간 평균 대비 급증(>=200%) 또는 3σ 초과
- 요약: llm_client.generate_summary() → LLM_PROVIDER=gemini 기본
"""
from __future__ import annotations
import os, time, json, math, statistics, datetime as dt
from zoneinfo import ZoneInfo
from dataclasses import dataclass
import mysql.connector
from jinja2 import Template
from dotenv import load_dotenv
from llm_client import generate_summary, safe_dumps  # ← Gemini 포함 멀티 프로바이더 요약

load_dotenv("/app/config.env")

def pick(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return None

def env(n, d=None): return os.getenv(n, d)

DB = dict(
    host=pick(os.getenv("REPORT_DB_HOST"), os.getenv("DB_HOST"), "mysql"),
    port=int(pick(os.getenv("REPORT_DB_PORT"), os.getenv("DB_PORT"), "3306")),
    user=pick(os.getenv("REPORT_DB_USER"), os.getenv("DB_USER"), "root"),
    password=pick(os.getenv("REPORT_DB_PW"), os.getenv("DB_PW"), "projectteam2@@"),
    database=pick(os.getenv("REPORT_DB_NAME"), os.getenv("DB_NAME"), "secondary_battery_db"),
)

KST = ZoneInfo("Asia/Seoul")
RUN_AT = env("REPORT_RUN_AT", "08:15")
REQ_PERIODS = [p.strip().upper() for p in env("REPORT_PERIODS", "").split(",") if p.strip()]

def get_conn(): return mysql.connector.connect(**DB, autocommit=True)
def q(cur, sql, params=None): cur.execute(sql, params or ()); return cur.fetchall()
def one(cur, sql, params=None):
    cur.execute(sql, params or ()); r = cur.fetchone()
    return (r[0] if r and not isinstance(r, dict) else (list(r.values())[0] if r else None))

@dataclass
class Range:
    start: dt.datetime
    end: dt.datetime
    label: str
    period: str  # 'D'|'W'|'M'

def prev_day() -> Range:
    today = dt.datetime.now(KST).date()
    s = dt.datetime.combine(today-dt.timedelta(days=1), dt.time(0,0,0,tzinfo=KST))
    e = dt.datetime.combine(today,                 dt.time(0,0,0,tzinfo=KST))
    return Range(s,e,s.date().isoformat(),"D")

def prev_week_mon_sun() -> Range:
    now = dt.datetime.now(KST)
    mon = dt.datetime.combine((now - dt.timedelta(days=now.weekday())).date(), dt.time(0,0,0,tzinfo=KST))
    s = mon - dt.timedelta(days=7); e = mon
    label = f"{s.date().isocalendar().year}-{s.date().isocalendar().week:02d}"
    return Range(s,e,label,"W")

def prev_month() -> Range:
    now = dt.datetime.now(KST)
    first_this = dt.datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=KST)
    first_prev = dt.datetime(now.year-1,12,1,0,0,0,tzinfo=KST) if now.month==1 else dt.datetime(now.year,now.month-1,1,0,0,0,tzinfo=KST)
    label = f"{first_prev.date().year}-{first_prev.date().month:02d}"
    return Range(first_prev, first_this, label, "M")

def should_run(period: str) -> bool:
    if REQ_PERIODS: return period in REQ_PERIODS
    today = dt.datetime.now(KST).date()
    if period=="D": return True
    if period=="W": return today.weekday()==0
    if period=="M": return today.day==1
    return False

def load_kpi(cur):
    rows = q(cur, """
      SELECT t.module_type, t.metric, t.target, t.warn_threshold, t.crit_threshold
      FROM kpi_target t
      JOIN (SELECT module_type, metric, MAX(effective_from) AS eff FROM kpi_target GROUP BY module_type, metric) x
      ON x.module_type=t.module_type AND x.metric=t.metric AND x.eff=t.effective_from
    """)
    m={}
    for r in rows:
        m[(r["module_type"], r["metric"])] = {
            "target": float(r["target"]),
            "warn": float(r["warn_threshold"]) if r["warn_threshold"] is not None else None,
            "crit": float(r["crit_threshold"]) if r["crit_threshold"] is not None else None
        }
    return m

def status_by_threshold(value: float, kpi: dict) -> str:
    if not kpi: return "NA"
    if kpi.get("crit") is not None and value < kpi["crit"]: return "CRIT"
    if kpi.get("warn") is not None and value < kpi["warn"]: return "WARN"
    return "OK"

def aggregate_payload(rng: Range) -> dict:
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        # 1) 생산/OK률
        by_type = q(cur, """
          SELECT module_type,
                 COUNT(*) AS total,
                 SUM(voltage_result='OK') AS ok_v,
                 SUM(voltage_result='NG') AS ng_v,
                 SUM((vision1_result='NG') OR (vision2_result='NG')) AS ng_vis
          FROM module
          WHERE created_at >= %s AND created_at < %s
          GROUP BY module_type
        """, (rng.start, rng.end))
        kpi = load_kpi(cur)
        for r in by_type:
            r["ok_rate"] = (r["ok_v"]/r["total"]) if r["total"] else 0.0
            r["ok_rate_status"] = status_by_threshold(r["ok_rate"], kpi.get((r["module_type"],"ok_rate")))
        totals = {"total":0,"ok":0}
        for r in by_type:
            totals["total"] += r["total"]; totals["ok"] += r["ok_v"]
        totals["ng"] = totals["total"] - totals["ok"]
        totals["ok_rate"] = (totals["ok"]/totals["total"]) if totals["total"] else 0.0

        # 2) 결함/심각도
        top_defects = q(cur, """
          SELECT d.defect_code, COUNT(*) AS cnt, c.category, c.severity
          FROM module_defect d JOIN defect_code c ON c.code=d.defect_code
          WHERE d.detected_at >= %s AND d.detected_at < %s
          GROUP BY d.defect_code, c.category, c.severity
          ORDER BY cnt DESC LIMIT 5
        """, (rng.start, rng.end))
        sev = q(cur, """
          SELECT c.severity, COUNT(*) AS cnt
          FROM module_defect d JOIN defect_code c ON c.code=d.defect_code
          WHERE d.detected_at >= %s AND d.detected_at < %s
          GROUP BY c.severity
        """, (rng.start, rng.end))
        severity_break = {r["severity"]: r["cnt"] for r in sev}

        # 3) CP/CPK 최신
        cp_rows = q(cur, """
          SELECT pc.module_type, pc.cp, pc.cpk, pc.lsl, pc.usl, pc.computed_at
          FROM process_capability pc
          WHERE pc.computed_at=(SELECT MAX(p2.computed_at) FROM process_capability p2 WHERE p2.module_type=pc.module_type)
        """)
        cp_cpk={}
        for r in cp_rows:
            mt=r["module_type"]
            cp_cpk[mt] = {"cp": float(r["cp"]), "cpk": float(r["cpk"]),
                          "lsl": float(r["lsl"] or 0), "usl": float(r["usl"] or 0),
                          "computed_at": str(r["computed_at"])}
            cp_cpk[mt]["cpk_status"] = status_by_threshold(cp_cpk[mt]["cpk"], kpi.get((mt,"cpk")))

        # 4) 팩 수
        packs = one(cur, "SELECT COUNT(*) FROM pack WHERE created_at >= %s AND created_at < %s", (rng.start, rng.end)) or 0

        # 5) 규격
        spec = q(cur, "SELECT module_type, metric, lsl, usl, target FROM vw_spec_active WHERE metric='voltage'")
        spec_map = {(r["module_type"], r["metric"]): {"lsl": float(r["lsl"] or 0),
                                                      "usl": float(r["usl"] or 0),
                                                      "target": float(r["target"] or 0)} for r in spec}
        return {
            "period": rng.period, "label": rng.label,
            "range_kst": {"start": rng.start.isoformat(), "end": rng.end.isoformat()},
            "totals": totals, "by_type": by_type, "defects_top": top_defects,
            "severity_break": severity_break, "cp_cpk": cp_cpk, "packs": int(packs), "spec": spec_map
        }

# === 이상탐지 ===============================================================
def days_in_period(rng: Range) -> int:
    return max(1, (rng.end.date() - rng.start.date()).days)

def _daily_ok_rate_baseline(cur, rng: Range, module_type: str, days=14):
    s = rng.start - dt.timedelta(days=days)
    rows = q(cur, """
      SELECT DATE(created_at) d, COUNT(*) t, SUM(voltage_result='OK') ok
      FROM module WHERE created_at >= %s AND created_at < %s AND module_type=%s
      GROUP BY DATE(created_at)
    """, (s, rng.start, module_type))
    rates = [(r["ok"]/r["t"]) for r in rows if r["t"]]
    if len(rates) < 5: return None
    return {"mean": statistics.fmean(rates), "std": statistics.pstdev(rates) or 1e-9}

def _defect_baseline(cur, rng: Range, code: str, days=14):
    s = rng.start - dt.timedelta(days=days)
    rows = q(cur, """
      SELECT COUNT(*) c FROM module_defect
      WHERE defect_code=%s AND detected_at >= %s AND detected_at < %s
    """, (code, s, rng.start))
    return int(rows[0]["c"]) if rows else 0

def find_anomalies(rng: Range, payload: dict) -> list[dict]:
    anomalies=[]
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        kpi = load_kpi(cur)
        # OK률
        for r in payload["by_type"]:
            mt, rate = r["module_type"], r["ok_rate"]
            base = _daily_ok_rate_baseline(cur, rng, mt)
            z = (rate - base["mean"]) / (base["std"] or 1e-9) if base else 0.0
            sev_kpi = status_by_threshold(rate, kpi.get((mt,"ok_rate")))
            sev = "CRIT" if z < -3 else ("WARN" if z < -2 else "OK")
            final = "CRIT" if "CRIT" in (sev, sev_kpi) else ("WARN" if "WARN" in (sev, sev_kpi) else "OK")
            if final in ("WARN","CRIT"):
                anomalies.append({
                    "type":"ok_rate_drop", "module_type": mt,
                    "current": rate, "baseline_mean": base["mean"] if base else None,
                    "z": round(z,2), "severity": final, "note": "OK률 급락(통계/KPI)"
                })
        # CPK
        for mt, v in payload["cp_cpk"].items():
            sev = status_by_threshold(v["cpk"], kpi.get((mt,"cpk")))
            if sev in ("WARN","CRIT"):
                anomalies.append({"type":"cpk_low","module_type": mt,"cpk": float(v["cpk"]),"severity": sev,"note":"공정능력 저하(KPI)"})
        # 결함 급증
        for d in payload["defects_top"]:
            code, cnt = d["defect_code"], int(d["cnt"])
            base_cnt = _defect_baseline(cur, rng, code) or 0
            base_avg = base_cnt / max(1, days_in_period(rng))
            thr = base_avg + 3*math.sqrt(max(base_avg,1))
            if (base_avg>0 and cnt >= 2*base_avg) or (cnt >= thr):
                anomalies.append({
                    "type":"defect_spike","code": code,
                    "count": cnt, "baseline_daily": round(base_avg,2),
                    "severity": "WARN" if cnt < 3*base_avg else "CRIT",
                    "note": "결함코드 급증"
                })
    return anomalies

# === 렌더링/저장 ============================================================
HTML_TPL = Template(r"""
<!doctype html><html lang="ko"><head>
<meta charset="utf-8"/>
<title>{{ '일간' if payload.period=='D' else ('주간' if payload.period=='W' else '월간') }} 리포트 - {{ payload.label }}</title>
<style>
 body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:24px}
 h1{font-size:20px;margin:0 0 12px} h2{font-size:16px;margin:20px 0 8px}
 table{border-collapse:collapse;width:100%;margin:8px 0} th,td{border:1px solid #ddd;padding:6px;font-size:12px;text-align:right}
 th:first-child,td:first-child{text-align:left}
 .ok{color:#066a0a}.warn{color:#b36b00}.crit{color:#b00020}.muted{color:#666;font-size:12px}
 .badge{padding:2px 6px;border-radius:8px;border:1px solid #ddd;font-size:11px}
 .b-ok{background:#e7f6ea}.b-warn{background:#fff4e5}.b-crit{background:#fdecea}
 pre{white-space:pre-wrap;background:#fafafa;border:1px solid #eee;padding:10px;border-radius:8px}
</style></head><body>
<h1>{{ '일간' if payload.period=='D' else ('주간' if payload.period=='W' else '월간') }} 리포트 — {{ payload.label }}</h1>
<div class="muted">{{ payload.range_kst.start }} ~ {{ payload.range_kst.end }} (KST)</div>

<h2>AI 요약</h2>
<pre>{{ ai_summary }}</pre>

<h2>요약 지표</h2>
<ul>
  <li>총 생산: {{ payload.totals.total }} ea, OK: {{ payload.totals.ok }} ea, OK률: {{ (payload.totals.ok_rate*100) | round(1) }}%</li>
  <li>팩 생성: {{ payload.packs }} ea</li>
</ul>

<h2>타입별 생산/OK률 (KPI)</h2>
<table>
  <tr><th>타입</th><th>총계</th><th>OK(전압)</th><th>OK률</th><th>상태</th><th>VISION NG</th><th>VOLT NG</th></tr>
  {% for r in payload.by_type %}
  {% set st = r.ok_rate_status or 'NA' %}
  <tr>
    <td>{{ r.module_type }}</td><td>{{ r.total }}</td><td>{{ r.ok_v }}</td>
    <td>{{ (r.ok_rate*100) | round(1) }}%</td>
    <td>{% if st=='OK' %}<span class="badge b-ok">OK</span>{% elif st=='WARN' %}<span class="badge b-warn">WARN</span>{% elif st=='CRIT' %}<span class="badge b-crit">CRIT</span>{% else %}<span class="badge">-</span>{% endif %}</td>
    <td class="crit">{{ r.ng_vis }}</td><td class="crit">{{ r.ng_v }}</td>
  </tr>
  {% endfor %}
</table>

<h2>CP/CPK (최신, KPI)</h2>
<table>
  <tr><th>타입</th><th>CP</th><th>CPK</th><th>상태</th><th>LSL</th><th>USL</th><th>계산시각</th></tr>
  {% for t, v in payload.cp_cpk.items() %}
  {% set st = v.cpk_status or 'NA' %}
  <tr>
    <td>{{ t }}</td><td>{{ '%.3f'|format(v.cp) }}</td><td>{{ '%.3f'|format(v.cpk) }}</td>
    <td>{% if st=='OK' %}<span class="badge b-ok">OK</span>{% elif st=='WARN' %}<span class="badge b-warn">WARN</span>{% elif st=='CRIT' %}<span class="badge b-crit">CRIT</span>{% else %}<span class="badge">-</span>{% endif %}</td>
    <td>{{ v.lsl }}</td><td>{{ v.usl }}</td><td>{{ v.computed_at }}</td>
  </tr>
  {% endfor %}
</table>

<h2>이상탐지 (상위)</h2>
<table>
  <tr><th>구분</th><th>대상</th><th>세부</th><th>심각도</th></tr>
  {% for a in anomalies %}
  <tr>
    {% if a.type=='ok_rate_drop' %}
      <td>OK률 급락</td><td>{{ a.module_type }}</td>
      <td>현재 {{ (a.current*100)|round(1) }}%, z={{ a.z }}</td><td>{{ a.severity }}</td>
    {% elif a.type=='cpk_low' %}
      <td>CPK 낮음</td><td>{{ a.module_type }}</td>
      <td>CPK {{ '%.3f'|format(a.cpk) }}</td><td>{{ a.severity }}</td>
    {% elif a.type=='defect_spike' %}
      <td>결함 급증</td><td>{{ a.code }}</td>
      <td>{{ a.count }}건 / 일평균 {{ a.baseline_daily }}</td><td>{{ a.severity }}</td>
    {% endif %}
  </tr>
  {% endfor %}
</table>

<h2>결함 상위 Top5</h2>
<table>
  <tr><th>코드</th><th>카테고리</th><th>심각도</th><th>건수</th></tr>
  {% for d in payload.defects_top %}
  <tr><td>{{ d.defect_code }}</td><td>{{ d.category }}</td><td>{{ d.severity }}</td><td>{{ d.cnt }}</td></tr>
  {% endfor %}
</table>

<h2>심각도 분포</h2>
<table><tr><th>MINOR</th><th>MAJOR</th><th>CRITICAL</th></tr>
<tr><td>{{ payload.severity_break.get('MINOR',0) }}</td><td>{{ payload.severity_break.get('MAJOR',0) }}</td><td class="crit">{{ payload.severity_break.get('CRITICAL',0) }}</td></tr>
</table>

<p class="muted">※ 요약은 LLM_PROVIDER(기본: gemini) 사용. KPI 기준은 kpi_target 최신값 기준.</p>
</body></html>
""")

def render_and_save(payload: dict, anomalies: list[dict], audience: str):
    ai_text = generate_summary(payload, anomalies)  # ← Gemini 포함
    html = HTML_TPL.render(payload=payload, anomalies=anomalies, audience=audience, ai_summary=ai_text)
    import os
    os.makedirs("/reports", exist_ok=True)
    suffix = {"D":"day","W":"week","M":"month"}[payload["period"]]
    fname = f"/reports/report_{suffix}_{payload['label']}_{audience}.html"
    with open(fname, "w", encoding="utf-8") as f: 
        f.write(html)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
          INSERT INTO report_archive(report_date, period, audience, json_payload, html, text_summary, prompt_version, hash)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
          ON DUPLICATE KEY UPDATE html=VALUES(html), text_summary=VALUES(text_summary)
        """, (
            (dt.datetime.fromisoformat(payload["range_kst"]["end"]).date() - dt.timedelta(days=1)).isoformat()
                if payload["period"] in ("D","W") else
            dt.datetime.fromisoformat(payload["range_kst"]["start"]).date().isoformat(),
            payload["period"], audience,
            safe_dumps({"payload": payload, "anomalies": anomalies}),
            html, ai_text, "v1.2", f"{payload['label']}-{payload['period']}-{audience}-v1.2"
        ))

def generate_for_range(rng: Range):
    payload = aggregate_payload(rng)
    anomalies = find_anomalies(rng, payload)
    for audience in [a.strip() for a in env("REPORT_AUDIENCES","operator,lead,manager").split(",") if a.strip()]:
        render_and_save(payload, anomalies, audience)
        print(f"[ai-reporter] saved {rng.period} {rng.label} for {audience}")

def run_once():
    if should_run("D"): generate_for_range(prev_day())
    if should_run("W"): generate_for_range(prev_week_mon_sun())
    if should_run("M"): generate_for_range(prev_month())

def sleep_until_next_run():
    hh, mm = [int(x) for x in RUN_AT.split(":")]
    while True:
        now = dt.datetime.now(KST)
        if now.hour==hh and now.minute==mm: return
        time.sleep(20)

def main_loop():
    while True:
        try:
            sleep_until_next_run(); run_once(); time.sleep(65)
        except Exception as e:
            print(f"[ai-reporter] ERROR: {e}"); time.sleep(5)

if __name__ == "__main__":
    main_loop()