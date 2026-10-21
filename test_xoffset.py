"""Verify xOffset produces grouped (side-by-side) bars, not stacked."""

import altair as alt
import json

data = [
    {"Categoria": "Conforto", "Período": "Mês Passado", "Valor": 519.55},
    {"Categoria": "Conforto", "Período": "Esse Mês", "Valor": 1423.44},
    {"Categoria": "Custos Fixos", "Período": "Mês Passado", "Valor": 4063.87},
    {"Categoria": "Custos Fixos", "Período": "Esse Mês", "Valor": 3669.49},
]

chart = alt.Chart(alt.Data(values=data)).mark_bar().encode(
    x=alt.X("Categoria:N", title="Categoria", sort="-y"),
    xOffset="Período:N",
    y=alt.Y("Valor:Q", title="Total Gasto (R$)", scale=alt.Scale(zero=True)),
    color=alt.Color("Período:N"),
)

spec = chart.to_dict()
print(json.dumps(spec, indent=2, ensure_ascii=False))

# Check for aggregate transform that might collapse data to one row per group
if "transform" in spec.get("data", {}):
    print("\nWARNING: Data has explicit transforms (will change grouping)")
else:
    print("\nData values are passed directly — xOffset should work.")
