# Demo：CI / PL 核验样例

`demo_ci.xlsx`（商业发票）与 `demo_pl.xlsx`（装箱单）是同一笔虚构订单（卖方 AcmeBolt Manufacturing Co., Ltd. / 买方 Global Fastener Trading Pty Ltd）的两份单据，共 8 个行项目，产品为 DIN 933 螺栓、DIN 934 螺母、DIN 125 平垫圈、DIN 127 弹簧垫圈。

## 生成方式

```bash
python3 generate_demo.py
```

用 openpyxl 生成，跑完会打印两个文件的 `SUCCESS` 路径，可直接重开验证。

## 故意埋的 4 处不一致（对答案）

| # | 位置 | 值 A | 值 B | 说明 |
|---|------|-------|-------|------|
| 1 | 行 3（Hex Bolt DIN 933, M10x50）数量 | CI=500 | PL=5000 | 典型的多打一个零，容易被忽视 |
| 2 | 行 6（Hex Nut DIN 934, M10）净重 | CI=45.2 kg | PL=42.5 kg | 数字换位，肉眼扫读极易漏检 |
| 3 | CI 合计金额（打印 TOTAL） | 253.5 | 逐行小计之和为 353.5 | 合计与明细不符，常见于手工改单后漏更新总计 |
| 4 | CI 金额大写（Amount in words） | 按 353.5 生成大写 | 打印 TOTAL 却是 253.5 | 大写金额与打印数字金额本身互相矛盾（`generate_demo.py` 中 `Amount in words` 按 `correct_total`=353.5 生成，而 `TOTAL` 单元格写入的是 `wrong_total`=253.5），大写与数字互相矛盾本身即构成一处独立不一致 |

跑 `verify-docs` skill 对这两个文件核验，应输出：数量、净重两条行级 MISMATCH；总金额维度应输出"代码重算合计（353.5）与 CI 打印 TOTAL（253.5）不一致"；金额大写核验应输出"大写解析值（353.5）与打印 TOTAL（253.5）不一致"——第 3、4 处虽然根源相同（都是打印 TOTAL 写错），但分属"总金额"和"金额大写"两个独立核验维度，报告中应分别列出，不得合并为一条。

## 用法

在 Claude Code 里对 skill 说：

```
帮我核验一下 verify-docs/examples/demo_ci.xlsx 和 verify-docs/examples/demo_pl.xlsx
```

预期报告应命中上述 4 处差异，其余行级数据应全部 PASS。
