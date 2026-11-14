# 安装详解

## 一、先决条件

| 项 | 要求 | 说明 |
|---|---|---|
| Python | 3.9+ | `python3 --version` 检查；Windows 用 `python --version` |
| pip | 随 Python | 用于装 PyMuPDF / openpyxl |
| WorkBuddy | 任意近期版本 | 只有用 Skill 编排时才需要；纯脚本方式可不装 |
| 操作系统 | macOS / Linux / Windows | 脚本分别提供 `.sh` 与 `.ps1` |

> 其他 Agent（Claude Code、Cursor 等）也能用：把 `skills/` 下 4 个目录放到该 Agent 读取 Skill 的目录即可，SKILL.md 里的流程是纯文本说明，脚本是标准 Python，不绑定 WorkBuddy 专有 API。

## 二、三种安装方式

### 方式 A：一键脚本（推荐）

```bash
cd xk-invoice-skills

# macOS / Linux：用户级（所有项目可用）
./install.sh --with-deps

# 只装到某个项目
./install.sh --project ~/code/my-project --with-deps

# 已有同名技能、想用仓库版本覆盖
./install.sh --force --with-deps
```

```powershell
# Windows PowerShell
.\install.ps1 -WithDeps
.\install.ps1 -Project C:\code\my-project -WithDeps
.\install.ps1 -Force -WithDeps
```

脚本行为：

- 默认目标：`~/.workbuddy/skills/`（Windows 为 `%USERPROFILE%\.workbuddy\skills\`）。
- 目标已存在同名技能时**默认跳过**，不会覆盖你的改动。
- 加 `--force` 时，旧目录被**移动**到 `~/.workbuddy/skills_backup_<时间戳>/`，不做删除，随时可恢复。
- `--with-deps` 才装 Python 依赖；不带则只复制文件。

### 方式 B：手动复制

把 `skills/` 里的 4 个目录整个拷到目标目录：

```bash
mkdir -p ~/.workbuddy/skills
cp -R skills/xk-invoice-pipeline \
      skills/xk-pdf-to-jpg \
      skills/xk-invoice-ocr-summary \
      skills/xk-invoice-ledger \
      ~/.workbuddy/skills/

python3 -m pip install -r requirements.txt
```

项目级目标改成 `<项目>/.workbuddy/skills/`。

### 方式 C：不装 Skill，直接跑脚本

只想用某个能力时，脚本可独立运行（路径按仓库实际位置替换）：

```bash
# ① PDF → JPG
python3 skills/xk-pdf-to-jpg/scripts/pdf2jpg.py "<发票目录>"

# ② 已有 JSON 时出汇总报告
python3 skills/xk-invoice-ocr-summary/scripts/summarize.py 发票数据.json 输出目录 "北京云测信息技术有限公司" "91110105664641441Q"

# ③ 按报销口径出台账（--scan 会交叉校验图片数 vs 数据条数）
python3 skills/xk-invoice-ledger/scripts/build_ledger.py --scan "<发票目录>" 发票数据.json 发票报销台账_报销口径.xlsx "北京云测信息技术有限公司"

# ④ 按科目归档图片
python3 skills/xk-invoice-ledger/scripts/organize_invoices.py 发票数据.json "<发票目录>" --extra 映射.json
```

JSON 格式见 `examples/示例发票数据.json`：纯数组，每项 `content` / `number` / `category` / `taxid` / `amount`（**字符串**）。

## 三、验证安装

```bash
python3 scripts/check_env.py
# 装在别处时：
python3 scripts/check_env.py --skills-dir /tmp/skill-test
```

自检会逐项报告 Python 版本、PyMuPDF、openpyxl、4 个技能的关键文件、以及 AIGC 打标脚本。必需项齐全时退出码 0。

然后重启 WorkBuddy（或重新加载技能），对助手说：

> 用 xk-invoice-pipeline 处理 `/path/to/发票目录` 的发票出报销台账

## 四、AIGC 合规标识（可选步骤）

流水线第 4 步的 `aigc_label.py` 属于 WorkBuddy 内置插件 `workbuddy-sheet-generation`，**不在本仓库内**：

| 环境 | 行为 |
|---|---|
| WorkBuddy | 助手自动在插件缓存目录中定位，正常写入标识 |
| 设置了 `AIGC_LABEL_SCRIPT` | 用该变量指向的脚本 |
| 其他环境、两者都没有 | 跳过此步，Excel 台账照常生成，只是不带隐式标识 |

手动指定：

```bash
export AIGC_LABEL_SCRIPT=/path/to/aigc_label.py
python3 "$AIGC_LABEL_SCRIPT" 发票报销台账_报销口径.xlsx --platform WORKBUDDY
python3 "$AIGC_LABEL_SCRIPT" 发票报销台账_报销口径.xlsx --check
```

`check_env.py` 会自动搜索常见插件路径，并把结果列为「可选」项，缺失不影响整体结论。

## 五、故障排查

| 现象 | 原因 / 处理 |
|---|---|
| `./install.sh: Permission denied` | 先 `chmod +x install.sh uninstall.sh tools/make_dist.sh`；或用 `bash install.sh` |
| `python3: command not found` | Windows 用 `python`；macOS 装 Python 3.9+ 后重试 |
| `pip install PyMuPDF` 失败 | 升级 pip：`python3 -m pip install -U pip`；公司内网可换镜像源 |
| 转出来的 JPG 是纯白 | 用了 `sips` 或 `qlmanage`。必须用 `pdf2jpg.py`（PyMuPDF） |
| 自检说技能未安装 | 确认路径：`--skills-dir` 指向的实际目录，或 WorkBuddy 是否用了自定义技能目录 |
| 装完助手仍找不到技能 | 重启 WorkBuddy / 重新加载技能列表；确认是用户级还是项目级目录 |
| PowerShell 提示脚本被禁止运行 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后用 `.\install.ps1` |

## 六、卸载

```bash
./uninstall.sh              # 预览，不改动
./uninstall.sh --yes        # 执行：移动到 skills_uninstalled_<时间戳>/，可恢复
./uninstall.sh --yes --dir /tmp/skill-test
```

卸载脚本不会删除任何文件，只把 4 个技能目录移出技能路径。
