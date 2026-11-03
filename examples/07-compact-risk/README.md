# 管理层风险快报

- 用户需求：生成华为技术有限公司风险快报，列表每类最多展示 5 条。
- 决策用途：验证紧凑分页下的风险摘要与证据引用。
- 本轮结果：**本轮检查通过**
- 实际工具调用：10；失败 0
- 章节覆盖率：45%（不代表证据质量）

## 预期业务检查（不自动宣称通过）

- 每个分页事件章节不超过 5 条或按实际返回
- 总量与样本记录数量应明确区分
- 代表记录应能回溯至核心章节

## 本轮自动检查发现


## 使用局限

- 仅反映本次 HandaaS 数据产品返回范围与生成时点，不等同于官方证明。
- 空结果必须保留为空，不能解释为该事项客观不存在。
- 快报是截断样本，不是完整风险事件清单。

## 证据与复现

- [审计结果](result.json)
- [工具调用、结果形态与响应摘要哈希](calls.json)
- [JSON](report.json) / [HTML](report.html) / [Markdown](report.md)

```bash
python3 enterprise-risk-skill/scripts/compose_report.py --enterprise '华为技术有限公司' --page-size 5 --output enterprise-risk-skill/output/07-compact-risk/report.json --report-output enterprise-risk-skill/output/07-compact-risk/report.html
```

## 逐场景业务复核

本轮正式真实产物已逐项复核；结论限于上游公开数据、本次分页样本及报告声明口径。

- **pass** 每个分页事件章节不超过 5 条或按实际返回：两个分页调用pageSize=5、row_count=5；core court_hearings/court_announcements各5行。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=华为技术有限公司，match_raw=华为技术有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=5,total=4401; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=5,total=6341; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=99; 上游模型等级=低风险; 开庭公告=4401; 立案公告=1325; 法院公告=6341; 裁判文书=3373; 被执行人=5; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=15445]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=5, court_announcements=5, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 总量与样本记录数量应明确区分：section note分别写上游总数4401/6341、当前返回5条；指标使用上游总量，不把5条样本冒充总数。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=华为技术有限公司，match_raw=华为技术有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=5,total=4401; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=5,total=6341; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=99; 上游模型等级=低风险; 开庭公告=4401; 立案公告=1325; 法院公告=6341; 裁判文书=3373; 被执行人=5; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=15445]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=5, court_announcements=5, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。
- **pass** 代表记录应能回溯至核心章节：representative_records 5条逐条来自court_hearings，例如(2025)粤0309民初45884号、深圳龙华法院，字段可回溯。 本轮实际产物：technical_status=passed，successful_data_calls=4，subject.enterprise=华为技术有限公司，match_raw=华为技术有限公司，resolved=True；calls=[enterprise_risk_insight_score:data,rows=None,total=None; risk_insight_serious_violations:empty,rows=None,total=None; risk_insight_chattel_mortgage:empty,rows=None,total=None; risk_insight_court_hearings:data,rows=5,total=4401; risk_insight_litigation_risk_profile:data,rows=None,total=None; risk_insight_court_announcements:data,rows=5,total=6341; risk_insight_intellectual_property_pledge:empty,rows=None,total=None; risk_insight_penalties:empty,rows=None,total=None; risk_insight_business_anomalies:empty,rows=None,total=None; risk_insight_consumption_restrictions:empty,rows=None,total=None]；metrics=[上游模型评分=99; 上游模型等级=低风险; 开庭公告=4401; 立案公告=1325; 法院公告=6341; 裁判文书=3373; 被执行人=5; 限制高消费=0; 失信被执行=0; 分维度记录数合计（未去重）=15445]；sections=[score_overview=3, litigation_overview=7, litigation_dist=5, serious_violations=0, chattel_mortgage=0, court_hearings=5, court_announcements=5, ip_pledge=0, penalties=0, business_anomalies=0, consumption_restrictions=0]；quality_report={"total_sections":11,"populated_sections":5,"empty_sections":6,"coverage_pct":45}。

## 离线浏览器检查

[Ego Lite 离线图表、页面溢出和脚本检查](browser-check.json)