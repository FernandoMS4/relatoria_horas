import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "modules"))

import streamlit as st
import pandas as pd
import altair as alt
from modules.gs_integrations import GSGoldenBagres
from modules.data_store import (
    table_exists, save_dataframe, load_dataframe, get_last_update,
    alocacao_exists, save_alocacao, load_alocacao,
    list_tables, load_table,
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
    df["HORAS_EM_MINUTOS"] = pd.to_numeric(df["HORAS_EM_MINUTOS"], errors="coerce").fillna(0).round(1)
    df["MINUTO"] = pd.to_numeric(df["MINUTO"], errors="coerce").fillna(0).round(1)
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
    data[y_col] = data[y_col].round(1)

    if horizontal:
        bars = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{y_col}:Q", title="Horas"),
            y=alt.Y(f"{x_col}:N", sort="-x", title=None),
        )
        text = bars.mark_text(
            align="right", fontSize=14, fontWeight="bold", color="white"
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=".1f"),
        )
    else:
        bars = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{x_col}:N", sort="-y", title=None),
            y=alt.Y(f"{y_col}:Q", title="Horas"),
        )
        text = bars.mark_text(
            baseline="top", dy=6, fontSize=14, fontWeight="bold", color="white"
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=".1f"),
        )

    return (bars + text).properties(height=350)


def stacked_bar_chart(data, index_col, columns_col, value_col):
    """Cria gráfico de barras empilhadas com valores visíveis."""
    melted = data.reset_index().melt(id_vars=index_col, var_name=columns_col, value_name=value_col)
    melted = melted[melted[value_col] > 0]
    melted[value_col] = melted[value_col].round(1)

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
        text=alt.Text(f"{value_col}:Q", format=".1f"),
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
            text=alt.Text("HORAS_EM_MINUTOS:Q", format=".1f"),
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
        comparativo["HORAS_GASTAS"] = comparativo["HORAS_GASTAS"].fillna(0).round(1)
        comparativo["HORAS_RESTANTES"] = (comparativo["HORAS_ALOCADAS"] - comparativo["HORAS_GASTAS"]).round(1)
        comparativo["HORAS_RESTANTES"] = comparativo["HORAS_RESTANTES"].clip(lower=0)
        comparativo["LABEL"] = comparativo["PROFISSIONAL"] + " / " + comparativo["CLIENTE"]

        # Preparar dados para gráfico empilhado
        chart_data = comparativo[["LABEL", "HORAS_GASTAS", "HORAS_RESTANTES"]].melt(
            id_vars="LABEL", var_name="STATUS", value_name="HORAS"
        )
        chart_data["HORAS"] = chart_data["HORAS"].round(1)
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


def _fmt(value: float) -> str:
    """Formata número no padrão brasileiro: 1.234,5"""
    inteiro = int(value)
    decimal = f"{value:.1f}".split(".")[1]
    parte_inteira = f"{inteiro:,}".replace(",", ".")
    return f"{parte_inteira},{decimal}"


def _bar_row(label: str, horas: float, max_horas: float) -> str:
    pct = (horas / max_horas * 100) if max_horas > 0 else 0
    return (
        f"<tr>"
        f'<td>{label}</td>'
        f'<td class="text-right">{_fmt(horas)}</td>'
        f'<td><div class="bar-cell">'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>'
        f'<span class="bar-value">{pct:.0f}%</span>'
        f'</div></td></tr>'
    )


def gerar_relatorio_html(df: pd.DataFrame) -> str:
    """Gera HTML do relatório com dados reais."""
    hoje = datetime.now().strftime("%d/%m/%Y")
    periodos = sorted(df["MES_ANO"].dropna().unique(), key=lambda x: (x.split("/")[1], x.split("/")[0]))
    periodo_str = f"{periodos[0]} – {periodos[-1]}" if periodos else "–"

    total_registros = len(df)
    horas_totais = df["HORAS_EM_MINUTOS"].sum()
    n_profissionais = df["PROFISSIONAL"].nunique()

    # Horas por profissional
    h_prof = df.groupby("PROFISSIONAL")["HORAS_EM_MINUTOS"].sum().sort_values(ascending=False)
    max_prof = h_prof.max() if len(h_prof) > 0 else 1
    rows_prof = "".join(_bar_row(nome, horas, max_prof) for nome, horas in h_prof.items())
    total_prof = h_prof.sum()

    # Horas por cliente
    h_cli = df.groupby("CLIENTE_CONCATENADO")["HORAS_EM_MINUTOS"].sum().sort_values(ascending=False)
    max_cli = h_cli.max() if len(h_cli) > 0 else 1
    rows_cli = "".join(_bar_row(nome, horas, max_cli) for nome, horas in h_cli.items())
    total_cli = h_cli.sum()

    # Alocação vs Realizado
    secao_alocacao = ""
    kpi_restantes = ""
    if alocacao_exists():
        df_aloc = load_alocacao()
        df_aloc["HORAS_ALOCADAS"] = (df_aloc["MES_ATUAL"] / 100) * df_aloc["HORAS_MES"]
        df_aloc["CONCAT_KEY"] = df_aloc["PROFISSIONAL"] + df_aloc["CLIENTE"]

        horas_gastas = df.copy()
        horas_gastas["CONCAT_KEY"] = horas_gastas["PROFISSIONAL"] + horas_gastas["CLIENTE_CONCATENADO"]
        horas_gastas = (
            horas_gastas.groupby("CONCAT_KEY")["HORAS_EM_MINUTOS"]
            .sum().reset_index().rename(columns={"HORAS_EM_MINUTOS": "HORAS_GASTAS"})
        )
        comp = df_aloc.merge(horas_gastas, on="CONCAT_KEY", how="left")
        comp["HORAS_GASTAS"] = comp["HORAS_GASTAS"].fillna(0).round(1)
        comp["HORAS_RESTANTES"] = (comp["HORAS_ALOCADAS"] - comp["HORAS_GASTAS"]).round(1)

        total_restantes = comp["HORAS_RESTANTES"].sum()
        kpi_restantes = f'''
    <div class="kpi accent-danger">
      <div class="label">Horas Restantes (Alocação)</div>
      <div class="value">{_fmt(total_restantes)}h</div>
    </div>'''

        rows_aloc = ""
        for _, r in comp.iterrows():
            pct_usado = (r["HORAS_GASTAS"] / r["HORAS_ALOCADAS"] * 100) if r["HORAS_ALOCADAS"] > 0 else 0
            if pct_usado > 100:
                status_cls, status_txt = "status-over", "Excedido"
            elif pct_usado >= 90:
                status_cls, status_txt = "status-warn", "Atenção"
            else:
                status_cls, status_txt = "status-ok", "No prazo"
            rows_aloc += (
                f'<tr><td>{r["PROFISSIONAL"]}</td><td>{r["CLIENTE"]}</td>'
                f'<td class="text-right">{_fmt(r["HORAS_ALOCADAS"])}</td>'
                f'<td class="text-right">{_fmt(r["HORAS_GASTAS"])}</td>'
                f'<td class="text-right">{_fmt(r["HORAS_RESTANTES"])}</td>'
                f'<td class="{status_cls}">{status_txt}</td></tr>'
            )
        secao_alocacao = f'''
  <section>
    <h2>Alocação vs Realizado</h2>
    <table>
      <thead><tr><th>Profissional</th><th>Cliente</th><th>Alocadas</th><th>Gastas</th><th>Restantes</th><th>Status</th></tr></thead>
      <tbody>{rows_aloc}</tbody>
    </table>
  </section>'''

    TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
    with open(os.path.join(TEMPLATE_DIR, "relatorio.html"), encoding="utf-8") as f:
        css = f.read().split("<style>")[1].split("</style>")[0]

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório – Controle de Horas</title>
  <style>{css}</style>
</head>
<body>
<div class="page">
  <header>
    <div>
      <h1>Controle de Horas</h1>
      <span style="color: var(--text-muted); font-size: 0.9rem;">Relatório de acompanhamento</span>
    </div>
    <div class="meta">
      <div>Período: <strong>{periodo_str}</strong></div>
      <div>Gerado em: <strong>{hoje}</strong></div>
    </div>
  </header>

  <div class="kpis">
    <div class="kpi">
      <div class="label">Total de Registros</div>
      <div class="value">{total_registros:,}</div>
    </div>
    <div class="kpi">
      <div class="label">Horas Totais</div>
      <div class="value">{_fmt(horas_totais)}h</div>
    </div>
    <div class="kpi">
      <div class="label">Profissionais</div>
      <div class="value">{n_profissionais}</div>
    </div>
    {kpi_restantes}
  </div>

  <section>
    <h2>Horas por Profissional</h2>
    <table>
      <thead><tr><th>Profissional</th><th>Horas</th><th style="width:40%">Distribuição</th></tr></thead>
      <tbody>{rows_prof}</tbody>
      <tfoot><tr><td>Total</td><td class="text-right">{_fmt(total_prof)}</td><td></td></tr></tfoot>
    </table>
  </section>

  <section>
    <h2>Horas por Cliente</h2>
    <table>
      <thead><tr><th>Cliente</th><th>Horas</th><th style="width:40%">Distribuição</th></tr></thead>
      <tbody>{rows_cli}</tbody>
      <tfoot><tr><td>Total</td><td class="text-right">{_fmt(total_cli)}</td><td></td></tr></tfoot>
    </table>
  </section>

  {secao_alocacao}

  <footer>
    Controle de Horas &middot; Relatório gerado automaticamente &middot; Golden Bagres ©
  </footer>
</div>
</body>
</html>'''


def render_relatorio():
    """Renderiza a aba de geração de relatório HTML."""
    df = load_data()
    if df is None:
        st.warning("Nenhum dado disponível. Carregue os dados primeiro na aba **Atualização de Dados**.")
        return

    st.subheader("Gerar Relatório HTML")

    # --- Filtros ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        periodos = sorted(
            df["MES_ANO"].dropna().unique(),
            key=lambda x: (x.split("/")[1], x.split("/")[0]),
        )
        sel_periodo = st.multiselect(
            "Período (Mês/Ano)",
            periodos,
            default=periodos,
            key="relatorio_periodo",
        )
    with col_f2:
        profissionais = sorted(df["PROFISSIONAL"].dropna().unique())
        sel_profissional = st.multiselect(
            "Profissional",
            profissionais,
            default=profissionais,
            key="relatorio_profissional",
        )
    filtered = df[df["MES_ANO"].isin(sel_periodo) & df["PROFISSIONAL"].isin(sel_profissional)]
    st.caption(f"**{len(filtered)}** registros com os filtros selecionados.")

    if st.button("Gerar relatório", type="primary"):
        html = gerar_relatorio_html(filtered)
        st.session_state["relatorio_html"] = html

    if "relatorio_html" in st.session_state:
        html = st.session_state["relatorio_html"]
        st.download_button(
            label="Baixar relatório HTML",
            data=html,
            file_name=f"relatorio_horas_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
        )
        st.divider()
        st.caption("Preview do relatório:")
        st.components.v1.html(html, height=800, scrolling=True)


def render_explorador():
    """Renderiza a aba do explorador de dados do DuckDB."""
    tables = list_tables()

    if not tables:
        st.warning("Nenhuma tabela encontrada no banco de dados.")
        return

    selected_table = st.selectbox("Selecione uma tabela", tables)

    if selected_table:
        df = load_table(selected_table)

        st.caption(f"**{len(df)}** registros | **{len(df.columns)}** colunas")

        # --- Filtros por coluna ---
        with st.expander("Filtros", expanded=False):
            filters = {}
            filter_cols = st.multiselect(
                "Colunas para filtrar",
                df.columns.tolist(),
            )
            for col in filter_cols:
                if df[col].dtype in ("object", "string"):
                    unique_vals = sorted(df[col].dropna().unique().tolist())
                    selected = st.multiselect(
                        f"{col}",
                        unique_vals,
                        default=unique_vals,
                        key=f"filter_{col}",
                    )
                    filters[col] = selected
                else:
                    col_min = float(df[col].min())
                    col_max = float(df[col].max())
                    if col_min == col_max:
                        st.text(f"{col}: valor único = {col_min}")
                    else:
                        vmin, vmax = st.slider(
                            f"{col}",
                            min_value=col_min,
                            max_value=col_max,
                            value=(col_min, col_max),
                            key=f"filter_{col}",
                        )
                        filters[col] = (vmin, vmax)

            # Aplicar filtros
            mask = pd.Series(True, index=df.index)
            for col, val in filters.items():
                if isinstance(val, list):
                    mask &= df[col].isin(val)
                else:
                    vmin, vmax = val
                    mask &= df[col].between(vmin, vmax)
            df = df[mask]

        st.caption(f"Exibindo **{len(df)}** registros após filtros")
        st.dataframe(df, use_container_width=True)


def main():
    st.set_page_config(page_title="Controle de Horas", layout="wide")
    st.title("Controle de Horas")

    tab_painel, tab_atualizar, tab_explorador, tab_relatorio = st.tabs(
        ["Painel", "Atualização de Dados", "Explorador de Dados", "Relatório"]
    )

    with tab_atualizar:
        render_atualizacao()

    with tab_painel:
        df = load_data()
        if df is None:
            st.warning("Nenhum dado disponível. Vá na aba **Atualização de Dados** para carregar.")
        else:
            render_painel(df)

    with tab_explorador:
        render_explorador()

    with tab_relatorio:
        render_relatorio()


if __name__ == "__main__":
    main()
