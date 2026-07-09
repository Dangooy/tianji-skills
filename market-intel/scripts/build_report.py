#!/usr/bin/env python3
"""
Market Intel 报告生成器 — 从线索 JSON 生成多 Sheet Excel。

设计要点：
- 直接读 JSON 文件（--leads leads.jsonl 或 --data '<json>'），避免脆弱的单行字符串转义
- 结构化写入 openpyxl，条件格式按 tier 着色
- 内置 round-trip 自验（生成后 openpyxl 重开核对行数/tier分布）

用法：
  python3 build_report.py --leads leads.jsonl --meta meta.json --output report.xlsx
  python3 build_report.py --data '<json数组>' --meta-data '<json>' --output report.xlsx

leads 结构见 references/lead-schema.md。meta 结构见 assets/report_template_notes.md。
成功打印 "SUCCESS: <路径>"，自验失败打印 "VERIFY_FAIL: <原因>" 并退出码 1。
"""
import argparse, json, sys
from datetime import datetime, timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── 样式 ──
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
TIER_FILL = {"A": PatternFill("solid", fgColor="C6EFCE"),   # 绿
             "B": PatternFill("solid", fgColor="FFEB9C"),   # 黄
             "C": PatternFill("solid", fgColor="FFC7CE")}   # 红
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

DISCLAIMER = ("本报告基于公开网页信息，不含海关采购记录；联系方式可信度见各行 email_level 分级"
              "（E1官网具名/部门·可直接发信，E2官网generic·通用模板，E3推断未验证，E4无邮箱）。")


def _hdr(ws, headers):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.fill, cell.font, cell.border = HEADER_FILL, HEADER_FONT, BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.freeze_panes = "A2"


def _best_email(dms):
    """取决策人里最佳邮箱 + 级别"""
    order = {"E1": 0, "E2": 1, "E3": 2, "E4": 3}
    cands = [(order.get(d.get("email_level", "E4"), 3), d) for d in dms if d.get("email")]
    if not cands:
        return "", "E4"
    cands.sort(key=lambda x: x[0])
    d = cands[0][1]
    return d.get("email", ""), d.get("email_level", "E4")


def _dm_summary(dms):
    parts = []
    for d in dms:
        nm = d.get("name") or d.get("role") or "generic"
        em = d.get("email", "")
        lv = d.get("email_level", "")
        parts.append(f"{nm}({d.get('role','')}) {em} [{lv}]".strip())
    return "\n".join(parts)


def build(leads, meta, output):
    wb = Workbook()

    # ── Sheet 1: 线索总览 ──
    ws = wb.active
    ws.title = "线索总览"
    cols = ["公司名", "国家", "tier", "score", "最佳邮箱", "邮箱级别",
            "决策人", "产品重合", "出单主体", "交叉源数", "推荐渠道", "切入策略"]
    _hdr(ws, cols)
    leads_sorted = sorted(leads, key=lambda x: ("ABC".index(x["credibility"]["tier"]),
                                                 -x["credibility"]["score"]))
    for r, ld in enumerate(leads_sorted, 2):
        co, cr, bd = ld["company"], ld["credibility"], ld.get("bd_strategy", {})
        email, lvl = _best_email(ld.get("decision_makers", []))
        row = [co.get("name_en") or co.get("name_local", ""), co.get("country", ""),
               cr["tier"], round(cr["score"], 2), email, lvl,
               _dm_summary(ld.get("decision_makers", [])),
               ", ".join(co.get("product_line_match", [])), co.get("target_entity", ""),
               ld.get("lead_source", {}).get("cross_source_count", 0),
               bd.get("recommended_channel", ""), bd.get("entry_angle", "")]
        for c, v in enumerate(row, 1):
            cell = ws.cell(r, c, v)
            cell.border, cell.alignment = BORDER, WRAP
        ws.cell(r, 3).fill = TIER_FILL.get(cr["tier"], PatternFill())
    _autosize(ws, {1: 26, 7: 34, 12: 40})

    # ── Sheet 2: A级·可直接发信 ──
    ws2 = wb.create_sheet("A级·可直接发信")
    a_cols = ["公司名", "国家", "官网", "决策人", "最佳邮箱", "产品重合",
              "切入角度", "模板提示", "母语渠道情报"]
    _hdr(ws2, a_cols)
    a_leads = [l for l in leads_sorted if l["credibility"]["tier"] == "A"]
    for r, ld in enumerate(a_leads, 2):
        co, bd = ld["company"], ld.get("bd_strategy", {})
        email, _ = _best_email(ld.get("decision_makers", []))
        row = [co.get("name_en") or co.get("name_local", ""), co.get("country", ""),
               co.get("homepage", ""), _dm_summary(ld.get("decision_makers", [])), email,
               ", ".join(co.get("product_line_match", [])), bd.get("entry_angle", ""),
               bd.get("template_hint", ""), ld.get("native_channel_intel", "")]
        for c, v in enumerate(row, 1):
            cell = ws2.cell(r, c, v); cell.border, cell.alignment = BORDER, WRAP
    _autosize(ws2, {1: 26, 3: 28, 4: 34, 7: 34, 8: 30, 9: 30})

    # ── Sheet 3: B/C级·待验证 ──
    ws3 = wb.create_sheet("B-C级·待验证")
    bc_cols = ["公司名", "国家", "tier", "score", "邮箱(级别)", "疑点", "下一步验证"]
    _hdr(ws3, bc_cols)
    bc_leads = [l for l in leads_sorted if l["credibility"]["tier"] in ("B", "C")]
    for r, ld in enumerate(bc_leads, 2):
        co, cr = ld["company"], ld["credibility"]
        email, lvl = _best_email(ld.get("decision_makers", []))
        row = [co.get("name_en") or co.get("name_local", ""), co.get("country", ""),
               cr["tier"], round(cr["score"], 2), f"{email} [{lvl}]",
               "; ".join(cr.get("red_flags", [])), cr.get("next_verification_step", "") or ""]
        for c, v in enumerate(row, 1):
            cell = ws3.cell(r, c, v); cell.border, cell.alignment = BORDER, WRAP
        ws3.cell(r, 3).fill = TIER_FILL.get(cr["tier"], PatternFill())
    _autosize(ws3, {1: 26, 6: 34, 7: 40})

    # ── Sheet 4: 母语渠道情报 ──
    ws4 = wb.create_sheet("母语渠道情报")
    _hdr(ws4, ["公司名", "国家", "母语渠道情报"])
    for r, ld in enumerate([l for l in leads_sorted if l.get("native_channel_intel")], 2):
        co = ld["company"]
        for c, v in enumerate([co.get("name_en") or co.get("name_local", ""),
                               co.get("country", ""), ld.get("native_channel_intel", "")], 1):
            cell = ws4.cell(r, c, v); cell.border, cell.alignment = BORDER, WRAP
    _autosize(ws4, {1: 26, 3: 60})

    # ── Sheet 5: 运行元数据 ──
    ws5 = wb.create_sheet("运行元数据")
    tiers = {"A": 0, "B": 0, "C": 0}
    for l in leads:
        tiers[l["credibility"]["tier"]] += 1
    rows = [
        ["报告生成时间", meta.get("generated_at", "")],
        ["关键词", ", ".join(meta.get("keywords", []))],
        ["HS编码", ", ".join(meta.get("hs_codes", []))],
        ["目标市场", ", ".join(meta.get("markets", []))],
        ["", ""],
        ["漏斗 · 发现候选", meta.get("funnel", {}).get("discovered", "")],
        ["漏斗 · 提取存活", meta.get("funnel", {}).get("extracted", "")],
        ["漏斗 · 背调完成", meta.get("funnel", {}).get("verified", "")],
        ["分级 · A(可直接发信)", tiers["A"]],
        ["分级 · B(待补验证)", tiers["B"]],
        ["分级 · C(仅供参考)", tiers["C"]],
        ["", ""],
        ["firecrawl credits 消耗", meta.get("cost", {}).get("firecrawl_credits", "")],
        ["数据源", ", ".join(meta.get("sources_used", []))],
        ["", ""],
        ["免责声明", DISCLAIMER],
    ]
    for r, (k, v) in enumerate(rows, 1):
        kc = ws5.cell(r, 1, k); kc.font = Font(bold=True); kc.alignment = WRAP
        vc = ws5.cell(r, 2, v); vc.alignment = WRAP
    ws5.column_dimensions["A"].width = 24
    ws5.column_dimensions["B"].width = 70

    wb.save(output)
    return {"total": len(leads), "tiers": tiers, "a_count": len(a_leads),
            "bc_count": len(bc_leads)}


def _autosize(ws, overrides=None):
    overrides = overrides or {}
    for c in range(1, ws.max_column + 1):
        if c in overrides:
            ws.column_dimensions[get_column_letter(c)].width = overrides[c]
        else:
            ws.column_dimensions[get_column_letter(c)].width = 14


def verify(output, expect):
    """Round-trip 自验：重开核对行数和 tier 分布"""
    wb = load_workbook(output)
    problems = []
    # 总览行数 == 线索数
    n_overview = wb["线索总览"].max_row - 1
    if n_overview != expect["total"]:
        problems.append(f"总览行数 {n_overview} != 线索数 {expect['total']}")
    # A级 sheet 行数 == A级数
    n_a = wb["A级·可直接发信"].max_row - 1
    if n_a != expect["a_count"]:
        problems.append(f"A级sheet行数 {n_a} != A级数 {expect['a_count']}")
    # B/C sheet 行数
    n_bc = wb["B-C级·待验证"].max_row - 1
    if n_bc != expect["bc_count"]:
        problems.append(f"B-C级sheet行数 {n_bc} != B-C级数 {expect['bc_count']}")
    # 免责声明存在
    meta_vals = [wb["运行元数据"].cell(r, 2).value for r in range(1, wb["运行元数据"].max_row + 1)]
    if not any(v and "不含海关采购记录" in str(v) for v in meta_vals):
        problems.append("元数据缺免责声明")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads", help="JSONL 文件路径（每行一条线索）")
    ap.add_argument("--data", help="JSON 数组字符串（备选）")
    ap.add_argument("--meta", help="meta JSON 文件路径")
    ap.add_argument("--meta-data", help="meta JSON 字符串（备选）")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if args.leads:
        with open(args.leads, encoding="utf-8") as f:
            leads = [json.loads(line) for line in f if line.strip()]
    elif args.data:
        leads = json.loads(args.data)
    else:
        print("VERIFY_FAIL: 需 --leads 或 --data", file=sys.stderr); sys.exit(1)

    if args.meta:
        with open(args.meta, encoding="utf-8") as f:
            meta = json.load(f)
    elif args.meta_data:
        meta = json.loads(args.meta_data)
    else:
        meta = {}
    meta.setdefault("generated_at", datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"))

    if not leads:
        print("VERIFY_FAIL: 线索为空", file=sys.stderr); sys.exit(1)

    expect = build(leads, meta, args.output)
    problems = verify(args.output, expect)
    if problems:
        print("VERIFY_FAIL: " + "; ".join(problems), file=sys.stderr); sys.exit(1)
    print(f"SUCCESS: {args.output}")
    print(f"  线索 {expect['total']} 条 | A {expect['tiers']['A']} / "
          f"B {expect['tiers']['B']} / C {expect['tiers']['C']}")


if __name__ == "__main__":
    main()
