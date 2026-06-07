from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).with_name("parts.db")
LOW_STOCK_THRESHOLD = 5
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

CATEGORIES = ["电阻", "电容", "芯片", "模块", "连接器", "其他"]
SOURCES = ["淘宝", "立创", "其他"]

DB_COLUMNS = [
    "id",
    "category",
    "name",
    "spec",
    "package",
    "quantity",
    "location",
    "source",
    "link",
    "purchase_date",
    "notes",
    "created_at",
    "updated_at",
]

DISPLAY_COLUMNS = {
    "id": "编号",
    "category": "类别",
    "name": "名称",
    "spec": "参数",
    "package": "封装",
    "quantity": "数量",
    "location": "存放位置",
    "source": "购买来源",
    "link": "商品链接",
    "purchase_date": "购买日期",
    "notes": "备注",
    "created_at": "创建时间",
    "updated_at": "更新时间",
}

MAIN_TABLE_COLUMNS = [
    "编号",
    "类别",
    "名称",
    "参数",
    "封装",
    "数量",
    "存放位置",
    "购买来源",
    "购买日期",
    "备注",
]

CSV_REQUIRED_COLUMNS = ["类别", "名称", "数量"]

AI_SYSTEM_PROMPT = f"""
你是一个中文电子元件库存助手，帮助用户管理本地 SQLite 库存。

你可以通过工具读取和写入库存：
1. 查询库存时，优先调用 list_inventory 或 inventory_summary，不要凭空假设库存。
2. 用户明确说“导入、保存、加入库存、录入”时，可以调用 import_parts 写入数据库。
3. 导入淘宝/订单文本时，尽量抽取类别、名称、参数、封装、数量、购买来源、购买日期、备注。
4. 数量要按实际元件数量计算，例如“10只 x3”应为 30。
5. 如果订单文本没有写每包数量，可以在 notes 里写明“数量为推断”，不要装作确定。
6. 分析项目缺什么时，先根据用户项目列出可能需要的元件，再结合库存查询结果判断“已有、数量不足、缺少、不确定”。
7. 回答保持简洁中文，说明你调用工具后的结论。

库存类别只能使用：{", ".join(CATEGORIES)}。
购买来源只能使用：{", ".join(SOURCES)}。
低库存阈值为 {LOW_STOCK_THRESHOLD}。
"""

AI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inventory_summary",
            "description": "获取当前库存汇总，包括种类数、总数量、低库存清单和类别统计。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_inventory",
            "description": "按关键词、类别、封装、存放位置查询库存。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "关键词，匹配名称、参数、类别、封装、存放位置。",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["全部", *CATEGORIES],
                        "description": "类别筛选，不确定时填全部。",
                    },
                    "package": {"type": "string", "description": "封装筛选，例如 0603、SOT-23。"},
                    "location": {"type": "string", "description": "存放位置筛选。"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 80,
                        "description": "最多返回多少条记录。",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_parts",
            "description": "把用户明确要求导入的元件追加写入库存数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string", "enum": CATEGORIES},
                                "name": {"type": "string"},
                                "spec": {"type": "string"},
                                "package": {"type": "string"},
                                "quantity": {"type": "integer", "minimum": 0},
                                "location": {"type": "string"},
                                "source": {"type": "string", "enum": SOURCES},
                                "link": {"type": "string"},
                                "purchase_date": {
                                    "type": "string",
                                    "description": "YYYY-MM-DD，没有就留空。",
                                },
                                "notes": {"type": "string"},
                            },
                            "required": ["category", "name", "quantity"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    },
]


def get_connection() -> sqlite3.Connection:
    """连接本地 SQLite 数据库。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """首次运行时自动创建库存表。"""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                spec TEXT,
                package TEXT,
                quantity INTEGER NOT NULL DEFAULT 0,
                location TEXT,
                source TEXT,
                link TEXT,
                purchase_date TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def now_text() -> str:
    """生成统一的时间文本，便于查看更新时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value: object) -> str:
    """把表单、CSV 或模型工具参数中的空值统一转成空字符串。"""
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clamp_quantity(value: object) -> int:
    """数量只允许保存为不小于 0 的整数。"""
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        quantity = 0
    return max(quantity, 0)


def safe_category(value: object) -> str:
    """把类别限定在应用允许的枚举里。"""
    text = normalize_text(value)
    return text if text in CATEGORIES else "其他"


def safe_source(value: object) -> str:
    """把购买来源限定在应用允许的枚举里。"""
    text = normalize_text(value)
    return text if text in SOURCES else "其他"


def read_parts() -> pd.DataFrame:
    """读取全部库存记录。"""
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM parts ORDER BY updated_at DESC, id DESC",
            conn,
        )
    for column in DB_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df[DB_COLUMNS]


def insert_part(data: dict[str, object]) -> None:
    """新增一条元件记录。"""
    timestamp = now_text()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO parts (
                category, name, spec, package, quantity, location, source,
                link, purchase_date, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                safe_category(data.get("category")),
                normalize_text(data.get("name")),
                normalize_text(data.get("spec")),
                normalize_text(data.get("package")),
                clamp_quantity(data.get("quantity")),
                normalize_text(data.get("location")),
                safe_source(data.get("source")),
                normalize_text(data.get("link")),
                normalize_text(data.get("purchase_date")),
                normalize_text(data.get("notes")),
                timestamp,
                timestamp,
            ),
        )


def update_part(part_id: int, data: dict[str, object]) -> None:
    """更新元件的基本信息。"""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE parts
            SET category = ?, name = ?, spec = ?, package = ?, quantity = ?,
                location = ?, source = ?, link = ?, purchase_date = ?,
                notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                safe_category(data.get("category")),
                normalize_text(data.get("name")),
                normalize_text(data.get("spec")),
                normalize_text(data.get("package")),
                clamp_quantity(data.get("quantity")),
                normalize_text(data.get("location")),
                safe_source(data.get("source")),
                normalize_text(data.get("link")),
                normalize_text(data.get("purchase_date")),
                normalize_text(data.get("notes")),
                now_text(),
                part_id,
            ),
        )


def update_quantity(part_id: int, new_quantity: int) -> None:
    """单独调整库存数量。"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE parts SET quantity = ?, updated_at = ? WHERE id = ?",
            (clamp_quantity(new_quantity), now_text(), part_id),
        )


def delete_part(part_id: int) -> None:
    """删除一条元件记录。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM parts WHERE id = ?", (part_id,))


def to_display_df(df: pd.DataFrame, include_link: bool = True) -> pd.DataFrame:
    """把数据库字段转换为中文表头。"""
    display = df.rename(columns=DISPLAY_COLUMNS).copy()
    if not include_link and "商品链接" in display.columns:
        display = display.drop(columns=["商品链接"])
    return display


def apply_filters(
    df: pd.DataFrame,
    keyword: str,
    category: str,
    package_filter: str,
    location_filter: str,
) -> pd.DataFrame:
    """按关键词、类别、封装、存放位置过滤库存。"""
    filtered = df.copy()

    keyword = keyword.strip().lower()
    if keyword:
        search_columns = ["name", "spec", "category", "package", "location"]
        mask = pd.Series(False, index=filtered.index)
        for column in search_columns:
            mask = mask | filtered[column].fillna("").astype(str).str.lower().str.contains(
                keyword,
                na=False,
                regex=False,
            )
        filtered = filtered[mask]

    if category != "全部":
        filtered = filtered[filtered["category"] == category]

    if package_filter.strip():
        filtered = filtered[
            filtered["package"]
            .fillna("")
            .astype(str)
            .str.contains(package_filter.strip(), case=False, na=False, regex=False)
        ]

    if location_filter.strip():
        filtered = filtered[
            filtered["location"]
            .fillna("")
            .astype(str)
            .str.contains(location_filter.strip(), case=False, na=False, regex=False)
        ]

    return filtered


def part_options(df: pd.DataFrame) -> dict[str, int]:
    """生成下拉框显示文本和元件编号的映射。"""
    options: dict[str, int] = {}
    for row in df.itertuples(index=False):
        label = (
            f"#{row.id} | {row.category} | {row.name} | {row.spec or '-'} | "
            f"{row.package or '-'} | 库存 {row.quantity} | {row.location or '未填写位置'}"
        )
        options[label] = int(row.id)
    return options


def get_part_by_id(df: pd.DataFrame, part_id: int) -> pd.Series | None:
    """从 DataFrame 中按编号找到一条记录。"""
    matched = df[df["id"] == part_id]
    if matched.empty:
        return None
    return matched.iloc[0]


def parse_date_text(value: object) -> date:
    """把数据库中的日期文本转回日期控件可用的 date。"""
    text = normalize_text(value)
    if not text:
        return date.today()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def display_inventory_table(df: pd.DataFrame) -> None:
    """展示主库存表，并对低库存做淡黄色提示。"""
    display_df = to_display_df(df, include_link=False)
    display_df = display_df[MAIN_TABLE_COLUMNS]

    if display_df.empty:
        st.info("还没有找到元件记录。可以先新增一条，或者调整搜索条件。")
        return

    def highlight_low_stock(row: pd.Series) -> list[str]:
        if row["数量"] <= LOW_STOCK_THRESHOLD:
            return ["background-color: #fff7d6" if col == "数量" else "" for col in row.index]
        return ["" for _ in row.index]

    styled = display_df.style.apply(highlight_low_stock, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


def csv_bytes(df: pd.DataFrame) -> bytes:
    """导出 UTF-8 with BOM，方便 Windows 上用 Excel 打开中文。"""
    display_df = to_display_df(df, include_link=True)
    return display_df.to_csv(index=False).encode("utf-8-sig")


def import_csv(uploaded_file) -> tuple[int, str]:
    """从 CSV 追加导入库存记录。"""
    try:
        imported = pd.read_csv(uploaded_file)
    except Exception as exc:
        return 0, f"CSV 读取失败：{exc}"

    missing_columns = [col for col in CSV_REQUIRED_COLUMNS if col not in imported.columns]
    if missing_columns:
        return 0, f"CSV 缺少必要列：{', '.join(missing_columns)}"

    imported = imported.rename(columns={value: key for key, value in DISPLAY_COLUMNS.items()})

    count = 0
    for _, row in imported.iterrows():
        name = normalize_text(row.get("name"))
        if not name:
            continue
        insert_part(
            {
                "category": row.get("category", "其他"),
                "name": name,
                "spec": row.get("spec", ""),
                "package": row.get("package", ""),
                "quantity": row.get("quantity", 0),
                "location": row.get("location", ""),
                "source": row.get("source", "其他"),
                "link": row.get("link", ""),
                "purchase_date": row.get("purchase_date", ""),
                "notes": row.get("notes", ""),
            }
        )
        count += 1

    return count, "导入完成"


def apply_page_style() -> None:
    """注入少量样式，让 Streamlit 默认界面更像紧凑白板工作台。"""
    st.markdown(
        """
        <style>
        :root {
            --app-blue: #2563eb;
            --app-border: #d8dee8;
            --app-muted: #667085;
            --app-canvas: #f4f6f8;
        }

        html, body, [class*="css"] {
            font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
        }

        .stApp {
            background: var(--app-canvas);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }

        h1 {
            font-size: 1.75rem;
            line-height: 1.2;
            margin-bottom: 0.2rem;
        }

        .app-subtitle {
            color: var(--app-muted);
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 0.85rem 1rem;
            min-height: 82px;
        }

        .metric-label {
            color: var(--app-muted);
            font-size: 0.84rem;
            margin-bottom: 0.25rem;
        }

        .metric-value {
            color: #111827;
            font-size: 1.45rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }

        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px;
        }

        .stButton > button,
        .stDownloadButton > button {
            border-radius: 8px;
            min-height: 40px;
        }

        .stButton > button:active,
        .stDownloadButton > button:active {
            transform: scale(0.98);
        }

        input, textarea, select {
            border-radius: 8px !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--app-border);
            border-radius: 8px;
            overflow: hidden;
            background: #ffffff;
        }

        .danger-note {
            color: #b42318;
            font-size: 0.9rem;
            margin-top: 0.4rem;
        }

        .ai-note {
            color: var(--app-muted);
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(df: pd.DataFrame) -> None:
    """渲染顶部三个库存指标。"""
    total_kinds = len(df)
    total_quantity = int(df["quantity"].sum()) if not df.empty else 0
    low_stock_count = int((df["quantity"] <= LOW_STOCK_THRESHOLD).sum()) if not df.empty else 0

    cols = st.columns(3)
    metrics = [
        ("元件种类数", total_kinds),
        ("总库存数量", total_quantity),
        ("低库存数量", low_stock_count),
    ]
    for col, (label, value) in zip(cols, metrics):
        col.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_add_tab() -> None:
    """新增元件标签页。"""
    with st.form("add_part_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        category = col1.selectbox("类别", CATEGORIES, key="add_category")
        name = col2.text_input("名称 *", placeholder="例如：贴片电阻")
        spec = col3.text_input("参数", placeholder="例如：10kΩ")

        col4, col5, col6 = st.columns(3)
        package = col4.text_input("封装", placeholder="例如：0603")
        quantity = col5.number_input("数量", min_value=0, step=1, value=0)
        location = col6.text_input("存放位置", placeholder="例如：A盒-第3格")

        col7, col8 = st.columns([1, 2])
        source = col7.selectbox("购买来源", SOURCES, key="add_source")
        link = col8.text_input("商品链接", placeholder="可选")

        purchase_date = st.date_input("购买日期", value=date.today())
        notes = st.text_area("备注", placeholder="例如：常用分压电阻，剩余半盘")

        submitted = st.form_submit_button("新增元件", type="primary")
        if submitted:
            if not name.strip():
                st.error("名称不能为空。")
            else:
                insert_part(
                    {
                        "category": category,
                        "name": name,
                        "spec": spec,
                        "package": package,
                        "quantity": quantity,
                        "location": location,
                        "source": source,
                        "link": link,
                        "purchase_date": purchase_date.isoformat(),
                        "notes": notes,
                    }
                )
                st.success("新增成功。")
                st.rerun()


def render_edit_tab(df: pd.DataFrame) -> None:
    """编辑和删除元件标签页。"""
    if df.empty:
        st.info("暂无元件可编辑。")
        return

    options = part_options(df)
    selected_label = st.selectbox("选择要编辑的元件", list(options.keys()))
    selected_id = options[selected_label]
    part = get_part_by_id(df, selected_id)
    if part is None:
        st.warning("没有找到这条记录，请刷新页面后重试。")
        return

    with st.form("edit_part_form"):
        col1, col2, col3 = st.columns(3)
        category = col1.selectbox(
            "类别",
            CATEGORIES,
            index=CATEGORIES.index(part["category"]) if part["category"] in CATEGORIES else 0,
            key=f"edit_category_{selected_id}",
        )
        name = col2.text_input("名称 *", value=part["name"])
        spec = col3.text_input("参数", value=part["spec"])

        col4, col5, col6 = st.columns(3)
        package = col4.text_input("封装", value=part["package"])
        quantity = col5.number_input(
            "数量",
            min_value=0,
            step=1,
            value=int(part["quantity"]),
        )
        location = col6.text_input("存放位置", value=part["location"])

        col7, col8 = st.columns([1, 2])
        source = col7.selectbox(
            "购买来源",
            SOURCES,
            index=SOURCES.index(part["source"]) if part["source"] in SOURCES else 0,
            key=f"edit_source_{selected_id}",
        )
        link = col8.text_input("商品链接", value=part["link"])

        purchase_date = st.date_input(
            "购买日期",
            value=parse_date_text(part["purchase_date"]),
            key=f"edit_purchase_date_{selected_id}",
        )
        notes = st.text_area("备注", value=part["notes"])

        submitted = st.form_submit_button("保存修改", type="primary")
        if submitted:
            if not name.strip():
                st.error("名称不能为空。")
            else:
                update_part(
                    selected_id,
                    {
                        "category": category,
                        "name": name,
                        "spec": spec,
                        "package": package,
                        "quantity": quantity,
                        "location": location,
                        "source": source,
                        "link": link,
                        "purchase_date": purchase_date.isoformat(),
                        "notes": notes,
                    },
                )
                st.success("保存成功。")
                st.rerun()

    st.divider()
    st.subheader("删除元件")
    st.markdown(
        '<div class="danger-note">删除后无法从应用内恢复，请确认这条记录确实不再需要。</div>',
        unsafe_allow_html=True,
    )
    confirm_delete = st.checkbox("我确认要删除这个元件")
    if st.button("删除该元件", type="secondary", disabled=not confirm_delete):
        delete_part(selected_id)
        st.success("删除成功。")
        st.rerun()


def render_quantity_tab(df: pd.DataFrame) -> None:
    """数量增加和减少标签页。"""
    if df.empty:
        st.info("暂无元件可调整数量。")
        return

    options = part_options(df)
    selected_label = st.selectbox("选择要调整数量的元件", list(options.keys()), key="qty_part")
    selected_id = options[selected_label]
    part = get_part_by_id(df, selected_id)
    if part is None:
        st.warning("没有找到这条记录，请刷新页面后重试。")
        return

    current_quantity = int(part["quantity"])
    st.write(f"当前数量：**{current_quantity}**")

    col1, col2, col3 = st.columns([1, 1, 2])
    delta = col1.number_input("调整数量", min_value=1, step=1, value=1)
    if col2.button("增加数量", type="primary"):
        update_quantity(selected_id, current_quantity + int(delta))
        st.success("数量已增加。")
        st.rerun()
    if col3.button("减少数量"):
        update_quantity(selected_id, max(current_quantity - int(delta), 0))
        st.success("数量已减少。")
        st.rerun()


def render_import_export_tab(df: pd.DataFrame) -> None:
    """CSV 导入导出标签页。"""
    st.download_button(
        "一键导出 CSV",
        data=csv_bytes(df),
        file_name=f"电子元件库存_{date.today().isoformat()}.csv",
        mime="text/csv",
        type="primary",
        disabled=df.empty,
    )
    if df.empty:
        st.caption("当前没有库存记录，新增或导入后即可导出。")

    st.divider()
    uploaded_file = st.file_uploader("从 CSV 导入", type=["csv"])
    st.caption("导入会追加为新记录，不会覆盖已有库存。至少需要包含：类别、名称、数量。")
    if uploaded_file is not None:
        if st.button("导入 CSV"):
            count, message = import_csv(uploaded_file)
            if count > 0:
                st.success(f"{message}，共导入 {count} 条记录。")
                st.rerun()
            else:
                st.warning(message)


def inventory_records_for_ai(df: pd.DataFrame, limit: int) -> list[dict[str, object]]:
    """把库存记录转换成模型容易阅读的 JSON 数据。"""
    if df.empty:
        return []
    compact_columns = [
        "id",
        "category",
        "name",
        "spec",
        "package",
        "quantity",
        "location",
        "source",
        "purchase_date",
        "notes",
    ]
    compact = df[compact_columns].head(limit).copy()
    compact = compact.where(pd.notnull(compact), "")
    return compact.to_dict(orient="records")


def tool_inventory_summary() -> dict[str, object]:
    """AI 工具：返回库存汇总。"""
    df = read_parts()
    if df.empty:
        return {
            "total_kinds": 0,
            "total_quantity": 0,
            "low_stock_threshold": LOW_STOCK_THRESHOLD,
            "low_stock_items": [],
            "category_counts": {},
        }

    category_counts = (
        df.groupby("category")["quantity"]
        .agg(kinds="count", total_quantity="sum")
        .reset_index()
        .to_dict(orient="records")
    )
    low_stock = df[df["quantity"] <= LOW_STOCK_THRESHOLD].copy()
    return {
        "total_kinds": int(len(df)),
        "total_quantity": int(df["quantity"].sum()),
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "low_stock_items": inventory_records_for_ai(low_stock, 50),
        "category_counts": category_counts,
    }


def tool_list_inventory(arguments: dict[str, Any]) -> dict[str, object]:
    """AI 工具：按模型给出的条件查询库存。"""
    df = read_parts()
    limit = min(max(clamp_quantity(arguments.get("limit", 30)), 1), 80)
    filtered = apply_filters(
        df,
        normalize_text(arguments.get("query")),
        normalize_text(arguments.get("category")) or "全部",
        normalize_text(arguments.get("package")),
        normalize_text(arguments.get("location")),
    )
    return {
        "count": int(len(filtered)),
        "returned": int(min(len(filtered), limit)),
        "items": inventory_records_for_ai(filtered, limit),
    }


def tool_import_parts(arguments: dict[str, Any]) -> dict[str, object]:
    """AI 工具：追加写入模型抽取出的元件。"""
    items = arguments.get("items", [])
    if not isinstance(items, list):
        return {"inserted": 0, "error": "items 必须是数组。"}

    inserted: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            skipped.append({"reason": "不是对象", "item": item})
            continue
        name = normalize_text(item.get("name"))
        if not name:
            skipped.append({"reason": "名称为空", "item": item})
            continue
        data = {
            "category": item.get("category", "其他"),
            "name": name,
            "spec": item.get("spec", ""),
            "package": item.get("package", ""),
            "quantity": item.get("quantity", 0),
            "location": item.get("location", ""),
            "source": item.get("source", "其他"),
            "link": item.get("link", ""),
            "purchase_date": item.get("purchase_date", ""),
            "notes": item.get("notes", ""),
        }
        insert_part(data)
        inserted.append(
            {
                "category": safe_category(data["category"]),
                "name": data["name"],
                "spec": normalize_text(data["spec"]),
                "package": normalize_text(data["package"]),
                "quantity": clamp_quantity(data["quantity"]),
            }
        )

    return {"inserted": len(inserted), "items": inserted, "skipped": skipped}


def execute_ai_tool(name: str, arguments: dict[str, Any]) -> dict[str, object]:
    """根据 DeepSeek 返回的工具名调用本地函数。"""
    if name == "inventory_summary":
        return tool_inventory_summary()
    if name == "list_inventory":
        return tool_list_inventory(arguments)
    if name == "import_parts":
        return tool_import_parts(arguments)
    return {"error": f"未知工具：{name}"}


def get_deepseek_api_key() -> str:
    """优先读取环境变量，其次读取 Streamlit Cloud Secrets。"""
    env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        secret_key = st.secrets.get("DEEPSEEK_API_KEY", "")
    except Exception:
        secret_key = ""
    return str(secret_key).strip()


def call_deepseek(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """调用 DeepSeek OpenAI 兼容聊天接口。"""
    api_key = get_deepseek_api_key()
    if not api_key:
        raise RuntimeError("未设置环境变量 DEEPSEEK_API_KEY。")

    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    request = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API 请求失败：HTTP {exc.code}，{body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek API 网络错误：{exc.reason}") from exc


def run_ai_turn(user_text: str) -> str:
    """执行一轮 AI 对话，并处理可能出现的工具调用。"""
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    st.session_state.ai_messages.append({"role": "user", "content": user_text})
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": AI_SYSTEM_PROMPT},
        *st.session_state.ai_messages,
    ]

    tool_logs: list[str] = []
    for _ in range(4):
        response = call_deepseek(messages, AI_TOOLS)
        choice = response["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            content = normalize_text(message.get("content"))
            st.session_state.ai_messages.append({"role": "assistant", "content": content})
            if tool_logs:
                st.session_state.last_ai_tool_logs = tool_logs
            return content

        messages.append(message)
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            name = function.get("name", "")
            raw_arguments = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {}
            result = execute_ai_tool(name, arguments)
            if name == "import_parts":
                tool_logs.append(f"已调用导入工具，写入 {result.get('inserted', 0)} 条记录。")
            else:
                tool_logs.append(f"已调用工具：{name}。")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    fallback = "工具调用轮次过多，我先停在这里。请把问题拆小一点再问。"
    st.session_state.ai_messages.append({"role": "assistant", "content": fallback})
    st.session_state.last_ai_tool_logs = tool_logs
    return fallback


def render_ai_tab() -> None:
    """DeepSeek 对话助手标签页。"""
    api_key_ready = bool(get_deepseek_api_key())
    st.markdown(
        f"""
        <div class="ai-note">
        使用环境变量 <code>DEEPSEEK_API_KEY</code> 调用 <code>{DEEPSEEK_MODEL}</code>。
        可以让它查询库存、导入订单文本、判断某个项目还缺哪些元件。
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not api_key_ready:
        st.warning("还没有检测到 DEEPSEEK_API_KEY。请先在启动 Streamlit 的终端里设置环境变量。")
        st.code(
            "$env:DEEPSEEK_API_KEY='你的 DeepSeek API Key'\n"
            ".\\.venv\\Scripts\\python.exe -m streamlit run app.py",
            language="powershell",
        )

    if st.button("清空对话"):
        st.session_state.ai_messages = []
        st.session_state.last_ai_tool_logs = []
        st.rerun()

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []
    if "last_ai_tool_logs" not in st.session_state:
        st.session_state.last_ai_tool_logs = []

    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    examples = st.expander("可以这样问")
    examples.markdown(
        """
        - `查一下我有没有 SOT-23 的 LDO。`
        - `把下面这段淘宝订单导入库存：...`
        - `我想做一个 ESP32 温湿度记录器，看看库存里还缺什么。`
        - `列出低库存和需要补货的东西。`
        """
    )

    user_text = st.chat_input("和库存助手对话，或粘贴订单文本让它导入")
    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        with st.chat_message("assistant"):
            if not api_key_ready:
                st.error("缺少 DEEPSEEK_API_KEY，无法调用 DeepSeek。")
                return
            with st.spinner("DeepSeek 正在读取库存并思考..."):
                try:
                    answer = run_ai_turn(user_text)
                except Exception as exc:
                    answer = f"调用失败：{exc}"
                    st.session_state.ai_messages.append({"role": "assistant", "content": answer})
                st.markdown(answer)
                for log in st.session_state.get("last_ai_tool_logs", []):
                    st.caption(log)


def main() -> None:
    st.set_page_config(page_title="电子元件库存管理", layout="wide")
    apply_page_style()
    init_db()

    st.title("电子元件库存管理")
    st.markdown(
        '<div class="app-subtitle">本地 SQLite 保存，适合记录元件数量和存放位置。</div>',
        unsafe_allow_html=True,
    )

    df = read_parts()
    render_metrics(df)

    st.subheader("查询库存")
    search_col, category_col, package_col, location_col = st.columns([2.2, 1, 1, 1])
    keyword = search_col.text_input(
        "关键词",
        placeholder="搜索名称、参数、封装、位置",
        label_visibility="collapsed",
    )
    category = category_col.selectbox("类别筛选", ["全部", *CATEGORIES])
    package_filter = package_col.text_input("封装筛选", placeholder="0603 / DIP-8")
    location_filter = location_col.text_input("位置筛选", placeholder="A盒")

    filtered_df = apply_filters(df, keyword, category, package_filter, location_filter)
    display_inventory_table(filtered_df)

    st.divider()
    add_tab, edit_tab, quantity_tab, import_export_tab, ai_tab = st.tabs(
        ["新增元件", "编辑库存", "数量调整", "导入导出", "AI 助手"]
    )
    with add_tab:
        render_add_tab()
    with edit_tab:
        render_edit_tab(df)
    with quantity_tab:
        render_quantity_tab(df)
    with import_export_tab:
        render_import_export_tab(df)
    with ai_tab:
        render_ai_tab()


if __name__ == "__main__":
    main()
