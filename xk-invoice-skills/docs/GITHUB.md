# 放到 GitHub

本仓库已按「可直接推送」组织：技能文件在 `skills/`，安装脚本与文档在根目录，`.gitignore` 默认拦截运行时产生的敏感文件。

> 当前托管：https://github.com/coonxu-t/skill/tree/main/xk-invoice-skills （公开仓库 `coonxu-t/skill` 中的 `xk-invoice-skills/` 子目录）。若改挂独立私有仓库，把下列地址替换为新仓库即可。

## 一、推送前检查清单

```bash
git status                      # 逐条看，确认没有真实业务数据
git ls-files | grep -Ei '\.(xlsx|xls|pdf|jpg|png)$|\.json$'
```

- [ ] **没有**真实发票 PDF / 图片 / 台账 Excel / `发票数据.json` / `invoice/` 归档图
- [ ] `examples/示例发票数据.json` 只是格式样例（假数据）
- [ ] 确认抬头、税号写进文档是否可接受：`README.md` 与 `skills/xk-invoice-pipeline/SKILL.md` 含「北京云测信息技术有限公司」和 `91110105664641441Q`
- [ ] 决定仓库**私有还是公开**（见下节）
- [ ] 决定并补充 `LICENSE`（本仓库默认不带）
- [ ] 可选：把内部口径文档（`使用说明.md` 等）改为通用措辞

> `.gitignore` 已忽略 `*.xlsx`、`发票数据.json`、`invoice/`、`tu/`、`*_small.jpg`、`.DS_Store` 等，但**已跟踪的文件不会被忽略规则追溯**，首次提交前务必 `git status` 复核。

## 二、私有还是公开

| 选择 | 适合 | 注意 |
|---|---|---|
| **私有仓库**（推荐） | 公司内部多电脑同步、团队协作 | 技能里含公司抬头/税号与报销口径，属内部约定 |
| 公开仓库 | 想开源分享通用流程 | 先把公司抬头、税号、内部文档引用替换成占位符，并补 LICENSE |

## 三、首次推送

本目录已初始化过 Git（含首次提交）。如果拿的是 zip 解压包，先初始化：

```bash
cd xk-invoice-skills
git init
git add .
git commit -m "feat: 导出 xk-invoice-skills 发票报销台账技能包"
```

### 通过 WorkBuddy 的 GitHub 连接器

连接器可直接读取/写入仓库文件。注意：GitHub App 集成令牌通常**没有「新建仓库」权限**（`POST /user/repos` 返回 403 `Resource not accessible by integration`），需先在网页建好空仓库，再用连接器把文件推上去；或用下面的 CLI / 原生 git 方式。

### 用 GitHub CLI（最省事）

```bash
# 私有仓库
gh repo create xk-invoice-skills --private --source=. --remote=origin --push

# 公开仓库
gh repo create xk-invoice-skills --public  --source=. --remote=origin --push
```

### 用网页新建 + 手动 remote

先在 GitHub 网页建空仓库（不要勾选初始化 README），然后：

```bash
git remote add origin git@github.com:<账号>/<仓库名>.git
git branch -M main
git push -u origin main
```

HTTPS 方式把地址换成 `https://github.com/<账号>/<仓库名>.git`。

## 四、在另一台电脑上装

```bash
git clone https://github.com/coonxu-t/skill.git
cd skill/xk-invoice-skills
./install.sh --with-deps          # Windows: .\install.ps1 -WithDeps
python3 scripts/check_env.py
```

不想装 Git 就用 Release 资产（下一节）。

## 五、打 Release / 分发压缩包

```bash
./tools/make_dist.sh
# 产出 dist/xk-invoice-skills.zip、.tar.gz、SHA256SUMS.txt
```

把 zip 传到 Release 附件，或直接拷 U 盘。对方解压后运行 `install.sh` 即可，无需 Git。

```bash
gh release create v1.0.0 dist/xk-invoice-skills.zip dist/xk-invoice-skills.tar.gz \
  --title "v1.0.0 发票报销台账技能包" --notes "4 个技能 + 一键安装脚本"
```

## 六、后续更新与多机同步

改了技能后，在任意一台机器：

```bash
git add skills/ README.md docs/
git commit -m "fix: 调整报销科目归类规则"
git push
```

其他机器：

```bash
git pull
./install.sh --force        # 旧版本自动移到 skills_backup_<时间戳>/
python3 scripts/check_env.py
```

> `--force` 是必要的：不加会跳过已存在的技能，改动不会生效。备份目录可随时恢复。

## 七、建议的分支习惯

- `main`：可安装、已验证的稳定版本
- 改 `classify()` / 固定口径这类会影响金额与归类的逻辑时，先用 `examples/示例发票数据.json` 跑一遍 `build_ledger.py` 回归
- 提交信息里注明「是否改变报销科目口径」，方便同事判断要不要重新出表
