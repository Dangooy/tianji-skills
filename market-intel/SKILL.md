---
name: market-intel
description: |
  外贸客户开发/市场情报系统。为 B2B 外贸工厂/贸易公司批量产出高质量、可直接触达的海外客户线索（本文档以紧固件/垫圈行业为贯穿示例，方法适用于任何标准化工业品）。当用户说"开发客户"、"找买家"、"找进口商"、"找经销商"、"XX国家谁买XX产品"、"客户开发"、"市场情报"、"找海外客户"、"批量开发"时触发。即使没明说"/market-intel"，只要意图是"系统性找一批可触达的目标客户"，就应触发。

  五阶段流水线：发现候选公司URL → firecrawl抓官网提取 → 免费并行背调验证 → 确定性打分分级 → 生成Excel报告。

  诚实边界：本系统只用公开网页+免费搜索+firecrawl，**不承诺**海关采购记录、决策人私密联系方式（那些需要付费专业库）。对每条线索按可信度诚实分级（A可直接发信/B待验证/C仅供参考）。
allowed-tools:
  - Bash(firecrawl *)
  - Bash(python3 *)
  - Bash(dig *)
  - WebSearch
  - WebFetch
  - Read
  - Write
  - TaskCreate
  - TaskUpdate
---

# Market Intel — 外贸客户开发系统

为资源有限的中小外贸团队设计：靠 AI 工具批量开发高质量外贸客户，替代"多个业务员手工找客户"。本文档以碳钢紧固件/垫圈行业为贯穿示例，换成你自己的产品线同样适用。

## 立身原则：诚实分级，不假装有海关数据

如果你没有任何付费数据库（ImportGenius/Panjiva 海关数据、企查查、LinkedIn Sales Navigator），本系统**只能**用公开网页 + 免费搜索 + firecrawl 结构化抓取。这决定了：

- **永不承诺**海关采购记录、决策人私人手机/私邮。
- 把免费公开数据靠**多源交叉拼图**做到可用，并对每条线索**诚实分级**。
- C 级线索必须带"下一步验证"，不伪装成可触达。

这不是缺陷，是立身之本：一份诚实标注可信度的 B 级线索表，远比一份伪装成 A 级的幻觉表有用。

## 运行前：填写公司画像

首次使用前，复制 `config/company-profile.template.md` 为 `config/company-profile.md`，填写：

- **产品线与标准号**：你能供的产品 + 对应标准（如 DIN 125 垫圈、DIN 933 螺栓）——S1 搜索词和 S4 产品重合度打分都依赖它。
- **出单主体映射**（可选）：若不同产品线走不同出口主体，在此映射，报告会按线索产品线自动填 `target_entity` 列。
- **目标市场及理由**：优先选有关税窗口的市场（例：ChAFTA 让中国紧固件对澳零关税；英国脱欧后部分欧盟反倾销税不再适用）。
- **质量卖点/开发信切入点**：你的差异化（认证、测试指标、交期），S5 会写进每条线索的"切入策略"。
- **现有客户排除名单**：已合作/已联系的公司，S1 命中即排除。
- **MAX_FIRECRAWL_CREDITS**：单次运行的 firecrawl 预算上限（默认 150）。

每次运行开始时读取此文件。

## 五阶段流水线

```
S1 发现 ──▶ S2 提取 ──▶ S3 背调验证 ──▶ S4 评分 ──▶ S5 输出
免费搜索     firecrawl    免费并行子agent   纯推理       xlsx报告
拿候选URL    中央限流      每公司1个子agent   确定性打分    round-trip自验
```

首次运行**小跨跑通**：限 5-8 家候选，验证整条链路。

### S1 — 发现（Discover）

用免费 WebSearch 跑**母语搜索矩阵**（见 `references/search-matrix.md`，含俄/澳/英三套本地术语+渠道示例），拿候选公司**官网 URL**（不求全文，零 credits）。WebSearch 不足时才用 `firecrawl search "..." --limit N`（仅要 URL，**不加 `--scrape`** 省 credits）。

- **去重 + 排除现有客户**：读 `config/company-profile.md` 的排除名单，命中标 `already_known` 不入 S2。
- 产出候选清单 JSON：`{company_name, homepage_url, country, discovery_channel, discovery_query}`。首次限 5-8 家。

### S2 — 提取（Extract）

**默认用 `firecrawl scrape`（约 1 credit/页），不用 `firecrawl agent`（几十 credit/次）。** 实战验证：对"抓官网 contact/about 页提取联系信息"这类任务，scrape 抓下 markdown、自己正则提取邮箱/电话/规模，效果和 agent 一样但省几十倍成本。agent 只留给需要多页自主导航的复杂站（如联系信息散落深层、要翻 team 页）。

```bash
# 抓 contact 页（失败或空则退回主页）；macOS 无 timeout 命令，直接跑；参数是 --format（单数）
firecrawl scrape "https://<公司>/contact-us" --format markdown -o /tmp/mi_<slug>.md
```

从 markdown 提取：邮箱 `[a-z0-9._%+-]+@[a-z0-9.-]+`、电话、具名联系人+职务（找 procurement/purchasing/sales/manager/director/founder）、是否经营你的产品品类、是否分销商、规模信号（员工/年限/仓库/门店）。

**中央限流（关键护栏）**：主 agent 是**唯一** firecrawl 调用方，`in_flight ≤ 2` 批处理循环——一次派 2 个，回收再派下 2 个，绝不击穿并发上限。批量可用 workflow 分批（每批 ≤2 家）。
- **早淘汰门**：`卖的不是目标品类` 或 `官网无任何联系方式` → 标 `dropped`，不进 S3（省下背调）。
- **邮箱现实**：工业品经销商官网普遍只挂 generic `sales@`/`info@`（E2），具名采购决策人罕见公开——这类市场线索天花板常是 B 级，A 级需靠后续人工触达升级，不要强行拔高评分。
- 记录每家 credits 消耗和抓取来源 URL+时间戳（供 sources 溯源）。

### S3 — 背调验证（Verify）

对每个 S2 存活候选，用 `TaskCreate` **扇出背调子 agent**（每公司一个，隔离上下文）。子 agent 按 `references/verification-playbook.md`：母语媒体交叉、邮箱 E1-E4 分级、规模信号、决策人分层、疑点标注。

- 子 agent **默认只用免费 WebSearch/WebFetch，不新增 firecrawl 外呼**。确需深抓则 SendMessage 向主 agent 申请配额（保证并发不被击穿）。
- 子 agent 回传结构化 JSON（cross_source_count/email_verification/scale_signals/decision_makers/red_flags/native_channel_intel）。

### S4 — 评分（Score）

主 agent 收齐所有子 agent JSON，按 `references/scoring-rubric.md` **确定性加权打分**（可复现，非 LLM 主观）：邮箱可触达 0.40 + 交叉验证 0.25 + 决策人分层 0.20 + 规模匹配 0.15 − 疑点惩罚 0.20（默认权重，按你的行业调整）。分级 A/B/C。组装成 `references/lead-schema.md` 的完整线索 JSON，写 `leads.jsonl`。

### S5 — 输出（Output）

1. 生成 meta.json（关键词/HS/市场/漏斗数/credits消耗/数据源）。
2. 跑报告脚本（内置 round-trip 自验，成功打印 `SUCCESS:`）：
   ```bash
   python3 scripts/build_report.py \
     --leads leads.jsonl --meta meta.json \
     --output ./output/leads_<市场>_<YYYYMMDD_HHMM>.xlsx
   ```
   （路径以 skill 目录为基准；按 Agent Skills 标准安装后即 `<skill目录>/scripts/build_report.py`。）
   脚本打印 `VERIFY_FAIL:` 则按提示修数据重跑，不要无视。
3. **沉淀（可选）**：如果你维护本地 CRM/知识库，可按 `references/lead-schema.md` 的 Markdown 形态把 A/B 级线索各写一个 `prospect-<slug>.md` 档案，C 级汇总成一个市场清单文件，避免档案目录膨胀。
4. 向用户汇报：Excel 路径、漏斗（发现N→存活N→A/B/C分布）、Top A 级线索、firecrawl credits 消耗、下一步建议。

## 成本与合规护栏

| 阶段 | Gate | 规则 |
|------|------|------|
| S1 免费搜索 | 0 | 只读，直接执行 |
| S2 firecrawl 批量 | **1** | 开跑前 `firecrawl --status` 读余额，估 `候选数 × 单次成本`，超 `MAX_FIRECRAWL_CREDITS`（config 中配置，默认 150）则展示计划待用户确认 |
| S5 生成报告 | 0 | 本地文件，round-trip 自验后报告 |

**工具成本阶梯（能免费绝不付费）**：WebSearch/WebFetch(免费) → firecrawl search(仅URL) → firecrawl scrape(约1 credit/页) → firecrawl agent(最贵，仅复杂站、探针后放量)。

**合规**：只抓公开网页，不做登录态抓取，社媒仅读公开页。

## 参考文件

- `references/search-matrix.md` — 母语搜索矩阵示例：俄/澳/英（S1）
- `references/scoring-rubric.md` — 确定性打分 + 邮箱 E1-E4 分级（S4）
- `references/lead-schema.md` — 线索数据 schema（S2-S5）
- `references/verification-playbook.md` — 背调子 agent 交叉验证清单（S3）
- `scripts/build_report.py` — Excel 报告生成 + round-trip 自验（S5）
- `config/company-profile.template.md` — 公司画像模板（运行前必填）
- `examples/` — 虚构 demo 数据，clone 后一条命令即可跑出示例 Excel
