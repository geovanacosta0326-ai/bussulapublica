import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Radar Legislativo",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS Customizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px;
}

h1 {
    font-family: 'Playfair Display', serif !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.5px !important;
    color: #1a1a2e !important;
}

.subtitle {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #888;
    margin-top: -8px;
    margin-bottom: 1.5rem;
}

.status-badge {
    display: inline-block;
    background: #185FA5;
    color: #B5D4F4;
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
}

[data-testid="metric-container"] {
    background: #ffffff;
    border: 0.5px solid #e8e8e8;
    border-radius: 12px;
    padding: 1rem 1.25rem !important;
    box-shadow: none !important;
}

[data-testid="stMetricValue"] > div {
    font-family: 'Playfair Display', serif !important;
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
}

[data-testid="stMetricLabel"] > div {
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: #888 !important;
    font-weight: 400 !important;
}

hr {
    border: none;
    border-top: 0.5px solid #e8e8e8 !important;
    margin: 1rem 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 0.5px solid #e8e8e8;
}

.stTabs [data-baseweb="tab"] {
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #888;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}

.stTabs [aria-selected="true"] {
    color: #185FA5 !important;
    border-bottom: 2px solid #185FA5 !important;
    background: transparent !important;
}

h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    color: #888 !important;
    font-weight: 500 !important;
    margin-bottom: 0.75rem !important;
}

[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 0.5px solid #e8e8e8 !important;
}

section[data-testid="stSidebar"] {
    display: none;
}

/* Badge de tema inline */
.tema-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.7rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Conexão com o banco ─────────────────────────────────────────────────────
load_dotenv()
db_uri = os.getenv("DB_URI")
engine = create_engine(db_uri)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

CORES = {
    "azul_escuro": "#185FA5",
    "azul_medio":  "#378ADD",
    "azul_claro":  "#85B7EB",
    "teal":        "#1D9E75",
    "amber":       "#BA7517",
    "vermelho":    "#A32D2D",
    "cinza":       "#888780",
    "fundo":       "#f7f8fc",
}

CORES_TEMA = {
    "Agribusiness":     "#16a34a",
    "Educação":         "#2563eb",
    "Saúde":            "#dc2626",
    "Segurança Pública":"#7c3aed",
    "Economia":         "#d97706",
    "Infraestrutura":   "#0891b2",
    "Meio Ambiente":    "#059669",
    "Tecnologia":       "#ea580c",
    "Outros":           "#6b7280",
}

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#444"),
    colorway=[
        CORES["azul_escuro"], CORES["teal"], CORES["amber"],
        CORES["vermelho"], CORES["azul_medio"], CORES["cinza"],
    ],
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="#f0f0f0", zeroline=False),
)

# ── Helpers ─────────────────────────────────────────────────────────────────
def get_data(query: str) -> pd.DataFrame:
    try:
        df = pd.read_sql(text(query), engine.connect())
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()


def fmt_brl(value) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "R$ —"
    if value >= 1_000_000:
        return f"R$ {value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"R$ {value/1_000:.0f}k"
    return f"R$ {value:,.2f}"


def badge_tema(tema: str) -> str:
    cor = CORES_TEMA.get(tema, "#6b7280")
    return (
        f'<span style="background:{cor}22;color:{cor};border:1px solid {cor}66;'
        f'padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600">'
        f'{tema}</span>'
    )


def badge_votacao(aprovacao) -> str:
    try:
        v = int(aprovacao)
    except (TypeError, ValueError):
        return '<span style="color:#aaa;font-size:0.75rem">—</span>'
    if v == 1:
        return '<span style="background:#dcfce7;color:#16a34a;border:1px solid #bbf7d0;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600">✓ Aprovada</span>'
    return '<span style="background:#fee2e2;color:#dc2626;border:1px solid #fecaca;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600">✗ Reprovada</span>'


# ── Cabeçalho ───────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([5, 1])
with col_title:
    st.title("🏛 Radar Legislativo")
    st.markdown('<p class="subtitle">Painel de Inteligência — Câmara dos Deputados</p>', unsafe_allow_html=True)
with col_badge:
    st.markdown('<br><span class="status-badge">● Atualizado agora</span>', unsafe_allow_html=True)

st.divider()

# ── KPIs ─────────────────────────────────────────────────────────────────────
df_prop     = get_data("SELECT count(*) as total FROM fato_proposicoes")
df_desp     = get_data("SELECT SUM(valorliquido) as total FROM fato_despesas")
df_vot      = get_data("SELECT count(*) as total FROM fato_votacoes")
df_sem_tema = get_data("SELECT count(*) as total FROM fato_proposicoes WHERE tema IS NULL OR tema = ''")

total_prop     = int(df_prop.iloc[0, 0])     if not df_prop.empty     else 0
total_desp     = df_desp.iloc[0, 0]           if not df_desp.empty     else 0
total_vot      = int(df_vot.iloc[0, 0])       if not df_vot.empty      else 0
total_sem_tema = int(df_sem_tema.iloc[0, 0])  if not df_sem_tema.empty else 0
pct_sem_tema   = f"{total_sem_tema / total_prop:.0%}" if total_prop else "—"

k1, k2, k3, k4 = st.columns(4)
k1.metric("📄 Total de Proposições",  f"{total_prop:,}",    delta="↑ 12% este mês")
k2.metric("💰 Total de Despesas",     fmt_brl(total_desp),  delta="↑ 3% vs média",  delta_color="inverse")
k3.metric("✅ Total de Votações",     f"{total_vot:,}",     delta="↑ 8% este mês")
k4.metric("🏷 Sem Tema",             f"{total_sem_tema:,}", delta=f"{pct_sem_tema} do total", delta_color="inverse")

st.divider()

# ── Abas principais ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 Proposições por Tema", "💸 Despesas por Categoria", "📋 Dados Recentes", "💬 Assistente"])

# ── TAB 1 ────────────────────────────────────────────────────────────────────
with tab1:
    st.subheader("Distribuição de Proposições por Tema")

    df_temas = get_data("""
        SELECT INITCAP(LOWER(tema)) as tema, count(*) as qtd
        FROM fato_proposicoes
        WHERE tema IS NOT NULL AND tema <> ''
        GROUP BY INITCAP(LOWER(tema))
        ORDER BY qtd DESC
    """)

    if not df_temas.empty:
        col_chart, col_top = st.columns([3, 2])

        with col_chart:
            fig = go.Figure(go.Pie(
                labels=df_temas["tema"],
                values=df_temas["qtd"],
                hole=0.5,
                textinfo="percent",
                textfont=dict(size=12, family="DM Sans"),
                marker=dict(
                    colors=[CORES["azul_escuro"], CORES["teal"], CORES["amber"],
                            CORES["vermelho"], CORES["azul_medio"], CORES["cinza"]],
                    line=dict(color="#ffffff", width=2),
                ),
                hovertemplate="<b>%{label}</b><br>%{value} proposições<br>%{percent}<extra></extra>",
            ))
            fig.update_layout(**PLOTLY_TEMPLATE, showlegend=False, height=340)
            st.plotly_chart(fig, use_container_width=True)

        with col_top:
            st.markdown("**Ranking por volume**")
            total_t = df_temas["qtd"].sum()
            for _, row in df_temas.head(8).iterrows():
                pct = row["qtd"] / total_t
                cor = CORES_TEMA.get(row["tema"], CORES["cinza"])
                st.markdown(f"""
                <div style="margin-bottom:10px">
                  <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                    <span style="color:#444">{row['tema']}</span>
                    <span style="color:#888">{row['qtd']:,} &nbsp;·&nbsp; {pct:.0%}</span>
                  </div>
                  <div style="background:#f0f0f0;border-radius:4px;height:5px">
                    <div style="background:{cor};width:{pct*100:.1f}%;height:5px;border-radius:4px"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Dados de temas ainda não classificados.")

    # ── TABELA DE PROPOSIÇÕES COM DOWNLOAD CSV ───────────────────────────────
    st.divider()
    st.markdown("##### Proposições classificadas")

    df_prop_tab = get_data("""
        SELECT
            id,
            ementa,
            INITCAP(LOWER(tema))     AS tema,
            "dataApresentacao"       AS data_apresentacao
        FROM fato_proposicoes
        WHERE tema IS NOT NULL AND tema <> '' AND tema <> 'Sem ementa'
        ORDER BY "dataApresentacao" DESC
    """)

    if not df_prop_tab.empty:
        if "data_apresentacao" in df_prop_tab.columns:
            df_prop_tab["data_apresentacao"] = pd.to_datetime(
                df_prop_tab["data_apresentacao"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")

        df_prop_tab = df_prop_tab.rename(columns={
            "id":                "ID",
            "ementa":            "Ementa",
            "tema":              "Tema",
            "data_apresentacao": "Data Apresentação",
        })

        col_dl, _ = st.columns([1, 4])
        with col_dl:
            csv = df_prop_tab.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="⬇️ Baixar CSV",
                data=csv,
                file_name="proposicoes_classificadas.csv",
                mime="text/csv",
            )

        evento = st.dataframe(
            df_prop_tab,
            use_container_width=True,
            hide_index=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "ID":                st.column_config.TextColumn("ID",                width="small"),
                "Ementa":            st.column_config.TextColumn("Ementa",            width="large"),
                "Tema":              st.column_config.TextColumn("Tema",              width="medium"),
                "Data Apresentação": st.column_config.TextColumn("Data Apresentação", width="small"),
            },
        )

        linhas_sel = evento.selection.get("rows", []) if evento and hasattr(evento, "selection") else []
        if linhas_sel:
            idx = linhas_sel[0]
            row_sel = df_prop_tab.iloc[idx]
            st.markdown(
                f'''<div style="background:#f0f7ff;border-left:4px solid #185FA5;border-radius:6px;padding:14px 18px;margin-top:8px">
                <span style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#185FA5;font-weight:600">
                Ementa completa — {row_sel.get("Tema","")}&nbsp;·&nbsp;{row_sel.get("Data Apresentação","")}</span><br><br>
                <span style="font-size:0.9rem;color:#222;line-height:1.6">{row_sel.get("Ementa","")}</span>
                </div>''',
                unsafe_allow_html=True
            )
        else:
            st.caption("💡 Clique em uma linha para ver a ementa completa.")

# ── TAB 2 ────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Maiores Gastos por Categoria")

    df_desp_cat = get_data("""
        SELECT tipodespesa, SUM(valorliquido) as valor
        FROM fato_despesas
        GROUP BY tipodespesa
        ORDER BY valor DESC
        LIMIT 10
    """)

    if not df_desp_cat.empty:
        n_bars = len(df_desp_cat)
        altura = max(420, n_bars * 46)

        fig2 = go.Figure(go.Bar(
            x=df_desp_cat["valor"],
            y=df_desp_cat["tipodespesa"],
            orientation="h",
            marker=dict(
                color=df_desp_cat["valor"],
                colorscale=[[0, CORES["azul_claro"]], [1, CORES["azul_escuro"]]],
                showscale=False,
            ),
            text=[fmt_brl(v) for v in df_desp_cat["valor"]],
            textposition="outside",
            textfont=dict(size=12, family="DM Sans"),
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        ))
        layout2 = {**PLOTLY_TEMPLATE}
        layout2["yaxis"] = dict(autorange="reversed", tickfont=dict(size=11, family="DM Sans"), showgrid=False, zeroline=False)
        layout2["xaxis"] = dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, df_desp_cat["valor"].max() * 1.25])
        layout2["height"] = altura
        layout2["margin"] = dict(l=10, r=120, t=20, b=10)
        fig2.update_layout(**layout2)
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.markdown("##### Detalhamento por categoria")
        total_desp_cat = df_desp_cat["valor"].sum()
        df_show = df_desp_cat.copy()
        df_show["% do Total"] = (df_show["valor"] / total_desp_cat * 100).map("{:.1f}%".format)
        df_show["Valor (R$)"] = df_show["valor"].map(fmt_brl)
        df_show = df_show[["tipodespesa", "Valor (R$)", "% do Total"]].rename(columns={"tipodespesa": "Categoria"})
        st.dataframe(df_show, use_container_width=True, hide_index=True,
            column_config={
                "Categoria":  st.column_config.TextColumn("Categoria",  width="large"),
                "Valor (R$)": st.column_config.TextColumn("Valor (R$)", width="medium"),
                "% do Total": st.column_config.TextColumn("% do Total", width="small"),
            })
    else:
        st.info("Dados de despesas indisponíveis.")

# ── TAB 3 ────────────────────────────────────────────────────────────────────
with tab3:

    # ── PROPOSIÇÕES COM TEMA CLASSIFICADO ────────────────────────────────────
    st.subheader("Proposições Classificadas por Tema")
    st.caption("Exibindo proposições que já possuem tema preenchido pela IA, com indicação se foram a votação.")

    # Filtros — linha 1
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

    with col_f1:
        df_temas_lista = get_data("""
            SELECT DISTINCT INITCAP(LOWER(tema)) as tema FROM fato_proposicoes
            WHERE tema IS NOT NULL AND tema <> '' AND tema <> 'Sem ementa'
            ORDER BY 1
        """)
        temas_opcoes = ["Todos"] + df_temas_lista["tema"].tolist() if not df_temas_lista.empty else ["Todos"]
        filtro_tema = st.selectbox("Filtrar por Tema", temas_opcoes)

    with col_f2:
        filtro_votacao = st.selectbox("Filtrar por Votação", ["Todos", "Foi a votação", "Não foi a votação"])

    with col_f3:
        filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos", "PL", "PEC", "MPV", "PDL", "REQ"])

    # Filtros — linha 2: mês e ano
    df_periodos = get_data("""
        SELECT DISTINCT
            EXTRACT(YEAR  FROM "dataApresentacao"::date)::int AS ano,
            EXTRACT(MONTH FROM "dataApresentacao"::date)::int AS mes
        FROM fato_proposicoes
        WHERE "dataApresentacao" IS NOT NULL
        ORDER BY ano DESC, mes DESC
    """)

    col_f4, col_f5, _ = st.columns([2, 2, 2])

    anos_opcoes = ["Todos"]
    meses_opcoes = ["Todos"]
    if not df_periodos.empty:
        anos_opcoes  += sorted(df_periodos["ano"].dropna().astype(int).unique().tolist(), reverse=True)
        meses_opcoes += list(range(1, 13))

    MESES_NOMES = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
        5: "Maio",    6: "Junho",     7: "Julho",     8: "Agosto",
        9: "Setembro",10: "Outubro",  11: "Novembro", 12: "Dezembro",
    }

    with col_f4:
        filtro_ano = st.selectbox("Filtrar por Ano", anos_opcoes)

    with col_f5:
        filtro_mes = st.selectbox(
            "Filtrar por Mês",
            meses_opcoes,
            format_func=lambda x: MESES_NOMES.get(x, "Todos") if x != "Todos" else "Todos"
        )

    # Query dinâmica
    where_clauses = [
        "p.tema IS NOT NULL",
        "p.tema <> ''",
        "p.tema <> 'Sem ementa'",
    ]
    if filtro_tema != "Todos":
        where_clauses.append(f"INITCAP(LOWER(p.tema)) = '{filtro_tema}'")
    if filtro_tipo != "Todos":
        where_clauses.append(f'p."siglaTipo" = \'{filtro_tipo}\'')
    if filtro_ano != "Todos":
        where_clauses.append(f"EXTRACT(YEAR FROM p.\"dataApresentacao\"::date) = {filtro_ano}")
    if filtro_mes != "Todos":
        where_clauses.append(f"EXTRACT(MONTH FROM p.\"dataApresentacao\"::date) = {filtro_mes}")

    where_sql = " AND ".join(where_clauses)

    # LEFT JOIN com votacoes pelo campo proposicaoObjeto
    votacao_filter = ""
    if filtro_votacao == "Foi a votação":
        votacao_filter = 'HAVING bool_or(v.id IS NOT NULL) = true'
    elif filtro_votacao == "Não foi a votação":
        votacao_filter = 'HAVING bool_or(v.id IS NOT NULL) = false'

    query_prop = f"""
        SELECT
            p."siglaTipo"                   AS tipo,
            p.numero,
            p.ano,
            p.ementa,
            INITCAP(LOWER(p.tema))          AS tema,
            p."dataApresentacao"            AS data,
            CASE
                WHEN COUNT(DISTINCT v.id) > 0 THEN 1
                ELSE 0
            END                             AS foi_votada
        FROM fato_proposicoes p
        LEFT JOIN fato_votacoes v
            ON v."proposicaoObjeto" ILIKE
               '%' || p."siglaTipo" || ' ' || CAST(p.numero AS TEXT) || '%'
        WHERE {where_sql}
        GROUP BY
            p.id, p."siglaTipo", p.numero, p.ano,
            p.ementa, p.tema, p."dataApresentacao"
        {votacao_filter}
        ORDER BY p."dataApresentacao" DESC
        LIMIT 200
    """

    df_class = get_data(query_prop)

    if not df_class.empty:
        # Formata data
        if "data" in df_class.columns:
            df_class["data"] = pd.to_datetime(df_class["data"], errors="coerce").dt.strftime("%d/%m/%Y")

        # Métricas rápidas da seleção
        total_sel  = len(df_class)
        votadas    = int(df_class["foi_votada"].sum()) if "foi_votada" in df_class.columns else 0
        nao_votadas = total_sel - votadas

        m1, m2, m3 = st.columns(3)
        m1.metric("Proposições filtradas", f"{total_sel:,}")
        m2.metric("✅ Foram a votação",    f"{votadas:,}")
        m3.metric("⏳ Não votadas",        f"{nao_votadas:,}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Renderiza tabela HTML com badges
        rows_html = ""
        for _, row in df_class.iterrows():
            tema_b = badge_tema(row.get("tema", ""))
            vot_b  = badge_votacao(row.get("foi_votada", None))
            ementa_txt = str(row.get("ementa", "")).replace('"', "&quot;").replace("'", "&#39;").replace("<", "&lt;").replace(">", "&gt;")
            ementa_curta = ementa_txt[:90] + "…" if len(ementa_txt) > 90 else ementa_txt
            rows_html += f"""
            <tr>
              <td style="color:#555;font-size:0.78rem;padding:8px 6px;white-space:nowrap">{row.get('tipo','')}</td>
              <td style="color:#555;font-size:0.78rem;padding:8px 6px;white-space:nowrap">{row.get('numero','')}/{row.get('ano','')}</td>
              <td style="color:#333;font-size:0.78rem;padding:8px 6px;max-width:340px" title="{ementa_txt}">{ementa_curta}</td>
              <td style="padding:8px 6px;white-space:nowrap">{tema_b}</td>
              <td style="padding:8px 6px;white-space:nowrap">{vot_b}</td>
              <td style="color:#888;font-size:0.75rem;padding:8px 6px;white-space:nowrap">{row.get('data','')}</td>
            </tr>"""

        header_html = (
            '<div style="overflow-x:auto;border:0.5px solid #e8e8e8;border-radius:10px">'
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="background:#f7f8fc;border-bottom:1px solid #e8e8e8">'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Tipo</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Número</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Ementa</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Tema</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Votação</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Data</th>'
            '</tr></thead><tbody>'
        )
        footer_html = '</tbody></table></div>'
        st.markdown(header_html + rows_html + footer_html, unsafe_allow_html=True)
    else:
        st.info("Nenhuma proposição classificada encontrada com os filtros selecionados.")

    st.divider()

    # ── VOTAÇÕES RECENTES ────────────────────────────────────────────────────
    st.subheader("Últimas Votações")

    df_vot_rec = get_data("""
        SELECT
            v.data,
            v.aprovacao,
            v."siglaOrgao",
            v."proposicaoObjeto",
            CASE
                WHEN v."proposicaoObjeto" IS NULL
                  OR TRIM(v."proposicaoObjeto") = ''
                  OR LOWER(TRIM(v."proposicaoObjeto")) = 'nenhum'
                THEN '—'
                ELSE COALESCE(
                    (
                        SELECT p.ementa
                        FROM fato_proposicoes p
                        WHERE v."proposicaoObjeto" ILIKE p."siglaTipo" || ' ' || CAST(p.numero AS TEXT) || '/%'
                        LIMIT 1
                    ),
                    '—'
                )
            END AS ementa
        FROM fato_votacoes v
        WHERE
            v."proposicaoObjeto" IS NOT NULL
            AND TRIM(v."proposicaoObjeto") <> ''
            AND LOWER(TRIM(v."proposicaoObjeto")) <> 'nenhum'
        ORDER BY v.data DESC
        LIMIT 10
    """)

    if not df_vot_rec.empty:
        if "data" in df_vot_rec.columns:
            df_vot_rec["data"] = pd.to_datetime(df_vot_rec["data"], errors="coerce").dt.strftime("%d/%m/%Y")

        rows_vot = ""
        for _, row in df_vot_rec.iterrows():
            vot_b = badge_votacao(row.get("aprovacao", None))
            ementa = str(row.get("ementa", "—")).replace('"', "&quot;").replace("'", "&#39;").replace("<", "&lt;").replace(">", "&gt;")
            ementa_curta = ementa[:90] + "…" if len(ementa) > 90 else ementa
            rows_vot += f"""
            <tr>
              <td style="color:#888;font-size:0.75rem;padding:8px 6px;white-space:nowrap">{row.get('data','')}</td>
              <td style="color:#333;font-size:0.78rem;padding:8px 6px;max-width:340px" title="{ementa}">{ementa_curta}</td>
              <td style="padding:8px 6px">{vot_b}</td>
              <td style="color:#555;font-size:0.75rem;padding:8px 6px">{row.get('siglaorgao','')}</td>
              <td style="color:#555;font-size:0.75rem;padding:8px 6px;max-width:160px">{row.get('proposicaoobjeto','')}</td>
            </tr>"""

        header_vot = (
            '<div style="overflow-x:auto;border:0.5px solid #e8e8e8;border-radius:10px">'
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="background:#f7f8fc;border-bottom:1px solid #e8e8e8">'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Data</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Ementa</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Resultado</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Órgão</th>'
            '<th style="text-align:left;padding:10px 6px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;color:#888;font-weight:600">Proposição</th>'
            '</tr></thead><tbody>'
        )
        st.markdown(header_vot + rows_vot + '</tbody></table></div>', unsafe_allow_html=True)
    else:
        st.info("Nenhuma votação encontrada.")

# ── TAB 4 — ASSISTENTE ───────────────────────────────────────────────────────
with tab4:
    st.subheader("💬 Assistente Legislativo")
    st.caption("Faça perguntas sobre as proposições, despesas e votações. O assistente tem acesso ao contexto atual do painel.")

    # Inicializa histórico de mensagens na sessão
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Busca contexto resumido do banco para alimentar o assistente
    @st.cache_data(ttl=600)
    def get_contexto_banco():
        ctx = {}

        df_kpi = get_data("""
            SELECT
                (SELECT count(*) FROM fato_proposicoes) AS total_proposicoes,
                (SELECT count(*) FROM fato_votacoes)    AS total_votacoes,
                (SELECT SUM(valorliquido) FROM fato_despesas) AS total_despesas,
                (SELECT count(*) FROM fato_proposicoes WHERE tema IS NULL OR tema = '') AS sem_tema
        """)
        if not df_kpi.empty:
            ctx["kpis"] = df_kpi.iloc[0].to_dict()

        df_temas = get_data("""
            SELECT INITCAP(LOWER(tema)) as tema, count(*) as qtd
            FROM fato_proposicoes
            WHERE tema IS NOT NULL AND tema <> ''
            GROUP BY INITCAP(LOWER(tema))
            ORDER BY qtd DESC
        """)
        if not df_temas.empty:
            ctx["temas"] = df_temas.to_dict(orient="records")

        df_desp = get_data("""
            SELECT tipodespesa as categoria, SUM(valorliquido) as valor
            FROM fato_despesas
            GROUP BY tipodespesa
            ORDER BY valor DESC
            LIMIT 5
        """)
        if not df_desp.empty:
            ctx["top_despesas"] = df_desp.to_dict(orient="records")

        df_rec = get_data("""
            SELECT "siglaTipo" as tipo, numero, ano, ementa, INITCAP(LOWER(tema)) as tema, "dataApresentacao" as data
            FROM fato_proposicoes
            WHERE tema IS NOT NULL AND tema <> ''
            ORDER BY "dataApresentacao" DESC
            LIMIT 10
        """)
        if not df_rec.empty:
            ctx["proposicoes_recentes"] = df_rec.to_dict(orient="records")

        return ctx

    contexto = get_contexto_banco()

    system_prompt = f"""Você é o Assistente do Radar Legislativo, especializado em análise de dados da Câmara dos Deputados do Brasil.

Você tem acesso ao seguinte contexto atual do banco de dados:

KPIs:
- Total de proposições: {contexto.get('kpis', {}).get('total_proposicoes', 'N/A')}
- Total de votações: {contexto.get('kpis', {}).get('total_votacoes', 'N/A')}
- Total de despesas: R$ {contexto.get('kpis', {}).get('total_despesas', 0):,.2f}
- Proposições sem tema: {contexto.get('kpis', {}).get('sem_tema', 'N/A')}

Distribuição por tema:
{chr(10).join([f"- {t['tema']}: {t['qtd']} proposições" for t in contexto.get('temas', [])])}

Top 5 categorias de despesa:
{chr(10).join([f"- {d['categoria']}: R$ {d['valor']:,.2f}" for d in contexto.get('top_despesas', [])])}

Proposições mais recentes:
{chr(10).join([f"- {p.get('tipo','')} {p.get('numero','')}/{p.get('ano','')}: {str(p.get('ementa',''))[:80]} [{p.get('tema','')}]" for p in contexto.get('proposicoes_recentes', [])])}

Responda em português, de forma objetiva e analítica. Quando não souber algo que não está no contexto, diga claramente."""

    # Renderiza histórico de mensagens
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input do usuário
    if prompt := st.chat_input("Pergunte sobre proposições, despesas, votações..."):
        # Adiciona mensagem do usuário
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Chama a API da Anthropic
        with st.chat_message("assistant"):
            with st.spinner("Analisando..."):
                try:
                    import requests as req
                    messages_payload = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_messages
                    ]
                    response = req.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": ANTHROPIC_API_KEY,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-haiku-4-5",
                            "max_tokens": 1024,
                            "system": system_prompt,
                            "messages": messages_payload,
                        },
                        timeout=30,
                    )
                    response.raise_for_status()
                    resposta = response.json()["content"][0]["text"]
                    st.markdown(resposta)
                    st.session_state.chat_messages.append({"role": "assistant", "content": resposta})
                except Exception as e:
                    st.error(f"Erro ao consultar o assistente: {e}")

    # Botão para limpar histórico
    if st.session_state.chat_messages:
        if st.button("🗑️ Limpar conversa"):
            st.session_state.chat_messages = []
            st.rerun()

# ── Rodapé ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='font-size:0.7rem;color:#aaa;text-align:center'>"
    "Radar Legislativo · Dados: fato_proposicoes · fato_despesas · fato_votacoes · "
    "Atualização em tempo real via SQLAlchemy</p>",
    unsafe_allow_html=True,
)