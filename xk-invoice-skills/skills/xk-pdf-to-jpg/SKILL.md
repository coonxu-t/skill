---
name: xk-pdf-to-jpg
description: PDF 批量转 JPG 图片。递归读取目录下所有子目录中的 PDF 文件（.pdf/.PDF），用 PyMuPDF 正确渲染成 JPG 图片（尺寸与原始 PDF 一致、不裁切、不空白），每个 PDF 的图片存在其所在子目录下的 tu 目录中。当用户要求把 PDF 转成图片、PDF 转 JPG、发票 PDF 转图片、生成发票图片时报账使用。
agent_created: true
---

# PDF 批量转 JPG

## 这个技能做什么

把一目录（含多层子目录）里的 PDF 文件批量转成 JPG 图片，每个 PDF 输出的图片存放在**它所在子目录下的 `tu` 目录**中。

核心要求与坑：
- **尺寸与原始 PDF 一致**：输出像素 = PDF 原始 Point 尺寸 × 缩放倍数（默认 2 倍，即 144 DPI），不裁切、不拉伸变形。
- **不能出空白图**：必须用 PyMuPDF 渲染，**禁止用 `sips` 转 PDF**（`sips` 对文字型矢量 PDF 会渲染成空白，如滴滴电子发票）。

## 何时使用

- 用户说「把这个目录的 PDF 转成 jpg / 图片」
- 用户说「发票 PDF 转图片」「生成发票图片」（用于报账、打印、上传）
- 要求图片「尺寸和原 PDF 一致」「存到 tu 目录 / 子目录」

## 标准流程

1. **确认目录与依赖**：确认目标目录存在；检查 PyMuPDF 是否可用：
   ```bash
   python3 -c "import fitz; print('ok')" 2>&1
   ```
   若报错，先安装（需在允许网络的场景）：
   ```bash
   python3 -m pip install PyMuPDF
   ```

2. **运行转换脚本**：
   ```bash
   python3 <skills>/xk-pdf-to-jpg/scripts/pdf2jpg.py <根目录> [缩放倍数]
   ```
   - `<根目录>`：要处理的目录，脚本会递归遍历其下所有子目录。
   - `[缩放倍数]`：可选，默认 2.0。
   - 脚本会跳过名为 `tu` 的目录，避免重复处理已生成的图片。

3. **自检（关键）**：转换后必须检查是否出现空白图。空白图的特征是文件极小（通常 < 10KB），正常渲染的发票图片都在 100KB 以上。
   ```bash
   # 按大小排序，最小的排前面，若出现几千字节的即为空白图
   find <根目录> -path '*/tu/*.jpg' -exec stat -f%z {} \; -print | sort -n | head
   ```
   若发现空白图，说明用了错误工具，应改用本技能的 PyMuPDF 脚本重转。

4. **汇报**：讲清楚转换成功的数量、失败数量、输出位置、图片尺寸，并说明是否发现空白图。

## 关键坑（务必遵守）

- **不要用 `sips` 转 PDF**。`sips -s format jpeg xxx.pdf` 只做预览级栅格化，文字型矢量 PDF（滴滴电子发票、纯文本电子发票）会渲染成纯空白图。必须用 PyMuPDF。
- **`qlmanage` 在本机沙箱下不可用**（"sandbox initialization failed"），不要依赖它。
- **尺寸「一致」的含义**：指输出像素与 PDF 原始尺寸成固定比例（缩放倍数），不是让所有图片统一成同一个尺寸。原始 PDF 尺寸不同，输出尺寸也会不同，这是正确行为。
- **文件名**：输出 JPG 沿用原 PDF 文件名（去 .pdf/.PDF 后缀），便于对账追溯。

## 文件地图

```
xk-pdf-to-jpg/
├── SKILL.md              # 本文件：流程与规矩
└── scripts/
    └── pdf2jpg.py        # PyMuPDF 批量转换脚本
```
