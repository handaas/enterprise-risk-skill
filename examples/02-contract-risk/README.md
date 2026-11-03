# 重大合同相对方风控

- 用户需求：检查中国建筑第八工程局有限公司的诉讼画像、开庭公告、法院公告与动产抵押。
- 决策用途：识别签约前需要法务进一步核实的风险事件。
- 本轮结果：**本轮检查通过**
- 实际工具调用：10；失败 0
- 章节覆盖率：64%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 开庭与法院公告不得重复视为两个独立案件
- 诉讼画像是统计而非裁判结论
- 抵押记录需保留登记信息和状态（若返回）

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 同名案件和历史事件需人工去重并核对当前状态。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 enterprise-risk-skill/scripts/compose_report.py --enterprise '中国建筑第八工程局有限公司' --page-size 10 --output enterprise-risk-skill/output/02-contract-risk/report.json --report-output enterprise-risk-skill/output/02-contract-risk/report.html
```

## 逐场景业务复核

本轮正式真实产物已逐项复核；结论限于上游公开数据、本次分页样本及报告声明口径。

- **pass** 开庭与法院公告不得重复视为两个独立案件：开庭17512与法院公告5739作为阶段记录分列；合计31775明确标“未去重”，洞察说明同案可能跨阶段重复，不能当独立案件数。 本轮实际产物：technical_status=passed，successful_data_calls=6，subject.enterprise=中国建筑第八工程局有限公司，match_raw=中国建筑第八工程局有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=17512; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=5739; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:data,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:data,rows=5,total=5]；metrics=[上游模型评分=59; 上游模型等级=高风险; 开庭公告=17512; 立案公告=165; 法院公告=5739; 裁判文书=7812; 被执行人=536; 限制高消费=5; 失信被执行=6; 行政处罚=3; 分维度记录数合计（未去重）=31775; 当前返回行政处罚明细数=3; 当前返回限高明细数=5]；sections=[score_overview=3, litigation_overview=7, litigation_dist=7, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=3, business_anomalies=0, consumption_restrictions=5]；quality_report={"total_sections":11,"populated_sections":7,"empty_sections":4,"coverage_pct":64}。
- **pass** 诉讼画像是统计而非裁判结论：摘要说明阶段计数不含角色/裁判结果/履行状态；59分与上游“高风险”原样呈现且未再按本地分数区间改写。 本轮实际产物：technical_status=passed，successful_data_calls=6，subject.enterprise=中国建筑第八工程局有限公司，match_raw=中国建筑第八工程局有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=17512; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=5739; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:data,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:data,rows=5,total=5]；metrics=[上游模型评分=59; 上游模型等级=高风险; 开庭公告=17512; 立案公告=165; 法院公告=5739; 裁判文书=7812; 被执行人=536; 限制高消费=5; 失信被执行=6; 行政处罚=3; 分维度记录数合计（未去重）=31775; 当前返回行政处罚明细数=3; 当前返回限高明细数=5]；sections=[score_overview=3, litigation_overview=7, litigation_dist=7, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=3, business_anomalies=0, consumption_restrictions=5]；quality_report={"total_sections":11,"populated_sections":7,"empty_sections":4,"coverage_pct":64}。
- **pass** 抵押记录需保留登记信息和状态（若返回）：risk_insight_chattel_mortgage status=empty，因此未生成抵押记录或状态；条件“若返回”不适用且无伪造。 本轮实际产物：technical_status=passed，successful_data_calls=6，subject.enterprise=中国建筑第八工程局有限公司，match_raw=中国建筑第八工程局有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=17512; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=5739; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:data,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:data,rows=5,total=5]；metrics=[上游模型评分=59; 上游模型等级=高风险; 开庭公告=17512; 立案公告=165; 法院公告=5739; 裁判文书=7812; 被执行人=536; 限制高消费=5; 失信被执行=6; 行政处罚=3; 分维度记录数合计（未去重）=31775; 当前返回行政处罚明细数=3; 当前返回限高明细数=5]；sections=[score_overview=3, litigation_overview=7, litigation_dist=7, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=3, business_anomalies=0, consumption_restrictions=5]；quality_report={"total_sections":11,"populated_sections":7,"empty_sections":4,"coverage_pct":64}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)