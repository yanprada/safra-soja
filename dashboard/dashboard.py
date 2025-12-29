import streamlit as st
from shapely import wkt
import pandas as pd
import geopandas as gpd
import plotly.express as px

# 1. Move set_page_config to the very top
st.set_page_config(page_title="Análise Comparativa PAM", layout="wide")


# 2. Cache the data loading
@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    """Function to load all necessary data for the dashboard."""
    data = {}
    data["pam_enriched_pct"] = pd.read_parquet("data/pam_enriched_pct.parquet")
    data["pam_uf"] = pd.read_parquet("data/pam_uf.parquet")
    data["growth_pam_uf"] = pd.read_parquet("data/growth_pam_uf.parquet")
    data["growth_pam_mun"] = pd.read_parquet("data/growth_pam_enriched_pct.parquet")
    return data


# 3. Helper to process and cache geometries separately
@st.cache_data
def get_geometry_lookup(df: pd.DataFrame, id_col: str, geo_col: str):
    """Extracts unique geometries and converts WKT to objects once."""
    # Get unique ID and Geometry pairs
    lookup = df[[id_col, geo_col]].drop_duplicates(subset=[id_col]).copy()
    # Convert WKT to geometry object
    lookup[geo_col] = lookup[geo_col].apply(wkt.loads)
    return lookup


data = load_data()

# ======================
# Sidebar filters
# ======================
st.sidebar.header("Filtros de Análise")

nivel_geo = st.sidebar.selectbox("Nível Geográfico", ["Brasil", "UF", "Município"])

df_mun = data["pam_enriched_pct"]
df_uf = data["pam_uf"]
df_growth_mun = data["growth_pam_mun"]
df_growth_uf = data["growth_pam_uf"]

regiao = st.sidebar.multiselect("Região", sorted(df_mun["regiao"].dropna().unique()))

if regiao:
    ufs_options = sorted(df_mun[df_mun["regiao"].isin(regiao)]["sg_uf"].unique())
else:
    ufs_options = sorted(df_mun["sg_uf"].unique())

ufs = st.sidebar.multiselect("UF", ufs_options)

# ======================
# Filter logic & Context Text
# ======================
context_text = ""

if nivel_geo == "Brasil":
    title_text = "Análise Nacional da Soja (PAM)"
    context_text = "Visualizando dados agregados para todo o **Brasil**."
    df_filt = df_uf.copy()
    df_filt_growth = df_growth_uf.copy()
    entity_col = "sg_uf"
    entity_name = "Estado"
elif nivel_geo == "UF":
    title_text = "Análise Estadual da Soja (PAM)"
    context_text = "Visualizando comparação entre **Unidades Federativas**."
    df_filt = df_uf.copy()
    df_filt_growth = df_growth_uf.copy()
    entity_col = "sg_uf"
    entity_name = "Estado"
else:
    title_text = "Análise Municipal da Soja (PAM)"
    context_text = "Visualizando dados detalhados por **Município**."
    df_filt = df_mun.copy()
    df_filt_growth = df_growth_mun.copy()
    entity_col = "nm_mun"
    entity_name = "Município"

if regiao:
    df_filt = df_filt[df_filt["regiao"].isin(regiao)]
    df_filt_growth = df_filt_growth[df_filt_growth["regiao"].isin(regiao)]
    context_text += f" Filtro de Região ativo: **{', '.join(regiao)}**."

if ufs:
    df_filt = df_filt[df_filt["sg_uf"].isin(ufs)]
    df_filt_growth = df_filt_growth[df_filt_growth["sg_uf"].isin(ufs)]
    context_text += f" Filtro de UF ativo: **{', '.join(ufs)}**."

st.title(f"📊 {title_text}")
st.markdown(f"ℹ️ {context_text}")

# ======================
# KPIs
# ======================
st.divider()
col1, col2, col3, col4 = st.columns(4)

total_area = df_filt["area_plantada_ha_pam"].sum()
total_prod = df_filt["quantidade_producao_t_pam"].sum()
total_val = df_filt["valor_producao_mil_reais"].sum()
avg_yield = df_filt["rendimento_medio_kg_ha_pam"].mean()

with col1:
    st.metric(
        "Área Plantada Total",
        f"{(total_area/1_000_000):,.1f} Mha".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Soma da área plantada em todos os anos selecionados.",
    )

with col2:
    st.metric(
        "Produção Total",
        f"{(total_prod/1_000_000):,.1f} Mt".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Soma da produção em toneladas.",
    )

with col3:
    st.metric(
        "Valor da Produção",
        f"R$ {(total_val/1_000_000):,.1f} Bi".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Valor total da produção em Bilhões de Reais.",
    )

with col4:
    st.metric(
        "Produtividade Média",
        f"{(avg_yield / 1000):,.2f} t/ha".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Média simples do rendimento (kg/ha) das regiões filtradas.",
    )

# ======================
# MAPA
# ======================
st.subheader("🗺️ Distribuição Espacial")

col_map_ctrl, col_map_viz = st.columns([1, 3])

with col_map_ctrl:
    st.markdown("**Configuração do Mapa**")
    metric_map = {
        "Área Plantada (ha)": "area_plantada_ha_pam",
        "Produção (t)": "quantidade_producao_t_pam",
        "Rendimento (kg/ha)": "rendimento_medio_kg_ha_pam",
    }

    selected_metric_label = st.selectbox(
        "Selecione a métrica:", list(metric_map.keys())
    )
    selected_metric_col = metric_map[selected_metric_label]

    st.info(
        f"O mapa ao lado exibe a **{selected_metric_label}** agregada por {entity_name.lower()}. "
        "Áreas mais escuras indicam valores maiores."
    )

with col_map_viz:
    agg_func = "mean" if "rendimento" in selected_metric_col else "sum"

    # Optimized Map Logic
    if nivel_geo == "Município":
        if not ufs or len(ufs) != 1:
            st.warning(
                "⚠️ Para visualizar o mapa por município, por favor selecione **apenas uma UF** no menu lateral (para performance)."
            )
        else:
            stats = df_filt.groupby(["cd_mun", "nm_mun"], as_index=False).agg(
                metric_value=(selected_metric_col, agg_func)
            )
            geo_lookup = get_geometry_lookup(df_mun, "cd_mun", "geometry_pam")
            gdf = pd.merge(stats, geo_lookup, on="cd_mun", how="inner")
            gdf = gpd.GeoDataFrame(gdf, geometry="geometry_pam")

            fig_map = px.choropleth(
                gdf,
                geojson=gdf["geometry_pam"],
                locations=gdf.index,
                color="metric_value",
                hover_name="nm_mun",
                color_continuous_scale="Greens",
                labels={"metric_value": selected_metric_label},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig_map, use_container_width=True)

    else:
        stats = df_filt.groupby(["sg_uf"], as_index=False).agg(
            metric_value=(selected_metric_col, agg_func)
        )
        geo_lookup = get_geometry_lookup(df_uf, "sg_uf", "geometry_uf")
        gdf = pd.merge(stats, geo_lookup, on="sg_uf", how="inner")
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry_uf")

        fig_map = px.choropleth(
            gdf,
            geojson=gdf["geometry_uf"],
            locations=gdf.index,
            color="metric_value",
            hover_name="sg_uf",
            color_continuous_scale="Greens",
            labels={"metric_value": selected_metric_label},
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig_map, use_container_width=True)

# ======================
# TOP RANKING
# ======================
st.divider()
col_rank, col_time = st.columns(2)

with col_rank:
    st.subheader(f"🏆 Top 10 {entity_name}s")
    st.markdown(
        f"Ranking dos maiores produtores considerando a métrica **{selected_metric_label}**."
    )

    # Group by entity and sum/mean based on metric
    df_rank = (
        df_filt.groupby(entity_col, as_index=False)
        .agg(val=(selected_metric_col, agg_func))
        .sort_values("val", ascending=True)
        .tail(10)
    )  # Tail because barh plots bottom-up

    fig_bar = px.bar(
        df_rank,
        x="val",
        y=entity_col,
        orientation="h",
        text_auto=".2s",
        labels={"val": selected_metric_label, entity_col: entity_name},
        color="val",
        color_continuous_scale="Greens",
    )
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, use_container_width=True)

# ======================
# TEMPORAL EVOLUTION
# ======================
with col_time:
    st.subheader("📈 Evolução Temporal")
    st.markdown("Como a métrica selecionada se comportou nas últimas safras?")

    df_line = df_filt.groupby("ano", as_index=False).agg(
        valor=(selected_metric_col, agg_func)
    )

    fig_line = px.line(
        df_line,
        x="ano",
        y="valor",
        markers=True,
        labels={"valor": selected_metric_label, "ano": "Safra"},
    )
    fig_line.update_traces(line_color="#2ca02c", line_width=3)
    st.plotly_chart(fig_line, use_container_width=True)

# ======================
# GROWTH SCATTER
# ======================
st.divider()
st.subheader("🚀 Matriz de Crescimento (2019 → 2021)")

with st.expander("📖 Como ler este gráfico?", expanded=True):
    st.markdown(
        """
    Este gráfico divide os locais em 4 quadrantes baseados no crescimento de **Área** (Eixo X) e **Produtividade** (Eixo Y):
    - 🟢 **Quadrante Superior Direito:** Crescimento em Área e Produtividade (Cenário Ideal).
    - 🟠 **Quadrante Inferior Direito:** Expansão de Área, mas queda na Produtividade.
    - 🔵 **Quadrante Superior Esquerdo:** Redução de Área, mas ganho de eficiência (Produtividade).
    - 🔴 **Quadrante Inferior Esquerdo:** Retração em ambos os indicadores.
    """
    )

# Calculate limits for background quadrants
x_col = "growth_area_plantada_ha_pam"
y_col = "growth_rendimento_medio_kg_ha_pam"

# Filter out extreme outliers for better visualization if needed, or just plot
x_max = df_filt_growth[x_col].max()
x_min = df_filt_growth[x_col].min()
y_max = df_filt_growth[y_col].max()
y_min = df_filt_growth[y_col].min()

# Handle empty data case
if pd.isna(x_max):
    st.warning(
        "Dados insuficientes para gerar a matriz de crescimento com os filtros atuais."
    )
else:
    x_pad = (x_max - x_min) * 0.1 if x_max != x_min else 1.0
    y_pad = (y_max - y_min) * 0.1 if y_max != y_min else 1.0

    max_x = x_max + x_pad
    min_x = x_min - x_pad
    max_y = y_max + y_pad
    min_y = y_min - y_pad

    hoover_tmp = "nm_mun" if nivel_geo == "Município" else "sg_uf"
    color_tmp = "sg_uf" if nivel_geo == "Município" else "regiao"

    fig_scatter = px.scatter(
        df_filt_growth,
        x=x_col,
        y=y_col,
        color=color_tmp,
        hover_name=hoover_tmp,
        labels={
            "growth_area_plantada_ha_pam": "Δ Área Plantada (ha)",
            "growth_rendimento_medio_kg_ha_pam": "Δ Rendimento (kg/ha)",
        },
        title=f"Dispersão de Crescimento: {entity_name}s",
    )

    # Add colored quadrants
    fig_scatter.add_shape(
        type="rect",
        x0=0,
        y0=0,
        x1=max(max_x, 0.1),
        y1=max(max_y, 0.1),
        fillcolor="rgba(0, 255, 0, 0.1)",
        line_width=0,
        layer="below",
    )
    fig_scatter.add_shape(
        type="rect",
        x0=min(min_x, -0.1),
        y0=0,
        x1=0,
        y1=max(max_y, 0.1),
        fillcolor="rgba(0, 0, 255, 0.1)",
        line_width=0,
        layer="below",
    )
    fig_scatter.add_shape(
        type="rect",
        x0=min(min_x, -0.1),
        y0=min(min_y, -0.1),
        x1=0,
        y1=0,
        fillcolor="rgba(255, 0, 0, 0.1)",
        line_width=0,
        layer="below",
    )
    fig_scatter.add_shape(
        type="rect",
        x0=0,
        y0=min(min_y, -0.1),
        x1=max(max_x, 0.1),
        y1=0,
        fillcolor="rgba(255, 165, 0, 0.1)",
        line_width=0,
        layer="below",
    )

    fig_scatter.update_xaxes(zeroline=True, zerolinewidth=2, zerolinecolor="black")
    fig_scatter.update_yaxes(zeroline=True, zerolinewidth=2, zerolinecolor="black")

    st.plotly_chart(fig_scatter, use_container_width=True)
# ======================
# DEEP DIVE ANALYTICS
# ======================
st.divider()
st.subheader("🔍 Aprofundamento da Análise")

col_tree, col_box = st.columns(2)

# --- 1. Treemap de Participação ---
with col_tree:
    st.markdown(f"**Participação na Produção Total ({entity_name})**")
    st.caption("Como a produção se divide hierarquicamente entre Regiões e Estados?")

    # Define hierarchy path based on selection
    if nivel_geo == "Município":
        path_tree = ["regiao", "sg_uf", "nm_mun"]
    else:
        path_tree = ["regiao", "sg_uf"]

    # Treemap handles aggregation automatically, but using df_filt is safer
    fig_tree = px.treemap(
        df_filt,
        path=path_tree,
        values=selected_metric_col,
        color=selected_metric_col,
        color_continuous_scale="Greens",
        hover_data=[selected_metric_col],
    )
    fig_tree.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_tree, use_container_width=True)

# --- 2. Boxplot de Produtividade ---
with col_box:
    st.markdown("**Distribuição de Produtividade (Rendimento)**")
    st.caption(
        "Variabilidade do rendimento (kg/ha) dos **municípios** dentro das regiões filtradas."
    )

    # For Boxplot, we always want the granular municipal data to show distribution/spread
    # regardless of the aggregation level selected in the sidebar.
    df_box_source = df_mun.copy()

    # Apply current filters to the granular dataset
    if regiao:
        df_box_source = df_box_source[df_box_source["regiao"].isin(regiao)]
    if ufs:
        df_box_source = df_box_source[df_box_source["sg_uf"].isin(ufs)]

    fig_box = px.box(
        df_box_source,
        x="regiao",
        y="rendimento_medio_kg_ha_pam",
        color="regiao",
        points="outliers",  # Show only outliers to avoid performance hit on heavy rendering
        labels={"rendimento_medio_kg_ha_pam": "Rendimento (kg/ha)", "regiao": "Região"},
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# --- 3. Bubble Chart (Economic Efficiency) ---
st.markdown("**💰 Eficiência Econômica: Área vs Valor da Produção**")
st.caption(
    "O tamanho da bolha representa a **Quantidade Produzida (t)**. Buscamos bolhas no canto superior esquerdo (Alto Valor, Menor Área)."
)

fig_bubble = px.scatter(
    df_filt,
    x="area_plantada_ha_pam",
    y="valor_producao_mil_reais",
    size="quantidade_producao_t_pam",
    color="regiao",
    hover_name=entity_col,
    log_x=True,  # Log scale helps visualization when there are huge disparities
    log_y=True,
    size_max=60,
    labels={
        "area_plantada_ha_pam": "Área Plantada (ha) [Log]",
        "valor_producao_mil_reais": "Valor da Produção (Mil R$) [Log]",
        "quantidade_producao_t_pam": "Produção (t)",
        "regiao": "Região",
    },
)
st.plotly_chart(fig_bubble, use_container_width=True)
# ======================
# TABLE
# ======================
st.subheader("📋 Detalhamento dos Dados")
st.markdown(
    f"Tabela detalhada contendo as métricas de crescimento para os **{df_filt_growth.shape[0]}** registros filtrados."
)

cols_to_show = [
    entity_col,
    "area_plantada_ha_pam_base",
    "area_plantada_ha_pam_target",
    "growth_area_plantada_ha_pam",
    "growth_rendimento_medio_kg_ha_pam",
]

# Rename columns for better display
cols_rename = {
    entity_col: entity_name,
    "area_plantada_ha_pam_base": "Área Base (ha)",
    "area_plantada_ha_pam_target": "Área Atual (ha)",
    "growth_area_plantada_ha_pam": "Cresc. Área (ha)",
    "growth_rendimento_medio_kg_ha_pam": "Cresc. Rendimento (kg/ha)",
}

df_display = (
    df_filt_growth[cols_to_show]
    .rename(columns=cols_rename)
    .sort_values("Cresc. Área (ha)", ascending=False)
)

st.dataframe(df_display, use_container_width=True, hide_index=True)
