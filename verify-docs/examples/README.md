# Demo：CI / PL 核验样例

`demo_ci.xlsx`（商业发票）与 `demo_pl.xlsx`（装箱单）是同一笔虚构订单（卖方 AcmeBolt Manufacturing Co., Ltd. / 买方 Global Fastener Trading Pty Ltd）的两份单据，共 8 个行项目，产品为 DIN 933 螺栓、DIN 934 螺母、DIN 125 平垫圈、DIN 127 弹簧垫圈。

## 生成方式

```bash
python3 generate_demo.py
```

用 openpyxl 生成，跑完会打印两个文件的 `SUCCESS` 路径，可直接重开验证。

## 故意埋的 3 处不一致（对答案）

| # | 位置 | CI 值 | PL 值 | 说明 |
|---|------|-------|-------|------|
| 1 | 行 3（Hex Bolt DIN 933, M10x50）数量 | 500 | 5000 | 典型的多打一个零，容易被忽视 |
| 2 | 行 6（Hex Nut DIN 934, M10）净重 | 45.2 kg | 42.5 kg | 数字换位，肉眼扫读极易漏检 |
| 3 | CI 合计金额（TOTAL） | 253.5 | 逐行小计之和为 353.5 | 合计与明细不符，常见于手工改单后漏更新总计 |

跑 `verify-docs` skill 对这两个文件核验，应输出 3 条 MISMATCH，且金额大写核验会显示：CI 数字金额（253.5，打印值）与逐行相加的真实合计（353.5）不一致。

## 用法

在 Claude Code 里对 skill 说：

```
帮我核验一下 verify-docs/examples/demo_ci.xlsx 和 verify-docs/examples/demo_pl.xlsx
```

预期报告应命中上述 3 处差异，其余 5 行应全部 PASS。
