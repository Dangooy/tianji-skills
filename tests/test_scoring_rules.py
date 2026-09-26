"""评分基础规则的单元测试。

覆盖 `build_report.py` 里所有参与"特征 → 分数"计算的纯函数。
这一层不生成 Excel，只验证判定逻辑本身 —— 一旦这些函数的行为变了，
上面的端到端测试会跟着变红，但只有这里能指出**具体哪个规则**坏了。
"""

from __future__ import annotations

import pytest


# 合成线索工厂 `lead_factory` 定义在 tests/conftest.py（供所有测试文件共用）


# ─────────────────────────────────────────────────────────────
# 域名与邮箱本地部分
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://www.example.com/contact", "example.com"),
        ("https://example.com", "example.com"),
        ("http://Example.COM:8443/x", "example.com"),
        ("example.com", "example.com"),  # 无 scheme 时补 http://
        ("", ""),
        (None, ""),
    ],
)
def test_domain_from_url(br, raw, expected):
    assert br._domain(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("sales@www.example.com", "example.com"),
        ("SALES@Example.COM", "example.com"),
        ("not-an-email", ""),
        ("", ""),
    ],
)
def test_domain_from_email(br, raw, expected):
    assert br._domain(raw, is_email=True) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [("purchasing@example.com", "purchasing"), ("A.B@x.example", "a.b"), ("no-at-sign", ""), ("", "")],
)
def test_local_part(br, raw, expected):
    assert br._local_part(raw) == expected


# ─────────────────────────────────────────────────────────────
# 邮箱分级 E1–E4
# ─────────────────────────────────────────────────────────────

HOME = "https://www.acme.example.invalid"


def _dm(**kwargs) -> dict:
    base = {"name": None, "role": "generic", "email": "info@acme.example.invalid",
            "email_level": "E2", "source": "synthetic"}
    base.update(kwargs)
    return base


@pytest.mark.parametrize(
    "dm,expected",
    [
        # 具名 + 域名匹配 → E1
        (_dm(name="Jane Doe", email="jane@acme.example.invalid", email_level="E1"), "E1"),
        # 采购职能前缀 + 域名匹配 → E1
        (_dm(email="purchasing@acme.example.invalid", email_level="E1"), "E1"),
        (_dm(email="procurement@acme.example.invalid", email_level="E1"), "E1"),
        (_dm(email="sourcing@acme.example.invalid", email_level="E1"), "E1"),
        # 通用前缀 → E2
        (_dm(email="sales@acme.example.invalid", email_level="E2"), "E2"),
        (_dm(email="office@acme.example.invalid", email_level="E2"), "E2"),
        # www. 归一化后仍算域名匹配
        (_dm(name="Jane", email="jane@www.acme.example.invalid", email_level="E1"), "E1"),
    ],
)
def test_email_level_happy_paths(br, dm, expected):
    level, critical = br._verify_email_level(dm, HOME)
    assert level == expected
    assert critical is None


def test_email_level_e1_claim_downgraded_when_not_named_or_purchasing(br):
    """自报 E1 但既不具名、本地部分也不占采购白名单前缀 → 强制降 E2。

    这是"随手挂个 E1"的虚报防线。
    """
    level, critical = br._verify_email_level(
        _dm(email="hello@acme.example.invalid", email_level="E1"), HOME
    )
    assert level == "E2"
    assert critical is None


def test_email_level_domain_mismatch_forces_e3_and_flags_critical(br):
    """邮箱域名与官网域名不符 → 无论自报什么，降 E3 并记 critical 红旗。"""
    level, critical = br._verify_email_level(
        _dm(name="Jane", email="jane@other-domain.example.invalid", email_level="E1"), HOME
    )
    assert level == "E3"
    assert critical and "域名" in critical


@pytest.mark.parametrize("claimed", ["E3", "E4"])
def test_email_level_never_upgrades_beyond_self_report(br, claimed):
    """代码只收紧、不放宽：没有页面证据时不能把"未验证"升成"已验证"。"""
    level, _ = br._verify_email_level(
        _dm(name="Jane", email="jane@acme.example.invalid", email_level=claimed), HOME
    )
    assert level == claimed


def test_email_level_mx_failure_forces_e4(br):
    """域名不收信（mx_ok=False）时任何级别一律降 E4。"""
    level, _ = br._verify_email_level(
        _dm(name="Jane", email="jane@acme.example.invalid", email_level="E1", mx_ok=False), HOME
    )
    assert level == "E4"


@pytest.mark.parametrize("bad", ["", "not-an-email", None])
def test_email_level_missing_email_is_e4(br, bad):
    level, critical = br._verify_email_level(_dm(email=bad), HOME)
    assert level == "E4"
    assert critical is None


@pytest.mark.parametrize(
    "level,expected",
    [("E1", 1.0), ("E2", 0.7), ("E3", 0.3), ("E4", 0.0), ("UNKNOWN", 0.0)],
)
def test_email_component_mapping(br, level, expected):
    assert br._email_component(level) == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────
# 决策人分层
# ─────────────────────────────────────────────────────────────


def test_decision_maker_named_is_full_credit(br):
    assert br._decision_maker_component([_dm(name="Jane Doe")]) == pytest.approx(1.0)


def test_decision_maker_department_role_is_partial(br):
    """不具名但有部门角色（role 非 generic）→ 0.6。"""
    dm = _dm(name=None, role="purchasing", email="purchasing@acme.example.invalid")
    assert br._decision_maker_component([dm]) == pytest.approx(0.6)


def test_decision_maker_generic_only_is_minimal(br):
    assert br._decision_maker_component([_dm(name=None, role="generic")]) == pytest.approx(0.3)


@pytest.mark.parametrize("dms", [[], [{"name": None, "role": "generic", "email": ""}]])
def test_decision_maker_none_is_zero(br, dms):
    assert br._decision_maker_component(dms) == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────
# 数值与常量约束
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [(1.5, 1.0), (-0.5, 0.0), (0.42, 0.42), ("0.8", 0.8), ("junk", 0.0), (None, 0.0)],
)
def test_clamp(br, raw, expected):
    assert br._clamp(raw) == pytest.approx(expected)


def test_weight_sum_is_one(br):
    """四个子分权重必须合计 1.0 —— 否则满分线索也到不了 1.0，或能超过 1.0。"""
    assert sum(br.W.values()) == pytest.approx(1.0)


def test_tier_thresholds_are_ordered(br):
    assert 0.0 < br.B_SCORE_MIN < br.A_SCORE_MIN <= 1.0


def test_penalty_constants_are_sane(br):
    assert 0.0 < br.PENALTY_PER_FLAG <= br.PENALTY_CAP <= 1.0


def test_email_and_purchasing_prefixes_do_not_overlap(br):
    """通用前缀与采购职能前缀重叠会让 E1/E2 判定互相打架。"""
    assert not set(br.GENERIC_PREFIXES) & set(br.PURCHASING_PREFIXES)


# ─────────────────────────────────────────────────────────────
# 输入结构校验 _check_lead（坏数据不得击穿整单）
# ─────────────────────────────────────────────────────────────


def test_check_lead_accepts_valid_lead(br, lead_factory):
    assert br._check_lead(lead_factory("synthetic-ok")) is None


@pytest.mark.parametrize(
    "mutate,expect_fragment",
    [
        (lambda ld: "a string", "不是 JSON 对象"),
        (lambda ld: {**ld, "company": "Acme Ltd"}, "company"),
        (lambda ld: {**ld, "credibility": "A"}, "credibility"),
        (lambda ld: {**ld, "credibility": {"tier": "X", "score": 0.5}}, "tier"),
        (lambda ld: {**ld, "credibility": {"tier": "A", "score": "high"}}, "score"),
        (lambda ld: {**ld, "decision_makers": "Jane"}, "decision_makers"),
        (lambda ld: {**ld, "decision_makers": ["Jane"]}, "decision_makers"),
        (lambda ld: {**ld, "bd_strategy": "nope"}, "bd_strategy"),
        (lambda ld: {**ld, "lead_source": 3}, "lead_source"),
        (lambda ld: {**ld, "scale_signals": []}, "scale_signals"),
    ],
)
def test_check_lead_rejects_malformed(br, mutate, expect_fragment, lead_factory):
    """嵌套字段类型错误必须被 _check_lead 拦下并走坏行路径。

    历史事故：`company` 为字符串时旧版校验通过，随后在复算阶段
    抛 AttributeError 击穿整单运行。
    """
    problem = br._check_lead(mutate(lead_factory("synthetic-bad")))
    assert problem is not None
    assert expect_fragment in problem
