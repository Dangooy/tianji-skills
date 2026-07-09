# Excel 报告结构说明

`build_report.py` 生成的 xlsx 有 5 个 Sheet：

| Sheet | 内容 | 给谁看 |
|-------|------|--------|
| **线索总览** | 全部线索按 tier(A绿/B黄/C红)排序，含公司/国家/score/最佳邮箱/决策人/产品重合/出单主体/交叉源数/推荐渠道/切入策略 | 快速浏览全局 |
| **A级·可直接发信** | 只含 A 级，完整触达信息 + 切入角度 + 模板提示 + 母语情报 | **当天可用的行动清单** |
| **B-C级·待验证** | B/C 级，每行带 red_flags 和 next_verification_step | 补验证后再触达 |
| **母语渠道情报** | 有母语渠道情报的线索按市场汇总 | 本地化开发参考 |
| **运行元数据** | 关键词/HS/市场、漏斗数、credits 消耗、数据源、免责声明 | 溯源与成本审计 |

"出单主体"列对应 lead JSON 的 `company.target_entity`，按 `config/company-profile.md` 的出单主体映射填写；如果你只有一个出口主体，可留空。

## 数据契约

脚本输入 = `leads.jsonl`（每行一条 `references/lead-schema.md` 的 JSON）+ `meta.json`。
不要手工拼单行 JSON 字符串传参（脆弱做法）——写成文件用 `--leads`/`--meta`。

meta.json 结构：
```json
{
  "keywords": [], "hs_codes": [], "markets": [],
  "funnel": {"discovered": 0, "extracted": 0, "verified": 0},
  "cost": {"firecrawl_credits": 0},
  "sources_used": []
}
```

## 自验契约

脚本内置 round-trip：生成后 openpyxl 重开，核对 总览行数==线索数、A级sheet行数==A级数、B-C行数==B-C数、免责声明存在。通过打印 `SUCCESS:`，失败打印 `VERIFY_FAIL: <原因>` 且退出码 1。
