# 品牌合作负面风险核验

- 用户需求：查看贵州茅台酒股份有限公司是否有处罚、异常、诉讼和限高线索。
- 决策用途：支持高价值品牌合作前的风险审阅。
- 本轮结果：**本轮检查通过**
- 实际工具调用：10；失败 0
- 章节覆盖率：45%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 无事件返回不得写成权威的“零风险”
- 相同主体名称应贯穿全部风险维度
- 摘要应突出已返回事实和数据局限

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 品牌声誉风险还需结合舆情等其他数据源。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 enterprise-risk-skill/scripts/compose_report.py --enterprise '贵州茅台酒股份有限公司' --page-size 8 --output enterprise-risk-skill/output/04-brand-risk/report.json --report-output enterprise-risk-skill/output/04-brand-risk/report.html
```

## 逐场景业务复核

本轮正式真实产物已逐项复核；结论限于上游公开数据、本次分页样本及报告声明口径。

- **pass** 无事件返回不得写成权威的“零风险”：虽上游评分100/等级低风险，报告同时列开庭3032、法院公告2559、裁判1965并明确“不能据此认定总体低风险”。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=贵州茅台酒股份有限公司，match_raw=贵州茅台酒股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=8,total=3032; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=8,total=2559; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=3032; 立案公告=156; 法院公告=2559; 裁判文书=1965; 被执行人=4; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=7716]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=8, court_announcements=8, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 相同主体名称应贯穿全部风险维度：subject及全部10个调用arguments.matchKeyword均为“贵州茅台酒股份有限公司”，未混入其他主体。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=贵州茅台酒股份有限公司，match_raw=贵州茅台酒股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=8,total=3032; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=8,total=2559; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=3032; 立案公告=156; 法院公告=2559; 裁判文书=1965; 被执行人=4; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=7716]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=8, court_announcements=8, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 摘要应突出已返回事实和数据局限：摘要只列实际覆盖的评分、诉讼画像/分布、开庭和法院公告，并说明不含角色、裁判结果或履行状态；quality=5/11、45%。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=贵州茅台酒股份有限公司，match_raw=贵州茅台酒股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=8,total=3032; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=8,total=2559; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=3032; 立案公告=156; 法院公告=2559; 裁判文书=1965; 被执行人=4; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=7716]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=8, court_announcements=8, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)