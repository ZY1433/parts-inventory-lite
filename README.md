# 电子元件库存管理

一个极简中文电子元件库存管理小工具，用来记录自己买过的电阻、电容、芯片、模块、连接器等元件，并快速查看数量、封装和存放位置。

项目使用 Python、Streamlit、SQLite 和 pandas。数据保存在本地 `parts.db`，不需要登录，不需要服务器，适合个人桌面使用。

## 功能特性

- 中文 Streamlit 界面
- SQLite 本地数据库，首次运行自动创建 `parts.db`
- 新增元件信息：
  - 类别
  - 名称
  - 参数
  - 封装
  - 数量
  - 存放位置
  - 购买来源
  - 商品链接
  - 购买日期
  - 备注
- 按名称、参数、类别、封装、存放位置搜索库存
- 对元件数量进行增加和减少
- 编辑元件信息
- 删除元件，删除前需要确认
- 一键导出 CSV
- 从 CSV 导入库存
- DeepSeek AI 助手：
  - 查询库存
  - 汇总低库存
  - 粘贴订单文本并导入
  - 根据想做的项目判断还缺什么元件

## 使用样例

### 1. 查看当前库存

启动应用后，首页会显示库存概览和查询表格。

示例库存概览：

```text
元件种类数：19
总库存数量：1075
低库存数量：3
```

可以在 `查询库存` 区域按名称、参数、封装或存放位置搜索，例如：

```text
0603
SOT-23
10kΩ
A盒
```

库存表会展示类似下面的记录：

| 编号 | 类别 | 名称 | 参数 | 封装 | 数量 | 存放位置 | 购买来源 | 购买日期 |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| 15 | 电容 | 0603贴片电容 | 1uF ±10% 16V X5R | 0603 | 100 |  | 淘宝 | 2025-11-01 |
| 14 | 电容 | 0603贴片电容 | 10uF ±20% 10V X5R | 0603 | 100 |  | 淘宝 | 2025-11-01 |
| 13 | 电容 | 0603贴片电容 | 100nF ±10% 50V X7R | 0603 | 100 |  | 淘宝 | 2025-11-01 |
| 11 | 电阻 | 0603贴片电阻 | 1kΩ ±1% 100只 | 0603 | 100 |  | 淘宝 | 2025-11-01 |
| 9 | 电阻 | 0603贴片电阻 | 10kΩ ±1% 100只 | 0603 | 100 |  | 淘宝 | 2025-11-01 |
| 6 | 其他 | UMW BAW56 A1 开关二极管 | 70V/200mA 20只 | SOT-23 | 20 |  | 淘宝 | 2025-11-01 |

数量小于等于 5 的元件会被视为低库存，表格中会用浅黄色提示。

### 2. 用 AI 助手判断项目缺什么

在 `AI 助手` 标签页里，可以直接粘贴 BOM、元件清单或自然语言需求。助手会调用本地库存查询工具，结合现有库存判断哪些已有、哪些缺少。

示例输入：

```text
这些元件我差哪些：
Comment Designator Footprint
10PF C1,C2 C0603
100nF C3,C10,C14,C6,C9,C17,C18,C21,C23,C26,C27 C0603
47uF C4,C5,C28 CASE-B_3528
1uF C7,C11,C12,C30 C0603
10uF C8,C13 C0603
22uF C15,C16 C0603
10k R1,R2,R18,R5,R16,R17 R0603
100k R3,R4 R0603
1.1k R7 R0603
1k R8 R0603
20k R9 R0603
180k R10 R0603
22R R11 R0603
5.1k R12,R13 R0603
4.7K R14,R15 R0603
SS34_C990020624 U2,U3 SMA
KH-TYPEC-16P USB1 USB-TYPEC-16P
```

示例输出会按库存状态分组：

```text
库存已有（够用）

| 元件 | 位号 | 需要数量 | 库存情况 |
| --- | --- | ---: | --- |
| 100nF / 0603 | C3,C10,C14,C6,C9,C17,C18,C21,C23,C26,C27 | 11 | 有 100nF x100，足够 |
| 1uF / 0603 | C7,C11,C12,C30 | 4 | 有 1uF x100，足够 |
| 10uF / 0603 | C8,C13 | 2 | 有 10uF x100，足够 |
| 10kΩ / 0603 | R1,R2,R18,R5,R16,R17 | 6 | 有 10kΩ x100，足够 |
| 1kΩ / 0603 | R8 | 1 | 有 1kΩ x100，足够 |
| 5.1kΩ / 0603 | R12,R13 | 2 | 有 5.1kΩ x100，足够 |

缺少（需要购买）

| 类别 | 元件 | 位号 | 需要数量 | 库存情况 |
| --- | --- | --- | ---: | --- |
| 电容 | 10pF / 0603 | C1,C2 | 2 | 库存无 |
| 电容 | 47uF / CASE-B_3528 | C4,C5,C28 | 3 | 库存无 |
| 电容 | 22uF / 0603 | C15,C16 | 2 | 库存无 |
| LED | LED-0603 绿色 | LED1 | 1 | 库存只有红色 LED，无绿色 |
| MOS管 | CJ3401 / SOT-23-3 | Q1,Q2 | 2 | 库存无 |
| MOS管 | SI2301CDS / SOT-23-3 | Q3 | 1 | 库存无 |
| 电阻 | 100kΩ / 0603 | R3,R4 | 2 | 库存无 |
| 电阻 | 1.1kΩ / 0603 | R7 | 1 | 库存无 |
| 电阻 | 20kΩ / 0603 | R9 | 1 | 库存无 |
| 二极管 | SS34 / SMA | U2,U3 | 2 | 库存无 |
| 连接器 | KH-TYPEC-16P | USB1 | 1 | 库存只有 6P Type-C，非 16P |
```

最后会给出摘要，例如：

```text
总结：
- 已有（不需要）：100nF、1uF、10uF、10kΩ、1kΩ、5.1kΩ
- 缺少（需购买）：小电容、22uF/47uF、电感、MOS管、若干阻值电阻、绿色 LED、SS34、16P Type-C 座
```

### 3. 用 AI 助手导入订单文本

把淘宝、立创等订单文本粘贴给 AI 助手，并明确说“导入库存”。

示例输入：

```text
把下面这段订单导入库存：

原装正品 LP5907QMFX-3.0Q1 SOT-23-5 低压降稳压器(LDO)芯片
￥1.26
x5

0603贴片电阻系列 精度1% 10R1K2.2K3.3K4.7K5.1K6.8K10K100K1MΩ
10kΩ;±1%;100只
￥1.66
x1

0603贴片电容器系列
100nF_±10%_50V_X7R
￥1.46
x1

2025-11-01
订单号: 4850946578231721649
```

AI 助手会抽取类别、名称、参数、封装、数量、购买日期和备注，并调用导入工具写入 `parts.db`。导入后建议到库存表里检查一次数量和封装。

## 技术栈

- Python
- Streamlit
- SQLite
- pandas
- DeepSeek API，使用环境变量 `DEEPSEEK_API_KEY`

## 项目结构

```text
.
|-- app.py
|-- requirements.txt
|-- README.md
+-- .gitignore
```

运行后会自动生成：

```text
parts.db
```

`parts.db` 是你的个人库存数据库，默认不会提交到 Git。

## 安装

建议使用虚拟环境。

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
streamlit run app.py
```

打开终端输出的本地地址，一般是：

```text
http://localhost:8501
```

## 使用 DeepSeek AI 助手

AI 助手会读取环境变量 `DEEPSEEK_API_KEY`，不会把 Key 写入数据库或项目文件。

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
streamlit run app.py
```

macOS / Linux：

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
streamlit run app.py
```

进入页面后打开 `AI 助手` 标签页，可以这样问：

```text
查一下我有没有 SOT-23 的 LDO。
```

```text
列出低库存和需要补货的东西。
```

```text
我想做一个 ESP32 温湿度记录器，看看库存里还缺什么。
```

也可以粘贴淘宝或其他订单文本：

```text
把下面这段订单导入库存：
0603贴片电阻 10kΩ ±1% 100只 x1
0603贴片电容 100nF 50V X7R x1
```

AI 助手会通过本地工具调用读写 SQLite 库存。导入时请检查数量，尤其是订单文本没有写清“每包多少只”的情况。

## 部署到 Streamlit Community Cloud

先把代码推送到 GitHub，然后在 Streamlit Community Cloud 中创建应用。

部署参数：

```text
Repository: ZY1433/parts-inventory-lite
Branch: main
Main file path: app.py
```

如果要使用 AI 助手，在应用的 Secrets 中添加：

```toml
DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
```

如果页面提示代码没有连接到远程 GitHub 仓库，请确认：

- GitHub 仓库已经存在并且当前分支已 push
- Streamlit Cloud 里选择的是 `ZY1433/parts-inventory-lite`
- 分支选择 `main`
- 主文件路径填写 `app.py`
- 如果本地 Streamlit 页面开着，push 后重启一次本地应用再点部署

## CSV 导入格式

CSV 使用中文表头。至少需要包含：

```csv
类别,名称,数量
电阻,0603贴片电阻,100
```

推荐完整格式：

```csv
类别,名称,参数,封装,数量,存放位置,购买来源,商品链接,购买日期,备注
电阻,0603贴片电阻,10kΩ ±1% 100只,0603,100,A盒-第3格,淘宝,,2025-11-01,常用分压电阻
电容,0603贴片电容,100nF ±10% 50V X7R,0603,100,A盒-第4格,淘宝,,2025-11-01,去耦常用
芯片,AMS1117-3.3,3.3V LDO,SOT-223,10,B盒-第1格,立创,,2025-11-01,
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| 类别 | 电阻 / 电容 / 芯片 / 模块 / 连接器 / 其他 |
| 名称 | 元件名称，例如 `0603贴片电阻` |
| 参数 | 规格参数，例如 `10kΩ ±1%` |
| 封装 | 例如 `0603`、`SOT-23`、`DIP-8` |
| 数量 | 当前库存数量，只保存不小于 0 的整数 |
| 存放位置 | 例如 `A盒-第3格` |
| 购买来源 | 淘宝 / 立创 / 其他 |
| 商品链接 | 可选 |
| 购买日期 | 推荐 `YYYY-MM-DD` |
| 备注 | 可选 |

CSV 导入采用追加模式，不会覆盖已有记录，也不会自动去重。

## 数据库说明

数据库文件名固定为：

```text
parts.db
```

表名为：

```text
parts
```

主要字段：

```text
id
category
name
spec
package
quantity
location
source
link
purchase_date
notes
created_at
updated_at
```

如果想备份库存，直接复制 `parts.db` 即可。

## 注意事项

- 这是个人本地工具，不包含登录、权限和多人协作功能。
- 不要把 `DEEPSEEK_API_KEY` 写进代码或提交到 GitHub。
- 不建议提交 `parts.db`，里面可能包含个人购买记录和商品链接。
- AI 导入订单文本时可能会推断数量，导入后建议人工检查。
- CSV 导入是追加模式，重复导入同一个文件会产生重复记录。

## 开发检查

基础语法检查：

```bash
python -m py_compile app.py
```

启动应用：

```bash
streamlit run app.py
```

## License

MIT License。
