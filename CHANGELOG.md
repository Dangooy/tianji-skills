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

### 测试与 CI（新增）

本仓库此前风有手动验证，无自动化测试也无 CI。本次补齐。

**新增 `tests/`（110 个测试）**，分四层：

| 文件 | 层级 | 覆盖 |
|---|---|---|
| `test_scoring_rules.py` | 单元 | 邮箱 E1–E4 分级、采购职能白名单、决策人分层、域名归一化、`_check_lead` 结构校验 |
| `test_credibility.py` | 单元 | `_recompute_credibility`：自报值覆盖、critical 红旗封顶 B、四个子分逐个交叉核对、`scale` 不得单独制造 A 级、旧数据兼容、幂等性 |
| `test_security_regression.py` | 端到端 | 真跑 CLI、真开 Excel、真看「A级·可直接发信」名单：三条不同手法的伪造成果均被拦，健康对照仍进 A |
| `test_report_output.py` | 端到端 | demo 回归（A1/B2/C1 零 WARN）、Sheet 名与顺序、坏行不击穿整单、空数据/缺参数干净失败、免责声明 |
| `test_docs_consistency.py` | 防漂移 | 评分权重／惩罚值与 rubric 公式一致、A/B 分数线与代码常量一致、S3 同时写明并行与串行、流水线图不得断言无条件并行、README 提及的 Sheet 名与实际一致、正文无字面量转义序列（反斜杠加 n）、frontmatter 符合 Agent Skills 规范 |

测试数据全部在运行期合成，域名用 `.invalid` 保留域，不含任何真实客户信息。

**新增 CI**（`.github/workflows/ci.yml`）：Python 3.11 / 3.12 矩阵，每次 push 与 PR 跑 `ruff check .` + `pytest`。

**新增配置**：`pyproject.toml`（pytest 与 ruff 配置；本仓库交付 skill 而非 Python 包，故无 `[project]` 段）、`requirements-dev.txt`（开发/CI 依赖）。

**顺带修掉的真问题**：

- `market-intel/scripts/build_report.py`：删除未使用的 `re` 导入（死代码）。
- `verify-docs/examples/generate_demo.py`：删除未使用的 `Alignment` 导入。

**同批修掉的文档不一致**（由新增的防漂移测试指出）：

- `market-intel/SKILL.md` 与 `market-intel/README.md`：流水线图仍写着「免费并行子agent / 每公司1个子agent」，与已改为条件式的 S3 正文矛盾；现改为「子agent背调(可选) / 逐公司验证清单」。README 正文的「并行子 agent 免费背调交叉验证」同步改为说明两条路径。
- `market-intel/README.md`：demo 小节的 Sheet 名写错（「A级行动清单 / B-C待验证」实际为「A级·可直接发信 / B-C级·待验证」），用户按名字去 Excel 里会找不到。
- 根 `README.md`：删掉正文里一处字面量转义序列（反斜杠加 n，GitHub 网页上会原样显示这几个字符）。

**已发现但未在本批修改**：`market-intel/scripts/build_report.py` 有 16 处语句风格告警（分号连写 E702、变量名 `l` E741）。已在 `pyproject.toml` 的 `[tool.ruff.lint]` 里显式排除 E7 并说明原因；若要收紧，应单独提交、逐条改完并重跑全部测试。
