# Demo：英文询盘转中文报价表样例

`demo_inquiry.xlsx` 是一份虚构的英文询盘，9 个行项目，覆盖 DIN 125（平垫圈）、DIN 7980（弹簧锁紧垫圈）、DIN 471（轴用弹性挡圈）三个标准。

## 生成方式

```bash
python3 generate_demo.py
```

## 覆盖的识别场景

| # | 场景 | 对应列/数据 |
|---|------|------------|
| 1 | 标准列头 + 有数据 | `COMMODITY DESCRIPTION` / `Surface treatment` / `Qty/Kgs` —— 直接翻译保留 |
| 2 | 标准列头 + 空数据（报价列） | `CNY/Kgs` 列全部留空，应被识别为报价填写列并标黄 |
| 3 | **无列头 + 有数据** | 第 3 列没有列头，但数据是 `C75S` / `65Mn` / `SS304`，应被推断为"钢材牌号"列，信息不丢失 |
| 4 | 只有规格号，需查表补全尺寸 | `M8`/`M10`/`M12`（DIN 125-1A）、`D8`/`D10`/`D12`（DIN 7980，其中 D12 为 HEAVY 重型）、`20`/`25`/`30`（DIN 471 轴用弹性挡圈的轴径）均只给规格号，需靠 `references/din_dimensions.md` 补全内径×外径×厚度或轴径×外径×厚度 |
| 5 | 表面处理留空的行 | 最后一行 `Surface treatment` 为空，模拟客户未填写的常见情况 |

## 用法

在 Claude Code 里对 skill 说：

```
帮我把 rfq-to-quotation/examples/demo_inquiry.xlsx 转成中文报价表
```

预期输出一份带黄色报价列的中文 Excel，9 行产品补全尺寸、无列头的钢材牌号列被正确识别为"钢材牌号"且未丢失任何数据。
