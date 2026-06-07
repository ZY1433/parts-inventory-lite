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
`-- .gitignore
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
