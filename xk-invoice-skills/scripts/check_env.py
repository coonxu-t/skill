#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xk-invoice-skills 环境自检。

检查：Python 版本、运行依赖、4 个技能是否装齐、AIGC 打标脚本是否可用。
AIGC 打标是可选步骤，缺失只警告，不影响整体结论。

用法:
    python3 check_env.py
    python3 check_env.py --skills-dir /tmp/skill-test
    python3 check_env.py --aigc-script /path/to/aigc_label.py
"""
import argparse
import glob
import importlib.util
import os
import sys

REQUIRED = {
    "xk-invoice-pipeline": ["SKILL.md"],
    "xk-pdf-to-jpg": ["SKILL.md", "scripts/pdf2jpg.py"],
    "xk-invoice-ocr-summary": [
        "SKILL.md",
        "scripts/summarize.py",
        "references/识别规范.md",
    ],
    "xk-invoice-ledger": [
        "SKILL.md",
        "scripts/build_ledger.py",
        "scripts/organize_invoices.py",
    ],
}

OK, WARN, FAIL = "✓", "⚠", "✗"


def find_aigc_script(explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("AIGC_LABEL_SCRIPT")
    if env and os.path.isfile(env):
        return env
    home = os.path.expanduser("~")
    patterns = [
        os.path.join(home, ".workbuddy", "plugins", "cache", "workbuddy-builtin",
                     "workbuddy-sheetagent", "*", "skills", "workbuddy-sheet-generation",
                     "scripts", "aigc_label.py"),
        os.path.join(home, ".workbuddy", "plugins", "cache", "*", "*", "skills",
                     "workbuddy-sheet-generation", "scripts", "aigc_label.py"),
    ]
    hits = []
    for p in patterns:
        hits.extend(glob.glob(p))
    # 同一插件可能缓存多个版本，取最新安装的那个（不要按路径字典序，5.9 会压过 5.11）
    return max(hits, key=os.path.getmtime) if hits else None


def main():
    ap = argparse.ArgumentParser(description="发票技能环境自检")
    ap.add_argument("--skills-dir", default=os.path.expanduser("~/.workbuddy/skills"),
                    help="技能安装目录（默认 ~/.workbuddy/skills）")
    ap.add_argument("--aigc-script", default=None, help="手工指定 aigc_label.py 路径")
    args = ap.parse_args()

    lines = []
    hard_fail = False

    # 1) Python
    v = sys.version_info
    good = v >= (3, 9)
    lines.append((OK if good else FAIL,
                  "Python 版本",
                  f"{v.major}.{v.minor}.{v.micro}（需 3.9+）"))
    hard_fail |= not good

    # 2) 依赖
    def installed(*mods):
        for mod in mods:
            try:
                if importlib.util.find_spec(mod) is not None:
                    return True
            except (ImportError, ValueError):
                pass
        return False

    mupdf_ok = installed("pymupdf", "fitz")
    xlsx_ok = installed("openpyxl")
    lines.append((OK if mupdf_ok else FAIL, "PyMuPDF",
                  "已安装" if mupdf_ok else "未安装：PDF 转 JPG 必需，勿用 sips 替代（会出空白图）"))
    lines.append((OK if xlsx_ok else FAIL, "openpyxl",
                  "已安装" if xlsx_ok else "未安装：生成 Excel 台账必需"))
    hard_fail |= not mupdf_ok
    hard_fail |= not xlsx_ok

    # 3) 技能文件
    root = os.path.abspath(os.path.expanduser(args.skills_dir))
    lines.append((OK if os.path.isdir(root) else FAIL, "技能目录", root))
    hard_fail |= not os.path.isdir(root)
    for name, files in REQUIRED.items():
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            lines.append((FAIL, name, "未安装（运行 install.sh）"))
            hard_fail = True
            continue
        missing = [f for f in files if not os.path.isfile(os.path.join(d, f))]
        if missing:
            lines.append((FAIL, name, "缺文件: " + ", ".join(missing)))
            hard_fail = True
        else:
            lines.append((OK, name, f"{len(files)} 个关键文件齐全"))

    # 4) 可选：AIGC 打标脚本
    hit = find_aigc_script(args.aigc_script)
    if hit:
        lines.append((OK, "AIGC 打标脚本（可选）", hit))
    else:
        lines.append((WARN, "AIGC 打标脚本（可选）",
                      "未找到；台账仍可正常生成，只是不写合规标识。见 docs/INSTALL.md"))

    # 输出
    print("=" * 78)
    print("xk-invoice-skills 环境自检")
    print("=" * 78)
    for mark, item, detail in lines:
        print(f"  {mark}  {item:<26} {detail}")
    print("-" * 78)
    if hard_fail:
        print("结论：存在必需项缺失，请先修复再运行流水线。")
        return 1
    print("结论：必需项齐全，可以运行流水线。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
