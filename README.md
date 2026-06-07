# 电子元件库存管理

一个给个人用的中文电子元件库存小工具。

它用 Streamlit 做界面，用 SQLite 把库存存在本地 `parts.db`。你可以记录电阻、电容、芯片、模块、连接器这些零件的数量、封装、位置和购买来源。更有用的是，它接入了 DeepSeek，可以直接帮你把订单文本整理成库存记录，也可以拿着 BOM 去查库存，告诉你哪些已经够用，哪些还得买。

这个项目不是 ERP，也不想做成复杂系统。它更像一个放在电脑上的元件盒清单，打开就能查，缺什么就问。

## 主要亮点

- 本地库存数据库，数据保存在 `parts.db`
- 中文界面，不需要登录，不需要服务器
- 支持新增、编辑、删除、搜索、数量增减
- 支持 CSV 导入和一键导出
- 支持 DeepSeek 对话助手
- 可以粘贴淘宝、立创等订单文本，让模型帮你整理并导入库存
- 可以上传 BOM `.xlsx`，或粘贴 BOM 文本，让模型结合当前库存判断缺什么
- 个人使用场景下 token 量很小，调用成本通常很低，实际费用以 DeepSeek 计费为准

## DeepSeek 能帮什么

这个工具最省事的地方在 AI 助手。

你不用手动把订单标题一点点拆成“类别、名称、参数、封装、数量”。把订单文本粘进去，说一句“导入库存”，DeepSeek 会尽量抽取元件信息，再通过本地工具写入 SQLite。

你也可以上传一个 BOM `.xlsx` 文件，应用会先用代码解析 `Comment`、`Designator`、`Footprint` 三列，再把解析结果连同你的问题一起发给 DeepSeek。没有表格文件时，也可以直接粘贴 BOM 文本，比如：

```text
这些元件我差哪些：
100nF C3,C10,C14,C6,C9,C17,C18,C21,C23,C26,C27 C0603
1uF C7,C11,C12,C30 C0603
10uF C8,C13 C0603
10k R1,R2,R18,R5,R16,R17 R0603
SS34 U2,U3 SMA
KH-TYPEC-16P USB1 USB-TYPEC-16P
```

它会先查你的库存，再按类似这样的方式回答：

```text
库存已有：
- 100nF / 0603，需要 11 个，库存 100 个，足够
- 1uF / 0603，需要 4 个，库存 100 个，足够
- 10uF / 0603，需要 2 个，库存 100 个，足够
- 10kΩ / 0603，需要 6 个，库存 100 个，足够

需要购买：
- SS34 / SMA，需要 2 个，库存无
- KH-TYPEC-16P，需要 1 个，库存只有 6P Type-C，规格不匹配
```

对于个人焊板、打样、补料来说，这比翻盒子和翻订单快很多。

## 目前还没做

现在 BOM `.xlsx` 已经可以上传，但订单截图识别还在计划里：

- 直接上传淘宝订单截图，让模型识别图片内容并导入库存

也就是说，当前版本适合上传 BOM `.xlsx`、粘贴 BOM 文本、粘贴订单文本或手动导入 CSV。图片识别还不是已完成能力。

## 功能

库存字段包括：

- 类别：电阻 / 电容 / 芯片 / 模块 / 连接器 / 其他
- 名称
- 参数，比如 `10kΩ`、`100nF`、`ESP32`、`AMS1117-3.3`
- 封装，比如 `0603`、`0805`、`DIP-8`、`SOT-223`
- 数量
- 存放位置，比如 `A盒-第3格`
- 购买来源：淘宝 / 立创 / 其他
- 商品链接
- 购买日期
- 备注

页面里可以做这些事：

- 查询库存
- 新增元件
- 编辑元件
- 增加或减少数量
- 删除元件，删除前需要确认
- 导入 CSV
- 导出 CSV
- 和 DeepSeek 对话，让它帮你查库存、导入订单、分析缺件

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

打开终端里显示的地址，一般是：

```text
http://localhost:8501
```

首次运行会自动创建：

```text
parts.db
```

这个文件就是你的本地库存数据库。

## 配置 DeepSeek

AI 助手会读取 `DEEPSEEK_API_KEY`。不要把 Key 写进代码，也不要提交到 GitHub。

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

Streamlit Community Cloud 可以在 Secrets 里添加：

```toml
DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
```

## CSV 导入

项目也支持csv直接导入，但是要按照格式，至少需要这三列：

```csv
类别,名称,数量
电阻,0603贴片电阻,100
```

推荐完整格式：

```csv
类别,名称,参数,封装,数量,存放位置,购买来源,商品链接,购买日期,备注
电阻,0603贴片电阻,10kΩ ±1%,0603,100,A盒-第3格,淘宝,,2025-11-01,常用分压电阻
电容,0603贴片电容,100nF 50V X7R,0603,100,A盒-第4格,淘宝,,2025-11-01,去耦常用
```

导入是追加模式，不会覆盖已有记录，也不会自动去重。重复导入同一个文件会产生重复记录。

## 导出

在 `导入导出` 标签页点击 `一键导出 CSV`，就可以把当前库存导出成 CSV。导出使用 UTF-8 with BOM，方便在 Windows 上用 Excel 打开中文。

DeepSeek 本身不会替你把文件下载到本地，但它可以帮你盘点库存、整理缺件清单，再配合 CSV 导出做记录。

## 项目结构

```text
.
|-- app.py
|-- requirements.txt
|-- README.md
|-- LICENSE
+-- .gitignore
```

## 数据和隐私

- `parts.db` 是你的个人库存数据，默认不提交到 Git
- `.env`、Streamlit secrets 和本地 CSV 也会被 `.gitignore` 忽略
- AI 助手需要把你的提问和订单文本发给 DeepSeek API
- 不建议把包含个人订单号、商品链接、地址等信息的数据库或 CSV 发到公开仓库

## 开发检查

```bash
python -m py_compile app.py
```

```bash
streamlit run app.py
```

## License

MIT License
