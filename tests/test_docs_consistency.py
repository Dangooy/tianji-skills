"""文档 / 代码一致性测试（防漂移）。

这类测试不检查"代码对不对"，而是检查**文档写的和代码做的还是不是一回事**。

为什么需要它：本仓库反复吃过的亏就是"改了代码没改文档"和"改了文档没改代码"——
评分权重写在三处（脚本常量、rubric 公式、SKILL.md 正文）、Sheet 名写在两处、
背调执行方式写在两处。人工同步迟早漏，让测试盯着。

这些测试是**故意**会在文档过时时变红的。红了就改文档，不要注释掉测试。
"""

from __future__ import annotations

import re

import pytest
import yaml

from conftest import (
    ALL_SHEETS,
    REPO_ROOT,
    RUBRIC,
    SKILL_README,
    SKILL_MD,
    SKILLS_DIRS,
    strip_code_fences,
)

# rubric 公式里的中文子分名 → 脚本常量键
COMPONENT_NAMES = {
    "邮箱可触达分": "email",
    "交叉验证分": "cross",
    "决策人分层分": "decision_maker",
    "规模匹配分": "scale",
}


@pytest.fixture(scope="module")
def rubric_text() -> str:
    return RUBRIC.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# 评分公式：rubric ↔ 脚本常量
# ─────────────────────────────────────────────────────────────


def test_rubric_weights_match_code(br, rubric_text):
    """`scoring-rubric.md` 公式里的权重必须与 `build_report.py` 的 W 完全一致。

    文档写 0.40 而代码算 0.35，用户按文档理解自己的分数就会错。
    """
    found = {
        COMPONENT_NAMES[name]: float(value)
        for value, name in re.findall(
            r"([0-9]*\.?[0-9]+)\s*·\s*(" + "|".join(COMPONENT_NAMES) + r")", rubric_text
        )
    }
    assert found, "rubric 里没解析到评分公式 —— 公式格式变了？"
    assert found == pytest.approx(br.W, abs=1e-9), (
        f"文档权重 {found} 与代码 {br.W} 不一致"
    )


def test_rubric_penalty_matches_code(br, rubric_text):
    """疑点惩罚的封顶值与单条扣分也必须一致。"""
    cap = re.search(r"−\s*([0-9]*\.?[0-9]+)\s*·\s*疑点惩罚", rubric_text)
    assert cap, "rubric 里没解析到疑点惩罚项"
    assert float(cap.group(1)) == pytest.approx(br.PENALTY_CAP)

    per_flag = re.search(r"每个\s*minor\s*red_flag\s*扣\s*([0-9]*\.?[0-9]+)", rubric_text)
    assert per_flag, "rubric 里没写单条 minor 红旗的扣分"
    assert float(per_flag.group(1)) == pytest.approx(br.PENALTY_PER_FLAG)


def test_rubric_documents_actual_tier_thresholds(br, rubric_text):
    """分级门槛（A / B 分数线）必须与代码常量一致。"""
    assert f"score ≥ {br.A_SCORE_MIN}" in rubric_text, "rubric 的 A 级分数线与 A_SCORE_MIN 不符"
    assert f"{br.B_SCORE_MIN} ≤ score" in rubric_text, "rubric 的 B 级下界与 B_SCORE_MIN 不符"


# ─────────────────────────────────────────────────────────────
# 背调执行方式：两处说法必须一致
# ─────────────────────────────────────────────────────────────


def _skill_s3_section() -> str:
    text = SKILL_MD.read_text(encoding="utf-8")
    start = text.find("### S3")
    end = text.find("### S4")
    assert start != -1 and end > start, "SKILL.md 里找不到 S3 段落"
    return text[start:end]


def test_skill_documents_both_fanout_paths():
    """S3 必须同时写明「并行」与「串行兜底」两条路径。

    设计意图：子 agent 并行是按环境能力选择的优化，不是硬性要求 ——
    不支持多代理的环境应当串行完成同一份清单，而不是跳过检查。
    只写并行会误导那些环境。
    """
    s3 = _skill_s3_section()
    assert "并行" in s3, "S3 未说明并行路径"
    assert "串行" in s3, "S3 未说明串行兜底路径"


def test_pipeline_diagram_does_not_promise_unconditional_subagents():
    """流水线图若提到子 agent，就必须体现"可选"而非断言每公司一个。

    历史事故（2026-09-26）：S3 正文已改为条件式并行，流水线图却仍写着
    「每公司1个子agent」—— 同一个文件自相矛盾。
    """
    text = SKILL_MD.read_text(encoding="utf-8")
    diagrams = re.findall(r"```(.*?)```", text, re.S)
    pipeline = [d for d in diagrams if "S1 发现" in d]
    assert pipeline, "SKILL.md 里找不到流水线图"

    for diagram in pipeline:
        if "子agent" in diagram or "子 agent" in diagram:
            assert any(k in diagram for k in ("可选", "条件", "合适", "视环境")), (
                "流水线图提到了子 agent，但没标明它是可选的：\n" + diagram
            )


def test_readme_diagram_matches_skill_diagram():
    """`market-intel/README.md` 的流水线图应与 SKILL.md 同一口径。"""
    readme_text = SKILL_README.read_text(encoding="utf-8")
    diagrams = re.findall(r"```(.*?)```", readme_text, re.S)
    pipeline = [d for d in diagrams if "S1 发现" in d]
    assert pipeline, "README 里找不到流水线图"

    for diagram in pipeline:
        if "子agent" in diagram or "子 agent" in diagram:
            assert any(k in diagram for k in ("可选", "条件", "合适", "视环境")), (
                "README 流水线图提到了子 agent，但没标明它是可选的：\n" + diagram
            )


# ─────────────────────────────────────────────────────────────
# Sheet 名：代码 ↔ README
# ─────────────────────────────────────────────────────────────


def test_readme_mentions_actual_sheet_names():
    """README 里提到的 Sheet 名必须与脚本实际生成的完全一致。

    历史问题：README 写「A级行动清单 / B-C待验证」，实际是
    「A级·可直接发信 / B-C级·待验证」—— 用户按名字去 Excel 里找会找不到。
    """
    readme = SKILL_README.read_text(encoding="utf-8")
    missing = [name for name in ALL_SHEETS if name not in strip_code_fences(readme)]
    assert not missing, f"README 未提及这些实际存在的 Sheet 名：{missing}"


# ─────────────────────────────────────────────────────────────
# 排版：字面量转义残留
# ─────────────────────────────────────────────────────────────


def test_no_literal_escape_sequences_in_markdown():
    r"""Markdown 正文里不得出现字面量 `\n` —— 在 GitHub 上会原样显示成 \n。

    历史问题：根 README.md 第 5 行有一处 `\n\n`，网页上直接渲染出这几个字符。
    代码块内的转义序列属正常用法，故先剥离围栏代码块再检查。
    """
    offenders = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        body = strip_code_fences(path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(body.splitlines(), 1):
            if "\\n" in line:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert not offenders, "正文含字面量 \\n（会原样显示在网页上）：" + ", ".join(offenders)


# ─────────────────────────────────────────────────────────────
# SKILL.md frontmatter：符合 Agent Skills 规范
# ─────────────────────────────────────────────────────────────


def _frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, f"{path.name} 缺少 frontmatter"
    return yaml.safe_load(match.group(1))


@pytest.mark.parametrize("skill_dir", SKILLS_DIRS, ids=lambda p: p.name)
def test_skill_frontmatter_is_spec_compliant(skill_dir):
    """按 Agent Skills 规范校验每个技能的 frontmatter。

    规范要求（见 pi 的 docs/skills.md 引用）：
    - `name`：小写字母/数字/连字符，≤64 字符，不得有连续或首尾连字符
    - `description`：≤1024 字符
    - 两者均为必填
    """
    fm = _frontmatter(skill_dir / "SKILL.md")

    assert isinstance(fm, dict), f"{skill_dir.name}: frontmatter 不是映射"
    name = fm.get("name")
    description = fm.get("description")

    assert name, f"{skill_dir.name}: 缺 name"
    assert description, f"{skill_dir.name}: 缺 description"

    # 名称与目录名一致（最可移植的做法）
    assert name == skill_dir.name, f"{skill_dir.name}: name「{name}」与目录名不一致"

    assert len(name) <= 64, f"{skill_dir.name}: name 超过 64 字符"
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name), (
        f"{skill_dir.name}: name 含非法字符或有连续/首尾连字符"
    )

    assert len(description) <= 1024, (
        f"{skill_dir.name}: description 长 {len(description)} 字符，超过规范上限 1024"
    )


@pytest.mark.parametrize("skill_dir", SKILLS_DIRS, ids=lambda p: p.name)
def test_skill_readme_exists(skill_dir):
    assert (skill_dir / "README.md").exists(), f"{skill_dir.name}: 缺 README.md"
