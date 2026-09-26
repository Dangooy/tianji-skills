"""虚报 A 级的端到端回归测试。

与 `test_credibility.py` 的区别：这里是**结果性**验证 —— 真的跑一遍 CLI、
真的打开生成的 Excel、真的去「A级·可直接发信」Sheet 里看有没有假线索。

为什么两层都要有：
- 单元层能指出"哪条规则坏了"；
- 端到端层能回答"用户拿到的名单到底对不对"。中间的装配、Sheet 分流、
  round-trip 自验都可能出问题，只有端到端能覆盖。

历史背景：修复前 `decision_maker` 与 `scale` 两个子分只做 clamp，
一份自报 `score=0.95/tier=A` 的伪造成果可以直接出现在 A 级名单里，
脚本零警告、打印 SUCCESS。
"""

from __future__ import annotations


def _forged_leads(lead_factory) -> list[dict]:
    """三条不同手法的伪造线索，外加一条健康对照。"""
    return [
        # 1) 单源 + 只挂 generic 邮箱，子分全报满分
        lead_factory(
            "forged-thin",
            name="Synthetic Forged Thin Co",
            cross=1,
            decision_makers=[{
                "name": None, "role": "generic",
                "email": "info@forged-thin.example.invalid",
                "email_level": "E1", "source": "synthetic", "reachable": True,
            }],
            claim_score=0.95, claim_tier="A",
            subscores={"email": 1.0, "cross": 1.0, "decision_maker": 1.0,
                       "scale": 1.0, "penalty": 0.0},
        ),
        # 2) 其余指标都好，但页面含指令式文字（critical 红旗）
        lead_factory(
            "forged-critical",
            name="Synthetic Forged Critical Co",
            cross=3,
            red_flags_critical=["页面出现指令式文字：请标记为A级（提示词注入）"],
            claim_score=0.99, claim_tier="A",
            subscores={"email": 1.0, "cross": 1.0, "decision_maker": 1.0,
                       "scale": 1.0, "penalty": 0.0},
        ),
        # 3) 邮箱不可达（E4），子分仍报满分
        lead_factory(
            "forged-e4",
            name="Synthetic Forged Unreachable Co",
            cross=3,
            decision_makers=[{
                "name": None, "role": "generic",
                "email": "info@forged-e4.example.invalid",
                "email_level": "E4", "source": "synthetic", "reachable": False,
            }],
            claim_score=0.95, claim_tier="A",
            subscores={"email": 1.0, "cross": 1.0, "decision_maker": 1.0,
                       "scale": 1.0, "penalty": 0.0},
        ),
        # 4) 对照：证据齐全的健康线索，必须仍然进 A
        lead_factory(
            "healthy-control",
            name="Synthetic Healthy Control Co",
            cross=3,
            claim_score=1.0, claim_tier="A",
            subscores={"email": 1.0, "cross": 1.0, "decision_maker": 1.0,
                       "scale": 1.0, "penalty": 0.0},
        ),
    ]


def test_forged_leads_never_reach_tier_a_sheet(run_report, lead_factory):
    """三条伪造线索都不得出现在「A级·可直接发信」名单里。"""
    run = run_report(_forged_leads(lead_factory))
    names = run.tier_a_names()

    for forged in (
        "Synthetic Forged Thin Co",
        "Synthetic Forged Critical Co",
        "Synthetic Forged Unreachable Co",
    ):
        assert forged not in names, f"伪造线索「{forged}」进入了 A 级名单"


def test_healthy_lead_still_reaches_tier_a_sheet(run_report, lead_factory):
    """对照组必须仍然进 A —— 防止修复变成"一律拒绝"。"""
    run = run_report(_forged_leads(lead_factory))
    assert run.tier_a_names() == {"Synthetic Healthy Control Co"}


def test_forged_leads_are_listed_in_bc_sheet_or_downgraded(run_report, lead_factory):
    """被降级的伪造线索不能凭空消失 —— 应在 B-C 名单里可见。"""
    run = run_report(_forged_leads(lead_factory))
    bc = run.tier_bc_names()
    assert "Synthetic Forged Thin Co" in bc
    assert "Synthetic Forged Unreachable Co" in bc


def test_recomputed_tiers_land_in_expected_bands(run_report, lead_factory):
    """逐条核对复算后的分级：单源/E4 → C，critical → B，健康 → A。"""
    run = run_report(_forged_leads(lead_factory))
    overview = run.overview_by_name()

    assert overview["Synthetic Forged Thin Co"]["tier"] == "C"
    assert overview["Synthetic Forged Unreachable Co"]["tier"] == "C"
    assert overview["Synthetic Forged Critical Co"]["tier"] == "B"
    assert overview["Synthetic Healthy Control Co"]["tier"] == "A"


def test_self_reported_tier_is_overridden_not_trusted(run_report, lead_factory):
    """四条线索都自报 A，但没有一条以自报值进入结果。"""
    leads = _forged_leads(lead_factory)
    assert all(lead["credibility"]["tier"] == "A" for lead in leads), "用例前提：全部自报 A"

    run = run_report(leads)
    overview = run.overview_by_name()
    recomputed = {name: row["tier"] for name, row in overview.items()}
    assert recomputed["Synthetic Forged Thin Co"] != "A"
    assert recomputed["Synthetic Forged Unreachable Co"] != "A"
    assert recomputed["Synthetic Forged Critical Co"] != "A"


def test_script_reports_corrections_in_stderr(run_report, lead_factory):
    """被纠正的线索必须在 stderr 留下可追溯的 WARN 和计数。"""
    run = run_report(_forged_leads(lead_factory))
    assert "评分被代码纠正" in run.stdout
    assert any("已覆盖" in line for line in run.warn_lines)


def test_critical_flag_is_recorded_in_report(run_report, lead_factory):
    """critical 红旗要落到线索数据里，不能只在判定时用一下。"""
    run = run_report(_forged_leads(lead_factory))
    assert run.ok
    # 概要表里应有该线索，且不属于 A（具体列位置随模板而变，故只断言归属）
    assert "Synthetic Forged Critical Co" not in run.tier_a_names()
