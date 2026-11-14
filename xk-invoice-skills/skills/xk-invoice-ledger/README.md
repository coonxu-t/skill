# xk-invoice-ledger 使用说明与设计文档

按报销口径生成发票台账，并支持按科目归档发票图片。这是全链路的**产出端**，核心逻辑都在这里。

## 一、两个脚本

| 脚本 | 作用 | 用法 |
|---|---|---|
| `scripts/build_ledger.py` | 按报销科目归类 → 出 Excel 台账 | `python3 build_ledger.py [--scan <目录>] <数据.json> <输出.xlsx> [抬头]` |
| `scripts/organize_invoices.py` | 按科目把图片拷贝到 `invoice/` | `python3 organize_invoices.py <数据.json> <目录> [--extra <映射.json>]` |

## 二、build_ledger.py 详解

### 输入

`数据.json`：纯数组，每项 5 字段 `content/number/category/taxid/amount`（amount 用字符串）。

### 输出

`输出.xlsx`，两个 Sheet：
- **报销汇总**：按科目分组，每类张数 + 金额，底部合计（静态数值，非公式）。
- **发票明细**：全部明细，含「报销科目」列，开筛选 + 冻结表头。

### 两种模式

```bash
# 模式 A：直接出表
python3 build_ledger.py 数据.json 输出.xlsx 北京云测信息技术有限公司

# 模式 B：目录遍历 + 交叉校验（推荐）
python3 build_ledger.py --scan 目录 数据.json 输出.xlsx 北京云测信息技术有限公司
```

`--scan` 会递归扫各子目录 `tu/` 图片，打印每子目录图片数，并比对「图片总数 vs 数据条数」，不一致打印 ⚠️。

### classify() 归类规则（核心，顺序很重要）

```python
if "住宿" in content or "房费" in content:    return "住宿费"
if "铁路" in content or "退票费" in content:  return "交通费-火车票"
if "交通运输服务" in content:                 return "交通费-网约车"
if "航空运输" or "机票" or "行程单" in content: return "交通费-机票"
if "旅游服务" in content:                     return "交通费-机票"
if "汽油" or "燃油" or "加油" in content:     return "交通费-油费"
if "印刷品" or "图书" in content:             return "图书资料费"
if "电信服务" in content:                     return "通信费"
if "停车费" or "非税票据" or "停放" in content: return "停车费"
if "餐饮" or "餐费" or "奶茶" or "饮品" in content: return "餐饮费"
return "其他"
```

**改归类规则就改这里**。顺序很重要：更具体的（住宿/铁路/交通运输/航空）排前面，泛词（餐饮/奶茶/饮品）排后面。

`CAT_ORDER` 列表决定汇总表里的显示顺序。

## 三、organize_invoices.py 详解

把目录下所有发票图片按报销科目**拷贝**（不改原文件）到 `目录/invoice/<科目>/`。

### 归类判定优先级

1. 文件名里**任一** 8~20 位数字段命中数据发票号（能处理 `11010126_0051523852.jpg` 这种多数字段名）
2. `--extra` 映射表（文件名 → 真实发票号）
3. 文件名关键字（`KEYWORD_RULES`：滴滴/网约→网约车，停车/非税→停车费，机票/行程单→机票，高铁/铁路→火车票）
4. 目录语义兜底（`DIR_CAT`：仅住宿/餐饮/餐饮大额/机票——**刻意排除会混票的「图书」「交通_高铁」目录**）

### 推荐用法（两遍法）

```bash
# 第一遍：看哪些图归不进（归入「其他」）
python3 organize_invoices.py 数据.json 目录

# 第二遍：把「其他」清单里的图用视觉识别出真实发票号，写映射重跑
python3 organize_invoices.py 数据.json 目录 --extra 映射.json
```

映射格式：
```json
{"微信图片_xxx.jpg": "26112000003714959716", "6388162342.jpg": "26117000001599225417"}
```

### 复用关系

`organize_invoices.py` 通过 `from build_ledger import classify` 复用归类逻辑，**保证归档与台账口径永远一致**。改 classify 一处即可，两脚本同步生效。

## 四、常见坑

- **金额必须字符串**，脚本内部 Decimal 累加，禁止 float 相加。
- **合计写静态数值**，不写公式（本机无 LibreOffice，公式会显示异常）。
- **停车费**是北京市非税收入票据，无税号，`taxid` 空串，`category` 写「北京市非税收入票据」。
- **机票行程单**金额口径是票价+基金+燃油，与增值税发票「价税合计」不同，单列统计。
- **文件名里数字未必是发票号**：可能是流水号（`6388162342.jpg` 是移动 boss 流水号）、客票号、时间戳。靠 `--extra` 映射兜底。

## 五、如何修改迭代

| 要改什么 | 改哪里 |
|---|---|
| 报销科目/归类规则 | `build_ledger.py` 的 `classify()` + `CAT_ORDER` |
| 汇总表/明细表版式 | `build_ledger.py` 的 `main()` 里样式部分 |
| 归档关键字规则 | `organize_invoices.py` 的 `KEYWORD_RULES` |
| 归档目录兜底 | `organize_invoices.py` 的 `DIR_CAT` |
| 新增归档手工映射 | 处理时用 `--extra` 传，不必改脚本 |

## 六、文件地图

```
xk-invoice-ledger/
├── SKILL.md                 # 技能元数据 + 流程
├── README.md                # 本文件
└── scripts/
    ├── build_ledger.py      # 归类 + 出台账
    └── organize_invoices.py # 按科目归档图片（复用 build_ledger 的 classify）
```
