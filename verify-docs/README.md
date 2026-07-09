# 🔎 verify-docs（核单）— 贸易文件交叉核验

一个 Claude Code skill：对比商业发票（CI）和装箱单（PL），逐项核验数量、品名、单价、总金额、净重毛重、金额大写是否一致，输出 Markdown 差异报告。

## 为什么做这个

CI 和 PL 理论上是同一批货的两种表述，但实际操作中它们经常是两份手工维护的 Excel——客户改单、业务员临时调整数量、报关行要求补件，任何一次编辑都可能导致两份文件的数字悄悄脱节。CI/PL 数字不符，轻则被银行或报关行打回来改单，重则押货款、清关延误。

人工逐格核对费眼且漏检——尤其是"数量多打一个零""净重数字换位""合计金额忘记更新"这类问题，肉眼扫读很容易放过。

## 核对的 8 个维度

1. 行项目数量（两份文件行数一致）
2. 品名/描述（逐行比对产品名称和规格）
3. 数量（quantity 逐行一致）
4. 单价（CI 与 PL 对应项一致，如 PL 有此列）
5. 总金额（逐行小计及合计一致）
6. 净重 N.W.（逐行及合计一致）
7. 毛重 G.W.（逐行及合计一致）
8. 金额大写（Amount in words 与数字金额一致）

## 输出示例

```markdown
# 贸易文件核验报告
- 文件1: demo_ci.xlsx
- 文件2: demo_pl.xlsx
- 核验时间: 2026-07-09

## 汇总
- 总行项目数: CI=8 / PL=8
- 差异数: 3
- 结果: FAIL

## 差异明细

| 行号 | 维度 | 文件1值 | 文件2值 | 状态 |
|------|------|---------|---------|------|
| 3 | 数量 | 500 | 5000 | MISMATCH |
| 6 | 净重 | 45.2kg | 42.5kg | MISMATCH |
| TOTAL | 合计金额 | 253.5 | 353.5(逐行之和) | MISMATCH |
```

## 先跑个 demo

```bash
python3 examples/generate_demo.py
```

生成 `examples/demo_ci.xlsx` 和 `examples/demo_pl.xlsx`，故意埋了 3 处不一致，具体见 [`examples/README.md`](./examples/README.md) 对答案。跑完 skill 应精准命中这 3 处。

## 安装

把 `verify-docs/` 目录放进 Claude Code skills 目录（如 `~/.claude/skills/verify-docs/`），或对 Claude 说"帮我安装这个 skill：<仓库URL>"。

依赖：`python3` + `openpyxl`（`pip install openpyxl`）。

## 目录结构

```
verify-docs/
├── SKILL.md              # skill 主文档
└── examples/
    ├── generate_demo.py  # 生成虚构 CI/PL demo（含3处埋点）
    ├── demo_ci.xlsx
    ├── demo_pl.xlsx
    └── README.md          # 埋点对答案
```
