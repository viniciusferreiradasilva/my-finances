import pandas as pd
import streamlit as st
import altair as alt
from altair import Chart
from datetime import date

# python -m streamlit run app.py

st.set_page_config(page_title="Minhas Finanças", page_icon="\U0001f4b0", layout="wide")

# Wider sidebar
st.markdown(
    """
    <style>
        .css-1d3mo5t {
            max-width: 320px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — file upload and global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("\U0001f5c3\ufe0f Arquivo")

    uploaded_file = st.file_uploader(
        "Abrir arquivo Excel",
        type=["xlsx", "xls"],
        label_visibility="visible",
        key="excel_upload",
    )

    if uploaded_file is None:
        st.info("\U0001f446 Por favor, abra/selecione seu arquivo Excel.")
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
    st.warning("Não foi possível detectar automaticamente a coluna de valor. Mostrando dados brutos.")
    df = df_raw.copy()

_detected_columns.update(det)


# ---------------------------------------------------------------------------
# Sidebar — global filters
# ---------------------------------------------------------------------------
with st.sidebar:
    pass


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
                    "\U0001f4c5 Período de Datas",
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

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("\U0001f4b0 Minhas Finanças")
st.markdown(f"### **{uploaded_file.name}** — Painel de Controle")


# ---------------------------------------------------------------------------
# KPI — Comparação de gastos: mês atual vs mês anterior (mesmo período)
# ---------------------------------------------------------------------------
this_month_spent = 0.0
last_month_spent = 0.0
month_delta = None

if det["date"] and det["amount"]:
    now = pd.Timestamp.today()
    this_year, this_month = now.year, now.month
    days_this_month = pd.Timestamp(this_year, this_month, 1).days_in_month
    # day-of-month range: from day 1 to "today"
    day_end = min(now.day, days_this_month)

    this_month_start = pd.Timestamp(this_year, this_month, 1)
    this_month_end = pd.Timestamp(this_year, this_month, day_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # last month: mesmo intervalo de dias do mês anterior
    if this_month == 1:
        lm_year, lm_month = this_year - 1, 12
    else:
        lm_year, lm_month = this_year, this_month - 1
    lm_days = pd.Timestamp(lm_year, lm_month, 1).days_in_month
    day_end_lm = min(day_end, lm_days)

    last_month_start = pd.Timestamp(lm_year, lm_month, 1)
    last_month_end = pd.Timestamp(lm_year, lm_month, day_end_lm) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    this_month_spent = float(df_filtered.loc[
        (df_filtered[det["date"]] >= this_month_start) & (df_filtered[det["date"]] <= this_month_end)
    ][det["amount"]].sum())

    last_month_spent = float(df_filtered.loc[
        (df_filtered[det["date"]] >= last_month_start) & (df_filtered[det["date"]] <= last_month_end)
    ][det["amount"]].sum())

    if last_month_spent > 0:
        month_delta = ((this_month_spent - last_month_spent) / last_month_spent) * 100

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

    # Spending KPI card
    if det["date"] and this_month_spent > 0 or last_month_spent > 0:
        delta_text = None
        delta_color = None
        if month_delta is not None:
            sign = "+" if month_delta > 0 else ""
            delta_text = f"{sign}{month_delta:.1f}% vs m\u00eas anterior"
            delta_color = "red" if month_delta > 0 else "green"
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        with kpi_col1:
            st.metric("Gasto Neste Mês", f"R$ {this_month_spent:,.2f}", delta=delta_text, delta_color=delta_color)
        with kpi_col2:
            st.metric("Mesmo Período Mês Anterior", f"R$ {last_month_spent:,.2f}")
        days_active = pd.Timestamp(this_year, this_month, 1).days_in_month
        with kpi_col3:
            avg_daily = this_month_spent / day_end if day_end > 0 else 0.0
            last_avg_daily = last_month_spent / day_end_lm if day_end_lm > 0 else 0.0
            st.metric("Gasto Diário Médio", f"R$ {avg_daily:,.2f}", delta=f"{avg_daily - last_avg_daily:,.2f}" if avg_daily != last_avg_daily else "N/A")

    # ---------------------------------------------------------------------------
    # Breakdown by category by month — grouped bar chart
    if det["date"] and det["category"]:
        df_by_month_cat = df_filtered.dropna(subset=[det["date"], det["category"]]).copy()
        df_by_month_cat["_month"] = df_by_month_cat[det["date"]].dt.to_period("M").astype(str)
        
        if not df_by_month_cat.empty:
            # Monthly category totals — build column mapping from the result (not before groupby)
            monthly_cat = (
                df_by_month_cat.groupby(["_month", det["category"]])[det["amount"]]
                .sum()
                .reset_index(name="Valor")
            )
            mc_cols = list(monthly_cat.columns)  # After reset_index: ["_month", "Categoria", "Valor"]
            monthly_cat = monthly_cat.rename(columns=dict(zip(mc_cols, ["Mes", "Categoria", "Valor"])))

            # Monthly totals per month — for top label on each stacked bar
            monthly_totals_raw = (
                df_by_month_cat.groupby("_month")[det["amount"]]
                .sum()
                .reset_index(name="TotalMes")
            )
            mt_cols = list(monthly_totals_raw.columns)  # After reset_index: ["_month", "TotalMes"]
            monthly_totals_raw = monthly_totals_raw.rename(columns=dict(zip(mt_cols, ["Mes", "TotalMes"])))

            st.subheader("\U0001f4ca Custo por Categoria — por Mês")

            # Palette keyed to categories present in the data
            palette = alt.Scale(
                scheme="category10",
                domain=sorted(monthly_cat["Categoria"].unique().tolist()),
            )

            # Build list-of-dicts for stacked bars
            _data = [
                {
                    "Mes": str(r["Mes"]),
                    "Cat": r["Categoria"],
                    "Val": float(r["Valor"]),
                }
                for _, r in monthly_cat.iterrows()
            ]

            # Monthly totals as separate data source for top labels
            _total_data = [
                {"Mes": str(r["Mes"]), "Tot": float(r["TotalMes"])}
                for _, r in monthly_totals_raw.iterrows()
            ]

            # Stacked bars — one per month, colored by category
            chart_bars = (
                alt.Chart(alt.Data(values=_data))
                .mark_bar()
                .encode(
                    x=alt.X("Mes:N", title=""),
                    y=alt.Y("Val:Q", title="", scale=alt.Scale(zero=True)),
                    color=alt.Color("Cat:N", scale=palette, legend=alt.Legend(title="")),
                )
            )

            # Label at the TOP of each stacked bar showing monthly total (white text)
            chart_labels_total = (
                alt.Chart(alt.Data(values=_total_data))
                .mark_text(dy=-4, color="#FFFFFF", fontSize=13, fontWeight="bold", align="center")
                .encode(
                    x=alt.X("Mes:N"),
                    y=alt.Y("Tot:Q"),
                    text=alt.Text("Tot:Q", format=",.2f"),
                )
            )

            chart_layer = alt.layer(chart_bars, chart_labels_total).properties(width=700, height=400)
            chart_layer = chart_layer.configure_axisX(labelAngle=0, labels=True, ticks=False, grid=False, domain=False)
            chart_layer = chart_layer.configure_axisY(ticks=False, grid=False, labels=False, domain=False)

            st.altair_chart(chart_layer, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Grouped bar chart — spending by category: last month vs this month (same day range)
    # ---------------------------------------------------------------------------
    if det["date"] and det["category"] and det["amount"]:
        now = pd.Timestamp.today()
        this_year, this_month = now.year, now.month
        day_end = min(now.day, pd.Timestamp(this_year, this_month, 1).days_in_month)

        if this_month == 1:
            lm_year, lm_month = this_year - 1, 12
        else:
            lm_year, lm_month = this_year, this_month - 1
        lm_days = pd.Timestamp(lm_year, lm_month, 1).days_in_month
        day_end_lm = min(day_end, lm_days)

        # Date ranges for filtering
        last_month_start = pd.Timestamp(lm_year, lm_month, 1)
        last_month_end = pd.Timestamp(lm_year, lm_month, day_end_lm) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        this_month_start = pd.Timestamp(this_year, this_month, 1)
        this_month_end = pd.Timestamp(this_year, this_month, day_end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

        mask_last = (df[det["date"]] >= last_month_start) & (df[det["date"]] <= last_month_end)
        mask_this = (df[det["date"]] >= this_month_start) & (df[det["date"]] <= this_month_end)

        df_last = df.loc[mask_last].copy()
        df_this = df.loc[mask_this].copy()

        # Aggregate spending by category for each period
        cat_totals_last = (
            df_last.groupby(det["category"])[det["amount"]]
            .sum()
            .reset_index(name="Valor")
            .rename(columns={det["category"]: "Categoria"})
        )
        cat_totals_this = (
            df_this.groupby(det["category"])[det["amount"]]
            .sum()
            .reset_index(name="Valor")
            .rename(columns={det["category"]: "Categoria"})
        )

        # Merge so all categories appear for both periods (fillna with 0)
        merged = pd.merge(
            cat_totals_last,
            cat_totals_this,
            on="Categoria",
            how="outer",
            suffixes=("_MêsPassado", "_EsseMês"),
        ).fillna(0)

        # Build long-form data for Altair grouped bars
        _cat_chart_data = []
        for _, r in merged.iterrows():
            _cat_chart_data.append({
                "Categoria": str(r["Categoria"]),
                "Período": "Mês Passado",
                "Valor": float(r["Valor_MêsPassado"]),
            })
            _cat_chart_data.append({
                "Categoria": str(r["Categoria"]),
                "Período": "Esse Mês",
                "Valor": float(r["Valor_EsseMês"]),
            })

        if _cat_chart_data:
            palette_cat = alt.Scale(domain=["Mês Passado", "Esse Mês"], range=["#5B8FF9", "#F7608C"])

            # Single chart with xOffset → Vega-Lite groups bars side-by-side (not stacked)
            chart_cat = (
                alt.Chart(alt.Data(values=_cat_chart_data))
                .mark_bar()
                .encode(
                    x=alt.X("Categoria:N", title="Categoria", sort="-y"),
                    xOffset=alt.XOffset("Período:N", sort=["Mês Passado", "Esse Mês"]),
                    y=alt.Y("Valor:Q", title="Total Gasto (R$)", scale=alt.Scale(zero=True)),
                    color=alt.Color("Período:N", scale=palette_cat, legend=alt.Legend(title="Período")),
                )
            )

            # Value label on top of each bar
            chart_labels = (
                alt.Chart(alt.Data(values=_cat_chart_data))
                .mark_text(dy=-6, color="#FFFFFF")
                .encode(
                    x=alt.X("Categoria:N", sort="-y"),
                    xOffset=alt.XOffset("Período:N", sort=["Mês Passado", "Esse Mês"]),
                    y=alt.Y("Valor:Q"),
                    text=alt.Text("Valor:Q", format=",.2f"),
                )
            )

            chart_layer = alt.layer(chart_cat, chart_labels).properties(width=700, height=400)
            chart_layer = chart_layer.configure_axisX(labelAngle=0, labels=True, ticks=False, grid=False, domain=False)
            chart_layer = chart_layer.configure_axisY(ticks=False, grid=False, labels=False, domain=False)

            st.subheader("\U0001f4c9 Gasto por Categoria — Mês Passado vs Esse Mês")
            st.altair_chart(chart_layer, use_container_width=True)

else:
    st.warning("Nenhuma coluna de valor detectada. Mostrando prévia dos dados brutos.")
    st.dataframe(df_filtered.head(5), use_container_width=True)

st.caption(f"\U0001f4d6 {len(df_filtered)} linhas exibidas — filtradas de {len(df_raw)} total")
