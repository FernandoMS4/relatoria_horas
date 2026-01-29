import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "modules"))

import streamlit as st
import pandas as pd
import altair as alt
from modules.gs_integrations import GSGoldenBagres
from modules.data_store import (
    table_exists, save_dataframe, load_dataframe, get_last_update,
    alocacao_exists, save_alocacao, load_alocacao,
)

SHEET_ID = "1ej9meDW8js9sPvqylB9eNbNLp3-phJlb7UE8j_BPvFk"
WORKSHEET = "HORAS_V2"


def fetch_and_store() -> pd.DataFrame:
    """Busca dados do Google Sheets, trata e salva no DuckDB."""
    client = GSGoldenBagres(sheet_id=SHEET_ID, worksheet=WORKSHEET, show_=False)
    df = client.start()

    df["HORAS_EM_MINUTOS"] = (
        df["HORAS_EM_MINUTOS"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    df["HORAS_EM_MINUTOS"] = pd.to_numeric(df["HORAS_EM_MINUTOS"], errors="coerce").fillna(0).round(3)
    df["MINUTO"] = pd.to_numeric(df["MINUTO"], errors="coerce").fillna(0).round(3)
    df["MES"] = df["MES"].astype(str).str.strip()
    df["ANO"] = df["ANO"].astype(str).str.strip()
    df["MES_ANO"] = df["MES"].str.zfill(2) + "/" + df["ANO"]

    save_dataframe(df)
    return df


def load_data() -> pd.DataFrame | None:
    """Lê dados do DuckDB. Retorna None se a tabela não existir."""
    if not table_exists():
        return None
    return load_dataframe()


def bar_chart_with_labels(data, x_col, y_col, horizontal=False):
    """Cria gráfico de barras Altair com valores visíveis nas barras."""
    data = data.copy()
    data[y_col] = data[y_col].round(3)

    if horizontal:
        bars = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{y_col}:Q", title="Horas"),
            y=alt.Y(f"{x_col}:N", sort="-x", title=None),
        )
        text = bars.mark_text(
            align="right", dx=-6, fontSize=14, fontWeight="bold", color="white"
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=".3f"),
        )
    else:
        bars = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{x_col}:N", sort="-y", title=None),
            y=alt.Y(f"{y_col}:Q", title="Horas"),
        )
        text = bars.mark_text(
            baseline="top", dy=6, fontSize=14, fontWeight="bold", color="white"
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=".3f"),
        )

    return (bars + text).properties(height=350)


def stacked_bar_chart(data, index_col, columns_col, value_col):
    """Cria gráfico de barras empilhadas com valores visíveis."""
    melted = data.reset_index().melt(id_vars=index_col, var_name=columns_col, value_name=value_col)
    melted = melted[melted[value_col] > 0]
    melted[value_col] = melted[value_col].round(3)

    bars = alt.Chart(melted).mark_bar().encode(
        x=alt.X(f"{index_col}:N", title=None),
        y=alt.Y(f"{value_col}:Q", title="Horas", stack="zero"),
        color=alt.Color(f"{columns_col}:N", title="Cliente"),
    )
    text = alt.Chart(melted).mark_text(
        fontSize=13, fontWeight="bold", color="white"
    ).encode(
        x=alt.X(f"{index_col}:N"),
        y=alt.Y(f"{value_col}:Q", stack="zero"),
        text=alt.Text(f"{value_col}:Q", format=".3f"),
    )

    return (bars + text).properties(height=400)


def render_painel(df: pd.DataFrame):
    """Renderiza a aba do painel com filtros e gráficos."""
    # --- Filtros na sidebar ---
    st.sidebar.header("Filtros")

    profissionais = sorted(df["PROFISSIONAL"].dropna().unique())
    clientes = sorted(df["CLIENTE_CONCATENADO"].dropna().unique())
    periodos = sorted(df["MES_ANO"].dropna().unique(), key=lambda x: (x.split("/")[1], x.split("/")[0]))

    sel_profissional = st.sidebar.multiselect("Profissional", profissionais, default=profissionais)
    sel_cliente = st.sidebar.multiselect("Cliente", clientes, default=clientes)
    sel_periodo = st.sidebar.multiselect("Período (Mês/Ano)", periodos, default=periodos)

    mask = (
        df["PROFISSIONAL"].isin(sel_profissional)
        & df["CLIENTE_CONCATENADO"].isin(sel_cliente)
        & df["MES_ANO"].isin(sel_periodo)
    )
    filtered = df[mask]

    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de registros", len(filtered))
    col2.metric("Horas totais", f"{filtered['HORAS_EM_MINUTOS'].sum():.3f}h")
    col3.metric("Profissionais", filtered["PROFISSIONAL"].nunique())

    st.divider()

    # --- Gráficos ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Horas por Profissional")
        hours_by_prof = (
            filtered.groupby("PROFISSIONAL")["HORAS_EM_MINUTOS"]
            .sum()
            .reset_index()
        )
        st.altair_chart(bar_chart_with_labels(hours_by_prof, "PROFISSIONAL", "HORAS_EM_MINUTOS", horizontal=True), width="stretch")

    with col_right:
        st.subheader("Horas por Cliente")
        hours_by_client = (
            filtered.groupby("CLIENTE_CONCATENADO")["HORAS_EM_MINUTOS"]
            .sum()
            .reset_index()
        )
        st.altair_chart(bar_chart_with_labels(hours_by_client, "CLIENTE_CONCATENADO", "HORAS_EM_MINUTOS", horizontal=True), width="stretch")

    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Horas por Período")
        hours_by_period = (
            filtered.groupby("MES_ANO")["HORAS_EM_MINUTOS"]
            .sum()
            .reset_index()
        )
        hours_by_period["_sort"] = hours_by_period["MES_ANO"].apply(
            lambda x: (x.split("/")[1], x.split("/")[0])
        )
        hours_by_period = hours_by_period.sort_values("_sort").drop(columns="_sort")
        sort_order = hours_by_period["MES_ANO"].tolist()

        bars = alt.Chart(hours_by_period).mark_bar().encode(
            x=alt.X("MES_ANO:N", sort=sort_order, title="Mês/Ano"),
            y=alt.Y("HORAS_EM_MINUTOS:Q", title="Horas"),
        )
        text = bars.mark_text(
            baseline="top", dy=6, fontSize=14, fontWeight="bold", color="white"
        ).encode(
            text=alt.Text("HORAS_EM_MINUTOS:Q", format=".3f"),
        )
        st.altair_chart((bars + text).properties(height=350), width="stretch")

    with col_right2:
        st.subheader("Horas por Área")
        hours_by_area = (
            filtered.groupby("AREA")["HORAS_EM_MINUTOS"]
            .sum()
            .reset_index()
        )
        st.altair_chart(bar_chart_with_labels(hours_by_area, "AREA", "HORAS_EM_MINUTOS", horizontal=True), width="stretch")

    st.subheader("Horas por Profissional × Cliente")
    pivot = (
        filtered.groupby(["PROFISSIONAL", "CLIENTE_CONCATENADO"])["HORAS_EM_MINUTOS"]
        .sum()
        .reset_index()
        .pivot_table(index="PROFISSIONAL", columns="CLIENTE_CONCATENADO", values="HORAS_EM_MINUTOS", fill_value=0)
    )
    st.altair_chart(stacked_bar_chart(pivot, "PROFISSIONAL", "CLIENTE_CONCATENADO", "HORAS_EM_MINUTOS"), width="stretch")

    # --- Alocação vs Realizado ---
    if alocacao_exists():
        st.subheader("Alocação vs Realizado")

        df_aloc = load_alocacao()
        df_aloc["HORAS_ALOCADAS"] = (df_aloc["MES_ATUAL"] / 100) * df_aloc["HORAS_MES"]

        # Criar chave concatenada para o join (mesma lógica do CLIENTE_CONCATENADO)
        df_aloc["CONCAT_KEY"] = df_aloc["PROFISSIONAL"] + df_aloc["CLIENTE"]

        # Filtrar alocação pelos mesmos filtros da sidebar
        aloc_mask = (
            df_aloc["PROFISSIONAL"].isin(sel_profissional)
            & df_aloc["CLIENTE"].isin(sel_cliente)
        )
        df_aloc = df_aloc[aloc_mask]

        # Horas gastas reais agrupadas por profissional + cliente
        horas_gastas = filtered.copy()
        horas_gastas["CONCAT_KEY"] = horas_gastas["PROFISSIONAL"] + horas_gastas["CLIENTE_CONCATENADO"]
        horas_gastas = (
            horas_gastas.groupby("CONCAT_KEY")["HORAS_EM_MINUTOS"]
            .sum()
            .reset_index()
            .rename(columns={"HORAS_EM_MINUTOS": "HORAS_GASTAS"})
        )

        # Juntar alocação com realizado pela chave concatenada
        comparativo = df_aloc.merge(
            horas_gastas,
            on="CONCAT_KEY",
            how="left",
        )
        comparativo["HORAS_GASTAS"] = comparativo["HORAS_GASTAS"].fillna(0).round(3)
        comparativo["HORAS_RESTANTES"] = (comparativo["HORAS_ALOCADAS"] - comparativo["HORAS_GASTAS"]).round(3)
        comparativo["HORAS_RESTANTES"] = comparativo["HORAS_RESTANTES"].clip(lower=0)
        comparativo["LABEL"] = comparativo["PROFISSIONAL"] + " / " + comparativo["CLIENTE"]

        # Preparar dados para gráfico empilhado
        chart_data = comparativo[["LABEL", "HORAS_GASTAS", "HORAS_RESTANTES"]].melt(
            id_vars="LABEL", var_name="STATUS", value_name="HORAS"
        )
        chart_data["HORAS"] = chart_data["HORAS"].round(3)
        chart_data["STATUS"] = chart_data["STATUS"].replace({
            "HORAS_GASTAS": "Gastas",
            "HORAS_RESTANTES": "Restantes",
        })

        color_scale = alt.Scale(
            domain=["Gastas", "Restantes"],
            range=["#4c78a8", "#e45756"],
        )

        bars = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("HORAS:Q", title="Horas", stack="zero"),
            y=alt.Y("LABEL:N", sort="-x", title=None),
            color=alt.Color("STATUS:N", scale=color_scale, title="Status"),
        )
        text = alt.Chart(chart_data).mark_text(
            align="center", fontSize=13, fontWeight="bold", color="white"
        ).encode(
            x=alt.X("HORAS:Q", stack="zero"),
            y=alt.Y("LABEL:N", sort="-x"),
            text=alt.Text("HORAS:Q", format=".1f"),
            opacity=alt.condition(alt.datum.HORAS > 0, alt.value(1), alt.value(0)),
        )

        chart_height = max(350, len(comparativo) * 35)
        st.altair_chart((bars + text).properties(height=chart_height), width="stretch")

        st.dataframe(
            comparativo[["PROFISSIONAL", "CLIENTE", "MES_ATUAL", "HORAS_MES", "HORAS_ALOCADAS", "HORAS_GASTAS", "HORAS_RESTANTES"]],
            width="stretch",
        )

    st.subheader("Dados filtrados")
    st.dataframe(filtered, width="stretch")


def render_atualizacao():
    """Renderiza a aba de atualização de dados."""
    # --- Seção: Horas (Google Sheets) ---
    st.subheader("Dados de Horas (Google Sheets)")
    last_update = get_last_update()
    has_data = table_exists()

    if has_data:
        st.info(f"Ultima atualização: **{last_update}**")
    else:
        st.warning("Nenhum dado encontrado. Faça a primeira carga abaixo.")

    if st.button("Atualizar dados do Google Sheets", type="primary"):
        with st.spinner("Buscando dados do Google Sheets..."):
            df = fetch_and_store()
        st.success(f"Dados atualizados com sucesso. {len(df)} registros carregados.")
        st.rerun()

    st.divider()

    # --- Seção: Alocação (CSV) ---
    st.subheader("Dados de Alocação (CSV)")

    if alocacao_exists():
        df_aloc = load_alocacao()
        st.info(f"Alocação carregada com **{len(df_aloc)}** registros.")
        st.dataframe(df_aloc, width="stretch")
    else:
        st.warning("Nenhuma alocação carregada.")

    uploaded = st.file_uploader("Enviar CSV de alocação", type=["csv"])
    if uploaded is not None:
        try:
            df_csv = pd.read_csv(uploaded, sep=None, engine="python")
            st.write("Preview dos dados:")
            st.dataframe(df_csv.head(10), width="stretch")
            if st.button("Confirmar upload de alocação", type="primary"):
                # Converter colunas numéricas
                for col in ["MES_ANTERIOR", "MES_ATUAL", "PROXIMO_MES", "HORAS_TOTAIS", "HORAS_MES"]:
                    if col in df_csv.columns:
                        df_csv[col] = pd.to_numeric(df_csv[col], errors="coerce").fillna(0)
                save_alocacao(df_csv)
                st.success(f"Alocação atualizada com sucesso. {len(df_csv)} registros carregados.")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler CSV: {e}")


def main():
    st.set_page_config(page_title="Controle de Horas", layout="wide")
    st.title("Controle de Horas")

    tab_painel, tab_atualizar = st.tabs(["Painel", "Atualização de Dados"])

    with tab_atualizar:
        render_atualizacao()

    with tab_painel:
        df = load_data()
        if df is None:
            st.warning("Nenhum dado disponível. Vá na aba **Atualização de Dados** para carregar.")
        else:
            render_painel(df)


if __name__ == "__main__":
    main()
