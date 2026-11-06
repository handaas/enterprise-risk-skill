#!/usr/bin/env python3
"""Compose an enterprise-risk analysis report by orchestrating the risk MCP.

Calls the upstream enterprise-risk-mcp-server tools and assembles a structured
JSON payload rendered into a professional HTML / Markdown report. Supports
``--dry-run`` which returns a well-formed skeleton from the bundled sample data
WITHOUT contacting the MCP.

Workflow (real run):
  1. Resolve the canonical enterprise name (fuzzy search if only a keyword).
  2. Query risk dimensions: 风险评分 / 严重违法 / 动产抵押 / 开庭公告 / 诉讼风险画像 /
     法院公告 / 知识产权出质 / 行政处罚 / 经营异常 / 限制高消费.
  3. Build unified report JSON with domain sections.
  4. Optionally render HTML + Markdown.

This file never prints secrets; MCP credentials live in the server's own .env.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import pathlib
from typing import Any, Dict, List, Mapping, Optional, Sequence

from common import REPORT_BANNER, REPORT_TYPE, attach_pagination, call_tool_once, collect_detail_pages, paid_call_scope, json_dumps, load_json_file, print_json
import mcp_client
from render_report import render_html, render_markdown, html_to_pdf

SAMPLE_PATH = pathlib.Path(__file__).resolve().parent.parent / "assets" / "report.example.json"

# Enterprise-risk MCP tools.
T_FUZZY = "risk_insight_fuzzy_search"
T_SCORE = "enterprise_risk_insight_score"
T_SERIOUS = "risk_insight_serious_violations"
T_MORTGAGE = "risk_insight_chattel_mortgage"
T_HEARINGS = "risk_insight_court_hearings"
T_LITIGATION = "risk_insight_litigation_risk_profile"
T_ANNOUNCE = "risk_insight_court_announcements"
T_IP_PLEDGE = "risk_insight_intellectual_property_pledge"
T_PENALTIES = "risk_insight_penalties"
T_ANOMALIES = "risk_insight_business_anomalies"
T_RESTRICTIONS = "risk_insight_consumption_restrictions"

_WRAPPER_LIST_COUNT_KEYS = (
    ("illegalInfoList", "illegalCount"),
    ("mortgageInfoList", "mortgageCount"),
    ("iprPledgeList", "iprPledgeCount"),
    ("punishmentList", "punishmentCount"),
    ("taxPenaltyList", "taxPenaltyCount"),
    ("anomalyList", "anomalyCount"),
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _is_empty_response(value: Any) -> bool:
    if value is None or value == "" or value == {}:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return any(token in text for token in ("查询数据为空", "暂无数据", "未查询到", "未检索到", "no data"))
    if isinstance(value, dict):
        for list_key, count_key in _WRAPPER_LIST_COUNT_KEYS:
            if list_key in value and count_key in value:
                rows = value.get(list_key)
                count = value.get(count_key)
                if rows in (None, []) and count in (None, 0, "0"):
                    return True
        for key in ("text", "message", "msg"):
            if key in value and _is_empty_response(value.get(key)):
                return True
        containers = [value.get(key) for key in ("resultList", "list", "items", "data") if key in value]
        if containers and all(item in (None, [], {}) for item in containers):
            total = value.get("total")
            return total in (None, 0, "0")
    return False


def _is_api_error(value: Any) -> bool:
    """Return True only for failed calls; platform empty-data text is not an error."""
    if value is None or _is_empty_response(value):
        return False
    if isinstance(value, str):
        text = value.lower()
        return any(token in text for token in (
            "接口调用失败", "查询失败", "状态码：4", "状态码：5",
            "upstream timeout", "tool failed", "unauthorized", "forbidden",
        ))
    if isinstance(value, dict):
        if value.get("isError") is True or value.get("is_error") is True or value.get("success") is False:
            return True
        if any(value.get(key) not in (None, "", False) for key in ("_error", "error")):
            return True
        code = value.get("code")
        if code not in (None, 0, "0", 200, "200", 10001, "10001"):
            return True
        return any(_is_api_error(value.get(key)) for key in ("text", "message", "msg") if key in value)
    return False


def _first_list(value: Any) -> List[Any]:
    if _is_api_error(value) or _is_empty_response(value):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("resultList", "list", "items", *[pair[0] for pair in _WRAPPER_LIST_COUNT_KEYS]):
            if isinstance(value.get(key), list):
                return value[key]
        nested = value.get("data")
        if isinstance(nested, list):
            return nested
        if isinstance(nested, dict):
            return _first_list(nested)
    return []


def _first_record(value: Any) -> Dict[str, Any]:
    if _is_api_error(value) or _is_empty_response(value):
        return {}
    for record in _first_list(value):
        if isinstance(record, dict) and _has_evidence(record):
            return record
    if isinstance(value, dict):
        envelope = {"resultList", "list", "items", "data", "total", "pageNo", "pageSize", "text", "message", "msg", "code"}
        envelope.update(key for pair in _WRAPPER_LIST_COUNT_KEYS for key in pair)
        if not set(value).issubset(envelope) and _has_evidence(value):
            return value
    return {}


def _has_evidence(value: Any) -> bool:
    if value is None or value == "" or value == "-":
        return False
    if _is_api_error(value) or _is_empty_response(value):
        return False
    if isinstance(value, dict):
        return any(_has_evidence(item) for key, item in value.items() if key not in {"total", "pageNo", "pageSize"})
    if isinstance(value, (list, tuple, set)):
        return any(_has_evidence(item) for item in value)
    return True


def _meaningful_row(row: Mapping[str, Any]) -> bool:
    return any(_has_evidence(value) for value in row.values())


def _attach_call_status(report: Dict[str, Any], calls: Mapping[str, Any]) -> Dict[str, Any]:
    """Disclose failed and genuine-empty domains without exposing upstream details."""
    failed = [name for name, payload in calls.items() if _is_api_error(payload)]
    empty = [name for name, payload in calls.items() if not _is_api_error(payload) and _is_empty_response(payload)]
    source = report.setdefault("data_source", {})
    source["failed_products"] = failed
    source["empty_products"] = empty
    return report


def _apply_resolution_limit(report: Dict[str, Any], resolved: Mapping[str, Any]) -> Dict[str, Any]:
    subject = report.setdefault("subject", {})
    subject["resolved"] = False
    subject["requires_confirmation"] = True
    subject["resolve_reason"] = resolved.get("reason", "主体未唯一确认")
    subject["candidate_sample"] = list(resolved.get("candidate_sample") or [])
    if resolved.get("fuzzy_total") is not None:
        subject["fuzzy_total"] = resolved.get("fuzzy_total")
    message = "输入未唯一确认到特定企业；已停止主体专属数据调用，不生成该企业的经营、风险或舆情评价。请使用候选企业全称或企业标识重试。"
    report["abstract"] = message
    report["summary"] = message
    report["executive_summary"] = [message]
    report["metrics"] = []
    report["representative_records"] = []
    report["insights"] = [{"feature": "主体确认受限", "evidence": subject["resolve_reason"], "interpretation": message}]
    report.setdefault("data_source", {})["subject_resolution"] = "confirmation_required"
    return report


def _text(value: Any, limit: int = 0) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        t = json.dumps(value, ensure_ascii=False)
    else:
        t = str(value)
    t = " ".join(t.split())
    if limit and len(t) > limit:
        return t[: limit - 1].rstrip() + "…"
    return t


def _text_or_dash(value: Any) -> str:
    text = _text(value)
    return text if text else "-"


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_call(tool: str, arguments: Dict[str, Any]) -> Any:
    try:
        result = call_tool_once(mcp_client.call_tool, tool, arguments)
        # Detect API error responses (405, etc.) and return error marker
        if _is_api_error(result):
            return {"_error": "API错误", "_raw": result}
        return result
    except Exception as exc:
        return {"_error": str(exc)}


def _safe_total(payload: Any) -> Any:
    if isinstance(payload, dict):
        if _is_api_error(payload):
            return None
        for key in ("total", *[pair[1] for pair in _WRAPPER_LIST_COUNT_KEYS]):
            if payload.get(key) is not None:
                return payload.get(key)
    return None


def _collect_detail_pages(tool: str, arguments: Dict[str, Any], max_pages: int) -> Dict[str, Any]:
    """Total-driven detail collection within an explicit paid-page budget (default 1 page).

    The first paid page serves both as report data and as total discovery; it is
    never refetched. Additional pages are only requested inside the budget.
    """
    return collect_detail_pages(
        _safe_call, tool, dict(arguments), get_rows=_first_list, get_total=_safe_total,
        is_error=_is_api_error, max_pages=max_pages,
    )


def _concentration(rows: List[Mapping[str, Any]], top_n: int = 3) -> Dict[str, Any]:
    """Compute top-N concentration (CRn) and dominant category.

    Rows use the unified {名称/类型/状态/年份, 数量} shape produced by
    section builders so it is interchangeable across skills.
    """
    name_key = "阶段"
    if rows and not any(name_key in r for r in rows if isinstance(r, Mapping)):
        name_key = "名称/类型/状态/年份"
    items = []
    for r in rows:
        try:
            items.append((r.get(name_key, "-"), float(str(r.get("数量", 0)).replace(",", ""))))
        except (TypeError, ValueError):
            items.append((r.get(name_key, "-"), 0.0))
    total = sum(v for _, v in items)
    if not total:
        return {}
    items.sort(key=lambda x: x[1], reverse=True)
    cr = sum(v for _, v in items[:top_n]) / total * 100
    return {"top": items[0][0], "top_share": items[0][1] / total * 100, "cr": cr, "total": total}


def _trend_analysis(rows: List[Mapping[str, Any]]) -> Dict[str, Any]:
    """Compute trend direction, peak, and YoY change from a {period,count} series."""
    name_key = "名称/类型/状态/年份"
    nums = []
    for r in rows:
        try:
            nums.append(float(str(r.get("数量", 0)).replace(",", "")))
        except (TypeError, ValueError):
            nums.append(0.0)
    if not nums:
        return {}
    peak_idx = max(range(len(nums)), key=lambda i: nums[i])
    direction = "持平"
    yoy = ""
    if len(nums) >= 2:
        last, prev = nums[-1], nums[-2]
        if prev > 0:
            pct = (last - prev) / prev * 100
            if pct > 5:
                direction = f"上升 {pct:.0f}%"
            elif pct < -5:
                direction = f"下降 {abs(pct):.0f}%"
            yoy = f"同比 {pct:+.0f}%"
    return {"peak_period": rows[peak_idx].get(name_key, "-"), "peak_value": nums[peak_idx], "direction": direction, "yoy": yoy, "last": nums[-1]}


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #

def resolve_enterprise_name(raw: str) -> Dict[str, Any]:
    raw = (raw or "").strip()
    if not raw:
        return {"keyword": "", "enterprise": "", "resolved": False, "requires_confirmation": True, "reason": "关键词为空", "candidate_sample": []}
    # A full legal-name-looking input is already an explicit subject selection.
    if any(suffix in raw for suffix in ("公司", "有限", "院", "厂", "中心", "事务所", "合作社", "合伙")):
        return {"keyword": raw, "enterprise": raw, "resolved": True, "requires_confirmation": False, "reason": "用户提供企业全称", "candidate_sample": []}

    fuzzy = _safe_call(T_FUZZY, {"matchKeyword": raw, "pageSize": 10})
    records = [item for item in _first_list(fuzzy) if isinstance(item, dict)]
    total = _int(_safe_total(fuzzy))
    id_keys = ("nameId", "id", "enterpriseId", "regNumber", "socialCreditCode")
    exact = [
        item for item in records
        if raw == str(item.get("name") or "").strip()
        or any(raw == str(item.get(key) or "").strip() for key in id_keys)
    ]
    if len(exact) == 1:
        record = exact[0]
        name = str(record.get("name") or raw).strip()
        return {"keyword": raw, "enterprise": name, "resolved": True, "requires_confirmation": False, "reason": "与候选企业全称或标识精确匹配", "fuzzy_total": total, "record": record, "candidate_sample": []}
    if len(records) == 1 and total == 1:
        record = records[0]
        name = str(record.get("name") or "").strip()
        if name:
            return {"keyword": raw, "enterprise": name, "resolved": True, "requires_confirmation": False, "reason": "模糊查询唯一命中", "fuzzy_total": total, "record": record, "candidate_sample": []}

    candidates = []
    for item in records[:5]:
        candidate = {"name": str(item.get("name") or "").strip()}
        for key in id_keys:
            if item.get(key) not in (None, ""):
                candidate[key] = str(item.get(key))
        if candidate.get("name") or len(candidate) > 1:
            candidates.append(candidate)
    if candidates:
        reason = f"模糊查询命中 {total if total is not None else '多个'} 个候选，未唯一确认主体"
    else:
        reason = "模糊查询未唯一命中企业，需提供企业全称或企业标识"
    return {
        "keyword": raw, "enterprise": raw, "resolved": False, "requires_confirmation": True,
        "reason": reason, "fuzzy_total": total, "candidate_sample": candidates,
    }



def _extract_profile(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract enterprise profile fields from a fuzzy_search record."""
    return {
        "name": _text(record.get("name")),
        "reg_capital": record.get("regCapitalValue"),
        "reg_capital_coin": _text(record.get("regCapitalCoinType")),
        "annual_turnover": _text(record.get("annualTurnover")),
        "oper_status": _text(record.get("operStatus")),
        "enterprise_type": _text(record.get("enterpriseType")),
        "found_time": _text(record.get("foundTime")),
        "legal_rep": _text(record.get("legalRepresentative")),
        "address": _text(record.get("address")),
        "homepage": _text(record.get("homepage")),
    }


def _format_capital(val: Any, coin: str = "") -> str:
    """Format capital value: 10995210218.0 -> '109.95 亿'."""
    try:
        v = float(val)
        if v >= 1e8:
            s = f"{v / 1e8:.2f} 亿"
        elif v >= 1e4:
            s = f"{v / 1e4:.2f} 万"
        else:
            s = f"{v:.0f}"
        if coin:
            s += f" {coin}"
        return s
    except (TypeError, ValueError):
        return _text(val) if val not in (None, "") else "-"


def _enrich_metrics_with_profile(metrics: List[Dict[str, Any]], record: Any) -> List[Dict[str, Any]]:
    """Append enterprise profile metrics from a fuzzy_search record."""
    if not isinstance(record, dict):
        return metrics
    _prof = _extract_profile(record)
    if _prof.get("reg_capital") not in ("-", "", None):
        metrics.append({"label": "注册资本", "value": _format_capital(_prof["reg_capital"], _prof.get("reg_capital_coin", "")), "hint": "工商登记注册资本"})
    if _prof.get("found_time") and _prof["found_time"] != "-":
        metrics.append({"label": "成立时间", "value": _prof["found_time"], "hint": "工商登记成立日期"})
    if _prof.get("oper_status") and _prof["oper_status"] != "-":
        metrics.append({"label": "经营状态", "value": _prof["oper_status"], "hint": "工商登记经营状态"})
    if _prof.get("enterprise_type") and _prof["enterprise_type"] != "-":
        metrics.append({"label": "企业类型", "value": _prof["enterprise_type"], "hint": "工商登记企业类型"})
    if _prof.get("legal_rep") and _prof["legal_rep"] != "-":
        metrics.append({"label": "法定代表人", "value": _prof["legal_rep"], "hint": "工商登记法定代表人"})
    return metrics


def _derive_core_metrics(metrics: List[Dict[str, Any]], core: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Derive additional metrics from core analysis sections."""
    penalties = core.get("penalties", []) if isinstance(core, dict) else []
    restrictions = core.get("consumption_restrictions", []) if isinstance(core, dict) else []
    lit_overview = core.get("litigation_overview", {}) if isinstance(core, dict) else {}
    if isinstance(lit_overview, dict) and lit_overview:
        total_lit = sum(int(v or 0) for v in lit_overview.values() if str(v).isdigit())
        if total_lit > 0:
            metrics.append({"label": "分维度记录数合计（未去重）", "value": str(total_lit), "hint": "诉讼画像各司法阶段合计（未跨阶段事件去重，不含抵押、处罚等其他产品），不代表独立案件数"})
    if isinstance(penalties, list) and penalties:
        metrics.append({"label": "当前返回行政处罚明细数", "value": str(len(penalties)), "hint": "当前响应 punishmentList/taxPenaltyList 的明细行数"})
    if isinstance(restrictions, list) and restrictions:
        metrics.append({"label": "当前返回限高明细数", "value": str(len(restrictions)), "hint": "本次采集 resultList 的明细行数"})
    return metrics


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def build_subject(raw: str, resolved: Mapping[str, Any], keyword_type: str) -> Dict[str, Any]:
    return {
        "enterprise": resolved.get("enterprise") or raw,
        "matchKeyword": resolved.get("enterprise") or raw,
        "keywordType": keyword_type,
        "match_raw": raw,
        "resolved": bool(resolved.get("resolved")),
        "resolve_reason": resolved.get("reason", ""),
    }


def build_caliber(subject: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "match_target": subject.get("enterprise") or subject.get("match_raw"),
        "match_type": f"风险维度按企业主体匹配（keywordType={subject.get('keywordType', 'name')}）；支持企业名称/注册号/统一社会信用代码/企业 id",
        "data_scope": "风险评分、严重违法、动产抵押、开庭公告、诉讼风险画像、法院公告、知识产权出质、行政处罚、经营异常、限制高消费",
        "products": ["企业风险评分", "严重违法", "动产抵押", "开庭公告", "诉讼风险画像", "法院公告", "知识产权出质", "行政处罚", "经营异常", "限制高消费"],
        "limit": "数据来自公开风险数据库；部分维度可能存在更新延迟或公示滞后期。司法阶段计数未提供当事人角色、裁判结果或履行状态，不能据此推断责任、败诉、未履行或失信。",
    }


def _kv_from(payload: Any, mapping: List[tuple]) -> Dict[str, Any]:
    p = payload if isinstance(payload, dict) else {}
    out: Dict[str, Any] = {}
    for key, label in mapping:
        val = p.get(key)
        if val not in (None, "", [], {}):
            out[label] = _text(val)
    return out


def _table_from(payload: Any, fields: List[tuple]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in _first_list(payload):
        if not isinstance(item, dict):
            continue
        row: Dict[str, Any] = {}
        for key, label in fields:
            keys = key if isinstance(key, tuple) else (key,)
            value = next((item.get(candidate) for candidate in keys if item.get(candidate) is not None), None)
            row[label] = _text(value) if value not in (None, "") else "-"
        if _meaningful_row(row):
            rows.append(row)
    return rows


# Real-key mapping tables (verified against live MCP responses).
# score / risk_insight_litigation_risk_profile use snake_case totals;
# the remaining tools expose lists described in their tool schemas.
_SCORE_FIELDS = [
    ("risk_score", "风险评分"),
    ("risk_level", "风险等级"),
]

# risk_insight_litigation_risk_profile totals (camelCase, verified live).
_LITIGATION_TOTAL_FIELDS = [
    ("caKaitingTotal", "开庭公告数"),
    ("caLianTotal", "立案公告数"),
    ("caTotal", "法院公告数"),
    ("jdTotal", "裁判文书数"),
    ("enforcementTotal", "被执行人记录数"),
    ("limitedTotal", "限制高消费数"),
    ("edTotal", "失信被执行人数"),
]

_LITIGATION_DIST = [
    ("caKaitingTotal", "开庭公告"),
    ("caLianTotal", "立案公告"),
    ("caTotal", "法院公告"),
    ("jdTotal", "裁判文书"),
    ("enforcementTotal", "被执行人"),
    ("limitedTotal", "限制高消费"),
    ("edTotal", "失信被执行人"),
]

_SERIOUS_FIELDS = [
    ("type", "类别"),
    ("createReason", "列入原因"),
    ("createAuthority", "决定机关"),
    ("createDate", "列入日期"),
    ("removeDate", "移除日期"),
    ("removeReason", "移除原因"),
]
_MORTGAGE_FIELDS = [
    ("date", "登记日期"),
    ("authority", "登记机关"),
    ("amount", "被担保债权数额"),
    ("type", "种类"),
    ("publicationDate", "公示日期"),
    ("term", "债务履行期限"),
    ("scope", "担保范围"),
]
# Court hearings + court announcements share the same shape (caseId/caseType/
# relatedCaseNumber/publishUnit + date/publishDate). hearings also has
# caseReason/address; we map the common, always-present keys.
_HEARING_FIELDS = [
    ("relatedCaseNumber", "案号"),
    ("caseType", "公告类型"),
    ("publishUnit", "法院"),
    ("date", "开庭日期"),
    ("caseReason", "案由"),
    ("publishDate", "公告日期"),
    ("address", "庭审地点"),
]
_ANNOUNCE_FIELDS = [
    ("relatedCaseNumber", "案号"),
    ("caseType", "公告类型"),
    ("publishUnit", "法院"),
    ("caseReason", "案由"),
    ("date", "开庭日期"),
    ("publishDate", "刊登日期"),
    ("address", "庭审地点"),
]
_PLEDGE_FIELDS = [
    ("iprName", "知识产权名称"),
    ("iprType", "种类"),
    ("iprPledgorName", "出质人"),
    ("iprPledgeeName", "质权人"),
    ("iprRegisterNum", "登记编号"),
    ("iprPledgePublicDate", "公示日期"),
    ("iprStatus", "状态"),
]
_PENALTY_FIELDS = [
    (("punishType", "penaltyType"), "违法行为类型"),
    (("punishContent", "penaltyReason"), "处罚内容"),
    (("punishAuthority", "penaltyAuthority"), "决定机关"),
    (("punishDecisionDate", "penaltyDate"), "决定日期"),
    ("punishDate", "公示日期"),
    (("punishId", "penaltyDecisionNumber"), "决定书文号"),
    ("penaltyAmount", "处罚金额"),
]
_ANOMALY_FIELDS = [
    ("createReason", "列入原因"),
    ("createAuthority", "列入决定机关"),
    ("createDate", "列入日期"),
    ("removeAuthority", "移出决定机关"),
    ("removeDate", "移出日期"),
    ("removeReason", "移出原因"),
]
_RESTRICTION_FIELDS = [
    ("efCaseNumber", "案号"),
    ("efExecutiveCourt", "执行法院"),
    ("efCaseCreateTime", "立案时间"),
    ("efLimitedPersonName", "限制消费人员"),
    ("efLimitedPersonCasePublishTime", "发布日期"),
    ("efLimitedPersonProvince", "省份"),
]


def _mortgagee_names(item: Mapping[str, Any]) -> str:
    names = []
    for m in _first_list(item.get("mortgageeList")):
        if isinstance(m, dict) and m.get("name"):
            names.append(str(m["name"]))
    return "、".join(names)


def build_core_analysis(
    score: Any,
    serious: Any,
    mortgage: Any,
    hearings: Any,
    litigation: Any,
    announce: Any,
    ip_pledge: Any,
    penalties: Any,
    anomalies: Any,
    restrictions: Any,
) -> Dict[str, Any]:
    s = score if isinstance(score, dict) else {}
    lit = litigation if isinstance(litigation, dict) else {}

    # Score KV (gauge reads 风险评分 / 风险等级 from this dict).
    score_kv = _kv_from(s, _SCORE_FIELDS)
    # 上游评级说明: risk_reason is a list[str] e.g. ["世界500强"].
    # It is the upstream model's explanation text, not a verified causal factor.
    reason = s.get("risk_reason") or s.get("riskReason")
    if isinstance(reason, list) and reason:
        score_kv["上游评级说明"] = "、".join(str(x) for x in reason if x)
    elif reason:
        score_kv["上游评级说明"] = _text(reason)

    # Litigation profile KV: real camelCase totals.
    litigation_kv = _kv_from(lit, _LITIGATION_TOTAL_FIELDS)

    # Litigation-stage distribution (bar chart) from the camelCase totals.
    litigation_dist: List[Dict[str, Any]] = []
    for key, label in _LITIGATION_DIST:
        n = _int(lit.get(key))
        if n is not None and n > 0:
            litigation_dist.append({"阶段": label, "数量": str(n)})

    serious_rows = _table_from(serious, _SERIOUS_FIELDS)
    mortgage_rows: List[Dict[str, Any]] = []
    for item in _first_list(mortgage):
        if not isinstance(item, dict):
            continue
        row: Dict[str, Any] = {}
        for key, label in _MORTGAGE_FIELDS:
            value = item.get(key)
            row[label] = _text(value) if value not in (None, "") else "-"
        row["抵押权人"] = _mortgagee_names(item) or "-"
        if _meaningful_row(row):
            mortgage_rows.append(row)
    hearing_rows = _table_from(hearings, _HEARING_FIELDS)
    announce_rows = _table_from(announce, _ANNOUNCE_FIELDS)
    pledge_rows = _table_from(ip_pledge, _PLEDGE_FIELDS)
    penalty_rows = _table_from(penalties, _PENALTY_FIELDS)
    anomaly_rows = _table_from(anomalies, _ANOMALY_FIELDS)
    restriction_rows = _table_from(restrictions, _RESTRICTION_FIELDS)

    def _section_note(label: str, payload: Any, rows: Sequence[Mapping[str, Any]]) -> str:
        total = _safe_total(payload) if isinstance(payload, dict) else None
        if total is None:
            return f"{label}：上游未返回总数，本次采集 {len(rows)} 条"
        return f"{label}：上游总数 {_text(total)} 条，本次采集 {len(rows)} 条"

    sections = [
        {"key": "score_overview", "title": "上游模型风险评分", "kind": "gauge", "note": "上游模型评分与等级（满分 100），不替代司法及合规明细核验", "chart": {"value_key": "风险评分", "level_key": "风险等级", "max": 100}},
        {"key": "litigation_overview", "title": "诉讼风险画像", "kind": "kv", "note": "按上游字段呈现开庭/立案/裁判/执行/限高/失信记录数；未提供当事人角色、裁判结果或履行状态"},
        {"key": "litigation_dist", "title": "诉讼阶段分布", "kind": "bar", "note": "按诉讼阶段统计记录数；同一事件可能在不同阶段各计一次，不能相加为独立案件数", "chart": {"name": "阶段", "value": "数量", "orient": "v"}, "columns": [("阶段", "阶段"), ("数量", "数量")]},
        {"key": "court_hearings", "title": "开庭公告", "kind": "table", "note": _section_note("开庭公告", hearings, hearing_rows), "columns": [("案号", "案号"), ("公告类型", "公告类型"), ("法院", "法院"), ("开庭日期", "开庭日期"), ("案由", "案由"), ("公告日期", "公告日期")]},
        {"key": "court_announcements", "title": "法院公告", "kind": "table", "note": _section_note("法院公告", announce, announce_rows), "columns": [("案号", "案号"), ("公告类型", "公告类型"), ("法院", "法院"), ("案由", "案由"), ("开庭日期", "开庭日期"), ("刊登日期", "刊登日期")]},
        {"key": "serious_violations", "title": "严重违法", "kind": "table", "note": _section_note("严重违法", serious, serious_rows), "columns": [("类别", "类别"), ("列入原因", "列入原因"), ("决定机关", "决定机关"), ("列入日期", "列入日期"), ("移除日期", "移除日期")]},
        {"key": "chattel_mortgage", "title": "动产抵押", "kind": "table", "note": _section_note("动产抵押", mortgage, mortgage_rows), "columns": [("登记日期", "登记日期"), ("登记机关", "登记机关"), ("抵押权人", "抵押权人"), ("被担保债权数额", "被担保债权数额"), ("种类", "种类"), ("公示日期", "公示日期")]},
        {"key": "ip_pledge", "title": "知识产权出质", "kind": "table", "note": _section_note("知识产权出质", ip_pledge, pledge_rows), "columns": [("知识产权名称", "知识产权名称"), ("种类", "种类"), ("质权人", "质权人"), ("登记编号", "登记编号"), ("公示日期", "公示日期"), ("状态", "状态")]},
        {"key": "penalties", "title": "行政处罚", "kind": "table", "note": _section_note("行政处罚", penalties, penalty_rows), "columns": [("违法行为类型", "违法行为类型"), ("处罚内容", "处罚内容"), ("决定机关", "决定机关"), ("决定日期", "决定日期"), ("决定书文号", "决定书文号"), ("处罚金额", "处罚金额")]},
        {"key": "business_anomalies", "title": "经营异常", "kind": "table", "note": _section_note("经营异常", anomalies, anomaly_rows), "columns": [("列入原因", "列入原因"), ("列入决定机关", "列入决定机关"), ("列入日期", "列入日期"), ("移出日期", "移出日期")]},
        {"key": "consumption_restrictions", "title": "限制高消费", "kind": "table", "note": _section_note("限制高消费", restrictions, restriction_rows), "columns": [("案号", "案号"), ("执行法院", "执行法院"), ("立案时间", "立案时间"), ("限制消费人员", "限制消费人员"), ("发布日期", "发布日期")]},
    ]

    return {
        "sections": sections,
        "score_overview": score_kv,
        "litigation_overview": litigation_kv,
        "litigation_dist": litigation_dist,
        "serious_violations": serious_rows,
        "chattel_mortgage": mortgage_rows,
        "court_hearings": hearing_rows,
        "court_announcements": announce_rows,
        "ip_pledge": pledge_rows,
        "penalties": penalty_rows,
        "business_anomalies": anomaly_rows,
        "consumption_restrictions": restriction_rows,
    }


def build_records(core: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in core.get("court_hearings") or []:
        out.append({
            "案号": _text_or_dash(item.get("案号")),
            "公告类型": _text_or_dash(item.get("公告类型")),
            "法院": _text_or_dash(item.get("法院")),
            "开庭日期": _text_or_dash(item.get("开庭日期")),
        })
    if not out:
        for item in core.get("consumption_restrictions") or []:
            out.append({
                "案号": _text_or_dash(item.get("案号")),
                "执行法院": _text_or_dash(item.get("执行法院")),
                "发布日期": _text_or_dash(item.get("发布日期")),
            })
    return out[:20]


def build_insights(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    metric_map = {m["label"]: str(m["value"]) for m in metrics}
    risk_score = metric_map.get("上游模型评分") or metric_map.get("风险评分")
    risk_level = metric_map.get("上游模型等级") or metric_map.get("风险等级")
    serious_total = metric_map.get("严重违法")

    judicial_exposure = bool(core.get("court_hearings") or core.get("court_announcements") or core.get("litigation_dist") or core.get("consumption_restrictions"))
    if risk_score or risk_level:
        evidence = "、".join(p for p in (f"上游模型评分 {risk_score}" if risk_score else None, f"上游模型等级 {risk_level}" if risk_level else None) if p)
        focus_hint = "（上游评分与等级按原值呈现，报告不自行按分数区间重分类）"
        if judicial_exposure:
            if risk_level and "低风险" in risk_level:
                focus_hint += "（司法记录非零，不能据此认定总体低风险，仍需结合明细交叉核验）"
            else:
                focus_hint += "（司法记录非零，仍需结合明细交叉核验）"
        insights.append({
            "feature": "综合风险水平",
            "evidence": f"{evidence}。{focus_hint}",
            "interpretation": "评分和等级是上游模型结果；应与司法、处罚等明细交叉核验，不应单独替代总体风险判断。",
        })
    # 上游评级说明 (risk_reason list) insight
    score_kv = core.get("score_overview") or {}
    reason = score_kv.get("上游评级说明") or score_kv.get("风险评级依据")
    if reason:
        insights.append({
            "feature": "上游评级说明",
            "evidence": f"上游原文：{reason}。",
            "interpretation": "该内容为上游模型返回的说明字段，不是经核验的风险成因，也不代表本报告对风险来源的认定；报告未获得模型权重或贡献度。",
        })
    # 诉讼阶段集中度 from litigation_dist bar chart rows.
    litigation_dist = core.get("litigation_dist") or []
    if litigation_dist:
        conc = _concentration(litigation_dist, 2)
        if conc:
            insights.append({
                "feature": "诉讼阶段集中度",
                "evidence": f"“{conc['top']}”为最主要的诉讼阶段，占比约 {conc['top_share']:.0f}%，前 2 阶段合计 {conc['cr']:.0f}%（CR2）。",
                "interpretation": "阶段占比仅描述上游记录数分布；未提供当事人角色、裁判结果或履行状态，不能据此推断责任、败诉、未履行或失信。",
            })
        dimension_sum = sum(_int(row.get("数量")) or 0 for row in litigation_dist if isinstance(row, dict))
        if dimension_sum:
            insights.append({
                "feature": "司法记录计数口径",
                "evidence": f"各司法阶段记录数算术合计为 {dimension_sum}（未去重）。",
                "interpretation": "同一案件可能跨开庭、公告、裁判或执行阶段重复出现，该合计不代表独立案件数。",
            })
    if serious_total and serious_total not in ("0", "-"):
        insights.append({
            "feature": "严重违法",
            "evidence": f"严重违法记录 {serious_total} 条。",
            "interpretation": "该值仅描述上游严重违法产品返回的记录数；具体事由、当前状态及业务影响需逐条核验。",
        })
    restrictions = core.get("consumption_restrictions") or []
    if restrictions:
        insights.append({
            "feature": "限制高消费",
            "evidence": f"限制高消费记录 {len(restrictions)} 条。",
            "interpretation": "该值仅描述上游返回的限制高消费记录；需核验案件主体身份、法律文书与当前状态，不据此推断责任或履行情况。",
        })
    anomalies = core.get("business_anomalies") or []
    if anomalies:
        insights.append({
            "feature": "经营异常",
            "evidence": f"经营异常记录 {len(anomalies)} 条。",
            "interpretation": "该值仅描述上游经营异常产品返回的记录；列入原因、移出状态及当前影响需逐条核验。",
        })
    # risk dimension coverage
    dimension_keys = [
        "serious_violations", "chattel_mortgage", "court_hearings", "court_announcements",
        "ip_pledge", "penalties", "business_anomalies", "consumption_restrictions",
    ]
    populated = sum(1 for k in dimension_keys if (core.get(k) or []))
    if populated:
        insights.append({
            "feature": "风险维度覆盖",
            "evidence": f"10 大风险维度中有 {populated} 个维度存在记录。",
            "interpretation": "该值仅描述本次查询中有记录的产品维度数量，不等于独立事件数、责任认定或整体风险等级。",
        })
    if not insights:
        insights.append({
            "feature": "数据完整性",
            "evidence": "部分维度未返回有效数据。",
            "interpretation": "建议核对匹配关键词是否为企业全称，或检查 MCP 连接与上游数据产品覆盖范围。",
        })
    return insights


def _populated_section_titles(core: Mapping[str, Any]) -> List[str]:
    titles: List[str] = []
    sections = core.get("sections")
    if not isinstance(sections, list):
        return titles
    for section in sections:
        if not isinstance(section, dict):
            continue
        key = section.get("key")
        title = section.get("title")
        if isinstance(key, str) and isinstance(title, str) and _has_evidence(core.get(key)):
            titles.append(title)
    return titles


def _with_judicial_section_limits(core: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(core)
    sections = core.get("sections")
    if not isinstance(sections, list):
        return normalized
    disclosure = "未提供当事人角色、裁判结果或履行状态"
    normalized_sections: List[Any] = []
    for section in sections:
        if not isinstance(section, dict):
            normalized_sections.append(section)
            continue
        item = dict(section)
        if item.get("key") in {"litigation_overview", "litigation_dist"}:
            note = str(item.get("note") or "按司法阶段统计记录数")
            if disclosure not in note:
                item["note"] = f"{note}；{disclosure}"
        normalized_sections.append(item)
    normalized["sections"] = normalized_sections
    return normalized


def build_metrics(
    score: Any,
    serious: Any,
    hearings: Any,
    announce: Any,
    penalties: Any,
    anomalies: Any,
    restrictions: Any,
    litigation: Any,
    mortgage: Any = None,
    ip_pledge: Any = None,
) -> List[Dict[str, Any]]:
    metrics: List[Dict[str, Any]] = []
    s = score if isinstance(score, dict) and "_error" not in score else {}
    lit = litigation if isinstance(litigation, dict) and "_error" not in litigation else {}

    def _ttotal(payload: Any) -> str:
        total = _safe_total(payload)
        if total is not None:
            return _text(total)
        return "-"

    # Preserve upstream score and level verbatim; do not impose local thresholds.
    metrics.append({"label": "上游模型评分", "value": _text_or_dash(s.get("risk_score")), "hint": "上游模型输出（满分 100），需与风险明细交叉核验"})
    risk_level_val = _text_or_dash(s.get("risk_level"))
    metrics.append({"label": "上游模型等级", "value": risk_level_val, "hint": "上游模型输出，不代表报告综合定性"})

    def _lit_int(key: str) -> str:
        n = _int(lit.get(key))
        return str(n) if n is not None else "-"

    metrics.append({"label": "开庭公告", "value": _lit_int("caKaitingTotal"), "hint": "开庭公告记录数"})
    metrics.append({"label": "立案公告", "value": _lit_int("caLianTotal"), "hint": "立案公告记录数"})
    metrics.append({"label": "法院公告", "value": _lit_int("caTotal"), "hint": "法院公告记录数"})
    metrics.append({"label": "裁判文书", "value": _lit_int("jdTotal"), "hint": "裁判文书记录数"})
    metrics.append({"label": "被执行人", "value": _lit_int("enforcementTotal"), "hint": "被执行人记录数"})
    metrics.append({"label": "限制高消费", "value": _lit_int("limitedTotal"), "hint": "限制高消费记录数"})
    metrics.append({"label": "失信被执行", "value": _lit_int("edTotal"), "hint": "失信被执行人记录数"})
    metrics.append({"label": "严重违法", "value": _ttotal(serious), "hint": "严重违法记录条数"})
    metrics.append({"label": "动产抵押", "value": _ttotal(mortgage), "hint": "上游 mortgageCount"})
    metrics.append({"label": "知识产权出质", "value": _ttotal(ip_pledge), "hint": "上游 iprPledgeCount"})
    metrics.append({"label": "行政处罚", "value": _ttotal(penalties), "hint": "行政处罚记录条数"})
    metrics.append({"label": "经营异常", "value": _ttotal(anomalies), "hint": "经营异常记录条数"})
    return [m for m in metrics if m.get("value") not in ("", None, "-")]


def build_abstract(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]) -> str:
    name = subject.get("enterprise") or subject.get("match_raw") or "目标企业"
    section_titles = _populated_section_titles(core)
    if section_titles:
        parts = [f"本报告以“{name}”为分析对象，基于企业风险公开数据。本次有效数据覆盖：{'、'.join(section_titles)}。"]
    else:
        parts = [f"本报告以“{name}”为分析对象；本次未返回有效风险数据章节，不生成风险判断。"]
    if metrics:
        kv = "、".join(f"{m['label']} {m['value']}" for m in metrics[:5])
        parts.append(f"关键指标包括：{kv}。")
    parts.append("报告仅对已返回字段、记录数与分布作结构化描述；司法阶段计数不包含当事人角色、裁判结果或履行状态。")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Dry-run sample
# --------------------------------------------------------------------------- #

def build_dry_run_payload(raw: str, keyword_type: str) -> Dict[str, Any]:
    try:
        sample = load_json_file(SAMPLE_PATH)
    except Exception:
        sample = {}
    sample = sample if isinstance(sample, dict) else {}
    subject = sample.get("subject") or {"enterprise": raw, "matchKeyword": raw, "keywordType": keyword_type, "match_raw": raw}
    subject = {**subject, "match_raw": raw, "keywordType": keyword_type}
    core = sample.get("core_analysis") or {}
    metrics = sample.get("metrics") or []
    return _assemble(subject, core, metrics, dry_run=True)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #

def _assemble(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], *, dry_run: bool) -> Dict[str, Any]:
    normalized_core = _with_judicial_section_limits(core)
    abstract = build_abstract(subject, normalized_core, metrics)
    records = build_records(normalized_core)
    insights = build_insights(subject, normalized_core, metrics)
    # Quality gate: count populated core-analysis sections.
    ca = normalized_core
    secs = ca.get("sections", [])
    if secs:
        total_secs = len(secs)
        populated = 0
        for section in secs:
            key = section.get("key") if isinstance(section, dict) else None
            if isinstance(key, str) and _has_evidence(ca.get(key)):
                populated += 1
    else:
        total_secs = max(1, len([k for k in ca if k != "sections"]))
        populated = sum(1 for k in ca if k != "sections" and _has_evidence(ca.get(k)))
    quality_report = {
        "total_sections": total_secs,
        "populated_sections": populated,
        "empty_sections": total_secs - populated,
        "coverage_pct": round(populated / max(1, total_secs) * 100),
    }
    if populated == 0:
        import sys
        print("⚠️ 质量门禁警告: 所有核心分析维度均无数据", file=sys.stderr)
    title = f"{subject.get('enterprise') or '目标企业'} 企业风险分析报告"
    report = {
        "report_type": REPORT_TYPE,
        "title": title,
        "banner": REPORT_BANNER,
        "subject": dict(subject),
        "abstract": abstract,
        "summary": abstract,
        "executive_summary": [item["interpretation"] for item in insights][:5] or [abstract[:120]],
        "metrics": list(metrics),
        "caliber": build_caliber(subject),
        "core_analysis": normalized_core,
        "representative_records": records,
        "insights": insights,
        "data_source": {
            "mcp_server": "enterprise-risk-mcp-server",
            "products": [
                {"name": "风险评分", "product_id": "68fb5d6c5e8fca298e2b1c7f"},
                {"name": "严重违法", "product_id": "669fb97b76742e172f2a5193"},
                {"name": "动产抵押", "product_id": "66a0e19aa84e3d948a9fc373"},
                {"name": "开庭公告", "product_id": "66a0e123bc2d198e864482c4"},
                {"name": "诉讼风险画像", "product_id": "66bb1aa834d3cd3e43928163"},
                {"name": "法院公告", "product_id": "669f997d0839b73a327efb4f"},
                {"name": "知识产权出质", "product_id": "66a0e1ca10026dc291e21049"},
                {"name": "行政处罚", "product_id": "66a24a59515324c521d6610d"},
                {"name": "经营异常", "product_id": "66a248f381d41651f2689d95"},
                {"name": "限制高消费", "product_id": "669e3087d6e30dd7e6d03e55"},
            ],
            "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "dry_run": dry_run,
            "quality_report": quality_report,
        },
    }
    return apply_content_review(report)


@paid_call_scope
def build_payload(raw: str, keyword_type: str, page_size: int, max_pages: Optional[int] = 1) -> Dict[str, Any]:
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages 必须为正整数")
    resolved = resolve_enterprise_name(raw)
    if resolved.get("requires_confirmation"):
        subject = build_subject(raw, resolved, keyword_type)
        return _apply_resolution_limit(_assemble(subject, {"sections": []}, [], dry_run=False), resolved)
    enterprise = resolved["enterprise"]
    mk_args: Dict[str, Any] = {"matchKeyword": enterprise, "keywordType": keyword_type}

    score = _safe_call(T_SCORE, mk_args)
    serious = _safe_call(T_SERIOUS, mk_args)
    mortgage = _safe_call(T_MORTGAGE, mk_args)
    hearings = _collect_detail_pages(T_HEARINGS, {**mk_args, "pageIndex": 1, "pageSize": page_size}, max_pages)
    litigation = _safe_call(T_LITIGATION, mk_args)
    announce = _collect_detail_pages(T_ANNOUNCE, {**mk_args, "pageIndex": 1, "pageSize": page_size}, max_pages)
    ip_pledge = _safe_call(T_IP_PLEDGE, mk_args)
    penalties = _safe_call(T_PENALTIES, mk_args)
    anomalies = _safe_call(T_ANOMALIES, mk_args)
    restrictions = _collect_detail_pages(T_RESTRICTIONS, {**mk_args, "pageIndex": 1, "pageSize": page_size}, max_pages)

    subject = build_subject(raw, resolved, keyword_type)
    core = build_core_analysis(score, serious, mortgage, hearings, litigation, announce, ip_pledge, penalties, anomalies, restrictions)
    metrics = build_metrics(
        score, serious, hearings, announce, penalties, anomalies, restrictions, litigation,
        mortgage=mortgage, ip_pledge=ip_pledge,
    )
    _derive_core_metrics(metrics, core if isinstance(core, dict) else {})
    # --- Enterprise profile enrichment (from fuzzy_search) ---
    _enrich_metrics_with_profile(metrics, resolved.get("record") if isinstance(resolved, dict) else None)
    report = _assemble(subject, core, metrics, dry_run=False)
    report = attach_pagination(report, {"开庭公告": hearings, "法院公告": announce, "限制高消费": restrictions})
    return _attach_call_status(report, {"风险评分": score, "严重违法": serious, "动产抵押": mortgage, "开庭公告": hearings, "诉讼画像": litigation, "法院公告": announce, "知识产权出质": ip_pledge, "行政处罚": penalties, "经营异常": anomalies, "限制高消费": restrictions})


def _refresh_quality_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh section-fill metrics after offline review changed sections.

    ``0`` is a populated value; None/""/[]/{} and documented empty sentinels are
    empty. coverage_pct is section fill only, never an accuracy claim.
    """
    core = report.get("core_analysis") or {}
    sections = core.get("sections")
    if isinstance(sections, list) and sections:
        total = len(sections)
        populated = sum(1 for s in sections if isinstance(s, dict) and _has_evidence(core.get(s.get("key"))))
    else:
        keys = [k for k in core if k != "sections"]
        total = max(1, len(keys))
        populated = sum(1 for k in keys if _has_evidence(core.get(k)))
    source = report.setdefault("data_source", {})
    source["quality_report"] = {
        "total_sections": total,
        "populated_sections": populated,
        "empty_sections": total - populated,
        "coverage_pct": round(populated / max(1, total) * 100),
        "metric": "section_fill_rate",
        "note": "章节填充率，仅表示有返回内容的 section 占比，不是内容准确率",
    }
    return report


def _merge_review_records(previous: Any, current: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Keep earlier review records when the same report is processed again."""
    merged: List[Dict[str, Any]] = []
    seen = set()
    for item in list(previous or []) + list(current or []):
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        key = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def apply_content_review(report: Mapping[str, Any], source_evidence: Optional[Any] = None) -> Dict[str, Any]:
    """Rebuild risk narrative from fields already present in a report.

    Pure/offline: no MCP call and no new facts. The only semantic relabeling is
    evidence-backed: an upstream composite key named
    "名称/类型/状态/年份" is renamed to "阶段" (the rows contain stage labels),
    and "风险评级依据" becomes "上游评级说明" because the upstream reason text
    (e.g. "世界500强") is not a verified cause of the score.
    """
    out = copy.deepcopy(dict(report))
    corrections: List[Dict[str, Any]] = []
    subject = out.get("subject") or {}
    core = out.get("core_analysis") or {}
    source = out.get("data_source") or {}
    previous_review = source.get("content_review") or {}

    rows = core.get("litigation_dist") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "名称/类型/状态/年份" in row:
            row["阶段"] = row.pop("名称/类型/状态/年份")
            corrections.append({
                "field": "core_analysis.litigation_dist[].名称/类型/状态/年份",
                "before": "名称/类型/状态/年份",
                "after": "阶段",
                "reason": "该列实际只承载诉讼阶段名称（开庭公告/立案公告等），复合列名会误导为多维字段",
            })
    for section in core.get("sections") or []:
        if not isinstance(section, dict) or section.get("key") != "litigation_dist":
            continue
        section["chart"] = {"name": "阶段", "value": "数量", "orient": "v"}
        section["columns"] = [("阶段", "阶段"), ("数量", "数量")]
        note = "按诉讼阶段统计记录数；同一事件可能在不同阶段各计一次，不能相加为独立案件数"
        if "未提供当事人角色、裁判结果或履行状态" not in note:
            note += "；未提供当事人角色、裁判结果或履行状态"
        section["note"] = note

    score = core.get("score_overview") or {}
    if isinstance(score, dict) and "风险评级依据" in score:
        before = score.pop("风险评级依据")
        score["上游评级说明"] = before
        corrections.append({
            "field": "core_analysis.score_overview.风险评级依据",
            "before": "风险评级依据",
            "after": "上游评级说明",
            "reason": "该字段是上游模型说明原文，不是经核验的风险成因",
        })

    insights = build_insights(subject, core, out.get("metrics") or [])
    out["insights"] = insights
    out["executive_summary"] = [item["interpretation"] for item in insights][:5] or [build_abstract(subject, core, out.get("metrics") or [])[:120]]
    abstract = build_abstract(subject, core, out.get("metrics") or [])
    out["abstract"] = abstract
    out["summary"] = abstract
    source = out.get("data_source") or {}
    source["content_review"] = {
        "mode": "offline_report_fields_only",
        "source_evidence_supplied": bool(source_evidence),
        "reviewed_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "corrections": _merge_review_records(previous_review.get("corrections"), corrections),
        "not_changed": [
            "未重新查询 MCP；未新增案件、处罚、执行或金额事实",
            "上游评分/等级原值保留，不按分数区间重分类",
            "缺失当事人角色、裁判结果、履行状态仍不推断",
        ],
    }
    out["data_source"] = source
    return _refresh_quality_report(out)




def main() -> None:
    parser = argparse.ArgumentParser(description="Compose an enterprise-risk analysis report via the risk MCP.")
    parser.add_argument("--enterprise", required=True, help="企业全称或关键词（关键词将自动模糊补全）")
    parser.add_argument("--keyword-type", default="name", help="主体类型：name/nameId/regNumber/socialCreditCode")
    parser.add_argument("--page-size", type=int, default=10, help="分页类风险维度单页大小（最多 50）")
    parser.add_argument("--max-pages", type=int, default=1, help="分页类风险明细最多查询页数（正整数，默认 1 页；按报告结论需要先计划预算再显式扩大）")
    parser.add_argument("--dry-run", action="store_true", help="不调用真实 MCP，使用样例数据组装报告骨架")
    parser.add_argument("--output", help="输出 JSON 路径；省略则打印到 stdout")
    parser.add_argument("--report-output", help="同时输出 HTML 报告（.html）与 Markdown 报告（.md）")
    parser.add_argument("--pdf-output", help="额外输出 PDF 报告（.pdf）；需要 Playwright + Chromium")
    args = parser.parse_args()

    if not 1 <= args.page_size <= 50:
        parser.error("--page-size 必须在 1 到 50 之间")
    if args.max_pages < 1:
        parser.error("--max-pages 必须为正整数")
    if args.dry_run:
        payload = build_dry_run_payload(args.enterprise, args.keyword_type)
    else:
        payload = build_payload(args.enterprise, args.keyword_type, args.page_size, args.max_pages)

    if args.output:
        out = pathlib.Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_dumps(payload, pretty=True), encoding="utf-8")
        print_json({"ok": True, "json": str(out), "dry_run": args.dry_run})
    else:
        print_json(payload)

    if args.report_output:
        base_out = pathlib.Path(args.report_output).expanduser()
        base_out.parent.mkdir(parents=True, exist_ok=True)
        html_path = base_out.with_suffix(".html") if base_out.suffix.lower() not in (".html", ".htm") else base_out
        md_path = html_path.with_suffix(".md")
        html_path.write_text(render_html(payload), encoding="utf-8")
        md_path.write_text(render_markdown(payload), encoding="utf-8")
        if args.pdf_output:
            pdf_path = pathlib.Path(args.pdf_output).expanduser()
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            html_to_pdf(render_html(payload), str(pdf_path))
        print_json({"ok": True, "html": str(html_path), "markdown": str(md_path), "pdf": str(pdf_path) if args.pdf_output else None, "dry_run": args.dry_run})


if __name__ == "__main__":
    main()
