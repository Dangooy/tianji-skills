# 母语/区域化搜索矩阵

S1 发现阶段用。核心原则：**用目标市场的母语和本地术语搜索，才能挖到本地买家/分销商**——英文 query 只能覆盖国际化大公司，漏掉大量本地中小采购商。

搜索目标：拿到**候选公司官网 URL**（不是数据墙站点如 zauba/volza）。优先免费 WebSearch，不足再上 firecrawl search（仅要 URL，不 `--scrape`）。

产品词按你 `config/company-profile.md` 里的产品线代入。以下以紧固件/垫圈为示例：`平垫圈 washer / 弹垫 spring washer / 螺栓 bolt / 螺母 nut / 紧固件 fastener` + DIN/ISO/GB 标准号。三个示例市场（俄/澳/英）演示矩阵怎么搭，换市场时照同样结构补一节即可。

---

## 俄罗斯 🇷🇺（示例市场一）

母语术语：
- `крепёж` (紧固件)、`шайба` (垫圈)、`болт` (螺栓)、`гайка` (螺母)
- `импортёр` (进口商)、`оптом` (批发)、`поставщик` (供应商)、`дистрибьютор`、`закупка` (采购)

Query 模板（俄语）：
- `шайба DIN 125 оптом поставщик` (DIN125垫圈批发供应商)
- `крепёж импортёр из Китая` (从中国进口紧固件的进口商)
- `болты гайки оптовый поставщик Россия`

本地渠道（优先在这些域名/平台找）：
- **Yandex** 搜索（比 Google 覆盖俄语商家更全）
- **VK 公开页**（公司主页，只读，禁登录态）
- **Pulscen.ru**、**Tiu.ru**（俄语 B2B 目录）
- 政府/企业 **tender 招标平台**（zakupki）——能看到真实采购需求
- 如果你在该市场已有客户：搜现有客户的同城同品类同行（竞对往往也是买家）

## 澳大利亚 🇦🇺（示例市场二：关税窗口）

术语（英语，但要本地化）：
- `fastener wholesaler`、`washer distributor`、`bolt supplier`、`fastener importer`
- `stockist`、`trade supplier`

Query 模板：
- `DIN 125 washer distributor Australia`
- `fastener wholesaler site:.com.au`
- `industrial fastener importer Australia contact`

本地渠道：
- **`.com.au` 域名优先**（本地注册商家）
- 澳洲行业协会会员名录、本地五金/工业黄页（Yellow Pages AU）
- 关税优势切入点示例：ChAFTA 使中国紧固件对澳零关税，而欧美市场对中国碳钢紧固件征反倾销税——开发信可强调价格优势

## 英国 🇬🇧（示例市场三：政策变动窗口）

术语：
- `fastener importer UK`、`fastener stockholder`、`washer supplier UK`
- `stockist`、`trade counter`、`industrial fasteners`

Query 模板：
- `DIN washer stockholder UK`
- `fastener importer site:.co.uk`
- `industrial fastener wholesaler England contact email`

本地渠道：
- **`.co.uk` 域名优先**
- 脱欧后本地分销名录（脱欧使部分欧盟反倾销税不再适用于英国，出现窗口）
- 英国紧固件协会（BAFA）会员

---

## 通用行业目录（跨市场，找候选池用）

- **Europages**、**Kompass**（欧洲 B2B 目录，含公司联系页）
- **展会参展商名单**：行业专业展的参展商名录是高质量候选池（紧固件行业例：MITEX 莫斯科、Fastener Fair 系列、各国五金展）
- 反向信号：已知买家的官网"distributors/partners"页，常列出同类采购商

## 排除规则（S1 必做）

搜到的候选，去重后**排除现有客户和已知联系对象**：
- 读 `config/company-profile.md` 的"现有客户排除名单"
- 如果你维护本地客户档案目录，也一并核对（含此前跑出的 prospect）
- 命中则标 `already_known`，不进入 S2
