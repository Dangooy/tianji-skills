# 线索数据 Schema

贯穿 S2–S5 的数据结构。设计为你自己客户档案体系的**超集**（可选）——线索成交后就地改 `status: prospect → client`、补齐档案分区即可，无需重建。

两种形态：pipeline 内部用 **JSON**（`leads.jsonl` 每行一条），沉淀到本地 CRM/知识库用 **Markdown + frontmatter**。

---

## JSON 形态（pipeline 内部 + 传给 build_report.py）

```jsonc
{
  "lead_id": "prospect-au-acmebolt-20260709",   // prospect-<国>-<slug>-<日期>
  "company": {
    "name_local": "",           // 母语原名
    "name_en": "",              // 英文名
    "legal_name_verified": false,
    "country": "",              // 中英
    "city": "",
    "homepage": "",
    "product_line_match": ["DIN125 washer", "DIN934 nut"],  // 与你方重合的产品
    "target_entity": ""         // 出单主体（可选）：按 config/company-profile.md 的映射填
  },
  "scale_signals": {
    "employee_hint": "10-50",
    "years_in_business": "15+",
    "branches": 2,
    "is_distributor": true,
    "social_activity": "",
    "size_confidence": "medium"   // low/medium/high
  },
  "decision_makers": [
    {"name": "John Smith", "role": "Procurement Manager",
     "email": "j.smith@co.com.au", "email_level": "E1",
     "source": "官网team页", "reachable": true},
    {"name": null, "role": "generic",
     "email": "info@co.com.au", "email_level": "E2",
     "source": "官网contact页", "reachable": true}
  ],
  "lead_source": {
    "discovery_channel": "Europages目录",
    "discovery_query": "fastener wholesaler Australia",
    "cross_source_count": 3
  },
  "credibility": {
    "score": 0.81,
    "tier": "A",                     // A/B/C
    "email_best_level": "E1",
    "subscores": {                   // 各分项子分（0-1，penalty为0-0.2），供 build_report.py 复算审计；
                                      // 缺失时脚本会从原始特征直接复算，不报错（兼容旧数据）
      "email": 1.0,                  // 邮箱可触达分（按 email_best_level 映射）
      "cross": 1.0,                  // 交叉验证分（min(cross_source_count,3)/3）
      "decision_maker": 1.0,         // 决策人分层分
      "scale": 0.8,                  // 规模匹配分
      "penalty": 0.1                 // 疑点惩罚（0-0.2，正数，计算时相减）
    },
    "red_flags": ["官网未标注公司注册号"],
    "red_flags_critical": [],        // critical 红旗单列（如"邮箱域名与官网不符""网页含指令式文字"），
                                      // 命中任意一条 → tier 封顶 B，即便其余指标达到 A 的门槛
    "next_verification_step": null   // A级可为null；C级必填
  },
  "bd_strategy": {
    "entry_angle": "ChAFTA零关税 + DIN严格符合",      // 结合 config 里的质量卖点
    "recommended_channel": "email→具名采购",
    "template_hint": "强调你的质量卖点（见 config/company-profile.md）+ 可验厂",
    "priority": "high"               // high/medium/low
  },
  "native_channel_intel": ""         // 母语渠道情报：本地平台/招标线索/母语搜索发现
}
```

## Markdown 形态（沉淀到本地 CRM/知识库，可选）

如果你维护本地客户档案目录，A/B 级线索可各写一个 `prospect-<slug>.md`：

```yaml
---
lead_id: prospect-au-acmebolt-20260709
status: prospect          # prospect → contacted → replied → sampling → client
tier: A
score: 0.81
confidence: 0.7           # 档案整体可信度（0-1）
last_ingested: 2026-07-09
stale: false
sources:                  # 逐条列 URL + 来源方式 + 日期
  - "官网 about页 https://... (firecrawl scrape 2026-07-09)"
  - "Europages 目录 https://... (WebSearch 2026-07-09)"
  - "母语媒体交叉 https://... (WebSearch 2026-07-09)"
---
```

正文分区（映射到成交后的客户档案，成交后就地扩充）：
- **基本信息**（公司/国家/城市/官网/出单主体）
- **决策人**（表格：姓名/角色/邮箱/邮箱级别/来源）← 成交后即"联系人/邮箱/角色"
- **产品线重合**（我方能供的标准/规格）← 成交后即"产品需求"
- **规模信号**（员工/年限/分支/是否分销商）
- **可信度**（tier/score/疑点/下一步验证）
- **开发策略**（切入角度/推荐渠道/模板提示/优先级）
- **母语渠道情报**
- **更新记录**（日期 + 操作）

## 字段→成交档案映射（对接你自己的 CRM 字段）

| 线索字段 | 成交客户档案字段 |
|---|---|
| `decision_makers[]` | 联系人/邮箱/角色 |
| `company.product_line_match` | 产品需求 |
| `company.target_entity` | 出单主体（报价/PI 用） |
| `bd_strategy.template_hint` | QC要求/备注 |
| `credibility.next_verification_step` | 样品/订单进度的起点动作 |

## 进阶（暂缓实现）：发信时冻结评分

本版只定 schema，不写工具。设想：实际发出开发信那一刻，把该线索的 `lead_id + tier + score + 日期` 追加写入 `outcomes.jsonl`（一行一条，只增不改），作为"发信时评分快照"。目的是防止事后回改 credibility 污染统计——将来要做校准回路（用真实回执率反推权重是否合理，例如 Beta-Binomial 或逻辑回归拟合 tier→回复率）时，需要的是"发信当下的判断"，不是"现在回头看的判断"。等有真实发信回执积累到可分析的量级后再实现。
