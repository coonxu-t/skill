# xk-invoice-skills · 发票报销台账技能包

把一整个发票目录（PDF + 图片，含多层子目录）自动处理成 **可交财务的报销台账 Excel** + **按报销科目归档的发票图片**。

这是 [WorkBuddy](https://www.workbuddy.cn/) 的 4 个技能（Skill）组成的完整流水线，已打包成可直接安装、可直接推到 GitHub 的技能包目录。技能文件为**原样导出**，只额外增加安装脚本与文档，不改技能逻辑。

```
PDF / 图片  →  ① 转 JPG  →  ② 逐张识别 + 合规核对  →  ③ 按报销科目出台账  →  ④ 按科目归档图片
```

## 包含哪些技能

| 技能 | 作用 |
|---|---|
| `xk-invoice-pipeline` | **总入口**：编排下面三个技能，串成不可跳步的五步流水线 |
| `xk-pdf-to-jpg` | 用 PyMuPDF 递归把各子目录 PDF 渲染成 JPG（存各自 `tu/`） |
| `xk-invoice-ocr-summary` | 逐张识别 6 字段、查重、核对抬头税号，生成汇总报告 |
| `xk-invoice-ledger` | 按报销科目归类出 Excel 台账，并按科目归档图片 |

## 快速开始

```bash
# 1. 拿到仓库
git clone https://github.com/coonxu-t/skill.git
cd skill/xk-invoice-skills       # 本技能包是仓库中的子目录
# 或者直接解压分发包 xk-invoice-skills.zip

# 2. 一键安装（macOS / Linux）
./install.sh --with-deps

#    Windows PowerShell：
#    .\install.ps1 -WithDeps

# 3. 环境自检
python3 scripts/check_env.py

# 4. 重启 WorkBuddy，对助手说：
#    「用 xk-invoice-pipeline 处理 /path/to/发票目录 出报销台账」
```

安装位置默认是 `~/.workbuddy/skills/`（用户级，所有项目可用）。装到单个项目用 `./install.sh --project ~/code/my-project`。

## 流水线做什么

1. **摸清目录**：统计 PDF 与已有图片，识别 `tu/`、`图/`、`定额图/` 等历史目录，不改动原始文件。
2. **PDF 转 JPG**：PyMuPDF 渲染，输出到各子目录 `tu/`，并自检空白图。**禁止用 `sips` 转 PDF**，文字型矢量发票会变纯白。
3. **逐张识别 + 核对**：发票号码、类别、抬头、税号、项目名称、价税合计；发现重复票 / 抬头不一致 / 税号不一致 / 非发票文件会**先暂停报告**，不直接出表。
4. **生成台账**：`发票报销台账_报销口径.xlsx`，含「报销汇总」「发票明细」两个 Sheet，金额全程 `Decimal`，合计写静态数值；并写入 AIGC 合规标识（见下文）。
5. **按科目归档**：把发票图片**拷贝**到 `invoice/<科目>/`，逐科目张数与台账交叉校验。

## 固定口径（长期约定）

| 项 | 值 |
|---|---|
| 购买方抬头 | 北京云测信息技术有限公司 |
| 购买方税号 | `91110105664641441Q` |
| 报销科目 | 餐饮费 / 住宿费 / 交通费-火车票 / 交通费-网约车 / 交通费-机票 / 交通费-油费 / 图书资料费 / 通信费 / 停车费 |
| 归类原则 | 按发票**实际内容**归类，不按所在文件夹 |
| 停车费 | 北京市非税收入票据，非增值税发票、无税号，单列 |
| 机票 | 行程单（票价+基金+燃油）与机票款电子发票都归「交通费-机票」 |
| 金额 | 全程 `Decimal`，JSON 里 `amount` 必须是字符串，合计不写公式 |

> 换公司抬头 / 税号 / 科目时，同步改 `skills/xk-invoice-pipeline/SKILL.md` 的「固定口径」和 `skills/xk-invoice-ledger/scripts/build_ledger.py` 的 `classify()` / `CAT_ORDER`，改完重新运行 `install.sh --force`。

## 运行依赖

Python 3.9+，以及 `requirements.txt` 里的两项：

```
PyMuPDF>=1.24     # PDF 渲染
openpyxl>=3.1     # Excel 台账
```

`install.sh --with-deps` 会自动安装；也可手动 `python3 -m pip install -r requirements.txt`。

## 关于 AIGC 合规标识（可选）

台账生成后，流水线第 4 步会调用 `aigc_label.py <xlsx> --platform WORKBUDDY` 写入隐式标识。这个脚本属于 **WorkBuddy 内置插件 `workbuddy-sheet-generation`，不属于本仓库**，因此没有随包分发：

- 在 WorkBuddy 环境里，助手会自动定位到内置插件里的脚本，无需配置。
- 在**非 WorkBuddy 环境**里跳过该步即可，台账功能完全不受影响；也可设置环境变量 `AIGC_LABEL_SCRIPT=/path/to/aigc_label.py` 指向自己的实现。
- `scripts/check_env.py` 会检测并报告该项状态，缺失只给警告。

详见 [docs/INSTALL.md](docs/INSTALL.md)。

## 在其他电脑上 / 放到 GitHub

> 仓库地址：https://github.com/coonxu-t/skill/tree/main/xk-invoice-skills （公开仓库 `coonxu-t/skill` 中的 `xk-invoice-skills/` 子目录）

- **拷到另一台电脑**：先运行 `./tools/make_dist.sh` 生成 `dist/xk-invoice-skills.zip`，拷过去解压后运行 `install.sh`（或 `install.ps1`）即可，不需要 Git。
- **放到 GitHub**：本仓库已带 `.gitignore`（自动排除台账、发票数据、`tu/`、`invoice/` 等敏感产物），`docs/GITHUB.md` 有从建仓到打 Release 的完整命令。
- **以后更新技能**：改动 `skills/` 后运行 `tools/make_dist.sh` 重新生成分发包。

> ⚠️ 仓库里**不要**提交真实发票、台账 Excel、`发票数据.json` 或 `invoice/` 归档图片 —— 这些含公司抬头、税号和交易信息。`.gitignore` 已做默认拦截，推送前仍请 `git status` 复核。
>
> 许可证：本技能包未附带 LICENSE 文件，由仓库所有者决定授权方式。当前托管在公开仓库中，公司抬头与税号为公开工商信息，报销科目口径属内部约定。

## 目录结构

```
xk-invoice-skills/
├── README.md                 本文件
├── requirements.txt          Python 依赖
├── .gitignore                排除台账/发票数据等敏感产物
├── install.sh                macOS / Linux 一键安装
├── install.ps1               Windows 一键安装
├── uninstall.sh              卸载（默认预览，移动而非删除）
├── skills/                   4 个技能，原样导出（15 个文件）
│   ├── xk-invoice-pipeline/
│   ├── xk-pdf-to-jpg/
│   ├── xk-invoice-ocr-summary/
│   └── xk-invoice-ledger/
├── scripts/
│   └── check_env.py          安装后环境自检
├── tools/
│   └── make_dist.sh          重新打包 zip / tar.gz
├── examples/
│   └── 示例发票数据.json       JSON 数据格式样例
└── docs/
    ├── INSTALL.md             安装详解 / 手动安装 / 故障排查
    ├── GITHUB.md              建仓、推送、Release、多机同步
    └── FAQ.md                 实战踩坑与常见问题
```

## 文档

| 文档 | 内容 |
|---|---|
| [docs/INSTALL.md](docs/INSTALL.md) | 三种安装方式、Windows、依赖、验证、故障排查 |
| [docs/GITHUB.md](docs/GITHUB.md) | 推送 GitHub、私有/公开选择、Release 资产、多机更新 |
| [docs/FAQ.md](docs/FAQ.md) | 20 位号码漏读、行程单超大图、扫描数量差异等实战坑 |
| `skills/xk-invoice-pipeline/README.md` | 技能自带的设计文档与数据流说明 |
