# 🔭 Tianji Skills

#### 天机，可以泄露 —— 一个把外贸生意跑在 Claude Code 上的工厂主

我是杨天机，在一家紧固件工厂用 Claude Code 跑日常外贸业务。这里沉淀的是**在真实生产环境里验证过、脱敏后开源**的 skill。每个 skill 都能直接装进你的 Claude Code 使用，行业示例以紧固件/垫圈为主，方法论适用于任何 B2B 外贸品类。

## Skill 目录

| Skill | 一句话定位 | 状态 |
|-------|-----------|------|
| [market-intel](./market-intel/) | 外贸客户开发流水线：免费公开数据 → 可触达的分级客户线索 Excel | ✅ 可用 |

（持续更新中）

## 安装

最简单的方式——直接对 Claude Code 说：

```
帮我安装这个 skill：https://github.com/Dangooy/tianji-skills 里的 market-intel
```

或手动安装：

```bash
git clone https://github.com/Dangooy/tianji-skills.git
cp -r tianji-skills/market-intel ~/.claude/skills/
```

然后按各 skill 目录内 README 的说明填写配置（如 `config/company-profile.md`）、准备依赖（如 firecrawl API key）。

## 设计理念

- **诚实优先**：拿不到的数据（海关记录、私密联系方式）明说拿不到，每条产出标注可信度，不给幻觉结果镀金。
- **能免费绝不付费**：免费搜索打底，付费 API 只在必要环节用，且带预算 gate。
- **可复现**：打分公式确定（相同抽取特征必得相同分数）、报告生成后 round-trip 重开自验输出自洽。

## 关于

我是杨天机，白天管工厂做外贸，晚上把跑通的 AI 工作流整理开源。这些 skill 都是自己每天在用的，对你有帮助的话给个 ⭐。

- 公众号：杨天看世界
- 小红书：杨天机

## License

MIT
