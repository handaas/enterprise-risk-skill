# 报告输出 — 企业风险分析报告

本文件规定 `enterprise-risk-report` skill 产出的报告结构、质量底线与渲染工作流。所有产物遵循 `AGENTS.md` 的统一 JSON 骨架与本 skill 的领域裁剪。

## 默认展示模式

- HTML：可分享 / 可交付的可视化报告；独立本地文件，内嵌 CSS，无调试 / 内部段落。
- Markdown：知识库 / wiki / PRD / 后续手工编辑。
- JSON：系统集成或二次处理。

`compose_report.py` 通过 `--report-output <path>` 同时产出 HTML + Markdown；`--output <path>` 产出 JSON。`render_report.py` 可基于已有 JSON 重渲染。

## 报告结构（7 章）

1. **报告摘要**：分析对象、数据覆盖范围、核心发现、关键指标卡。
2. **查询对象与口径**：企业全称、匹配方式、数据范围、产品、局限。
3. **数据总览**：风险评分、风险等级、案件总数、严重违法、行政处罚、经营异常、开庭公告、法院公告、限制高消费等指标卡。
4. **核心分析**（风险专属子章节，由 `core_analysis.sections` 驱动渲染）：
   - 风险评分（KV：综合评分 / 等级 / 分项等级）。
   - 诉讼风险画像（KV：案件数 / 原被告身份 / 涉案金额 / 趋势）。
   - 严重违法（表：案件名称 / 违法事实 / 处罚内容 / 决定日期 / 决定机关）。
   - 动产抵押（表：登记编号 / 抵押权人 / 金额 / 状态 / 登记日期 / 担保范围）。
   - 开庭公告（表：案号 / 案由 / 法院 / 开庭日期 / 身份）。
   - 法院公告（表：案号 / 公告内容 / 法院 / 刊登日期）。
   - 知识产权出质（表：知识产权名称 / 质权人 / 金额 / 登记日期 / 状态）。
   - 行政处罚（表：处罚决定书文号 / 违法事实 / 处罚内容 / 决定日期 / 决定机关）。
   - 经营异常（表：列入原因 / 决定机关 / 列入日期 / 移出日期 / 状态）。
   - 限制高消费（表：案号 / 申请执行人 / 执行法院 / 发布日期 / 限制内容）。
5. **代表性记录**：关键风险记录 Top N（案号 / 案由 / 法院 / 日期）。
6. **特征与洞察**：结构化解读（综合风险水平 / 诉讼风险 / 严重违法 / 限制高消费 / 经营异常），每条含 `feature` / `evidence` / `interpretation`。
7. **数据口径与来源**：MCP server、数据产品、生成时间、是否 dry-run。

## 质量底线

- 报告脱离 Skill 上下文也可独立阅读；正文只见风险事实与结构化数据。
- 绝不出现工具名、入参（如 `matchKeyword=...`）、product_id、内部字段名、空表、调试信息。
- HTML 采用研究报告视觉风格：A4 风、灰色顶部条纹、蓝色报告横幅、左侧目录 / 范围侧栏、深蓝章节标题、深蓝表头、浅蓝斑马行、打印友好分页。
- 数据为空时明确说明数据范围 / 口径，不渲染空表、不臆造事实。
- 绝不打印 `secret_id` / `secret_key` / 签名 / token / 原始签名请求。
- 自动补全企业全称时，在报告口径中说明“由关键词模糊查询补全”。

### 数据格式约束（铁律）

以下约束适用于 compose_report.py 组装数据与 render_report.py 渲染输出的全过程：

1. **嵌套 JSON 字符串必须解析**：MCP 返回的某些字段（如 `regCapital`、`addressValue`、`subscriptionDetail`）可能是 JSON 字符串（例：`{"coinType":"人民币","value":430000000.0}`）。compose 层必须调用 `_unwrap_json_str()` / `_parse_reg_capital()` / `_flatten_addr()` 解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市滨江区..."）。绝不在报告正文、表格单元格或指标值中输出原始 JSON 字符串。

2. **section 标题必须用中文**：`core_analysis.sections` 数组中每个 section 的 `title` 字段必须使用中文（如"企业基本信息"、"对外投资"、"股东信息"）。`key` 字段用英文 snake_case 供程序索引，但 `title` 绝不可显示英文 key。即使缺少 sections 数组，渲染器回退逻辑也内置了 `_TITLE_MAP` 映射。

3. **指标值可读化**：所有 `metrics` 的 `value` 字段必须格式化为人类可读形式：
   - 金额：`10995210218.0` → `109.95 亿 人民币`（≥1 亿用亿，≥1 万用万）
   - 地址：嵌套 dict → 省+市+区拼接 或取 `value` 字段
   - 比率：`0.8858` → `88.58%`
   - 日期：保持 `yyyy-MM-dd` 格式
   - "-" 表示字段缺失（MCP 未返回）；`0` 表示真实为零

4. **企业画像指标提取**：有 fuzzy_search 的 skill 必须从返回的 record 中提取 `regCapitalValue` / `foundTime` / `operStatus` / `enterpriseType` / `legalRepresentative`，通过 `_enrich_metrics_with_profile()` 追加为指标卡。

5. **分布派生指标**：`_derive_core_metrics()` 从 core_analysis 各 section 计算分布指标（CR3 集中度、覆盖城市/平台/类目数、价格区间、正面占比等），确保指标总数 M ≥ 6。

## AI 审校交付门禁（草稿 → final）

`compose_*` 正常生成与 `--dry-run` 只产出草稿：JSON 标记 `data_source.semantic_review.status=pending`，同名 HTML/Markdown 带“数据草稿（待AI语义审校）”提示，不能交付。`apply_content_review`/`organize_report` 是确定性整理，不是 AI 审校。

```bash
python scripts/review_report.py --input output/draft.json --request output/review-request.json
# 当前 AI 阅读请求中的 report 后写 output/ai-review.json
python scripts/review_report.py --input output/draft.json --review output/ai-review.json \
  --output output/final/report.json --report-output output/final/report.html
```

请求含 `source_sha256`、`report`、`visible_section_keys`、`instructions`、`response_fields`；响应：

```json
{
  "source_sha256": "<与请求一致>",
  "summary": [{"text": "逐句摘要", "sources": ["/core_analysis/..."], "kind": "fact"}],
  "normalizations": [{"sources": ["/core_analysis/..."], "category": "类别", "normalized": "规范表达", "evidence": "原文摘录", "reason": "理由"}],
  "insights": [{"feature": "特征", "evidence": "证据摘录", "interpretation": "解读", "sources": ["/metrics/0"]}]
}
```

- `source_sha256` 必须与请求一致；不一致须重新请求，不能沿用旧判断。
- `sources` 使用 JSON Pointer，只能指向本报告实际存在的 `/subject/…`、`/core_analysis/…`、`/metrics/…`、`/caliber/…`、`/data_source/…`、`/analysis_request/…`；`/core_analysis/sections`、`/data_source/semantic_review` 与旧 `abstract`/`summary`/`insights` 不是事实依据。
- 每项至少一个来源且不能重复路径；同一来源可支持多项判断；不能借其他企业、案例、记录或常识补本记录。
- `summary` 写 3–5 句有信息量的逐句摘要，`kind` 只能是 `fact`/`interpretation`/`limitation`；无数据依据只能写 `limitation`。`normalizations` 是独立视图，原文不改写；`evidence` 必填，由当前 AI 选择简洁可读的原文摘录作为“原文依据”列，并由同项 `sources` 支撑，完整原值仍保留在 draft/request 与来源 SHA 记录中；必须保留否定、最高、至少、至多、试用期、转正后、仅限、部分、疑似、待定、已失效等限定；不同主体、互斥金额或比例不能合并；没有实际归类需要时可为空；`insights` 的 `feature`、`evidence`、`interpretation` 都须由同一 `sources` 支撑；`evidence` 是实际 AI 写的简洁可读证据摘录，保留来源数字、单位与限定。
- 所有文本（含 `normalized`、`category`、`reason`、`evidence`、洞察）中的数字必须逐字出现在所引 values 中，不新造派生数字、不改精度；需要派生指标先在脚本计算再引用。
- 只使用本次数据，不调用 MCP/外部模型 API/新增查询。应用后 `status=reviewed` 并记录来源 SHA-256、原 `generated_at`、审校时间与判断证据；原查询时间和原件不变。`summary` 写入 `abstract`/`summary`/`executive_summary`，`normalizations` 写入 `core_analysis.ai_normalization`（独立表格），`insights` 写入 `insights`；原始字段不改写。

**展示与交付**：空板块连标题和目录一起隐藏，但只能影响展示，不能从 `quality_report` 分母抹去未覆盖维度或提高覆盖率；真实 `0`/`False` 保留，缺失/未查询不等于 0；失败只写口径限制，不推断“无风险”。AI 标准化/摘要是解释视图，不新增数据来源或覆盖率。核对最终 JSON/HTML/Markdown 后才交付；请求文件、草稿或手工润色件不算完成。

## 工作流

```bash
# 1. 干跑（不调真实 API，用样例数据组装报告骨架）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --dry-run \
  --output output/risk.json \
  --report-output output/risk.html

# 2. 真实查询 + 渲染（需 MCP 连接就绪）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --output output/risk.json \
  --report-output output/risk.html

# 3. 重渲染已有 JSON
python scripts/render_report.py --input output/risk.json --output output/risk.html
python scripts/render_report.py --input output/risk.json --output output/risk.md
```

返回：JSON 路径、HTML 路径、Markdown 路径，以及企业全称映射与数据口径摘要。

## 交付前 AI 审校清单（风险）

| 检查项 | 原值示例 | 允许的规范动作 | 证据位置 |
| --- | --- | --- | --- |
| 评分与明细 | 评分 100 / 低风险，司法记录 466 | 保留评分，同时写“记录非零，需交叉核验” | `score_overview`、`litigation_overview` |
| 评级说明 | `世界500强` | 标为“上游原文/上游评级说明”，不写成风险成因 | `risk_reason` |
| 阶段列名 | `名称/类型/状态/年份` | 规范为 `阶段`，不改值 | `litigation_dist[]` |
| 阶段合计 | 466 | 标“未去重、不等于独立案件数” | `litigation_dist` 求和 |
| 记录缺失 | `案号 -`、`开庭日期 -` | 保留 `-`；不补“无风险/已履行” | 各类明细表 |
| 维度覆盖 | `10 个维度中 3 个有记录` | 只描述覆盖，不推断其余维度无风险 | `sections` 填充数 |

离线修订入口：`compose_report.py::apply_content_review(report)`。正常生成（`build_payload` / CLI 非 `--dry-run`）已在组装阶段自动执行同一确定性规则整理（不是 AI 语义审校）；离线入口只读报告已有字段，不查 MCP；修正项写入 `data_source.content_review.corrections`，重复处理保留既有修正记录。司法阶段分布保持“未去重、不等于独立案件数、未提供当事人角色/裁判结果/履行状态”的样本边界说明。

审校复核：完整保留有来源的摘要句子及采集层“数据缺口／主体解析受阻”提示；重审不得引用 `/core_analysis/ai_normalization` 等既有 AI 视图作为原始证据。HTML 与 Markdown 应使用一致的样本数量、趋势顺序及数据列，单元格中的竖线和换行不得破坏表格结构。
