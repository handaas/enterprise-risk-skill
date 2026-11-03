# 平台企业合规风险概览

- 用户需求：核查北京京东世纪贸易有限公司的行政处罚、经营异常、诉讼画像和法院公告。
- 决策用途：梳理平台合作中的监管与争议线索。
- 本轮结果：**本轮检查通过**
- 实际工具调用：10；失败 0
- 章节覆盖率：45%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 行政处罚与经营异常要分维度展示
- 法院公告与开庭公告应保留类型和时间
- 分页展示数不能冒充事件总数

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 不同地区、不同主体的事件不可合并归因。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 enterprise-risk-skill/scripts/compose_report.py --enterprise '北京京东世纪贸易有限公司' --page-size 10 --output enterprise-risk-skill/output/05-platform-risk/report.json --report-output enterprise-risk-skill/output/05-platform-risk/report.html
```

## 逐场景业务复核

本轮正式真实产物已逐项复核；结论限于上游公开数据、本次分页样本及报告声明口径。

- **pass** 行政处罚与经营异常要分维度展示：core_analysis分别定义penalties与business_anomalies，两个对应调用均status=empty并分别列入empty_products，没有相互替代或伪造0记录。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=北京京东世纪贸易有限公司，match_raw=北京京东世纪贸易有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=2613; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=926; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=2613; 立案公告=59; 法院公告=926; 裁判文书=2291; 被执行人=20; 限制高消费=0; 失信被执行=1; 分维度记录数合计（未去重）=5910]；sections=[score_overview=3, litigation_overview=7, litigation_dist=6, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 法院公告与开庭公告应保留类型和时间：开庭与法院公告各保留类型及可用时间，例如辽宁丹东记录“起诉状副本及开庭传票/公告日期2026-10-21”，法院公告刊登日期同为2026-10-21。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=北京京东世纪贸易有限公司，match_raw=北京京东世纪贸易有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=2613; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=926; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=2613; 立案公告=59; 法院公告=926; 裁判文书=2291; 被执行人=20; 限制高消费=0; 失信被执行=1; 分维度记录数合计（未去重）=5910]；sections=[score_overview=3, litigation_overview=7, litigation_dist=6, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 分页展示数不能冒充事件总数：调用row_count均10而reported_total分别2613/926；section note明确“上游总数…当前返回10条”，没有用分页展示数冒充总数。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=北京京东世纪贸易有限公司，match_raw=北京京东世纪贸易有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=10,total=2613; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=10,total=926; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=100; 上游模型等级=低风险; 开庭公告=2613; 立案公告=59; 法院公告=926; 裁判文书=2291; 被执行人=20; 限制高消费=0; 失信被执行=1; 分维度记录数合计（未去重）=5910]；sections=[score_overview=3, litigation_overview=7, litigation_dist=6, serious_violations=0, chattel_mortgage=0, court_hearings=10, court_announcements=10, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)