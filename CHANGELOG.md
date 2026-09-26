# 更新记录

面向公开的方法与规则变更记在此处。私有配置、客户与业务数据不入库——公开范围见 [Publication Policy](PUBLICATION_POLICY.md)。

---

## 2026-09-26

### market-intel — 评分复算补强（安全修复）

**问题**：`scripts/build_report.py` 只复算 `email` / `cross` / `penalty` 三个子分，`decision_maker` 与 `scale` 仅做 `[0,1]` 截断。效果等同于「自报值可直接参与 A 级判定」。

合成数据实测：一条只有 generic 邮箱（诚实决策人分 0.3）、3 个交叉源的线索，配上自报 `decision_maker=1.0` 与 `scale=1.0`，即可越过门槛进入「A级·可直接发信」名单。

**修复**：

1. `decision_maker` 与 `_decision_maker_component()` 交叉核对——该判据早已写在 `references/scoring-rubric.md`，函数也已存在，此前只是漏调用。
2. A 级门槛新增「可复算子集」条件：`0.40·email + 0.25·cross + 0.20·dm − penalty ≥ 0.75`，即去掉唯一无法独立复算的 `scale`。

**效果**：决策人诚实分取最低档 0.3 时，可复算子集上限为 `0.40 + 0.25 + 0.06 = 0.71 < 0.75`，`scale` 无法再单独把证据不足的线索抬进 A 级。A 级完全由代码可验证的证据支撑。

**验证**（`/usr/bin/python3` + openpyxl 3.1.5）：

| 检验 | 结果 |
|---|---|
| 示例数据回归 | `SUCCESS`，A1/B2/C1，**零 WARN**（无回归） |
| 3 条合成「虚报 A」线索（自报 E1 与实际不符 / 单源 / critical 红旗） | 全部未进入 A 级 |
| 健康对照线索 | 仍进入 A 级（门槛非一刀切） |
| 决策人分膨胀探针 | 被拦截 |

### market-intel — 执行方式改为按环境能力选择

S3 背调原先写死「用 `TaskCreate` 扇出子 agent」。改为：**子 agent 机制可用、且成本与并发范围合适时并行；否则由主 agent 串行完成同一份验证清单**，两种方式输出字段完全一致。

理由：CLI 支持多代理，不等于每个环境都该并行——决定的是速度，不是覆盖率。与 [Roadmap](ROADMAP.md) 中 "Keep skills usable across agent environments where their required tools and permissions are available" 一致。

### market-intel — 本地定制下沉到私有配置

- `config/company-profile.template.md` 新增两个**可选**配置段：「知识库回写」与「付费工具门禁」。
- S5 的沉淀步骤改为由配置驱动：未配置则跳过，不臆造路径。
- 通用 `SKILL.md` 不再承载任何具体路径或企业信息——换知识库、换公司只需改配置，无需改技能本体。

### 文档

- `references/scoring-rubric.md`：补 A 级第二条件与「可复算子集」定义；明确 `scale` 是唯一无法独立复算的分量（此前「逐条复算」的表述过宽，已收紧为诚实边界说明）。
