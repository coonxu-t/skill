#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 批量转 JPG（PyMuPDF 渲染，尺寸与原始 PDF 一致，避免空白图）。

用法：
    python3 pdf2jpg.py <根目录> [缩放倍数]

    <根目录>   要处理的目录（递归遍历其下所有子目录中的 .pdf）
    [缩放倍数] 可选，默认 2.0（即 144 DPI，输出像素 = PDF Point 尺寸 × 2）

行为：
    - 递归遍历根目录下所有子目录，找到所有 .pdf / .PDF 文件
    - 每个 PDF 在其所在子目录下生成 tu/ 目录，输出同名 .jpg
    - 尺寸与原始 PDF 一致（原始 Point 尺寸 × 缩放倍数），不裁切、不拉伸变形
    - 用 PyMuPDF 正确栅格化矢量文字型 PDF（如滴滴电子发票），不会出空白图

依赖：PyMuPDF（fitz）。若未安装：
    python3 -m pip install PyMuPDF
"""
import sys
import os
import fitz  # PyMuPDF


def convert(pdf_path, out_path, zoom):
    doc = fitz.open(pdf_path)
    page = doc[0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_path)
    doc.close()
    return pix.width, pix.height


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    base = sys.argv[1]
    zoom = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

    if not os.path.isdir(base):
        print(f"错误：目录不存在：{base}")
        sys.exit(1)

    ok = fail = 0
    for root, dirs, files in os.walk(base):
        # 跳过已生成的 tu 目录，避免重复处理
        if os.path.basename(root) == 'tu':
            continue
        dirs[:] = [d for d in dirs if d not in ('.git', '.DS_Store')]
        for name in files:
            if name.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, name)
                tu_dir = os.path.join(root, 'tu')
                os.makedirs(tu_dir, exist_ok=True)
                out_name = os.path.splitext(name)[0] + '.jpg'
                out_path = os.path.join(tu_dir, out_name)
                try:
                    w, h = convert(pdf_path, out_path, zoom)
                    print(f"OK  {w}x{h}  {out_path}")
                    ok += 1
                except Exception as e:
                    print(f"FAIL  {pdf_path}: {e}")
                    fail += 1

    print(f"\n成功={ok} 失败={fail}")


if __name__ == '__main__':
    main()
