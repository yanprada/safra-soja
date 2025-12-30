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
    data["pam_enriched_pct"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/pam_enriched_pct.parquet"
    )
    data["pam_uf"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/pam_uf.parquet"
    )
    data["pam_projected_2022"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/pam_projected_2022.parquet"
    )
    data["growth_pam_uf"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/growth_pam_uf.parquet"
    )
    data["growth_pam_mun"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/growth_pam_enriched_pct.parquet"
    )
    data["geom_mun"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/geom_mun.parquet"
    )
    data["geom_mun"]["geometry"] = data["geom_mun"]["geometry"].apply(wkt.loads)
    data["geom_uf"] = pd.read_parquet(
        "https://github.com/yanprada/safra-soja/releases/download/database_v1/geom_uf.parquet"
    )
    data["geom_uf"]["geometry"] = data["geom_uf"]["geometry"].apply(wkt.loads)
    return data


data = load_data()

# ======================
# Sidebar filters
# ======================
st.sidebar.header("Filtros de Análise")

database = st.sidebar.selectbox("Base de Dados", ["PAM", "CONAB"], index=0)
if database == "PAM":
    nivel_geo = st.sidebar.selectbox("Nível Geográfico", ["Brasil", "UF", "Município"])
else:
    nivel_geo = st.sidebar.selectbox("Nível Geográfico", ["Brasil", "UF"])
df_mun = data["pam_enriched_pct"]
df_uf = data["pam_uf"]
df_growth_mun = data["growth_pam_mun"]
df_growth_uf = data["growth_pam_uf"]
if nivel_geo == "Brasil":
    regiao = None
    ufs = None  # No additional filters
else:
    regiao = st.sidebar.multiselect(
        "Região", sorted(df_mun["regiao"].dropna().unique())
    )

    if regiao:
        ufs_options = sorted(df_mun[df_mun["regiao"].isin(regiao)]["sg_uf"].unique())
    else:
        ufs_options = sorted(df_mun["sg_uf"].unique())

    ufs = st.sidebar.multiselect("UF", ufs_options)
anos = st.sidebar.multiselect(
    "Ano da Safra",
    sorted(df_mun["ano"].unique()),
    default=sorted(df_mun["ano"].unique()),
)
# ======================
# Filter logic & Context Text
# ======================
context_text = ""

if nivel_geo == "Brasil":
    title_text = f"Análise Nacional da Soja ({database})"
    context_text = "Visualizando dados agregados para todo o **Brasil**."
    df_filt = df_uf.copy()
    df_filt_growth = df_growth_uf.copy()
    entity_col = "sg_uf"
    entity_name = "Estado"
elif nivel_geo == "UF":
    title_text = f"Análise Estadual da Soja ({database})"
    context_text = "Visualizando comparação entre **Unidades Federativas**."
    df_filt = df_uf.copy()
    df_filt_growth = df_growth_uf.copy()
    entity_col = "sg_uf"
    entity_name = "Estado"
else:
    title_text = f"Análise Municipal da Soja ({database})"
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
if anos:
    df_filt = df_filt[df_filt["ano"].isin(anos)]
    context_text += f" Filtro de Ano ativo: **{', '.join(map(str, anos))}**."
df_filt = df_filt.fillna(0)
st.title(f"📊 {title_text}")
st.markdown(f"ℹ️ {context_text}")

# ======================
# KPIs
# ======================
st.divider()
col1, col2, col3, col4 = st.columns(4)

total_area = df_filt.groupby("ano")[f"area_plantada_ha_{database.lower()}"].sum().mean()
total_prod = df_filt[f"quantidade_producao_t_{database.lower()}"].sum()
if database == "PAM":
    total_val = df_filt["valor_producao_mil_reais"].sum()
else:
    total_val = "N/A"  # CONAB does not have production value data
avg_yield = df_filt[f"rendimento_medio_kg_ha_{database.lower()}"].mean()

with col1:
    st.metric(
        "Área Plantada Total",
        f"{(total_area/1_000_000):,.1f} Mha".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Média da área plantada em todos os anos selecionados.",
    )

with col2:
    st.metric(
        "Produção Total",
        f"{(total_prod/1_000_000):,.1f} Mt".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Soma da produção em toneladas, somadas para os anos selecionados.",
    )

with col3:
    if total_val == "N/A":
        st.metric(
            "Valor da Produção",
            "N/A",
            help="Dados de valor da produção não disponíveis para CONAB.",
        )
    else:
        st.metric(
            "Valor da Produção",
            f"R$ {(total_val/1_000_000):,.1f} Bi".replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
            help="Valor total da produção em Bilhões de Reais, somadas para os anos selecionados.",
        )

with col4:
    st.metric(
        "Produtividade Média",
        f"{(avg_yield / 1000):,.2f} t/ha".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
        help="Média simples do rendimento (kg/ha) das regiões filtradas, levando em conta todos os anos selecionados.",
    )

# ======================
# MAPA
# ======================
st.subheader("🌍 Distribuição Espacial")

col_map_ctrl, col_map_viz = st.columns([1, 3])

with col_map_ctrl:
    st.markdown("**Configuração do Mapa**")

    metric_map = {
        "Área Plantada (ha)": f"area_plantada_ha_{database.lower()}",
        "Produção (t)": f"quantidade_producao_t_{database.lower()}",
        "Rendimento (kg/ha)": f"rendimento_medio_kg_ha_{database.lower()}",
    }
    if database == "PAM":
        metric_map["Valor da Produção (Mil R$)"] = "valor_producao_mil_reais"
    selected_metric_label = st.selectbox(
        "Selecione a métrica:", list(metric_map.keys())
    )
    selected_metric_col = metric_map[selected_metric_label]

    st.info(
        f"O mapa ao lado exibe a **{selected_metric_label}** agregada por {entity_name.lower()}. "
        "Áreas mais escuras indicam valores maiores."
    )

with col_map_viz:
    agg_func = "sum" if "producao" in selected_metric_col else "mean"

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
            gdf = pd.merge(
                stats, data["geom_mun"], on=["cd_mun", "nm_mun"], how="inner"
            )
            gdf = gpd.GeoDataFrame(gdf, geometry="geometry")

            fig_map = px.choropleth(
                gdf,
                geojson=gdf["geometry"],
                locations=gdf.index,
                color="metric_value",
                hover_name="nm_mun",
                color_continuous_scale="Greens",
                labels={"metric_value": selected_metric_label},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig_map, width="stretch")

    else:
        stats = df_filt.groupby(["sg_uf"], as_index=False).agg(
            metric_value=(selected_metric_col, agg_func)
        )
        gdf = pd.merge(stats, data["geom_uf"], on="sg_uf", how="inner")
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry")

        fig_map = px.choropleth(
            gdf,
            geojson=gdf["geometry"],
            locations=gdf.index,
            color="metric_value",
            hover_name="sg_uf",
            color_continuous_scale="Greens",
            labels={"metric_value": selected_metric_label},
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        st.plotly_chart(fig_map, width="stretch")

# ======================
# TOP RANKING
# ======================
st.divider()
col_rank, col_time = st.columns(2)

with col_rank:
    st.subheader(f"🏆 Top 10 {entity_name}s")
    agg_msg = (
        "somando os anos selecionados"
        if "producao" in selected_metric_col
        else "calculando a média dos anos selecionados"
    )
    st.markdown(
        f"Ranking dos maiores produtores considerando a métrica **{selected_metric_label}**, {agg_msg}."
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
    st.plotly_chart(fig_bar, width="stretch")

# ======================
# TEMPORAL EVOLUTION
# ======================
with col_time:
    st.subheader("📈 Evolução Temporal")
    st.markdown("Como a métrica selecionada se comportou nas últimas safras?")
    agg_func = "mean" if "rendimento" in selected_metric_col else "sum"
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
    st.plotly_chart(fig_line, width="stretch")

# ======================
# GROWTH SCATTER
# ======================
if database == "PAM":
    st.divider()
    st.subheader("🚀 Matriz de Crescimento (2019 → 2021)")

    with st.expander("📖 Como ler este gráfico?", expanded=True):
        st.markdown(
            """
        Este gráfico divide os locais em 4 quadrantes baseados no crescimento de **Área** (Eixo X) e **Produtividade** (Eixo Y):
        - 🟢 **Quadrante Superior Direito:** Crescimento em Área e Produtividade.
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

        st.plotly_chart(fig_scatter, width="stretch")
    # ======================
    # PROJECTIONS 2022
    # ======================
    if nivel_geo == "Município":
        st.divider()
        st.subheader("🔮 Projeções 2022 (Municípios)")
        st.markdown(
            f"Projeção estimada para o ano de 2022 para a métrica **{selected_metric_label}**."
        )

        df_proj = data["pam_projected_2022"].copy()

        # Enrich with municipality names and region
        mun_meta = df_mun[["cd_mun", "nm_mun", "regiao"]].drop_duplicates()
        df_proj = df_proj.merge(mun_meta, on="cd_mun", how="left")

        # Filter projections based on sidebar selection
        if regiao:
            df_proj = df_proj[df_proj["regiao"].isin(regiao)]
        if ufs:
            df_proj = df_proj[df_proj["sg_uf"].isin(ufs)]

        # Specific Municipality Filter for Projections
        available_muns = sorted(df_proj["nm_mun"].dropna().unique())
        selected_mun_proj = st.multiselect(
            "Filtrar Município Específico (Projeção)",
            options=available_muns,
            placeholder="Selecione um ou mais municípios para filtrar...",
        )

        if selected_mun_proj:
            df_proj = df_proj[df_proj["nm_mun"].isin(selected_mun_proj)]

        # Map selected metric to projection columns
        proj_col_map = {
            "Área Plantada (ha)": "projected_area_plantada_ha",
            "Produção (t)": "projected_quantidade_producao_t",
        }

        proj_col = None
        if selected_metric_label in proj_col_map:
            proj_col = proj_col_map[selected_metric_label]
        elif selected_metric_label == "Rendimento (kg/ha)":
            # Calculate yield: (Production (t) * 1000) / Area (ha)
            df_proj["projected_rendimento_kg_ha"] = (
                df_proj["projected_quantidade_producao_t"] * 1000
            ) / df_proj["projected_area_plantada_ha"]
            proj_col = "projected_rendimento_kg_ha"

        if proj_col and proj_col in df_proj.columns:
            # Top 15 projected (or all selected if filtered)
            limit = 15 if not selected_mun_proj else None
            df_proj_rank = (
                df_proj[["nm_mun", "sg_uf", proj_col]]
                .sort_values(proj_col, ascending=False)
                .head(limit)
            )

            if df_proj_rank.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                fig_proj = px.bar(
                    df_proj_rank,
                    x=proj_col,
                    y="nm_mun",
                    orientation="h",
                    text_auto=".2s",
                    labels={
                        proj_col: f"Projeção 2022 - {selected_metric_label}",
                        "nm_mun": "Município",
                    },
                    color=proj_col,
                    color_continuous_scale="Blues",
                    title=f"Top {len(df_proj_rank)} Municípios - Projeção 2022 ({selected_metric_label})",
                )
                fig_proj.update_layout(
                    yaxis={"categoryorder": "total ascending"}, showlegend=False
                )
                st.plotly_chart(fig_proj, width="stretch")
        else:
            st.info("Projeções não disponíveis para a métrica selecionada.")
# ======================
# DEEP DIVE ANALYTICS
# ======================
st.divider()
st.subheader("🔍 Aprofundamento da Análise")

col_tree, col_box = st.columns(2)
# --- 1. Treemap de Participação ---
with col_tree:
    st.markdown(f"**Participação na Produção Total ({entity_name})**")
    agg_msg = (
        "Somamos os anos selecionados"
        if "producao" in selected_metric_col
        else "Calculamos a média dos anos selecionados"
    )
    st.caption(
        f"Como a produção se divide hierarquicamente entre Regiões e Estados? {agg_msg}."
    )

    # Define hierarchy path based on selection
    if nivel_geo == "Município":
        path_tree = ["regiao", "sg_uf", "nm_mun"]
    else:
        path_tree = ["regiao", "sg_uf"]

    # Aggregation logic matching the stats/map section
    agg_func = "sum" if "producao" in selected_metric_col else "mean"

    # Pre-aggregate data to handle multiple years selection correctly
    df_tree = df_filt.groupby(path_tree, as_index=False)[selected_metric_col].agg(
        agg_func
    )

    # Treemap handles aggregation automatically, but using df_filt is safer
    fig_tree = px.treemap(
        df_tree,
        path=path_tree,
        values=selected_metric_col,
        color=selected_metric_col,
        color_continuous_scale="Greens",
        hover_data=[selected_metric_col],
    )
    fig_tree.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig_tree, width="stretch")

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
        y=f"rendimento_medio_kg_ha_{database.lower()}",
        color="regiao",
        points="outliers",  # Show only outliers to avoid performance hit on heavy rendering
        labels={
            f"rendimento_medio_kg_ha_{database.lower()}": "Rendimento (kg/ha)",
            "regiao": "Região",
        },
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, width="stretch")
if database == "PAM":
    # --- 3. Bubble Chart (Economic Efficiency) ---
    st.markdown("**💰 Eficiência Econômica: Área vs Valor da Produção**")
    st.caption(
        "O tamanho da bolha representa a **Quantidade Produzida (t)**. Buscamos bolhas no canto superior esquerdo (Alto Valor, Menor Área)."
    )

    fig_bubble = px.scatter(
        df_filt,
        x=f"area_plantada_ha_{database.lower()}",
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
    st.plotly_chart(fig_bubble, width="stretch")
    # ======================
    # TABLE
    # ======================
    st.subheader("📋 Detalhamento dos Dados")
    st.markdown(
        f"Tabela detalhada contendo as métricas de crescimento para os **{df_filt_growth.shape[0]}** registros filtrados."
    )
    if entity_col == "nm_mun":

        cols_to_show = [
            entity_col,
            "sg_uf",
            "area_plantada_ha_pam_base",
            "area_plantada_ha_pam_target",
            "growth_area_plantada_ha_pam",
            "growth_rendimento_medio_kg_ha_pam",
        ]

        # Rename columns for better display
        cols_rename = {
            entity_col: entity_name,
            "sg_uf": "Estado",
            "area_plantada_ha_pam_base": "Área Base (ha)",
            "area_plantada_ha_pam_target": "Área Atual (ha)",
            "growth_area_plantada_ha_pam": "Cresc. Área (%)",
            "growth_rendimento_medio_kg_ha_pam": "Cresc. Rendimento (%)",
        }
    else:
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
            "growth_area_plantada_ha_pam": "Cresc. Área (%)",
            "growth_rendimento_medio_kg_ha_pam": "Cresc. Rendimento (%)",
        }
    df_display = (
        df_filt_growth[cols_to_show]
        .rename(columns=cols_rename)
        .sort_values("Cresc. Área (%)", ascending=False)
    )

    st.dataframe(df_display, width="stretch", hide_index=True)
