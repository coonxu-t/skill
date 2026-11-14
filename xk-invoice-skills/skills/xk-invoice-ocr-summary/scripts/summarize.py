#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发票汇总计算脚本（高精度 Decimal）
================================
输入：一个 JSON 文件，含发票数组（纯数组 `[...]`），每张发票字段：
  content  发票内容（如 "*生产生活服务*餐费"）
  number   发票号码
  category 发票类别（如 "电子发票（普通发票）"）
  taxid    购买方税号
  amount   价税合计金额（字符串，如 "296.00"，避免浮点误差）
  title    购买方抬头（可选；缺省时用「期望抬头」参数填充）

用法：
  python3 summarize.py 发票数据.json 输出目录 [期望抬头] [期望税号]
    - 期望抬头/期望税号：用于核对与填充，缺省则只统计不比对

输出：
  - 输出目录/发票汇总报告.xlsx（4 个 Sheet：明细/分类统计/汇总过程/核对说明）
  - 控制台打印逐笔明细、重复检查、税号核对、分类统计、汇总中间步骤

依赖：openpyxl（若未安装，脚本仍会打印全部统计结果，仅跳过 Excel 生成）
"""
import sys
import os
import json
from decimal import Decimal, getcontext
from collections import Counter

getcontext().prec = 50


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 兼容两种结构：{"invoices": [...]} 或直接 [...]
    if isinstance(data, dict) and "invoices" in data:
        data = data["invoices"]
    return data


def validate(invoices, expect_title=None):
    """校验字段完整性，返回 (正常列表, 错误列表)。

    必填字段：content / number / category / taxid / amount（5 项）。
    title 为可选字段：缺失时用 expect_title 回填，两者皆无则填空字符串。
    """
    ok, err = [], []
    for i, inv in enumerate(invoices, 1):
        missing = [k for k in ("content", "number", "category", "taxid", "amount")
                   if k not in inv or inv[k] is None or str(inv[k]).strip() == ""]
        if missing:
            err.append((i, inv.get("number", "?"), missing))
        else:
            # title 回填
            if "title" not in inv or not str(inv.get("title", "")).strip():
                inv["title"] = expect_title or ""
            ok.append(inv)
    return ok, err


def fmt(d):
    return f"¥{d:.2f}"


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    data_path = args[0]
    outdir = args[1]
    expect_title = args[2] if len(args) > 2 else None
    expect_taxid = args[3] if len(args) > 3 else None

    invoices = load(data_path)
    ok, err = validate(invoices, expect_title)
    if err:
        print("⚠️ 以下发票字段缺失，已跳过：")
        for i, num, missing in err:
            print(f"  第{i}张(号码{num}) 缺字段: {missing}")

    # 逐笔金额 + 汇总（Decimal 高精度）
    print("=" * 70)
    print("发票明细及逐笔金额（价税合计）")
    print("=" * 70)
    total = Decimal("0")
    steps = []
    for inv in ok:
        d = Decimal(str(inv["amount"]))
        total += d
        steps.append(d)
        print(f"  {inv['number']}  {fmt(d):>12}  | {inv['content']}")

    print()
    print("=" * 70)
    print("汇总计算过程（逐步累加，Decimal 高精度）")
    print("=" * 70)
    s = Decimal("0")
    for i, d in enumerate(steps, 1):
        prev = s
        s += d
        print(f"  第{i:2d}步：{fmt(prev)} + {fmt(d)} = {fmt(s)}")
    print()
    print(f"  有效发票张数：{len(ok)}")
    print(f"  价税合计总额：{fmt(s)}")

    # 重复发票检查（按号码）
    print()
    print("=" * 70)
    print("重复发票检查（按发票号码）")
    print("=" * 70)
    nums = [inv["number"] for inv in ok]
    cnt = Counter(nums)
    dups = {k: v for k, v in cnt.items() if v > 1}
    if dups:
        for num, c in dups.items():
            print(f"  ⚠️ 重复号码 {num} 出现 {c} 次")
    else:
        print("  未发现重复发票，所有号码均唯一")

    # 抬头 / 税号核对
    print()
    print("=" * 70)
    print("购买方抬头 / 税号核对")
    print("=" * 70)
    titles = Counter(inv.get("title", "") for inv in ok)
    taxids = Counter(inv.get("taxid", "") for inv in ok)
    print("  抬头分布：")
    for t, c in titles.items():
        flag = "✅" if (expect_title is None or t == expect_title) else "⚠️"
        print(f"    {flag} {t} ×{c}")
    print("  税号分布：")
    for t, c in taxids.items():
        flag = "✅" if (expect_taxid is None or t == expect_taxid) else "⚠️"
        print(f"    {flag} {t} ×{c}")
    if expect_title and len(titles) > 1:
        print(f"  ⚠️ 抬头不一致，期望「{expect_title}」")
    if expect_taxid and len(taxids) > 1:
        print(f"  ⚠️ 税号不一致，期望「{expect_taxid}」")

    # 分类统计（按发票内容归大类）
    print()
    print("=" * 70)
    print("发票分类统计")
    print("=" * 70)
    cats = {}
    for inv in ok:
        # 简单归类：按「*xx服务*」标签取服务大类，缺省归「其他」
        content = inv.get("content", "")
        import re
        m = re.search(r"\*([^*]+)\*", content)
        cat = m.group(1) if m else "其他"
        cats.setdefault(cat, []).append(inv)
    for cat, items in cats.items():
        subtotal = sum((Decimal(str(x["amount"])) for x in items), Decimal("0"))
        print(f"  类别「{cat}」：{len(items)} 张，小计 {fmt(subtotal)}")
        for x in items:
            print(f"      - {x['number']}  {fmt(Decimal(str(x['amount'])))}")

    # 生成 Excel
    try:
        import openpyxl
    except ImportError:
        print("\n[提示] 未安装 openpyxl，跳过 Excel 生成（统计结果已在控制台输出）。")
        return

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = openpyxl.Workbook()
    hf = PatternFill("solid", fgColor="4472C4")
    hfont = Font(bold=True, color="FFFFFF", size=11)
    tfont = Font(bold=True, size=11)
    wfill = PatternFill("solid", fgColor="FFF2CC")
    thin = Side(style="thin", color="BFBFBF")
    bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    ct = Alignment(horizontal="center", vertical="center")

    ws1 = wb.active
    ws1.title = "全部发票明细"
    ws1.append(["序号", "发票内容", "发票号码", "发票类别", "购买方抬头", "购买方税号", "价税合计（元）"])
    for c in range(1, 8):
        cell = ws1.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment, cell.border = hf, hfont, ct, bd
    for i, inv in enumerate(ok, 1):
        ws1.append([i, inv["content"], inv["number"], inv["category"],
                    inv.get("title", ""), inv.get("taxid", ""), float(Decimal(str(inv["amount"])))])
        if expect_taxid and inv.get("taxid", "") != expect_taxid:
            ws1.cell(row=ws1.max_row, column=6).fill = wfill
    ws1.append(["合计", "", "", "", "", "", float(s)])
    for c in range(1, 8):
        cell = ws1.cell(row=ws1.max_row, column=c)
        cell.font, cell.border = tfont, bd
        cell.fill = PatternFill("solid", fgColor="DDEBF7")

    ws2 = wb.create_sheet("分类统计")
    ws2.append(["发票类别", "张数", "小计金额（元）"])
    for c in range(1, 4):
        cell = ws2.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment, cell.border = hf, hfont, ct, bd
    r = 2
    for cat, items in cats.items():
        subtotal = sum((Decimal(str(x["amount"])) for x in items), Decimal("0"))
        ws2.append([cat, len(items), float(subtotal)])
        r += 1
    ws2.append(["合计", len(ok), float(s)])
    for c in range(1, 4):
        ws2.cell(row=ws2.max_row, column=c).font = tfont
        ws2.cell(row=ws2.max_row, column=c).fill = PatternFill("solid", fgColor="DDEBF7")

    ws3 = wb.create_sheet("汇总计算过程")
    ws3.append(["步骤", "累计前金额（元）", "本张金额（元）", "累计后金额（元）", "对应发票号码"])
    for c in range(1, 6):
        cell = ws3.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment, cell.border = hf, hfont, ct, bd
    ss = Decimal("0")
    for i, inv in enumerate(ok, 1):
        d = Decimal(str(inv["amount"]))
        prev = ss
        ss += d
        ws3.append([f"第{i}步", float(prev), float(d), float(ss), inv["number"]])
    ws3.append(["最终合计", "", "", float(ss), ""])
    for c in range(1, 6):
        ws3.cell(row=ws3.max_row, column=c).fill = PatternFill("solid", fgColor="DDEBF7")
    ws3.cell(row=ws3.max_row, column=1).font = tfont
    ws3.cell(row=ws3.max_row, column=4).font = tfont

    ws4 = wb.create_sheet("核对与说明")
    ws4.append(["发票核对与说明"])
    ws4.cell(row=1, column=1).font = Font(bold=True, size=13)
    rows = [
        ["核对项", "结果"],
        ["有效发票张数", str(len(ok))],
        ["价税合计总额", fmt(s)],
        ["重复发票", ("发现重复：" + "、".join(dups)) if dups else "无"],
        ["抬头一致性", "一致" if len(titles) == 1 else "不一致：" + "、".join(titles)],
        ["税号一致性", "一致" if len(taxids) == 1 else "不一致：" + "、".join(taxids)],
    ]
    for r in rows:
        ws4.append(r)
    ws4.cell(row=2, column=1).font = tfont
    ws4.cell(row=2, column=2).font = tfont

    for ws, widths in ((ws1, [6, 22, 24, 20, 26, 24, 16]),
                       (ws2, [30, 10, 16]),
                       (ws3, [10, 18, 18, 18, 24]),
                       (ws4, [24, 60])):
        for col, w in zip("ABCDEFG"[:len(widths)], widths):
            ws.column_dimensions[col].width = w

    os.makedirs(outdir, exist_ok=True)
    xlsx_path = os.path.join(outdir, "发票汇总报告.xlsx")
    wb.save(xlsx_path)
    print(f"\n✅ 已生成 Excel：{xlsx_path}")


if __name__ == "__main__":
    main()
