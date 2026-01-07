import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import gc

# 1. Move set_page_config to the very top
st.set_page_config(page_title="Análise Comparativa PAM", layout="wide")


# 2. Cache the data loading
@st.cache_data(show_spinner=True)
def load_data() -> dict[str, pd.DataFrame]:
    """Function to load all necessary data for the dashboard."""
    data = {}
    path_base = "https://github.com/yanprada/safra-soja/releases/download/database_v1/"

    # Load and optimize main datasets
    data["pam_enriched_pct"] = pd.read_parquet(f"{path_base}pam_enriched_pct.parquet")

    data["pam_uf"] = pd.read_parquet(f"{path_base}pam_uf.parquet")
    data["pam_projected_2022"] = pd.read_parquet(
        f"{path_base}pam_projected_2022.parquet"
    )

    data["growth_pam_uf"] = pd.read_parquet(f"{path_base}growth_pam_uf.parquet")

    data["growth_pam_mun"] = pd.read_parquet(
        f"{path_base}growth_pam_enriched_pct.parquet"
    )

    geom_mun = pd.read_parquet(f"{path_base}geom_mun.parquet")
    # Ensure cd_mun matches the type in pam data (usually string or int)
    if "cd_mun" in data["pam_enriched_pct"].columns:
        target_type = data["pam_enriched_pct"]["cd_mun"].dtype
        geom_mun["cd_mun"] = geom_mun["cd_mun"].astype(target_type)
    data["geom_mun"] = geom_mun

    data["geom_uf"] = pd.read_parquet(f"{path_base}geom_uf.parquet")

    return data


data = load_data()

# ======================
# Sidebar filters
# ======================
st.sidebar.header("Filtros de Análise")

# Use references, not copies initially
df_mun = data["pam_enriched_pct"]
df_uf = data["pam_uf"]

# Explicitly invoke Garbage Collector to free up initial load overhead
gc.collect()

database = st.sidebar.selectbox("Base de Dados", ["PAM", "CONAB"], index=0)

if database == "PAM":
    nivel_geo = st.sidebar.selectbox("Nível Geográfico", ["Brasil", "UF", "Município"])
else:
    nivel_geo = st.sidebar.selectbox("Nível Geográfico", ["Brasil", "UF"])

if nivel_geo == "Brasil":
    regiao = None
    ufs = None
    municipios = None
else:
    # Get unique regions directly
    regiao = st.sidebar.multiselect(
        "Região", sorted(df_mun["regiao"].dropna().unique())
    )

    # Filter logic for UF dropdown
    mask_reg = pd.Series(True, index=df_mun.index)
    if regiao:
        mask_reg = df_mun["regiao"].isin(regiao)

    ufs_options = sorted(df_mun.loc[mask_reg, "sg_uf"].unique())
    ufs = st.sidebar.multiselect("UF", ufs_options)

    municipios = None
    if nivel_geo == "Município":
        # Filter logic for Municipality dropdown
        mask_uf = pd.Series(True, index=df_mun.index)
        if ufs:
            mask_uf = df_mun["sg_uf"].isin(ufs)

        mun_options = sorted(df_mun.loc[mask_reg & mask_uf, "nm_mun"].unique())
        municipios = st.sidebar.multiselect("Município", mun_options)

# Once filters are built, we can clean up some references if logic allows,
# but main data dependencies persist.
# However, we can clear the mask variables
if "mask_reg" in locals():
    del mask_reg
if "mask_uf" in locals():
    del mask_uf

anos = st.sidebar.multiselect(
    "Ano da Safra",
    sorted(df_mun["ano"].unique()),
    default=sorted(df_mun["ano"].unique()),
)

# ======================
# Filter logic & Context Text
# ======================
context_text = ""

# Determine Base DF and Entity
if nivel_geo == "Brasil" or nivel_geo == "UF":
    current_df = df_uf
    current_growth = data["growth_pam_uf"]
    # Drop huge municipal data if not needed
    del df_mun
    if "pam_enriched_pct" in data:
        del data["pam_enriched_pct"]
    if "growth_pam_mun" in data:
        del data["growth_pam_mun"]
    if "geom_mun" in data:
        del data["geom_mun"]

    entity_col = "sg_uf"
    entity_name = "Estado"
    title_text = f"Análise {('Nacional' if nivel_geo == 'Brasil' else 'Estadual')} da Soja ({database})"
else:
    current_df = df_mun
    current_growth = data["growth_pam_mun"]
    # Drop UF data if running municipal analysis (optional, but saves some)
    del df_uf
    if "pam_uf" in data:
        del data["pam_uf"]
    if "growth_pam_uf" in data:
        del data["growth_pam_uf"]
    if "geom_uf" in data:
        del data["geom_uf"]

    entity_col = "nm_mun"
    entity_name = "Município"
    title_text = f"Análise Municipal da Soja ({database})"

gc.collect()

# Build boolean mask instead of copying DFs repeatedly
mask = pd.Series(True, index=current_df.index)
mask_growth = pd.Series(True, index=current_growth.index)

if regiao:
    curr_mask = current_df["regiao"].isin(regiao)
    mask &= curr_mask
    mask_growth &= current_growth["regiao"].isin(regiao)
    context_text += f" Região: **{', '.join(regiao)}**."

if ufs:
    curr_mask = current_df["sg_uf"].isin(ufs)
    mask &= curr_mask
    mask_growth &= current_growth["sg_uf"].isin(ufs)
    context_text += f" UF: **{', '.join(ufs)}**."

if municipios:
    # Only applies if entity is municipality
    if "nm_mun" in current_df.columns:
        curr_mask = current_df["nm_mun"].isin(municipios)
        mask &= curr_mask
        mask_growth &= current_growth["nm_mun"].isin(municipios)
        mun_text = (
            f"{len(municipios)} selecionados"
            if len(municipios) > 5
            else ", ".join(municipios)
        )
        context_text += f" Município: **{mun_text}**."

# Apply Year filter only to main DF, not growth (growth is static comparison)
mask_year = (
    current_df["ano"].isin(anos) if anos else pd.Series(True, index=current_df.index)
)
final_mask = mask & mask_year
del mask, mask_year

# Create filtered views (avoid full deep copies where possible)
df_filt = current_df[final_mask].copy()  # Copy needed to fillna safely
df_filt_growth = current_growth[mask_growth].copy()

# Free up the big original DataFrames now that we have the filtered copies
del current_df
del current_growth
gc.collect()

df_filt.fillna(0, inplace=True)

st.title(f"📊 {title_text}")
if context_text:
    st.markdown(f"ℹ️ Filtros: {context_text}")

# ======================
# KPIs
# ======================
st.divider()
col1, col2, col3, col4 = st.columns(4)

# Calculate KPIs efficiently
col_area = f"area_plantada_ha_{database.lower()}"
col_prod = f"quantidade_producao_t_{database.lower()}"
col_val = "valor_producao_mil_reais"
col_yield = f"rendimento_medio_kg_ha_{database.lower()}"

total_area = df_filt.groupby("ano")[col_area].sum().mean()
total_prod = df_filt[col_prod].sum()
total_val_num = df_filt[col_val].sum() if database == "PAM" else 0
avg_yield = df_filt[col_yield].mean()


def fmt_num(val, suffix=""):
    s = f"{val:,.1f}{suffix}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


with col1:
    st.metric("Área Plantada Total", fmt_num(total_area / 1_000_000, " Mha"))
with col2:
    st.metric("Produção Total", fmt_num(total_prod / 1_000_000, " Mt"))
with col3:
    if database == "PAM":
        st.metric("Valor da Produção", f"R$ {fmt_num(total_val_num/1_000_000, ' Bi')}")
    else:
        st.metric("Valor da Produção", "N/A")
with col4:
    st.metric("Produtividade Média", fmt_num(avg_yield / 1000, " t/ha"))

# ======================
# MAPA (Optimized Geometry Loading)
# ======================
st.subheader("🌍 Distribuição Espacial")

col_map_ctrl, col_map_viz = st.columns([1, 3])

metric_map = {
    "Área Plantada (ha)": col_area,
    "Produção (t)": col_prod,
    "Rendimento (kg/ha)": col_yield,
}
if database == "PAM":
    metric_map["Valor da Produção (Mil R$)"] = col_val

with col_map_ctrl:
    st.markdown("**Configuração do Mapa**")
    selected_metric_label = st.selectbox(
        "Selecione a métrica:", list(metric_map.keys())
    )
    selected_metric_col = metric_map[selected_metric_label]
    st.info("**Observação:** Somente as áreas com dados serão exibidas no mapa.")

with col_map_viz:
    agg_func = "sum" if "producao" in selected_metric_col else "mean"

    should_plot_map = True
    if nivel_geo == "Município":
        # Strict logic to prevent memory crash on browser/backend
        if (not ufs or len(ufs) != 1) and not municipios:
            st.warning(
                "⚠️ Para mapa por município, selecione **apenas uma UF** ou filtre municípios."
            )
            should_plot_map = False

    if should_plot_map:
        if nivel_geo == "Município":
            stats = df_filt.groupby(["cd_mun", "nm_mun"], as_index=False).agg(
                metric_value=(selected_metric_col, agg_func)
            )

            # OPTIMIZATION: Filter geometry dataframe generically BEFORE geometry conversion
            geom_subset = data["geom_mun"][
                data["geom_mun"]["cd_mun"].isin(stats["cd_mun"])
            ].copy()

            # Merge
            gdf = pd.merge(stats, geom_subset, on=["cd_mun", "nm_mun"], how="inner")

            # Convert WKT to Geometry ONLY for the visible subset
            if not gdf.empty:
                gdf["geometry"] = gpd.GeoSeries.from_wkb(gdf["geometry"])
                gdf = gpd.GeoDataFrame(gdf, geometry="geometry")
                hover_key = "nm_mun"
            else:
                should_plot_map = False

        else:
            stats = df_filt.groupby(["sg_uf"], as_index=False).agg(
                metric_value=(selected_metric_col, agg_func)
            )
            # Filter UF geometries
            geom_subset = data["geom_uf"][
                data["geom_uf"]["sg_uf"].isin(stats["sg_uf"])
            ].copy()

            gdf = pd.merge(stats, geom_subset, on="sg_uf", how="inner")

            if not gdf.empty:
                gdf["geometry"] = gpd.GeoSeries.from_wkb(gdf["geometry"])
                gdf = gpd.GeoDataFrame(gdf, geometry="geometry")
                hover_key = "sg_uf"
            else:
                should_plot_map = False

        # Clean stats immediately
        del stats
        if "geom_subset" in locals():
            del geom_subset

        if should_plot_map and not gdf.empty:
            # Simplify geometry slightly for display speed if huge
            # gdf["geometry"] = gdf["geometry"].simplify(0.01)

            fig_map = px.choropleth(
                gdf,
                geojson=gdf.geometry,
                locations=gdf.index,
                color="metric_value",
                hover_name=hover_key,
                color_continuous_scale="Greens",
                labels={"metric_value": selected_metric_label},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
            st.plotly_chart(fig_map, width="stretch")

            # Cleanup
            del gdf
            gc.collect()

# ======================
# TOP RANKING
# ======================
st.divider()
col_rank, col_time = st.columns(2)

with col_rank:
    st.subheader(f"🏆 Top 10 {entity_name}s")

    # Efficient GroupBy
    df_rank = (
        df_filt.groupby(entity_col, as_index=False)[selected_metric_col]
        .agg(agg_func)
        .rename(columns={selected_metric_col: "val"})
        .sort_values("val", ascending=True)
        .tail(10)
    )

    hover_data = None
    if entity_col == "nm_mun":
        # We need state info, but df_mun might be deleted if nivel_geo != Município
        # However, inside df_filt we likely have sg_uf.
        # If not, and we deleted df_mun, we rely on what's in df_filt.
        if "sg_uf" in df_filt.columns:
            uf_map = df_filt[[entity_col, "sg_uf"]].drop_duplicates(subset=entity_col)
            df_rank = df_rank.merge(uf_map, on=entity_col, how="left")
            hover_data = ["sg_uf"]

    fig_bar = px.bar(
        df_rank,
        x="val",
        y=entity_col,
        orientation="h",
        text_auto=".2s",
        labels={"val": selected_metric_label, entity_col: entity_name, "sg_uf": "UF"},
        color="val",
        color_continuous_scale="Greens",
        hover_data=hover_data,
    )
    fig_bar.update_layout(showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_bar, width="stretch")
    del df_rank

# ======================
# TEMPORAL EVOLUTION
# ======================
with col_time:
    st.subheader("📈 Evolução Temporal")
    agg_func_idx = "mean" if "rendimento" in selected_metric_col else "sum"
    df_line = df_filt.groupby("ano", as_index=False)[selected_metric_col].agg(
        agg_func_idx
    )

    fig_line = px.line(
        df_line,
        x="ano",
        y=selected_metric_col,
        markers=True,
        labels={selected_metric_col: selected_metric_label, "ano": "Safra"},
    )
    fig_line.update_traces(line_color="#2ca02c", line_width=3)
    st.plotly_chart(fig_line, width="stretch")
    del df_line
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
        - 🟠 **Quadrante Inferior Direito:** Expansão de Área, mas queda na Produtividade (Pior Cenário).
        - 🔵 **Quadrante Superior Esquerdo:** Redução de Área, mas ganho de eficiência (Produtividade).
        - 🔴 **Quadrante Inferior Esquerdo:** Retração em ambos os indicadores.
        """
        )

    # Creating a local copy for visualization to apply specific density filters
    df_scatter_viz = df_filt_growth.copy()

    # Filter logic: if Municipality, reduce clutter by keeping top 50% relevant
    if nivel_geo == "Município":
        # Check if we have the size metric to determine relevance
        size_col = "area_plantada_ha_pam_target"
        if size_col in df_scatter_viz.columns:
            threshold = df_scatter_viz[size_col].quantile(0.85)
            # Safe filtering (ignoring NaNs in size column)
            df_scatter_viz = df_scatter_viz[df_scatter_viz[size_col] >= threshold]
            st.info(
                "📍 Visualizando apenas os 15% municípios mais relevantes para facilitar a leitura."
            )

    # Calculate limits for background quadrants
    x_col = "growth_area_plantada_ha_pam"
    y_col = "growth_rendimento_medio_kg_ha_pam"

    # Filter out extreme outliers for better visualization if needed, or just plot
    x_max = df_scatter_viz[x_col].max()
    x_min = df_scatter_viz[x_col].min()
    y_max = df_scatter_viz[y_col].max()
    y_min = df_scatter_viz[y_col].min()

    # Handle empty data case
    if pd.isna(x_max) or df_scatter_viz.empty:
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
            df_scatter_viz,
            x=x_col,
            y=y_col,
            color=color_tmp,
            hover_name=hoover_tmp,
            labels={
                "growth_area_plantada_ha_pam": "Δ Área Plantada (ha)",
                "growth_rendimento_medio_kg_ha_pam": "Δ Rendimento (kg/ha)",
                "sg_uf": "Estado",
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

    del df_scatter_viz

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

        # Enrich with municipality names and region.
        # Note: We rely on df_filt since we might have deleted large df_mun
        mun_meta = df_filt[["cd_mun", "nm_mun", "regiao"]].drop_duplicates()
        df_proj = df_proj.merge(mun_meta, on="cd_mun", how="left")

        # Filter projections based on sidebar selection
        if regiao:
            df_proj = df_proj[df_proj["regiao"].isin(regiao)]
        if ufs:
            df_proj = df_proj[df_proj["sg_uf"].isin(ufs)]
        if municipios:
            df_proj = df_proj[df_proj["nm_mun"].isin(municipios)]

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

            del df_proj_rank
        else:
            st.info("Projeções não disponíveis para a métrica selecionada.")

        del df_proj

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

    # Filter top 50% for Municipalities to reduce clutter
    if nivel_geo == "Município":
        threshold = df_tree[selected_metric_col].quantile(0.75)
        df_tree = df_tree[df_tree[selected_metric_col] >= threshold]
        st.info(
            f"📍 Filtrando top 15% municípios por **{selected_metric_label}** para facilitar leitura."
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
    del df_tree

# --- 2. Boxplot de Produtividade ---
with col_box:
    st.markdown("**Distribuição de Produtividade (Rendimento)**")
    st.caption(
        "Variabilidade do rendimento (kg/ha) dos **municípios** dentro das regiões filtradas."
    )

    df_box_source = df_filt.copy()

    fig_box = px.box(
        df_box_source,
        x="regiao",
        y=f"rendimento_medio_kg_ha_{database.lower()}",
        color="regiao",
        points="outliers",  # Show only outliers to avoid performance hit on heavy rendering
        hover_name=entity_col,  # Add municipality/uf name to hover
        hover_data=["sg_uf"] if "sg_uf" in df_box_source.columns else None,
        labels={
            f"rendimento_medio_kg_ha_{database.lower()}": "Rendimento (kg/ha)",
            "regiao": "Região",
            "sg_uf": "Estado",
        },
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, width="stretch")
    del df_box_source

if database == "PAM":
    # --- 3. Bubble Chart (Economic Efficiency) ---
    st.markdown("**💰 Eficiência Econômica: Área vs Valor da Produção**")
    st.caption(
        "O tamanho da bolha representa a **Quantidade Produzida (t)**. Buscamos bolhas no canto superior esquerdo (Alto Valor, Menor Área)."
    )

    col_area_bubble = f"area_plantada_ha_{database.lower()}"
    df_bubble = df_filt.groupby(entity_col, as_index=False).agg(
        {
            col_area_bubble: "mean",
            "valor_producao_mil_reais": "sum",
            f"quantidade_producao_t_{database.lower()}": "sum",
            "regiao": "first",
        }
    )

    if nivel_geo == "Município":
        threshold_bubble = df_bubble[col_area_bubble].quantile(0.85)
        df_bubble = df_bubble[df_bubble[col_area_bubble] >= threshold_bubble]
        st.info(
            f"📍 Filtrando top 15% municípios por Área Plantada para facilitar leitura."
        )

    fig_bubble = px.scatter(
        df_bubble,
        x=f"area_plantada_ha_{database.lower()}",
        y="valor_producao_mil_reais",
        size=f"quantidade_producao_t_{database.lower()}",
        color="regiao",
        hover_name=entity_col,
        log_x=True,  # Log scale helps visualization when there are huge disparities
        log_y=True,
        size_max=60,
        labels={
            f"area_plantada_ha_{database.lower()}": "Área Plantada (ha) [Log]",
            "valor_producao_mil_reais": "Valor da Produção (Mil R$) [Log]",
            f"quantidade_producao_t_{database.lower()}": "Produção (t)",
            "regiao": "Região",
        },
    )
    st.plotly_chart(fig_bubble, width="stretch")
    del df_bubble

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
        .round(2)
    )

    st.dataframe(df_display, width="stretch", hide_index=True)
    del df_display

# Final generic cleanup
gc.collect()
