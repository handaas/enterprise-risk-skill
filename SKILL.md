---
name: enterprise-risk-report
description: Use for generating a professional enterprise risk analysis report (企业风险分析报告) from the HandaaS enterprise-risk MCP — covering 风险评分、严重违法、动产抵押、开庭公告、诉讼风险画像、法院公告、知识产权出质、行政处罚、经营异常、限制高消费. Trigger when users ask for “企业风险分析报告”, “企业风险报告”, “风险尽调报告”, “查一家公司的风险”, “风险评分”, “诉讼风险”, “行政处罚”, “经营异常”, “限制高消费”, or “严重违法”. Infer the canonical enterprise name (auto-fuzzy-completing a keyword), pick the right MCP tools, and produce HTML + Markdown + JSON reports automatically. MCP 服务名称触发词：企业风险监测。
---

# 企业风险分析报告

## 用户契约

把“企业风险分析报告”作为面向用户的调用短语。`enterprise-risk-report` 仅为内部包名。

当本 skill 处于激活状态：

1. 不要向用户索要 product_id、MCP 工具名、API 字段、内部参数或凭证信息；只接受企业名称、统一社会信用代码、注册号或企业 ID。
2. 接受自然目标，例如“查一下某某公司的风险”“分析这家企业的风险敞口”“给我一份某某公司的风险尽调报告”“看看这家公司有没有被执行/限高/行政处罚”。
3. 当用户只给关键词时，自动调用关键词模糊查询补全企业全称，再查风险维度。
4. 优先使用 MCP 连接（`ENTERPRISE_RISK_MCP_URL` Remote MCP 或本地 `handaas-mcp-server/enterprise-risk-mcp-server`）；不要让用户处理签名或凭证。
5. 同时产出 HTML（可分享交付）、Markdown（知识库 / wiki）、JSON（系统集成）三类产物。
6. 报告正文必须是专业研究报告风格：只见风险事实与结构化数据，绝不出现工具名、入参、product_id、内部字段或空表。
7. 绝不打印 `secret_id`、`secret_key`、签名、token 或原始签名请求。
8. 默认 dry-run；真实付费 / 凭证调用需用户明确要求且 MCP 连接配置完整。
9. 数据为空时明确说明数据范围 / 口径，不渲染空表、不臆造事实。


- MCP 返回的嵌套 JSON 字符串（如金额 `{"coinType":"人民币","value":430000000.0}`、地址 `{"city":"杭州市",...}`）必须解析为可读文本（如"4.30 亿 人民币"、"浙江省杭州市"），绝不在报告正文、表格或指标中输出原始 JSON 字符串。
- 报告所有章节标题、指标卡标签必须用中文；`core_analysis.sections` 的 `title` 字段必须中文，不可显示英文 key（如 `holders`、`investments`）。
- 指标值必须可读化：金额格式为"X 亿/万 + 币种"，地址拼接省市区，比率显示百分号。详见 `references/report-output.md` 的「数据格式约束」。

## 付费调用与分页预算（强制）

每次 MCP 业务调用和每一页明细请求都可能计费；希望得到 total / 页数计算**不是**全量拉取的授权。

1. **先计划再调用**：调用前先推导本次报告必需的结论、需要的数据维度、工具与参数方案、所需页数和最大调用预算。上游 total 未知时，第一个必要的明细页同时用于发现 total 与报告数据，绝不为此页重复付费。
2. **优先统计 / 概况接口**：当结论可由风险评分、诉讼风险画像等聚合接口回答时优先使用它们；仅在结论、图表、代表性记录或用户明确要求全量/计数时才拉取明细。只有在用户确实要求综合报告时才跑完整流水线，绝不因为工具存在就全部调用。
3. **预算内取数**：使用 schema 允许的合理最大 pageSize 获取所需行数，达到证据/样本目标即停止，且始终在显式预算内。额外翻页必须有缺失结论的正当理由，而不是“想填满所有章节”。不得用样本分布冒充全量结论。
4. **复用相同请求**：同一任务/报告内相同的工具+参数只调用一次（含首屏规划数据）；渲染只用本地已保存 JSON 重渲，不重跑 compose/MCP。禁止自动重试、重复拉取相同统计/明细、并行拉取相同数据。补充查询前先列出具体缺口并复用已返回记录。
5. **总数与完整性口径**：`total_pages` / `remaining_pages` 只是按请求 pageSize 的估算；短而未完的页在预算内要继续翻。仅当稳定有效的 total 与实扫条数一致才算完整采集；报错、提前空页、重复页、total 变化/缺失或数量溢出均视为不完整。因显式预算或样本目标提前停止的都是部分采集，绝不宣称全量数据。
6. **预算不足要说清缺口**：若预算不足以支撑某个关键结论，在申请扩大授权前先说明证据缺口与预计的额外调用数；不得静默降级结论，也不得擅自扩大计费范围。

本 skill 分页明细：开庭公告、法院公告、限制高消费三个接口支持 pageIndex/pageSize（单页最多 50），CLI `--max-pages`（默认 1）为其共同页数预算；评分/严重违法/动产抵押/诉讼画像/知识产权出质/行政处罚/经营异常接口不支持 pageIndex，关键词模糊查询（pageSize=10）仅用于主体确认，均保持单次调用。

## MCP 服务入口

- MCP 服务当前名称：企业风险监测（连接仍使用原服务目录标识）。

- 上游 MCP 项目：`handaas-mcp-server/enterprise-risk-mcp-server`（位于 `HANDAAS_MCP_SERVER_ROOT` 或本仓库同级目录）。
- Remote MCP：设置环境变量 `ENTERPRISE_RISK_MCP_URL`（streamable-http），可选 `ENTERPRISE_RISK_MCP_TOKEN`。
- 本地 MCP：设置 `HANDAAS_MCP_SERVER_ROOT` 指向 `handaas-mcp-server` 仓库根目录；该 server 自己的 `.env` 提供 `INTEGRATOR_ID` / `SECRET_ID` / `SECRET_KEY`。
- 首次真实查询前，运行 `scripts/mcp_client.py ping` 与 `scripts/mcp_client.py list-tools` 验证连通。

## 按需加载 references

- 不清楚该 MCP 有哪些工具、参数、返回字段、何时调用：`references/mcp-tools-reference.md`。
- 报告结构、章节、质量底线、渲染工作流：`references/report-output.md`。

## 意图路由

| 用户意图 | 内部工作流 |
| --- | --- |
| 查一家公司的全维度风险报告 | 调全部 10 个风险维度组装全量报告；`compose_report.py --enterprise ...` |
| 只要风险评分 / 诉讼画像 | 仅调 `enterprise_risk_insight_score` / `risk_insight_litigation_risk_profile` |
| 只要某一类风险（如行政处罚 / 经营异常 / 限高） | 调对应维度工具，按统一骨架组装 |
| 看诉讼 / 开庭 / 法院公告 | 调 `risk_insight_court_hearings` / `risk_insight_court_announcements` |
| 只给关键词（不是全称） | 先 `risk_insight_fuzzy_search` 补全全称，再查风险维度 |
| 只要 JSON / 只要 HTML / 只要 Markdown | 用 `--output`（JSON）或 `--report-output`（HTML+MD），或 `render_report.py` 重渲染 |
| 连接 / 工具不存在 / 传参错误 | `mcp_client.py ping` / `list-tools` 排查；报脱敏后的缺失项 |

## Golden path for 企业风险分析报告

1. **解析企业全称**：若输入含“公司/集团/有限/院/厂/中心/事务所/合作社/合伙”等后缀视为全称；否则调 `risk_insight_fuzzy_search` 取首个命中。
2. **调用风险维度工具**（入参均为 `matchKeyword`（企业全称）+ `keywordType`）：`enterprise_risk_insight_score`（风险评分）、`risk_insight_litigation_risk_profile`（诉讼风险画像）、`risk_insight_serious_violations`（严重违法）、`risk_insight_chattel_mortgage`（动产抵押）、`risk_insight_court_hearings`（开庭公告）、`risk_insight_court_announcements`（法院公告）、`risk_insight_intellectual_property_pledge`（知识产权出质）、`risk_insight_penalties`（行政处罚）、`risk_insight_business_anomalies`（经营异常）、`risk_insight_consumption_restrictions`（限制高消费）。
3. **组装统一报告**：核心分析含风险评分（KV）、诉讼风险画像（KV）、严重违法（表）、动产抵押（表）、开庭公告（表）、法院公告（表）、知识产权出质（表）、行政处罚（表）、经营异常（表）、限制高消费（表）。
4. **渲染三件套**：`compose_report.py --enterprise ... --output ... --report-output ...` 直接产出 JSON + HTML + Markdown；或 `render_report.py --input ... --output ...` 重渲染。
5. **返回路径**：返回 JSON、HTML、Markdown 文件路径，以及企业全称映射与数据口径。

- **渲染前置检查**：执行会产出含图表 HTML / PDF 的报告命令前，先验证 `node --version` 与本 skill 自带 `assets/vendor/echarts.min.js` 存在；内嵌静态 SVG 的生成需要 Node.js（推荐当前 LTS，无需 npm 包），缺失时报告生成明确报错。查看已生成的 HTML 与 Markdown 输出不需要 Node。

## 数据整理与交付前 AI 审校（强制）

正常生成（`build_payload` / CLI 非 `--dry-run`）在组装阶段已自动执行 `apply_content_review`；`--dry-run` 与正常生成共用同一条路径且只执行一次。`apply_content_review` 只是确定性规则整理，不等于实际 AI 语义审校。离线入口仅用于复核已有报告，重复调用保留此前 `content_review.corrections`。以下语义核对仍须由当前 AI 逐项完成，并把“原值 → 规范值 → 证据位置”写入审校记录。

评分与记录数不是同一层证据；以下核对必须由当前 AI 完成，并在审校记录中保留原值、规范值与证据位置。

1. **评分与明细分层**：`风险评分/等级` 是上游模型输出，不能替代司法、处罚、执行明细；评分低但记录非零时，必须同时写出“司法记录非零，仍需核验”，不得把“低风险”写成总体结论。
2. **评级说明不是成因**：`risk_reason` 中的“世界500强”“存在负债风险”等是上游说明原文，不是经核验的风险成因；写作时用“上游原文”，不据此推断模型权重。
3. **阶段计数不是案件数**：开庭公告/立案公告/法院公告/裁判文书/被执行等阶段可能对同一事件重复计数；阶段合计标注“未去重、不代表独立案件数”，CR2 只描述记录数分布。
4. **字段缺失**：案号、开庭日期、当事人角色、裁判结果、履行状态缺失时保留 `-`，不补“无风险”或“已履行”；日期不明不当作当前有效。
5. **维度覆盖**：`10 大风险维度中有 N 个存在记录` 只表示返回数据覆盖，不表示其余维度不存在风险；未返回维度写“未覆盖/待核验”。
6. **主体确认**：未唯一确认主体时不调用主体风险数据、不生成风险评价。

离线修订已有报告（不调用 MCP，不覆盖 `examples/`）：

```python
import json
from compose_report import apply_content_review

report = json.load(open("examples/01-supplier-risk/report.json", encoding="utf-8"))
revised = apply_content_review(report)
json.dump(revised, open("output/content-quality-review/01-supplier-risk/report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
```

`apply_content_review` 将复合列名 `名称/类型/状态/年份` 规范为 `阶段`，将“风险评级依据”改为“上游评级说明”，并刷新摘要/洞察；不改评分、等级、记录数或案件事实。

### 草稿 → AI 审校 → 最终交付

1. **采集一次，只出草稿**：本 Skill 的采集脚本（`compose_report.py` 或 `compose_fusion_report.py`，以脚本速查为准）在正常生成和 `--dry-run` 时都于写盘前标记 `data_source.semantic_review.status=pending`，产出 `output/draft.json` 与 `output/draft.html`/`draft.md`。后两者只是预览，不能交付；`apply_content_review`、`organize_report` 等确定性整理不等于实际 AI 审校。
2. **实际阅读再判断**：当前 AI 智能体打开 draft，逐项阅读 `subject`、`core_analysis`、`metrics`、`caliber`、`analysis_request`、`data_source`，按含义做标准化归类、3–5 句三层摘要和有证据的洞察；只引用本报告实际存在的 JSON Pointer，数字逐字取自所引 values，保留否定、最高/至少/至多、试用期/转正后、仅限/部分、疑似/待定/已失效等限定；无数据不生成事实或业务判断。
3. **准备审校请求**：`python scripts/review_report.py --input output/draft.json --request output/review-request.json`。该命令只读草稿，不调用 MCP、外部模型 API，也不新增查询。
4. **写回实际判断**：按请求的 `response_fields` 将逐句摘要、标准化和含 evidence 的洞察写入 `output/ai-review.json`；`source_sha256` 必须与请求一致。字段与 JSON Pointer 规则见 `references/report-output.md`。
5. **应用并核对成品**：`python scripts/review_report.py --input output/draft.json --review output/ai-review.json --output output/final/report.json --report-output output/final/report.html`；核对最终 JSON、HTML、Markdown（目录、图表、空章节）后才交付。不得停在审校请求文件，也不得另存手工润色件冒充最终报告。
6. **展示纪律**：空板块连标题和目录一起隐藏；真实 `0`/`False` 原样保留；失败或未查询只在口径限制中简述，不补 0、不推断“无风险”或“无数据”。空维度只影响展示，不从 `quality_report` 分母抹去未覆盖维度；AI 标准化/摘要是解释视图，不新增数据来源或源数据覆盖率。

## 脚本速查
以下采集示例只生成待审校草稿（`data_source.semantic_review.status=pending`）；最终报告须按上方门禁用 `review_report.py` 生成。

```bash
# 校验连接配置（脱敏）
python scripts/validate_config.py --allow-placeholders

# 连通性自测
python scripts/mcp_client.py ping
python scripts/mcp_client.py list-tools

# 干跑（不调真实 API，用样例数据组装报告骨架）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --dry-run \
  --output output/risk.json \
  --report-output output/risk.html

# 真实查询 + 渲染（需 MCP 连接就绪）
python scripts/compose_report.py \
  --enterprise "示例科技有限公司" \
  --output output/risk.json \
  --report-output output/risk.html

# 明细页数预算：默认仅 1 页；先按报告结论计划所需页数，再显式授权扩大
python scripts/compose_report.py --enterprise "示例科技有限公司" --page-size 50 --max-pages 3 --report-output output/risk.html

# 手动调单个工具
python scripts/mcp_client.py call-tool \
  --tool enterprise_risk_insight_score \
  --arguments-json '{"matchKeyword": "示例科技有限公司", "keywordType": "name"}'

# 重渲染已有 JSON
python scripts/render_report.py --input output/risk.json --output output/risk.html
python scripts/render_report.py --input output/risk.json --output output/risk.md
```

## 输出字段

- `subject`：企业全称、匹配关键词、主体类型、是否自动补全。
- `abstract` / `summary`：封面摘要与详细摘要。
- `metrics`：风险评分、风险等级、案件总数、严重违法、行政处罚、经营异常、开庭公告、法院公告、限制高消费等指标卡。
- `caliber`：匹配对象、匹配方式、数据范围、产品、局限。
- `core_analysis`：风险评分（KV）、诉讼风险画像（KV）、严重违法（表）、动产抵押（表）、开庭公告（表）、法院公告（表）、知识产权出质（表）、行政处罚（表）、经营异常（表）、限制高消费（表）。
- `representative_records`：代表性风险记录（案号 / 案由 / 法院 / 日期）。
- `insights`：结构化解读（综合风险水平 / 诉讼风险 / 严重违法 / 限制高消费 / 经营异常）。
- `data_source`：MCP server、数据产品、生成时间、是否 dry-run。

若 API 调用失败，明确报出缺失的配置 / 缺失的工具 / MCP 错误 / 参数校验错误 / 上游网络错误，给出 dry-run 命令或配置步骤，绝不暴露密钥。
