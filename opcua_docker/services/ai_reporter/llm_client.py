# llm_client.py — JSON 직렬화 안전 패치 + Gemini 그대로 사용
import os, json, datetime, decimal
from typing import Any

# -------- JSON 안전 변환 유틸 --------
def _to_jsonable(o: Any):
    # 기본 타입은 그대로
    if o is None or isinstance(o, (str, int, float, bool)):
        return o

    # 날짜/시간 -> ISO 문자열
    if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
        # datetime.time은 ISO가 길 수 있어 문자열 처리
        try:
            return o.isoformat()
        except Exception:
            return str(o)

    # Decimal -> float (정밀도 유지 원하면 str로 바꿔도 됨)
    if isinstance(o, decimal.Decimal):
        try:
            return float(o)
        except Exception:
            return str(o)

    # bytes -> utf-8 문자열
    if isinstance(o, (bytes, bytearray, memoryview)):
        try:
            return bytes(o).decode("utf-8", "ignore")
        except Exception:
            return str(o)

    # dict: key를 전부 문자열로 강제, value도 재귀 변환
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            # 키가 tuple 같은 경우 문자열로 평탄화
            try:
                sk = k if isinstance(k, str) else str(k)
            except Exception:
                sk = repr(k)
            out[sk] = _to_jsonable(v)
        return out

    # list/tuple/set 등 시퀀스 -> 리스트로 변환
    if isinstance(o, (list, tuple, set)):
        return [_to_jsonable(x) for x in o]

    # numpy 계열 지원(있으면)
    try:
        import numpy as np  # type: ignore
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, (np.ndarray,)):
            return [_to_jsonable(x) for x in o.tolist()]
    except Exception:
        pass

    # Enum 등 기타 -> 문자열
    try:
        return str(o)
    except Exception:
        return repr(o)

def safe_dumps(obj: Any) -> str:
    return json.dumps(_to_jsonable(obj), ensure_ascii=False)

# -------- 프롬프트 빌더 --------
def build_prompt(payload, anomalies, lang="ko"):
    """
    payload/anomalies 안에 튜플 key, Decimal, datetime, bytes 등이 섞여있어도
    safe_dumps로 안전하게 직렬화해서 LLM에 전달.
    """
    data_json = safe_dumps({"payload": payload, "anomalies": anomalies})
    return (
        f"[AI MANUFACTURING REPORT]\n"
        f"LANG: {lang}\n"
        f"ROLE: You are a senior process engineer. Summarize KPIs, yield, defects, and actions.\n\n"
        f"DATA(JSON):\n{data_json}\n\n"
        f"REQUIREMENTS:\n"
        f"- Use bullet points.\n"
        f"- Include numbers with units and time ranges.\n"
        f"- Separate 'Highlights', 'Issues', 'Root-cause guesses', 'Actions (next 24h/7d)'.\n"
        f"- Keep it concise but specific.\n"
    )

# -------- 요약 생성(Gemini) --------
def generate_summary(payload, anomalies, lang="ko"):
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            model_id = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY not set")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_id)
            prompt = build_prompt(payload, anomalies, lang)
            resp = model.generate_content(prompt)
            return (resp.text or "").strip()
        except Exception as e:
            # LLM 실패 시 폴백
            return fallback_summary(payload, anomalies, lang, error=str(e))
    else:
        # 다른 공급자 미설정 시 폴백
        return fallback_summary(payload, anomalies, lang)

# -------- 폴백 요약(LLM 없이 동작) --------
def fallback_summary(payload, anomalies, lang="ko", error: str | None = None):
    # 간단한 규칙 기반 요약(최소 동작 보장)
    # payload/anomalies가 어떤 형태든 safe_dumps로 일부만 보여줌
    head = "AI 보고서 (폴백)" if lang.startswith("ko") else "AI Report (Fallback)"
    errline = f"\n[LLM 오류] {error}" if error else ""
    snippet = safe_dumps({"preview": {"payload_keys": list(_to_jsonable(payload).keys()) if isinstance(payload, dict) else "list/other",
                                      "anomalies_len": len(anomalies) if hasattr(anomalies, '__len__') else 'n/a'}})
    body = [
        "● 하이라이트: 데이터 집계 완료",
        "● 이슈: LLM 비활성/오류로 간단 요약 제공",
        "● 액션(24h): LLM 키 설정 확인, 데이터 표본 점검",
    ] if lang.startswith("ko") else [
        "● Highlights: Aggregation complete",
        "● Issue: LLM disabled/errored, providing minimal summary",
        "● Actions (24h): Check LLM key and data sample",
    ]
    return f"{head}{errline}\n{snippet}\n" + "\n".join(body)