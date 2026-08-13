# MCP 工具参考 — enterprise-risk-mcp-server

本 skill 连接的 MCP server：`handaas-mcp-server/enterprise-risk-mcp-server`（“企业风险分析洞察”）。

> **重要**：风险维度类工具入参为 `matchKeyword`（**企业全称** / 注册号 / 统一社会信用代码 / 企业 id）+ `keywordType`；当用户只给企业关键词时，必须先调关键词模糊查询补全全称。

## 通用约定

- `keywordType` 枚举：`name`（企业名称）/ `nameId`（企业 id）/ `regNumber`（注册号）/ `socialCreditCode`（统一社会信用代码）。
- 分页：`pageIndex` 从 1 开始；`pageSize` 单页最多 50。

---

## 工具清单

### 1. `risk_insight_fuzzy_search` — 关键词模糊查询企业

用途：根据企业名称 / 人名 / 品牌 / 产品 / 岗位等关键词模糊查询企业列表，用于补全企业全称。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 匹配关键词 |
| `pageIndex` | int | 否 | 分页开始位置（默认 1） |
| `pageSize` | int | 否 | 单页最多 50 |

返回：`total` + 企业列表（`name`、`nameId`、`regCapitalValue`、`foundTime`、`operStatus`、`address`、`legalRepresentative`、`enterpriseType`、`catchReason` 命中原因等）。

product_id：`675cea1f0e009a9ea37edaa1`。

---

### 2. `enterprise_risk_insight_score` — 风险评分

用途：按企业主体返回综合风险评分、风险等级及分项风险等级。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业名称 / 注册号 / 统一社会信用代码 / 企业 id |
| `keywordType` | string | 否 | 主体类型：name / nameId / regNumber / socialCreditCode |

返回：`riskScore`（风险评分）、`riskLevel`（风险等级）、`litigationRiskLevel`（诉讼风险等级）、`operRiskLevel`（经营风险等级）、`creditRiskLevel`（信用风险等级）、`updateTime`（评分更新时间）等。

product_id：`68fb5d6c5e8fca298e2b1c7f`。

---

### 3. `risk_insight_serious_violations` — 严重违法

用途：返回企业严重违法记录。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`caseName`（案件名称）、`illegalFact`（违法事实）、`penaltyContent`（处罚内容）、`penaltyDate`（决定日期）、`department`（决定机关）等。

product_id：`669fb97b76742e172f2a5193`。

---

### 4. `risk_insight_chattel_mortgage` — 动产抵押

用途：返回企业动产抵押登记记录。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`mortgageRegNum`（登记编号）、`mortgagee`（抵押权人）、`pledgeAmount`（金额）、`status`（状态）、`regDate`（登记日期）、`scope`（担保范围）等。

product_id：`66a0e19aa84e3d948a9fc373`。

---

### 5. `risk_insight_court_hearings` — 开庭公告

用途：返回企业开庭公告记录（分页）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 单页最多 50（默认 10） |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`caseNo`（案号）、`caseReason`（案由）、`court`（法院）、`hearingDate`（开庭日期）、`role`（身份）等。

product_id：`66a0e123bc2d198e864482c4`。

---

### 6. `risk_insight_litigation_risk_profile` — 诉讼风险画像

用途：按企业主体返回诉讼风险整体画像（案件数、原被告身份、涉案金额等）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回：`litigationRiskLevel`（诉讼风险等级）、`caseCount`（案件总数）、`asDefendantCount`（作为被告次数）、`asPlaintiffCount`（作为原告次数）、`recentCaseCount`（近一年案件数）、`totalAmount`（涉案总金额）、`riskTrend`（风险趋势）等。

product_id：`66bb1aa834d3cd3e43928163`。

---

### 7. `risk_insight_court_announcements` — 法院公告

用途：返回企业法院公告记录（分页）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `pageSize` | int | 否 | 单页最多 50（默认 10） |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`caseNo`（案号）、`content`（公告内容）、`court`（法院）、`publishDate`（刊登日期）等。

product_id：`669f997d0839b73a327efb4f`。

---

### 8. `risk_insight_intellectual_property_pledge` — 知识产权出质

用途：返回企业知识产权出质登记记录。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`pledgeName`（知识产权名称）、`pledgee`（质权人）、`pledgeAmount`（金额）、`regDate`（登记日期）、`status`（状态）等。

product_id：`66a0e1ca10026dc291e21049`。

---

### 9. `risk_insight_penalties` — 行政处罚

用途：返回企业行政处罚记录。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`penaltyNo`（处罚决定书文号）、`illegalFact`（违法事实）、`penaltyContent`（处罚内容）、`penaltyDate`（决定日期）、`department`（决定机关）等。

product_id：`66a24a59515324c521d6610d`。

---

### 10. `risk_insight_business_anomalies` — 经营异常

用途：返回企业经营异常名录记录。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `keywordType` | string | 否 | 主体类型 |

返回（list + `total`）：`reason`（列入原因）、`department`（决定机关）、`inDate`（列入日期）、`outDate`（移出日期）、`status`（状态）等。

product_id：`66a248f381d41651f2689d95`。

---

### 11. `risk_insight_consumption_restrictions` — 限制高消费

用途：返回企业限制高消费记录（分页）。

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `matchKeyword` | string | 是 | 企业主体 |
| `pageIndex` | int | 否 | 从 1 开始（默认 1） |
| `keywordType` | string | 否 | 主体类型 |
| `pageSize` | int | 否 | 单页最多 50（默认 10） |

返回（list + `total`）：`caseNo`（案号）、`applicant`（申请执行人）、`court`（执行法院）、`publishDate`（发布日期）、`restrictContent`（限制内容）等。

product_id：`669e3087d6e30dd7e6d03e55`。

---

## 推荐调用顺序（报告编排）

1. （若仅有关键词）`risk_insight_fuzzy_search` → 取 `name` 作为全称。
2. `enterprise_risk_insight_score` → 综合风险评分。
3. `risk_insight_litigation_risk_profile` → 诉讼风险画像。
4. 各风险维度明细（严重违法 / 动产抵押 / 开庭公告 / 法院公告 / 知识产权出质 / 行政处罚 / 经营异常 / 限制高消费）。

> 单次报告通常调用 10 个工具；所有维度入参均为企业主体 `matchKeyword` + `keywordType`，分页类可按需控制 `pageSize`。
