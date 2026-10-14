import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(page_title="My Finance", page_icon="\U0001f4b0", layout="wide")


# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------
uploaded_file = st.file_uploader(
    "\U0001f4c2 Open file",
    type=["xlsx", "xls"],
    label_visibility="visible",
    key="excel_upload",
)

if uploaded_file is None:
    st.info("\U0001f446 Please open/select your Excel file using the button above.")
    st.stop()


# ---------------------------------------------------------------------------
# Auto-detect column structure from the first row of data
# ---------------------------------------------------------------------------
def _normalize(name: str) -> str:
    return "".join(c.lower() for c in name if c.isalpha())


_detected_columns: dict[str, str | None] = {}


def detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    cols = df.columns.tolist()
    normed = {(_normalize(c), c): c for c in cols}

    rules_amount = ["valor", "montante", "amount", "debito", "credito", "lancamento"]
    rules_date = ["data", "date", "dt", "lancamento", "emissao"]
    rules_category = ["categoria", "categoria2", "grupo", "tipo", "classe", "natureza"]
    rules_subcategory = ["subcategoria", "subcategory", "sub-grupo", "subgrupo", "sub tipo"]

    def _find(rules):
        for r in rules:
            found = [v for k, v in normed.items() if r in k]
            if found:
                return found[0]
        return None

    detected: dict[str, str | None] = {}
    detected["amount"] = _find(rules_amount)
    detected["date"] = _find(rules_date)
    detected["category"] = _find(rules_category)
    detected["subcategory"] = _find(rules_subcategory)
    return detected


def load_lancamentos(uploaded_file) -> pd.DataFrame:
    df = pd.read_excel(uploaded_file, sheet_name="Lançamentos")
    df.columns = [str(c).strip() for c in df.columns]
    return df


df_raw = load_lancamentos(uploaded_file)

det = detect_columns(df_raw)
if det["amount"]:
    df = df_raw.copy()
    df[det["amount"]] = pd.to_numeric(df[det["amount"]], errors="coerce")
else:
    st.warning("Could not auto-detect the amount column. Showing raw data.")
    df = df_raw.copy()

_detected_columns.update(det)


# ---------------------------------------------------------------------------
# Sidebar — global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("\U0001f4c2 Filters")

    # Amount range
    if det["amount"]:
        min_amount = float(df[det["amount"]].min()) if not df[det["amount"]].isna().all() else 0.0
        max_amount = float(df[det["amount"]].max()) if not df[det["amount"]].isna().all() else 1000.0
        amount_range = st.slider(
            "\U0001f4b0 Amount Range",
            min_value=min_amount,
            max_value=max_amount,
            value=(min_amount, max_amount),
            step=1.0,
            key="filter_amount",
        )
    else:
        amount_range = (0.0, 1000.0)

    st.markdown("---")
    st.caption("Filters are also available above the dashboard.")


# ---------------------------------------------------------------------------
# Top filters — Date range + Categoria + Subcategoria
# ---------------------------------------------------------------------------
with st.container():
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        start_date = None
        end_date = None
        if det["date"]:
            df[det["date"]] = pd.to_datetime(df[det["date"]], errors="coerce")
            date_min = df[det["date"]].min()
            date_max = df[det["date"]].max()
            if pd.notna(date_min) and pd.notna(date_max):
                start_date, end_date = st.date_input(
                    "\U0001f4c5 Date Range",
                    value=[date_min.date(), date_max.date()],
                    min_value=date_min.date() if pd.notna(date_min) else None,
                    max_value=date_max.date() if pd.notna(date_max) else None,
                )

    with fcol2:
        selected_category = None
        if det["category"] and det["category"] in df.columns:
            cats = sorted(df[det["category"]].dropna().unique().tolist())
            selected_category = st.multiselect(
                "\U0001f3e2 Categoria",
                options=cats,
                default=cats,
                key="filter_categoria",
            )

    with fcol3:
        selected_subcategory = None
        if det["subcategory"] and det["subcategory"] in df.columns:
            subs = sorted(df[det["subcategory"]].dropna().unique().tolist())
            selected_subcategory = st.multiselect(
                "\U0001f5c3\ufe0f Subcategoria",
                options=subs,
                default=subs,
                key="filter_subcategoria",
            )


# ---------------------------------------------------------------------------
# Apply all filters
# ---------------------------------------------------------------------------
df_filtered = df.copy()
if selected_category:
    df_filtered = df_filtered[df_filtered[det["category"]].isin(selected_category)]
if selected_subcategory:
    df_filtered = df_filtered[df_filtered[det["subcategory"]].isin(selected_subcategory)]
if start_date and end_date:
    mask = (df_filtered[det["date"]].dt.date >= start_date) & (df_filtered[det["date"]].dt.date <= end_date)
    df_filtered = df_filtered[mask]
amount_min, amount_max = amount_range
if det["amount"]:
    df_filtered = df_filtered[(df_filtered[det["amount"]] >= amount_min) & (df_filtered[det["amount"]] <= amount_max)]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("\U0001f4b0 My Finance")
st.markdown(f"### **{uploaded_file.name}** — Dashboard")


# ---------------------------------------------------------------------------
# Totalizers row
# ---------------------------------------------------------------------------
if det["amount"]:
    total_spent = float(df_filtered[det["amount"]].sum())
    count_transactions = len(df_filtered)
    avg_amount = float(df_filtered[det["amount"]].mean()) if not df_filtered[det["amount"]].isna().all() else 0.0
    min_val = df_filtered[det["amount"]].min()
    max_val = df_filtered[det["amount"]].max()
    min_str = f"R$ {min_val:,.2f}" if pd.notna(min_val) else "N/A"
    max_str = f"R$ {max_val:,.2f}" if pd.notna(max_val) else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Spent", f"R$ {total_spent:,.2f}", delta=f"{count_transactions} transactions")
    with col2:
        st.metric("Average Transaction", f"R$ {avg_amount:,.2f}")
    with col3:
        st.metric("Min Transaction", min_str)
    with col4:
        st.metric("Max Transaction", max_str)

    st.markdown("---")

    # Breakdown by category (if detected)
    if det["category"] and det["category"] in df_filtered.columns:
        cat_count = df_filtered[det["category"]].value_counts().rename_axis("Category").reset_index(name="Count")
        cat_sum_raw = df_filtered.groupby(det["category"])[det["amount"]].sum().reset_index() if det["amount"] and det["amount"] in df_filtered.columns else pd.DataFrame()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("\U0001f4c8 By Categoria (Count)")
            st.dataframe(cat_count.head(20), use_container_width=True)
        with col2:
            st.subheader("\U0001f4cb Sum by Categoria")
            cat_sum_raw.columns = ["Categoria", "Total"]
            st.dataframe(cat_sum_raw.head(20), use_container_width=True)

    # Breakdown by month (if date detected)
    if det["date"]:
        df_m = df_filtered.copy()
        df_m["_month"] = df_filtered[det["date"]].dt.to_period("M").astype(str)
        monthly = df_m.groupby("_month")[det["amount"]].sum().reset_index()
        if not monthly.empty:
            monthly.columns = ["Month", "Total"]
            st.markdown("---")
            st.subheader("\U0001f4c5 Monthly Trend")
            col3, col4 = st.columns(2)
            with col3:
                st.bar_chart(monthly.set_index("Month"))
else:
    st.warning("No amount column detected. Showing raw data preview.")
    st.dataframe(df_filtered.head(5), use_container_width=True)

st.caption(f"\U0001f4d6 {len(df_filtered)} rows displayed — filtered from {len(df_raw)} total")
