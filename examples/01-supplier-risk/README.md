# 供应商风险准入

- 用户需求：对宁德时代新能源科技股份有限公司做供应商风险初筛，覆盖评分、诉讼、处罚、异常和限高。
- 决策用途：为采购准入提供外部风险线索。
- 本轮结果：**本轮检查通过**
- 实际工具调用：10；失败 0
- 章节覆盖率：55%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 评分与各风险事件必须分开解释
- 处罚、异常和限高的零/空语义应严格区分
- 事件日期和案号应按源数据保留
- 不得因单一事件输出自动否决结论

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 风险初筛不能替代法务复核和裁判文书核验。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 enterprise-risk-skill/scripts/compose_report.py --enterprise '宁德时代新能源科技股份有限公司' --page-size 10 --output enterprise-risk-skill/output/01-supplier-risk/report.json --report-output enterprise-risk-skill/output/01-supplier-risk/report.html
```

## 逐场景业务复核

本轮正式真实产物已逐项复核；结论限于上游公开数据、本次分页样本及报告声明口径。

- **pass** 评分与各风险事件必须分开解释：评分100/上游等级低风险单列；司法画像229开庭、137法院公告、97裁判、2被执行及动产抵押11分别呈现，且明确上游等级不代表总体定性。 本轮实际产物：technical_status=passed，successful_data_calls=5，subject.enterprise=宁德时代新能源科技股份有限公司，match_raw=宁德时代新能源科技股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:data,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=229; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=137; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=229; 立案公告=1; 法院公告=137; 裁判文书=97; 被执行人=2; 限制高消费=0; 失信被执行=0; 动产抵押=11; 分维度记录数合计（未去重）=466]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=11, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":6,"empty_sections":5,"coverage_pct":55}。
- **pass** 处罚、异常和限高的零/空语义应严格区分：penalties/business_anomalies/consumption_restrictions调用均status=empty并进入data_source.empty_products；诉讼画像limitedTotal=0作为上游真实数值展示，未把空调用伪造成0条明细。 本轮实际产物：technical_status=passed，successful_data_calls=5，subject.enterprise=宁德时代新能源科技股份有限公司，match_raw=宁德时代新能源科技股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:data,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=229; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=137; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=229; 立案公告=1; 法院公告=137; 裁判文书=97; 被执行人=2; 限制高消费=0; 失信被执行=0; 动产抵押=11; 分维度记录数合计（未去重）=466]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=11, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":6,"empty_sections":5,"coverage_pct":55}。
- **pass** 事件日期和案号应按源数据保留：开庭/法院公告保留可用案号与日期，如(2026)闽0212民初1369号、(2025)京73行初18536号及刊登日期2026-02-11；源缺失值保留“-”。 本轮实际产物：technical_status=passed，successful_data_calls=5，subject.enterprise=宁德时代新能源科技股份有限公司，match_raw=宁德时代新能源科技股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:data,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=229; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=137; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=229; 立案公告=1; 法院公告=137; 裁判文书=97; 被执行人=2; 限制高消费=0; 失信被执行=0; 动产抵押=11; 分维度记录数合计（未去重）=466]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=11, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":6,"empty_sections":5,"coverage_pct":55}。
- **pass** 不得因单一事件输出自动否决结论：洞察明确司法阶段计数无当事人角色、裁判结果或履行状态，不能推断责任、败诉、未履行或失信，也没有自动否决结论。 本轮实际产物：technical_status=passed，successful_data_calls=5，subject.enterprise=宁德时代新能源科技股份有限公司，match_raw=宁德时代新能源科技股份有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:data,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=229; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=137; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=229; 立案公告=1; 法院公告=137; 裁判文书=97; 被执行人=2; 限制高消费=0; 失信被执行=0; 动产抵押=11; 分维度记录数合计（未去重）=466]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=11, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":6,"empty_sections":5,"coverage_pct":55}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)
[页面截图](browser.png)