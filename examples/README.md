# enterprise-risk-skill：已验收示例

本目录只展示 **5 个完全通过的真实正向场景**（最低要求4例）。

每例均为真实、非空、非缓存调用；技术检查、独立业务检查和离线浏览器检查全部通过。不把空数据、报错处理或仅生成页面计作通过。历史验收记录保留在本地 test-records/；本目录的 HTML/Markdown 由原 JSON 重渲染，不代表重新查询或重新验收。

| 场景 | 真实使用需求 | 报告 |
|---|---|---|
| [供应商风险准入](01-supplier-risk/README.md) | 对宁德时代新能源科技股份有限公司做供应商风险初筛，覆盖评分、诉讼、处罚、异常和限高。 | [HTML](01-supplier-risk/report.html) / [MD](01-supplier-risk/report.md) / [JSON](01-supplier-risk/report.json) |
| [重大合同相对方风控](02-contract-risk/README.md) | 检查中国建筑第八工程局有限公司的诉讼画像、开庭公告、法院公告与动产抵押。 | [HTML](02-contract-risk/report.html) / [MD](02-contract-risk/report.md) / [JSON](02-contract-risk/report.json) |
| [品牌合作负面风险核验](04-brand-risk/README.md) | 查看贵州茅台酒股份有限公司是否有处罚、异常、诉讼和限高线索。 | [HTML](04-brand-risk/report.html) / [MD](04-brand-risk/report.md) / [JSON](04-brand-risk/report.json) |
| [平台企业合规风险概览](05-platform-risk/README.md) | 核查北京京东世纪贸易有限公司的行政处罚、经营异常、诉讼画像和法院公告。 | [HTML](05-platform-risk/report.html) / [MD](05-platform-risk/report.md) / [JSON](05-platform-risk/report.json) |
| [管理层风险快报](07-compact-risk/README.md) | 生成华为技术有限公司风险快报，列表每类最多展示 5 条。 | [HTML](07-compact-risk/report.html) / [MD](07-compact-risk/report.md) / [JSON](07-compact-risk/report.json) |

- [逐例验收结果](results.json) · [业务复核](review.json) · [证据摘要](evidence-index.json)
- 完整测试记录仅存于本地 test-records/live-replaced-20261027/（仅本地审计用，不随本目录发布），不属于可展示示例。
- 当前数据与结论限于原查询时点及公开样本；覆盖率不代表准确率或低风险。
