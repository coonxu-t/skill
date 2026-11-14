# -*- coding: utf-8 -*-
"""
按报销科目把发票图片拷贝到 invoice 子目录。

输入：
    <数据.json>：发票明细数组（与 build_ledger.py 同格式，字段含 content/number/category/taxid/amount）
    <目录>：发票根目录（图片散落在各子目录的 tu/ 下，或任意层级）

行为：
    遍历 <目录> 下所有 *.jpg/*.jpeg/*.png（跳过已有的 invoice/ 目录），
    按以下优先级判定每张图片的报销科目，再拷贝到 <目录>/invoice/<科目>/ 下：

    1) 文件名里的 8~20 位号码 → 命中数据里的发票号码 → 取该数据的科目
    2) 额外映射表（--extra 传入，或脚本内 EXTRA_NUM）：文件名 → 真实发票号
    3) 文件名关键字（滴滴/网约 → 网约车；停车/非税 → 停车费；机票/行程单 → 机票）
    4) 目录语义兜底（住宿/餐饮/餐饮大额/机票/图书/交通_高铁 等目录名）

    拷贝保持原文件名（copy2 保留元数据），同名不冲突（源目录里 basename 唯一）。

用法：
    python3 organize_invoices.py <数据.json> <目录> [--extra <映射.json>]

    --extra 映射 JSON 格式：{ "文件名.jpg": "发票号码", ... }
    用于处理「文件名不含发票号」或「文件名数字是流水号/行程单号」的图片，
    由 agent 用视觉识别出真实发票号后传入。若未传，脚本会把无法自动归类的
    图片归入「其他」，并在结束打印清单，供 agent 补识别后重跑。

复用 build_ledger.py 的 classify() 归类逻辑，保证与台账口径一致。
"""
import json
import os
import re
import shutil
import sys
from collections import Counter

# 复用台账脚本的归类逻辑（同目录），保持口径一致
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_ledger import classify  # noqa: E402

# 文件名关键字规则（在目录语义之前判定，避免「图书」目录里的通信发票被误归）
KEYWORD_RULES = [
    (("滴滴", "网约", "出租车"), "交通费-网约车"),
    (("停车", "非税", "停放"), "停车费"),
    (("机票", "行程单", "航空"), "交通费-机票"),
    (("高铁", "火车", "铁路"), "交通费-火车票"),
]

# 目录语义兜底：顶层子目录名 → 报销科目（仅当以上规则都未命中时使用）
# 注意：只能放「目录名 = 科目」且基本不会混票的目录。会混票的目录（如「图书」
#       夹里混电信发票、「交通_高铁」里混滴滴/停车费/地铁发票）不要放这里，
#       否则会违背「按内容不按文件夹」的口径，靠文件名号码/关键字/映射处理。
DIR_CAT = {
    "住宿": "住宿费",
    "餐饮": "餐饮费",
    "餐饮大额": "餐饮费",
    "机票": "交通费-机票",
}


def extract_numbers(filename: str):
    """从文件名提取所有 8~20 位数字段（可能有多个，如「11010126_0051523852.jpg」）。"""
    return re.findall(r"\d{8,20}", filename)


def collect_images(root: str):
    """遍历目录收集所有图片绝对路径，跳过 invoice/ 目录。"""
    imgs = []
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "invoice"]
        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                imgs.append(os.path.join(cur, f))
    return imgs


def classify_image(img: str, num2cat: dict, extra_num: dict, root: str) -> str:
    """判定单张图片的报销科目。"""
    base = os.path.basename(img)
    rel = os.path.relpath(img, start=root)
    top = rel.split(os.sep)[0]

    # 1) 文件名里任一 8~20 位数字段命中数据号码（如「11010126_0051523852.jpg」）
    for num in extract_numbers(base):
        if num in num2cat:
            return num2cat[num]
    # 2) 额外映射表（文件名 → 真实发票号）
    if base in extra_num and extra_num[base] in num2cat:
        return num2cat[extra_num[base]]
    # 3) 文件名关键字
    for keys, cat in KEYWORD_RULES:
        if any(k in base for k in keys):
            return cat
    # 4) 目录语义兜底
    if top in DIR_CAT:
        return DIR_CAT[top]
    return "其他"


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法: python3 organize_invoices.py <数据.json> <目录> [--extra <映射.json>]")
        sys.exit(1)

    data_path = args[0]
    root = args[1]
    extra_path = None
    if "--extra" in args:
        idx = args.index("--extra")
        if idx + 1 < len(args):
            extra_path = args[idx + 1]

    if not os.path.isdir(root):
        print(f"[错误] 目录不存在: {root}")
        sys.exit(1)

    with open(data_path, "r", encoding="utf-8") as f:
        invoices = json.load(f)

    # 额外映射表
    extra_num = {}
    if extra_path:
        with open(extra_path, "r", encoding="utf-8") as f:
            extra_num = json.load(f)
        print(f"[映射] 已载入 {len(extra_num)} 条额外文件名→号码映射")

    # 发票号码 → 科目
    num2cat = {str(inv.get("number", "")): classify(inv.get("content", ""))
               for inv in invoices if inv.get("number")}

    imgs = collect_images(root)
    print(f"[扫描] 图片总数: {len(imgs)} 张")

    result = {}
    for img in imgs:
        result[img] = classify_image(img, num2cat, extra_num, root)

    # 拷贝
    invoice_dir = os.path.join(root, "invoice")
    os.makedirs(invoice_dir, exist_ok=True)

    counts = Counter()
    for img, cat in result.items():
        target = os.path.join(invoice_dir, cat)
        os.makedirs(target, exist_ok=True)
        shutil.copy2(img, os.path.join(target, os.path.basename(img)))
        counts[cat] += 1

    # 汇报
    print(f"[完成] 已拷贝到 {invoice_dir}")
    print("[分布]")
    for cat in sorted(counts):
        print(f"    {cat}: {counts[cat]} 张")
    print(f"    合计: {sum(counts.values())} 张")

    # 未归类预警：这些需要 agent 用视觉识别真实发票号后，通过 --extra 传入重跑
    unresolved = [i for i, c in result.items() if c == "其他"]
    if unresolved:
        print(f"\n[待人工归类] {len(unresolved)} 张归入「其他」，请逐张识别发票号后补 --extra 映射重跑：")
        for u in unresolved:
            print(f"    - {os.path.basename(u)}")


if __name__ == "__main__":
    main()
