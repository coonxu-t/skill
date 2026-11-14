# -*- coding: utf-8 -*-
"""
按报销口径生成发票台账（报销汇总 + 发票明细）。

输入：一个 JSON 文件，格式为发票明细数组，每项字段：
    content  : 发票内容 / 项目名称（用于归类，含 "*xx服务*xx" 或 "*停车费*非税票据" 等标签）
    number   : 发票号码 / 票据号码（非税票据无号码时填空字符串）
    category : 发票类别（如"电子发票（普通发票）"、"增值税专用发票"、"航空运输电子客票行程单"、"北京市非税收入票据"）
    taxid    : 购买方税号（非税票据无税号时填空字符串）
    amount   : 金额（字符串，避免浮点误差）

输出：一份 .xlsx，含两个 Sheet：
    Sheet1「报销汇总」：按报销科目分组，每类张数 + 金额，底部合计。
    Sheet2「发票明细」：全部明细，含"报销科目"列，开启筛选与冻结表头。

用法：
    python3 build_ledger.py <数据.json> <输出.xlsx> [购买方抬头]

报销科目归类规则（可按需调整 classify() 函数）：
    住宿费 / 交通费-火车票 / 交通费-网约车 / 交通费-机票 /
    图书资料费 / 通信费 / 餐饮费 / 停车费 / 其他
"""
import json
import sys
import os
import glob
import re
from collections import defaultdict
from decimal import Decimal

try:
    import openpyxl
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def xl_color(css_hex: str) -> str:
    value = css_hex.removeprefix("#").upper()
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + value


XL_HEAD_BG = xl_color("#4472C4")
XL_SUM_BG = xl_color("#2F5597")
XL_BORDER = xl_color("#BFBFBF")
XL_LIGHT = xl_color("#F2F2F2")

thin = Side(style="thin", color=XL_BORDER)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
HEAD_FONT = Font(bold=True, color="FFFFFF", size=11)
SUM_FONT = Font(bold=True, color="FFFFFF", size=11)
BOLD = Font(bold=True, size=11)
CENTER = Alignment(horizontal="center", vertical="center")

# 报销科目归类顺序（决定汇总表里的显示顺序）
CAT_ORDER = [
    "餐饮费", "住宿费",
    "交通费-火车票", "交通费-网约车", "交通费-机票", "交通费-油费",
    "图书资料费", "通信费", "停车费",
]


def classify(content: str) -> str:
    """根据发票内容标签归到报销科目。顺序很重要：先匹配更具体的。"""
    if "住宿" in content or "房费" in content:
        return "住宿费"
    if "铁路" in content or "退票费" in content:
        return "交通费-火车票"
    if "交通运输服务" in content:
        return "交通费-网约车"
    if "航空运输" in content or "机票" in content or "行程单" in content:
        return "交通费-机票"
    if "旅游服务" in content:
        return "交通费-机票"
    if "汽油" in content or "燃油" in content or "加油" in content:
        return "交通费-油费"
    if "印刷品" in content or "图书" in content:
        return "图书资料费"
    if "电信服务" in content:
        return "通信费"
    if "停车" in content or "非税票据" in content or "非税收入" in content or "停放" in content:
        return "停车费"
    if "餐饮" in content or "餐费" in content or "奶茶" in content or "饮品" in content:
        return "餐饮费"
    return "其他"


def scan_images(root: str) -> dict:
    """递归遍历目录，收集各子目录 tu 下的图片文件。

    支持两种结构：
    1. 分类子目录结构：<root>/<子目录>/tu/*.jpg（如 住宿/tu、餐饮/tu）
    2. 扁平结构：<root>/tu/*.jpg（所有图片集中在顶层 tu 目录）

    返回 {子目录名: [图片绝对路径列表]}，仅统计 *.jpg/*.jpeg/*.png（不含 pdf）。
    扁平结构时用特殊键 "__root__" 表示顶层 tu。
    """
    result = defaultdict(list)

    def collect(tu_dir: str, key: str):
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for f in glob.glob(os.path.join(tu_dir, ext)):
                result[key].append(f)

    # 1) 顶层 tu 目录（扁平结构）
    root_tu = os.path.join(root, "tu")
    if os.path.isdir(root_tu):
        collect(root_tu, "__root__")

    # 2) 各分类子目录下的 tu 目录
    for d in sorted(os.listdir(root)):
        sub = os.path.join(root, d)
        if not os.path.isdir(sub):
            continue
        tu = os.path.join(sub, "tu")
        if os.path.isdir(tu):
            collect(tu, d)

    return dict(result)


def extract_number_from_filename(filename: str) -> str:
    """从图片文件名中提取票据号码（8~20 位数字，若存在）。

    注意：文件名不一定含号码（如「滴滴电子发票A.jpg」），
    这类文件无法用文件名关联，交叉校验时会归入「无法关联」，
    属于正常情况而非缺失。
    """
    m = re.search(r"\d{8,20}", filename)
    return m.group(0) if m else ""


def main():
    if len(sys.argv) < 3:
        print("用法:")
        print("  python3 build_ledger.py <数据.json> <输出.xlsx> [购买方抬头]")
        print("  python3 build_ledger.py --scan <目录> <数据.json> <输出.xlsx> [购买方抬头]")
        sys.exit(1)

    scan_root = None
    if sys.argv[1] == "--scan":
        scan_root = sys.argv[2]
        data_path = sys.argv[3]
        out_path = sys.argv[4]
        title = sys.argv[5] if len(sys.argv) > 5 else ""
    else:
        data_path = sys.argv[1]
        out_path = sys.argv[2]
        title = sys.argv[3] if len(sys.argv) > 3 else ""

    with open(data_path, "r", encoding="utf-8") as f:
        invoices = json.load(f)

    # ---- 目录遍历模式：扫描各子目录 tu 下的图片，与数据做交叉校验 ----
    scan_report = None
    if scan_root:
        image_map = scan_images(scan_root)
        total_images = sum(len(v) for v in image_map.values())
        print(f"[扫描] 根目录: {scan_root}")
        print(f"[扫描] 发现子目录 tu 图片: {total_images} 张")
        for d, files in image_map.items():
            print(f"    - {d}: {len(files)} 张")

        # 号码模糊关联：数据号码 ↔ 文件名里的号码（能关联上的跳过）
        data_nums = {str(inv.get("number", "")) for inv in invoices if inv.get("number")}
        file_nums = set()
        for files in image_map.values():
            for f in files:
                n = extract_number_from_filename(os.path.basename(f))
                if n:
                    file_nums.add(n)

        matched = data_nums & file_nums
        data_only = data_nums - file_nums
        file_only = file_nums - data_nums

        scan_report = {
            "total_images": total_images,
            "subdir_counts": {k: len(v) for k, v in image_map.items()},
            "data_count": len(invoices),
            "matched_by_number": len(matched),
            "data_only": sorted(data_only),
            "file_only": sorted(file_only),
        }
        print(f"[扫描] 数据记录数: {len(invoices)}  图片总数: {total_images}")
        print(f"[扫描] 号码直接关联上: {len(matched)} 条")
        print(f"[扫描] 数据号码未在文件名匹配到（正常，文件名未必含号）: {len(data_only)} 条")
        print(f"[扫描] 图片文件名号码未在数据中（正常，可能是客票号/时间戳）: {len(file_only)} 张")
        # 数量级差异提示（这才是真正需要关注的）
        diff = total_images - len(invoices)
        if diff != 0:
            print(f"[扫描] ⚠️ 图片总数({total_images}) 与 数据条数({len(invoices)}) 相差 {diff}，请确认是否有遗漏或多计。")

    rows = []
    for inv in invoices:
        content = inv.get("content", "")
        number = inv.get("number", "")
        category = inv.get("category", "")
        taxid = inv.get("taxid", "")
        amount = str(inv.get("amount", "0"))
        cat = classify(content)
        rows.append({
            "content": content, "number": number, "category": category,
            "title": title, "taxid": taxid, "amount": amount, "cat": cat,
        })

    cat_map = defaultdict(list)
    for r in rows:
        cat_map[r["cat"]].append(r)

    ordered_cats = [c for c in CAT_ORDER if c in cat_map] + [c for c in cat_map if c not in CAT_ORDER]

    wb = openpyxl.Workbook()

    # ============ Sheet1 报销汇总 ============
    ws1 = wb.active
    ws1.title = "报销汇总"

    ws1["A1"] = "发票报销汇总（按报销科目）"
    ws1.merge_cells("A1:C1")
    ws1["A1"].font = Font(bold=True, size=14)
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 28

    headers = ["报销科目", "发票张数", "金额（元）"]
    for col, name in zip("ABC", headers):
        c = ws1[f"{col}2"]
        c.value = name
        c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
        c.font = HEAD_FONT
        c.alignment = CENTER
        c.border = BORDER

    r = 3
    cat_total_amount = {}
    for cat in ordered_cats:
        items = cat_map[cat]
        subtotal = sum((Decimal(x["amount"]) for x in items), Decimal("0"))
        cat_total_amount[cat] = (len(items), subtotal)
        ws1[f"A{r}"] = cat
        ws1[f"B{r}"] = len(items)
        ws1[f"C{r}"] = float(subtotal)
        ws1[f"C{r}"].number_format = "#,##0.00"
        for col in "ABC":
            ws1[f"{col}{r}"].border = BORDER
            if col == "C":
                ws1[f"{col}{r}"].alignment = Alignment(horizontal="right", vertical="center")
        r += 1

    total_count = sum(v[0] for v in cat_total_amount.values())
    total_amount = sum((v[1] for v in cat_total_amount.values()), Decimal("0"))
    ws1[f"A{r}"] = "合计"
    ws1[f"B{r}"] = total_count
    ws1[f"C{r}"] = float(total_amount)
    ws1[f"C{r}"].number_format = "#,##0.00"
    for col in "ABC":
        c = ws1[f"{col}{r}"]
        c.fill = PatternFill("solid", fgColor=XL_SUM_BG)
        c.font = SUM_FONT
        c.border = BORDER
        c.alignment = Alignment(horizontal="right" if col == "C" else "center", vertical="center")

    ws1.column_dimensions["A"].width = 22
    ws1.column_dimensions["B"].width = 12
    ws1.column_dimensions["C"].width = 16

    # ============ Sheet2 发票明细 ============
    ws2 = wb.create_sheet("发票明细")
    detail_headers = ["序号", "报销科目", "发票内容", "发票号码", "发票类别", "购买方抬头", "购买方税号", "金额（元）"]
    for col, name in zip("ABCDEFGH", detail_headers):
        c = ws2[f"{col}1"]
        c.value = name
        c.fill = PatternFill("solid", fgColor=XL_HEAD_BG)
        c.font = HEAD_FONT
        c.alignment = CENTER
        c.border = BORDER

    drow = 2
    for cat in ordered_cats:
        for x in cat_map[cat]:
            ws2[f"A{drow}"] = drow - 1
            ws2[f"B{drow}"] = cat
            ws2[f"C{drow}"] = x["content"]
            ws2[f"D{drow}"] = x["number"] if x["number"] else ""
            ws2[f"E{drow}"] = x["category"]
            ws2[f"F{drow}"] = x["title"] if x["title"] else ""
            ws2[f"G{drow}"] = x["taxid"] if x["taxid"] else ""
            ws2[f"H{drow}"] = float(Decimal(x["amount"]))
            ws2[f"H{drow}"].number_format = "#,##0.00"
            for col in "ABCDEFGH":
                ws2[f"{col}{drow}"].border = BORDER
            ws2[f"A{drow}"].alignment = CENTER
            ws2[f"H{drow}"].alignment = Alignment(horizontal="right", vertical="center")
            ws2[f"G{drow}"].alignment = Alignment(horizontal="left", vertical="center")
            drow += 1

    ws2[f"A{drow}"] = ""
    ws2[f"B{drow}"] = "合计"
    ws2[f"H{drow}"] = float(total_amount)
    ws2[f"H{drow}"].number_format = "#,##0.00"
    for col in "ABCDEFGH":
        c = ws2[f"{col}{drow}"]
        c.fill = PatternFill("solid", fgColor=XL_LIGHT)
        c.font = BOLD
        c.border = BORDER

    ws2.auto_filter.ref = f"A1:H{drow}"
    ws2.freeze_panes = "A2"

    widths = {"A": 6, "B": 16, "C": 28, "D": 22, "E": 24, "F": 26, "G": 22, "H": 14}
    for col, w in widths.items():
        ws2.column_dimensions[col].width = w

    wb.properties.title = "发票报销汇总（按报销科目）"
    wb.save(out_path)

    print(f"已生成：{out_path}")
    print("科目分布：", {c: cat_total_amount[c][0] for c in ordered_cats})
    print(f"总张数：{total_count}  总金额：{total_amount}")


if __name__ == "__main__":
    main()
