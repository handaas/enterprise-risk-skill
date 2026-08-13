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
import datetime as dt
import json
import pathlib
import sys
from typing import Any, Dict, List, Mapping, Optional

from common import REPORT_BANNER, REPORT_TYPE, json_dumps, load_json_file, print_json
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


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _is_api_error(value: Any) -> bool:
    """Detect MCP API error responses (not empty data, but actual failures like 405)."""
    if value is None:
        return False
    if isinstance(value, str):
        return any(s in value for s in ("接口调用失败", "查询失败", "状态码：4", "状态码：5"))
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, str) and any(s in v for s in ("接口调用失败", "查询失败", "状态码：4", "状态码：5")):
                return True
    return False

def _first_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if _is_api_error(value):
            return []
        # Upstream "empty" responses come back as {"text": "查询数据为空"} or
        # {"error": "..."}; treat these as empty so tables don't render a
        # phantom all-"-" row.
        if set(value.keys()) <= {"text", "error", "code", "_error"} and not any(
            value.get(k) for k in ("resultList", "list", "items", "data")
        ):
            return []
        for key in ("resultList", "list", "items", "data"):
            if isinstance(value.get(key), list):
                return value[key]
    if value in (None, "", {}):
        return []
    return [value]


def _first_record(value: Any) -> Dict[str, Any]:
    for record in _first_list(value):
        if isinstance(record, dict):
            return record
    if isinstance(value, dict):
        return value
    return {}


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


def _int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_call(tool: str, arguments: Dict[str, Any]) -> Any:
    try:
        result = mcp_client.call_tool(tool, arguments)
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
        return payload.get("total")
    return None


def _concentration(rows: List[Mapping[str, Any]], top_n: int = 3) -> Dict[str, Any]:
    """Compute top-N concentration (CRn) and dominant category.

    Rows use the unified {名称/类型/状态/年份, 数量} shape produced by
    section builders so it is interchangeable across skills.
    """
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
        return {"keyword": "", "enterprise": "", "resolved": False, "reason": "关键词为空"}
    if any(suffix in raw for suffix in ("公司", "集团", "有限", "院", "厂", "中心", "事务所", "合作社", "合伙")):
        return {"keyword": raw, "enterprise": raw, "resolved": True, "reason": "视为企业全称"}
    fuzzy = _safe_call(T_FUZZY, {"matchKeyword": raw, "pageSize": 1})
    record = _first_record(fuzzy)
    name = str(record.get("name") or "").strip()
    if name:
        return {"keyword": raw, "enterprise": name, "resolved": True, "reason": "由关键词模糊查询补全", "fuzzy_total": _int(_safe_total(fuzzy)), "record": record}
    return {"keyword": raw, "enterprise": raw, "resolved": False, "reason": "模糊查询未命中企业全称，按关键词直查"}


# --------------------------------------------------------------------------- #
# Enterprise profile helpers (from fuzzy_search record)
# --------------------------------------------------------------------------- #

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
        return _text(val) if val else "-"


def _enrich_metrics_with_profile(metrics: List[Dict[str, Any]], record: Any) -> List[Dict[str, Any]]:
    """Append enterprise profile metrics from a fuzzy_search record."""
    if not isinstance(record, dict):
        return metrics
    _prof = _extract_profile(record)
    if _prof.get("reg_capital") and _prof["reg_capital"] not in ("-", "", None):
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
    hearings = core.get("court_hearings", []) if isinstance(core, dict) else []
    announcements = core.get("court_announcements", []) if isinstance(core, dict) else []
    penalties = core.get("penalties", []) if isinstance(core, dict) else []
    restrictions = core.get("consumption_restrictions", []) if isinstance(core, dict) else []
    lit_overview = core.get("litigation_overview", {}) if isinstance(core, dict) else {}
    if isinstance(lit_overview, dict) and lit_overview:
        total_lit = sum(int(v or 0) for v in lit_overview.values() if str(v).isdigit())
        if total_lit > 0:
            metrics.append({"label": "司法记录总数", "value": str(total_lit), "hint": "诉讼/立案/裁判/执行记录合计"})
    if isinstance(penalties, list) and penalties:
        metrics.append({"label": "行政处罚数", "value": str(len(penalties)), "hint": "行政处罚明细记录数"})
    if isinstance(restrictions, list) and restrictions:
        metrics.append({"label": "限高记录数", "value": str(len(restrictions)), "hint": "限制高消费记录数"})
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
        "limit": "数据来自公开风险数据库；部分维度可能存在更新延迟或公示滞后期。",
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
            row[label] = _text(item.get(key)) or "-"
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
    ("punishType", "违法行为类型"),
    ("punishContent", "处罚内容"),
    ("punishAuthority", "决定机关"),
    ("punishDecisionDate", "决定日期"),
    ("punishDate", "公示日期"),
    ("punishId", "决定书文号"),
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
    # 风险评级依据: risk_reason is a list[str] e.g. ["世界500强"].
    reason = s.get("risk_reason") or s.get("riskReason")
    if isinstance(reason, list) and reason:
        score_kv["风险评级依据"] = "、".join(str(x) for x in reason if x)
    elif reason:
        score_kv["风险评级依据"] = _text(reason)

    # Litigation profile KV: real camelCase totals.
    litigation_kv = _kv_from(lit, _LITIGATION_TOTAL_FIELDS)

    # Litigation-stage distribution (bar chart) from the camelCase totals.
    litigation_dist: List[Dict[str, Any]] = []
    for key, label in _LITIGATION_DIST:
        n = _int(lit.get(key))
        if n is not None and n > 0:
            litigation_dist.append({"名称/类型/状态/年份": label, "数量": str(n)})

    serious_rows = _table_from(serious, _SERIOUS_FIELDS)
    mortgage_rows: List[Dict[str, Any]] = []
    for item in _first_list(mortgage):
        if not isinstance(item, dict):
            continue
        row: Dict[str, Any] = {}
        for key, label in _MORTGAGE_FIELDS:
            row[label] = _text(item.get(key)) or "-"
        row["抵押权人"] = _mortgagee_names(item) or "-"
        mortgage_rows.append(row)
    hearing_rows = _table_from(hearings, _HEARING_FIELDS)
    announce_rows = _table_from(announce, _ANNOUNCE_FIELDS)
    pledge_rows = _table_from(ip_pledge, _PLEDGE_FIELDS)
    penalty_rows = _table_from(penalties, _PENALTY_FIELDS)
    anomaly_rows = _table_from(anomalies, _ANOMALY_FIELDS)
    restriction_rows = _table_from(restrictions, _RESTRICTION_FIELDS)

    def _total(payload: Any) -> Any:
        return _safe_total(payload) if isinstance(payload, dict) else None

    sections = [
        {"key": "score_overview", "title": "风险评分", "kind": "gauge", "note": "综合风险评分与等级（满分 100，分值越低风险越高）", "chart": {"value_key": "风险评分", "level_key": "风险等级", "max": 100}},
        {"key": "litigation_overview", "title": "诉讼风险画像", "kind": "kv", "note": "诉讼风险整体画像（开庭/立案/裁判/执行/限高/失信）"},
        {"key": "litigation_dist", "title": "诉讼阶段分布", "kind": "bar", "note": "按诉讼阶段统计记录数", "chart": {"name": "名称/类型/状态/年份", "value": "数量", "orient": "v"}, "columns": [("阶段", "名称/类型/状态/年份"), ("数量", "数量")]},
        {"key": "court_hearings", "title": "开庭公告", "kind": "table", "note": f"开庭公告 {_total(hearings) or '若干'} 条", "columns": [("案号", "案号"), ("公告类型", "公告类型"), ("法院", "法院"), ("开庭日期", "开庭日期"), ("案由", "案由"), ("公告日期", "公告日期")]},
        {"key": "court_announcements", "title": "法院公告", "kind": "table", "note": f"法院公告 {_total(announce) or '若干'} 条", "columns": [("案号", "案号"), ("公告类型", "公告类型"), ("法院", "法院"), ("案由", "案由"), ("开庭日期", "开庭日期"), ("刊登日期", "刊登日期")]},
        {"key": "serious_violations", "title": "严重违法", "kind": "table", "note": f"严重违法记录 {_total(serious) or '若干'} 条", "columns": [("类别", "类别"), ("列入原因", "列入原因"), ("决定机关", "决定机关"), ("列入日期", "列入日期"), ("移除日期", "移除日期")]},
        {"key": "chattel_mortgage", "title": "动产抵押", "kind": "table", "note": f"动产抵押记录 {_total(mortgage) or '若干'} 条", "columns": [("登记日期", "登记日期"), ("登记机关", "登记机关"), ("抵押权人", "抵押权人"), ("被担保债权数额", "被担保债权数额"), ("种类", "种类"), ("公示日期", "公示日期")]},
        {"key": "ip_pledge", "title": "知识产权出质", "kind": "table", "note": f"知识产权出质记录 {_total(ip_pledge) or '若干'} 条", "columns": [("知识产权名称", "知识产权名称"), ("种类", "种类"), ("质权人", "质权人"), ("登记编号", "登记编号"), ("公示日期", "公示日期"), ("状态", "状态")]},
        {"key": "penalties", "title": "行政处罚", "kind": "table", "note": f"行政处罚记录 {_total(penalties) or '若干'} 条", "columns": [("违法行为类型", "违法行为类型"), ("处罚内容", "处罚内容"), ("决定机关", "决定机关"), ("决定日期", "决定日期"), ("决定书文号", "决定书文号")]},
        {"key": "business_anomalies", "title": "经营异常", "kind": "table", "note": f"经营异常记录 {_total(anomalies) or '若干'} 条", "columns": [("列入原因", "列入原因"), ("列入决定机关", "列入决定机关"), ("列入日期", "列入日期"), ("移出日期", "移出日期")]},
        {"key": "consumption_restrictions", "title": "限制高消费", "kind": "table", "note": f"限制高消费记录 {_total(restrictions) or '若干'} 条", "columns": [("案号", "案号"), ("执行法院", "执行法院"), ("立案时间", "立案时间"), ("限制消费人员", "限制消费人员"), ("发布日期", "发布日期")]},
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
            "案号": item.get("案号") or "-",
            "公告类型": item.get("公告类型") or "-",
            "法院": item.get("法院") or "-",
            "开庭日期": item.get("开庭日期") or "-",
        })
    if not out:
        for item in core.get("consumption_restrictions") or []:
            out.append({
                "案号": item.get("案号") or "-",
                "执行法院": item.get("执行法院") or "-",
                "发布日期": item.get("发布日期") or "-",
            })
    return out[:20]


def build_insights(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    metric_map = {m["label"]: str(m["value"]) for m in metrics}
    risk_score = metric_map.get("风险评分")
    risk_level = metric_map.get("风险等级")
    serious_total = metric_map.get("严重违法")

    if risk_score or risk_level:
        evidence = "、".join(p for p in (f"风险评分 {risk_score}" if risk_score else None, f"风险等级 {risk_level}" if risk_level else None) if p)
        # Score semantics: 100 = safest, lower = riskier.
        focus_hint = ""
        try:
            score_n = float(risk_score) if risk_score else None
            if score_n is not None:
                if score_n < 40:
                    focus_hint = "（评分<40 属高风险，需重点核查诉讼、严重违法与限制高消费维度）"
                elif score_n < 70:
                    focus_hint = "（评分 40-70 属中等风险，建议关注经营异常与行政处罚）"
                else:
                    focus_hint = "（评分≥70 整体风险较低，建议常规跟踪）"
        except (TypeError, ValueError):
            pass
        insights.append({
            "feature": "综合风险水平",
            "evidence": f"{evidence}。{focus_hint}",
            "interpretation": "风险评分与等级反映企业整体风险敞口；等级越高，提示越需要关注潜在经营、信用与合规风险。",
        })
    # 风险评级依据 (risk_reason list) insight
    score_kv = core.get("score_overview") or {}
    reason = score_kv.get("风险评级依据")
    if reason:
        insights.append({
            "feature": "风险评级依据",
            "evidence": f"评级依据：{reason}。",
            "interpretation": "评级依据给出风险评分的主要驱动因素；正面依据（如头部企业）会拉高评分，负面依据（如严重违法、被执行）会拉低评分。",
        })
    # 诉讼阶段集中度 from litigation_dist bar chart rows.
    litigation_dist = core.get("litigation_dist") or []
    if litigation_dist:
        conc = _concentration(litigation_dist, 2)
        if conc:
            insights.append({
                "feature": "诉讼阶段集中度",
                "evidence": f"“{conc['top']}”为最主要的诉讼阶段，占比约 {conc['top_share']:.0f}%，前 2 阶段合计 {conc['cr']:.0f}%（CR2）。",
                "interpretation": "开庭/立案偏多通常意味着诉讼处于活跃推进状态；裁判/执行/限高偏多则意味着已有较多未履行义务或败诉案件，风险敞口更大。",
            })
    if serious_total and serious_total not in ("0", "-"):
        insights.append({
            "feature": "严重违法",
            "evidence": f"严重违法记录 {serious_total} 条。",
            "interpretation": "严重违法记录属于高风险信号，可能影响企业信用评级、招投标与政府合作，建议重点核查并跟踪整改情况。",
        })
    restrictions = core.get("consumption_restrictions") or []
    if restrictions:
        insights.append({
            "feature": "限制高消费",
            "evidence": f"限制高消费记录 {len(restrictions)} 条。",
            "interpretation": "被限制高消费通常源于未履行生效法律文书义务，是企业信用与履约能力的负面信号。",
        })
    anomalies = core.get("business_anomalies") or []
    if anomalies:
        insights.append({
            "feature": "经营异常",
            "evidence": f"经营异常记录 {len(anomalies)} 条。",
            "interpretation": "经营异常多因公示信息隐瞒、地址失联等触发；若未及时移出，将持续影响企业信用。",
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
            "interpretation": "风险维度覆盖面越广，说明企业暴露的风险点越多；集中爆发于诉讼/违法/高消费维度时，整体风险敞口显著上升。",
        })
    if not insights:
        insights.append({
            "feature": "数据完整性",
            "evidence": "部分维度未返回有效数据。",
            "interpretation": "建议核对匹配关键词是否为企业全称，或检查 MCP 连接与上游数据产品覆盖范围。",
        })
    return insights


def build_metrics(score: Any, serious: Any, hearings: Any, announce: Any, penalties: Any, anomalies: Any, restrictions: Any, litigation: Any) -> List[Dict[str, Any]]:
    metrics: List[Dict[str, Any]] = []
    s = score if isinstance(score, dict) and "_error" not in score else {}
    lit = litigation if isinstance(litigation, dict) and "_error" not in litigation else {}

    def _ttotal(payload: Any) -> str:
        if isinstance(payload, dict) and payload.get("total") is not None:
            return _text(payload.get("total"))
        return "-"

    # risk_score / risk_level are real snake_case keys; high score = low risk.
    metrics.append({"label": "风险评分", "value": _text(s.get("risk_score")) or "-", "hint": "综合风险评分（满分 100）"})
    risk_level_val = _text(s.get("risk_level")) or "-"
    risk_score_n = _int(s.get("risk_score"))
    level_delta = ""
    if risk_level_val != "-" and risk_score_n is not None:
        if risk_level_val.find("高") >= 0 or risk_score_n < 40:
            level_delta = "重点关注"
        elif risk_level_val.find("中") >= 0 or risk_score_n < 70:
            level_delta = "中等关注"
        else:
            level_delta = "整体偏低"
    metrics.append({"label": "风险等级", "value": risk_level_val, "hint": "综合风险等级", "delta": level_delta} if level_delta else {"label": "风险等级", "value": risk_level_val, "hint": "综合风险等级"})

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
    metrics.append({"label": "行政处罚", "value": _ttotal(penalties), "hint": "行政处罚记录条数"})
    metrics.append({"label": "经营异常", "value": _ttotal(anomalies), "hint": "经营异常记录条数"})
    return [m for m in metrics if m.get("value") not in ("", None, "-")]


def build_abstract(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]]) -> str:
    name = subject.get("enterprise") or subject.get("match_raw") or "目标企业"
    parts = [f"本报告以“{name}”为分析对象，基于企业风险公开数据，系统呈现企业风险评分、诉讼风险画像及严重违法、动产抵押、开庭公告、法院公告、知识产权出质、行政处罚、经营异常、限制高消费等多维度风险记录。"]
    if metrics:
        kv = "、".join(f"{m['label']} {m['value']}" for m in metrics[:5])
        parts.append(f"关键指标包括：{kv}。")
    parts.append("报告围绕风险维度覆盖度与高风险信号给出结构化解读，便于尽职调查、合作准入与风险预警决策参考。")
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

def _assemble(subject: Mapping[str, Any], core: Mapping[str, Any], metrics: List[Mapping[str, Any]], *, dry_run: bool) -> Dict[str, Any]:
    abstract = build_abstract(subject, core, metrics)
    records = build_records(core)
    insights = build_insights(subject, core, metrics)
    # Quality gate: count populated core-analysis sections.
    ca = core if isinstance(core, dict) else {}
    secs = ca.get("sections", [])
    if secs:
        total_secs = len(secs)
        populated = sum(1 for s in secs if isinstance(s, dict) and ca.get(s.get("key")) not in (None, "", [], {}))
    else:
        total_secs = max(1, len([k for k in ca if k != "sections"]))
        populated = sum(1 for k in ca if k != "sections" and ca.get(k) not in (None, "", [], {}))
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
    return {
        "report_type": REPORT_TYPE,
        "title": title,
        "banner": REPORT_BANNER,
        "subject": dict(subject),
        "abstract": abstract,
        "summary": abstract,
        "executive_summary": [item["interpretation"] for item in insights][:5] or [abstract[:120]],
        "metrics": list(metrics),
        "caliber": build_caliber(subject),
        "core_analysis": dict(core),
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


def build_payload(raw: str, keyword_type: str, page_size: int) -> Dict[str, Any]:
    resolved = resolve_enterprise_name(raw)
    enterprise = resolved["enterprise"]
    mk_args: Dict[str, Any] = {"matchKeyword": enterprise, "keywordType": keyword_type}

    score = _safe_call(T_SCORE, mk_args)
    serious = _safe_call(T_SERIOUS, mk_args)
    mortgage = _safe_call(T_MORTGAGE, mk_args)
    hearings = _safe_call(T_HEARINGS, {**mk_args, "pageIndex": 1, "pageSize": page_size})
    litigation = _safe_call(T_LITIGATION, mk_args)
    announce = _safe_call(T_ANNOUNCE, {**mk_args, "pageIndex": 1, "pageSize": page_size})
    ip_pledge = _safe_call(T_IP_PLEDGE, mk_args)
    penalties = _safe_call(T_PENALTIES, mk_args)
    anomalies = _safe_call(T_ANOMALIES, mk_args)
    restrictions = _safe_call(T_RESTRICTIONS, {**mk_args, "pageIndex": 1, "pageSize": page_size})

    subject = build_subject(raw, resolved, keyword_type)
    core = build_core_analysis(score, serious, mortgage, hearings, litigation, announce, ip_pledge, penalties, anomalies, restrictions)
    metrics = build_metrics(score, serious, hearings, announce, penalties, anomalies, restrictions, litigation)
    _derive_core_metrics(metrics, core if isinstance(core, dict) else {})
    # --- Enterprise profile enrichment (from fuzzy_search) ---
    _enrich_metrics_with_profile(metrics, resolved.get("record") if isinstance(resolved, dict) else None)
    return _assemble(subject, core, metrics, dry_run=False)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(description="Compose an enterprise-risk analysis report via the risk MCP.")
    parser.add_argument("--enterprise", required=True, help="企业全称或关键词（关键词将自动模糊补全）")
    parser.add_argument("--keyword-type", default="name", help="主体类型：name/nameId/regNumber/socialCreditCode")
    parser.add_argument("--page-size", type=int, default=10, help="分页类风险维度单页大小（最多 50）")
    parser.add_argument("--dry-run", action="store_true", help="不调用真实 MCP，使用样例数据组装报告骨架")
    parser.add_argument("--output", help="输出 JSON 路径；省略则打印到 stdout")
    parser.add_argument("--report-output", help="同时输出 HTML 报告（.html）与 Markdown 报告（.md）")
    parser.add_argument("--pdf-output", help="额外输出 PDF 报告（.pdf）；需要 Playwright + Chromium")
    args = parser.parse_args()

    if args.dry_run:
        payload = build_dry_run_payload(args.enterprise, args.keyword_type)
    else:
        payload = build_payload(args.enterprise, args.keyword_type, args.page_size)

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
