# market-intel — 外贸客户开发/市场情报系统

一个 Claude Code skill：为 B2B 外贸工厂/贸易公司**系统性批量产出可触达的海外客户线索**，替代"多个业务员手工找客户"。本仓库以紧固件/垫圈行业为贯穿示例，换成你自己的产品线同样适用。

## 为什么做这个

大多数中小外贸团队找客户的现状：业务员在 Google 里一个个搜，搜到官网抄个 `info@` 邮箱，群发开发信，回复率趋近于零。市面上的"客户开发工具"要么卖你海关数据（贵），要么给你一堆没验证过的邮箱列表（假）。

这个 skill 的答案是：**不装作有付费数据，把免费公开数据做扎实**——母语搜索找到本地买家、firecrawl 结构化抓官网、并行子 agent 免费背调交叉验证、确定性打分，最后诚实告诉你每条线索"能不能直接发信"。

## 三个设计亮点

1. **诚实分级立身**：A 级"可直接发信"、B 级"补一步验证"、C 级"仅供参考且必须带下一步验证动作"。永不承诺海关记录和私密联系方式。一份诚实的 B 级表，比一份伪装的 A 级表值钱。
2. **firecrawl 中央限流**：主 agent 是唯一 firecrawl 调用方，`in_flight ≤ 2` 批处理，预算 gate 超限先问人——多 agent 并行时不击穿并发和钱包。
3. **scrape 代替 agent，省几十倍成本**：实战验证，"抓官网提取联系方式"这类任务用 `firecrawl scrape`（约 1 credit）抓 markdown 自己正则提取，效果与 `firecrawl agent`（几十 credits）相同。agent 只留给真正需要多页自主导航的复杂站。

## 五阶段流水线

```
S1 发现 ──▶ S2 提取 ──▶ S3 背调验证 ──▶ S4 评分 ──▶ S5 输出
免费搜索     firecrawl    免费并行子agent   纯推理       xlsx报告
拿候选URL    中央限流      每公司1个子agent   确定性打分    round-trip自验
```

## 搜索与抓取工具栈

本 skill 用两层工具，各司其职：

| 层 | 工具 | 用在哪 | 成本 |
|---|---|---|---|
| 搜索/背调 | Agent 内建 WebSearch / WebFetch | S1 发现候选、S3 背调交叉验证 | 免费 |
| 结构化抓取 | [firecrawl](https://firecrawl.dev)（云端 API） | S2 抓官网提取联系方式 | 按 credit 计费 |

**能搜到的范围**（全部是公开可索引的网页）：

- 公司官网（about / contact / team 页）
- B2B 行业目录：Europages、Kompass、本地黄页（如澳洲 Yellow Pages、俄语 Pulscen/Tiu）
- 行业协会会员名录、展会参展商名单
- 母语媒体、新闻、政府招标公告（真实经营的旁证）
- 社媒**公开页**：LinkedIn 公司页、VK 公司主页（只读，不登录）

**拿不到的**（诚实边界的另一面）：登录墙后的内容、海关采购数据库、付费库（LinkedIn Sales Navigator 等）里的私密联系方式。

**最佳实践**：

1. **不用本地浏览器，也不用无头浏览器。** firecrawl 在云端完成 JS 渲染并返回 markdown，本机零 Chrome/Playwright/Selenium 依赖——不用维护浏览器环境，也不会把你自己的 IP 暴露给反爬系统。
2. **不做登录态抓取。** 不登录任何平台去扒数据：一是合规，二是零封号风险（你的社媒账号是资产）。社媒信息只取公开页。
3. **母语搜索优于英文搜索。** 搜俄罗斯买家用俄语词（`крепёж импортёр`），并优先 Yandex 系渠道——英文 query 只能捞到国际化大公司，本地中小采购商全在母语结果里。详见 `references/search-matrix.md`。
4. **成本阶梯，能免费绝不付费**：WebSearch（免费）→ firecrawl search（仅拿 URL，不带 `--scrape`）→ firecrawl scrape（约 1 credit/页）→ firecrawl agent（几十 credits，只留给联系方式藏得深的复杂站）。

## 安装与依赖

1. 把 `market-intel/` 目录放进你的 Claude Code skills 目录（如 `~/.claude/skills/market-intel/`），或直接对 Claude 说"帮我安装这个 skill：<仓库URL>"。
2. 依赖：
   - [firecrawl CLI](https://firecrawl.dev)（自备 API key，S2 抓取用；免费额度即可跑小批量）
   - `python3` + `openpyxl`（`pip install openpyxl`，Excel 报告用）
3. 复制 `config/company-profile.template.md` 为 `config/company-profile.md`，填入你的产品线、目标市场、卖点和排除名单。

## 先跑个 demo

不配置任何东西，先用虚构示例数据验证报告链路：

```bash
python3 scripts/build_report.py \
  --leads examples/demo_leads.jsonl \
  --meta examples/demo_meta.json \
  --output /tmp/demo_report.xlsx
```

打印 `SUCCESS: /tmp/demo_report.xlsx` 即通。打开看 5 个 Sheet：线索总览 / A级行动清单 / B-C待验证 / 母语渠道情报 / 运行元数据。

## 诚实边界（务必读）

本系统只用公开网页 + 免费搜索 + firecrawl。它**拿不到**：海关采购记录、决策人私人手机/私邮、付费库数据。工业品经销商官网普遍只挂 `sales@`/`info@`，所以这类市场的线索天花板常是 B 级——这是数据现实，不是系统缺陷。A 级靠后续人工触达升级，不靠评分注水。

## 目录结构

```
market-intel/
├── SKILL.md                        # skill 主文档（五阶段流水线 + 护栏）
├── config/company-profile.template.md  # 运行前必填的公司画像模板
├── references/
│   ├── search-matrix.md            # 母语搜索矩阵（俄/澳/英示例）
│   ├── scoring-rubric.md           # 确定性打分 + 邮箱E1-E4分级
│   ├── verification-playbook.md    # 背调子agent清单
│   └── lead-schema.md              # 线索数据schema
├── scripts/build_report.py         # Excel报告生成 + round-trip自验
├── assets/report_template_notes.md # 报告结构说明
└── examples/                       # 虚构demo数据（clone即可跑）
```
