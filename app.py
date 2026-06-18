import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import database as db
import parser as ps
import exports as ex

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gestão de Disputas Shopee",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_db()

# ─────────────────────────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background: #f8f9fa; }
    [data-testid="stSidebar"] { background: #ee4d2d; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stRadio label { color: white !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.3) !important; }
    
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #ee4d2d;
        margin-bottom: 10px;
    }
    .metric-card.green  { border-left-color: #28a745; }
    .metric-card.red    { border-left-color: #dc3545; }
    .metric-card.yellow { border-left-color: #ffc107; }
    .metric-card.blue   { border-left-color: #007bff; }
    .metric-card.orange { border-left-color: #fd7e14; }
    
    .metric-value { font-size: 28px; font-weight: 700; color: #212529; }
    .metric-label { font-size: 13px; color: #6c757d; margin-top: 4px; }
    
    .alert-box {
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 14px;
    }
    .alert-danger  { background: #f8d7da; border-left: 4px solid #dc3545; color: #721c24; }
    .alert-warning { background: #fff3cd; border-left: 4px solid #ffc107; color: #856404; }
    .alert-info    { background: #d1ecf1; border-left: 4px solid #17a2b8; color: #0c5460; }
    
    .page-title { font-size: 26px; font-weight: 700; color: #ee4d2d; margin-bottom: 4px; }
    .page-sub   { font-size: 14px; color: #6c757d; margin-bottom: 24px; }
    
    div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    .stTabs [data-baseweb="tab"] { font-size: 14px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def card(label, value, color="", icon=""):
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-value">{icon} {value}</div>
        <div class="metric-label">{label}</div>
    </div>""", unsafe_allow_html=True)


def alert(msg, tipo="warning"):
    st.markdown(f'<div class="alert-box alert-{tipo}">{msg}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛍️ Shopee Disputas")
    st.markdown("---")
    pagina = st.radio("Navegação", [
        "📊 Dashboard",
        "📤 Importar Planilha",
        "🗃️ Disputas",
        "🏷️ Cadastro de Produtos",
        "📈 Relatórios",
        "🚨 Alertas",
        "💾 Exportar",
        "📋 Histórico",
        "📦 Devoluções",
    ])
    st.markdown("---")
    total_dis = len(db.get_disputas())
    st.markdown(f"**📁 Total no banco:** {total_dis} disputas")
    st.markdown("---")
    with st.expander("⚙️ Configuracoes"):
        st.warning("Atencao: acao irreversivel!")
        if st.button("Limpar Historico", key="btn_reset"):
            st.session_state["confirmar_reset"] = True
        if st.session_state.get("confirmar_reset"):
            st.error("Confirma apagar tudo?")
            c1r, c2r = st.columns(2)
            with c1r:
                if st.button("Sim, apagar", type="primary", key="reset_sim"):
                    db.reset_db()
                    st.session_state["confirmar_reset"] = False
                    st.rerun()
            with c2r:
                if st.button("Cancelar", key="reset_nao"):
                    st.session_state["confirmar_reset"] = False
                    st.rerun()


# ─────────────────────────────────────────────────────────────────
# PÁGINA: DASHBOARD
# ─────────────────────────────────────────────────────────────────
if pagina == "📊 Dashboard":
    st.markdown('<div class="page-title">📊 Dashboard de Disputas</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Visão geral financeira das suas disputas na Shopee</div>', unsafe_allow_html=True)

    # Filtro rápido de período
    col_f1, col_f2, col_f3 = st.columns([2, 2, 4])
    with col_f1:
        d_ini = st.date_input("De", value=date(2024, 1, 1), key="dash_ini")
    with col_f2:
        d_fim = st.date_input("Até", value=date.today(), key="dash_fim")

    filtros = {"data_inicio": str(d_ini), "data_fim": str(d_fim)}
    disputas = db.get_disputas(filtros)
    df = pd.DataFrame(disputas)

    if df.empty:
        st.info("📭 Nenhuma disputa encontrada. Importe uma planilha na aba **Importar Planilha**.")
    else:
        # ── KPIs ──
        total       = len(df)
        ganhou      = (df["resultado_disputa"] == "Ganhou").sum()
        perdeu      = (df["resultado_disputa"] == "Perdeu").sum()
        em_analise  = (df["resultado_disputa"] == "Em análise").sum()
        taxa_vitoria = f"{ganhou/total*100:.1f}%" if total else "0%"

        val_reimb  = df["valor_reembolsado"].sum()
        comp_total = df["compensacao_vendedor"].sum()
        val_perd   = df["valor_perdido"].sum()
        prej_total = df["prejuizo_estimado"].sum()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            card("Total de Disputas",     str(total),       "blue",   "📋")
            card("Valor Total Reembolsado", fmt_brl(val_reimb), "red", "💸")
        with c2:
            card("Disputas Ganhas",       str(ganhou),      "green",  "✅")
            card("Compensação Recebida",  fmt_brl(comp_total), "green", "🤝")
        with c3:
            card("Disputas Perdidas",     str(perdeu),      "red",    "❌")
            card("Valor Total Perdido",   fmt_brl(val_perd), "orange", "📉")
        with c4:
            card("Em Análise",            str(em_analise),  "yellow", "⏳")
            card("Prejuízo Estimado",     fmt_brl(prej_total), "red", "🔴")

        st.markdown(f"**Taxa de Vitória:** `{taxa_vitoria}`  |  **{ganhou}** ganhou · **{perdeu}** perdeu · **{em_analise}** em análise")

        st.markdown("---")

        # ── Gráficos ──
        g1, g2 = st.columns(2)

        with g1:
            res_counts = df["resultado_disputa"].value_counts().reset_index()
            res_counts.columns = ["Resultado", "Qtd"]
            fig = px.pie(res_counts, values="Qtd", names="Resultado",
                         title="Resultado das Disputas",
                         color="Resultado",
                         color_discrete_map={"Ganhou": "#28a745", "Perdeu": "#dc3545", "Em análise": "#ffc107"},
                         hole=0.4)
            fig.update_layout(height=320, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with g2:
            cat_counts = df["categoria_motivo"].value_counts().reset_index()
            cat_counts.columns = ["Categoria", "Qtd"]
            fig2 = px.bar(cat_counts, x="Qtd", y="Categoria", orientation="h",
                          title="Categorias de Motivo", color="Qtd",
                          color_continuous_scale="Oranges")
            fig2.update_layout(height=320, margin=dict(t=40, b=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # ── Evolução mensal ──
        df["mes"] = pd.to_datetime(df["data_criacao"], errors="coerce").dt.to_period("M").astype(str)
        mensal = df.groupby("mes").agg(
            total=("id", "count"),
            prejuizo=("prejuizo_estimado", "sum"),
            val_perdido=("valor_perdido", "sum")
        ).reset_index().sort_values("mes")

        if len(mensal) > 1:
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=mensal["mes"], y=mensal["total"], name="Disputas", yaxis="y", marker_color="#ee4d2d"))
            fig3.add_trace(go.Scatter(x=mensal["mes"], y=mensal["prejuizo"], name="Prejuízo Est.", yaxis="y2", line=dict(color="#dc3545", width=3)))
            fig3.update_layout(
                title="Evolução Mensal",
                yaxis=dict(title="Disputas"),
                yaxis2=dict(title="R$ Prejuízo", overlaying="y", side="right"),
                height=300, margin=dict(t=40, b=0)
            )
            st.plotly_chart(fig3, use_container_width=True)

        # ── Top 5 produtos prejudicados ──
        st.markdown("#### 🔴 Top 5 Produtos com Maior Prejuízo")
        top5 = (df.groupby(["sku_principal", "nome_produto"])
                .agg(disputas=("id", "count"), prejuizo=("prejuizo_estimado", "sum"))
                .reset_index()
                .sort_values("prejuizo", ascending=False)
                .head(5))
        top5["prejuizo_fmt"] = top5["prejuizo"].apply(fmt_brl)
        st.dataframe(
            top5[["sku_principal", "nome_produto", "disputas", "prejuizo_fmt"]].rename(columns={
                "sku_principal": "SKU", "nome_produto": "Produto",
                "disputas": "Disputas", "prejuizo_fmt": "Prejuízo Est."
            }),
            use_container_width=True, hide_index=True
        )


# ─────────────────────────────────────────────────────────────────
# PÁGINA: IMPORTAR PLANILHA
# ─────────────────────────────────────────────────────────────────
elif pagina == "📤 Importar Planilha":
    st.markdown('<div class="page-title">📤 Importar Planilha Shopee</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Carregue o relatório de devoluções/reembolsos exportado da Shopee</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Selecione o arquivo (.xls, .xlsx, .csv)",
        type=["xls", "xlsx", "csv"]
    )

    if uploaded:
        with st.spinner("Lendo arquivo..."):
            try:
                file_bytes = uploaded.read()
                df_raw = ps.load_file(file_bytes, uploaded.name)
                col_map = ps.detect_columns(df_raw)
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
                st.stop()

        st.success(f"✅ Arquivo lido: **{len(df_raw)} linhas** · **{len(df_raw.columns)} colunas**")

        with st.expander("🔍 Prévia do arquivo (5 primeiras linhas)"):
            st.dataframe(df_raw.head(), use_container_width=True)

        st.markdown("#### 🗺️ Mapeamento de Colunas")
        st.caption("Verifique se os campos foram detectados corretamente. Ajuste se necessário.")

        cols_disp = ["(não mapear)"] + list(df_raw.columns)
        mapa_final = {}
        campos_label = {
            "id_devolucao":        "ID da Devolução *",
            "id_pedido":           "ID do Pedido *",
            "data_criacao":        "Data de Criação",
            "nome_produto":        "Nome do Produto",
            "sku_principal":       "SKU Principal",
            "nome_variacao":       "Nome da Variação",
            "sku_variacao":        "SKU da Variação",
            "preco_unitario":      "Preço Unitário",
            "status_devolucao":    "Status da Devolução",
            "quantidade":          "Quantidade",
            "motivo_devolucao":    "Motivo da Devolução",
            "valor_reembolsado":   "Valor Reembolsado",
            "compensacao_vendedor":"Compensação ao Vendedor",
            "valor_pago_comprador":"Valor Pago pelo Comprador",
            "motivo_disputa":      "Motivo da Disputa",
        }

        col_a, col_b = st.columns(2)
        items = list(campos_label.items())
        for i, (field, label) in enumerate(items):
            detected = col_map.get(field)
            idx = cols_disp.index(detected) if detected in cols_disp else 0
            target_col = col_a if i % 2 == 0 else col_b
            with target_col:
                escolha = st.selectbox(label, cols_disp, index=idx, key=f"map_{field}")
                mapa_final[field] = None if escolha == "(não mapear)" else escolha

        st.markdown("---")
        if st.button("🚀 Importar Dados", type="primary", use_container_width=True):
            with st.spinner("Importando..."):
                iid = db.create_importacao(uploaded.name)
                total, novas, dup = ps.processar_linhas(df_raw, mapa_final, iid)
                db.recalcular_financeiro()

            st.success(f"✅ Importação concluída! **{novas}** novas · **{dup}** duplicadas (de {total} linhas)")
            if novas > 0:
                st.balloons()


# ─────────────────────────────────────────────────────────────────
# PÁGINA: DISPUTAS
# ─────────────────────────────────────────────────────────────────
elif pagina == "🗃️ Disputas":
    st.markdown('<div class="page-title">🗃️ Lista de Disputas</div>', unsafe_allow_html=True)

    with st.expander("🔎 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_ini = st.date_input("De", value=date(2024, 1, 1), key="lst_ini")
            f_sku = st.text_input("SKU")
        with c2:
            f_fim = st.date_input("Até", value=date.today(), key="lst_fim")
            f_prod = st.text_input("Produto")
        with c3:
            f_status = st.selectbox("Status", ["", "Disputa aprovada", "Disputa rejeitada",
                                               "Reembolso Concluído", "Aguardando"])
            f_resultado = st.selectbox("Resultado", ["", "Ganhou", "Perdeu", "Em análise"])
        with c4:
            f_motivo = st.selectbox("Categoria Motivo", ["", "Erro interno", "Transporte",
                                                          "Cliente", "Plataforma/Shopee", "Outros"])

    filtros = {
        "data_inicio": str(f_ini), "data_fim": str(f_fim),
        "sku": f_sku, "produto": f_prod,
        "status": f_status, "resultado": f_resultado, "motivo": f_motivo,
    }
    disputas = db.get_disputas(filtros)
    df = pd.DataFrame(disputas)

    st.markdown(f"**{len(disputas)} disputas encontradas**")

    if not df.empty:
        cols_show = ["id_devolucao", "id_pedido", "data_criacao", "nome_produto",
                     "sku_principal", "quantidade", "status_devolucao", "resultado_disputa",
                     "categoria_motivo", "valor_reembolsado", "compensacao_vendedor",
                     "valor_perdido", "prejuizo_estimado", "resultado_financeiro"]
        df_show = df[[c for c in cols_show if c in df.columns]].copy()
        df_show.rename(columns={
            "id_devolucao": "ID Dev.", "id_pedido": "ID Pedido", "data_criacao": "Data",
            "nome_produto": "Produto", "sku_principal": "SKU", "quantidade": "Qtd",
            "status_devolucao": "Status", "resultado_disputa": "Resultado",
            "categoria_motivo": "Categoria", "valor_reembolsado": "Reembolsado",
            "compensacao_vendedor": "Compensação", "valor_perdido": "Val. Perdido",
            "prejuizo_estimado": "Prejuízo Est.", "resultado_financeiro": "Res. Fin.",
        }, inplace=True)

        def color_resultado(val):
            colors = {"Perdeu": "background-color:#f8d7da",
                      "Ganhou": "background-color:#d4edda",
                      "Em análise": "background-color:#fff3cd",
                      "prejuízo": "background-color:#f8d7da",
                      "recuperado": "background-color:#d4edda",
                      "neutro": ""}
            return colors.get(str(val), "")

        styled = df_show.style.applymap(color_resultado, subset=["Resultado", "Res. Fin."])
        st.dataframe(styled, use_container_width=True, hide_index=True, height=480)
    else:
        st.info("Nenhuma disputa encontrada com esses filtros.")


# ─────────────────────────────────────────────────────────────────
# PÁGINA: CADASTRO DE PRODUTOS
# ─────────────────────────────────────────────────────────────────
elif pagina == "🏷️ Cadastro de Produtos":
    st.markdown('<div class="page-title">🏷️ Cadastro de Produtos</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-sub">Cadastre o custo de cada SKU para calcular o prejuízo real</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ Novo / Editar", "📋 Produtos Cadastrados"])

    with tab1:
        with st.form("form_produto"):
            c1, c2 = st.columns(2)
            with c1:
                sku      = st.text_input("SKU *", placeholder="SHP1-524600")
                nome     = st.text_input("Nome do Produto")
                custo    = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, format="%.2f")
            with c2:
                fornecedor = st.text_input("Fornecedor")
                categoria  = st.selectbox("Categoria", ["", "Eletrodoméstico", "Cozinha",
                                                         "Vestuário", "Eletrônico", "Casa e Jardim",
                                                         "Brinquedo", "Beleza", "Outro"])
                obs = st.text_area("Observação", height=80)

            submitted = st.form_submit_button("💾 Salvar Produto", use_container_width=True, type="primary")
            if submitted:
                if not sku:
                    st.error("SKU é obrigatório!")
                else:
                    db.upsert_produto(sku.strip(), nome, custo, fornecedor, categoria, obs)
                    db.recalcular_financeiro()
                    st.success(f"✅ Produto **{sku}** salvo! Cálculos financeiros atualizados.")

    with tab2:
        produtos = db.get_produtos()
        if produtos:
            dfp = pd.DataFrame(produtos)
            dfp["custo_unitario"] = dfp["custo_unitario"].apply(fmt_brl)
            st.dataframe(
                dfp[["sku", "nome", "custo_unitario", "fornecedor", "categoria", "observacao"]].rename(columns={
                    "sku": "SKU", "nome": "Nome", "custo_unitario": "Custo Unit.",
                    "fornecedor": "Fornecedor", "categoria": "Categoria", "observacao": "Obs."
                }),
                use_container_width=True, hide_index=True
            )

            st.markdown("---")
            sku_del = st.selectbox("Excluir produto (SKU)", [p["sku"] for p in produtos])
            if st.button("🗑️ Excluir", type="secondary"):
                db.delete_produto(sku_del)
                st.success(f"Produto {sku_del} excluído.")
                st.rerun()
        else:
            st.info("Nenhum produto cadastrado ainda.")

        st.markdown("---")
        st.markdown("**💡 Dica:** Importe custos em massa via CSV abaixo (sku, nome, custo, fornecedor, categoria)")
        csv_up = st.file_uploader("Importar custos (.csv)", type=["csv"], key="csv_prod")
        if csv_up:
            try:
                df_prod = pd.read_csv(csv_up)
                df_prod.columns = [c.lower().strip() for c in df_prod.columns]
                count = 0
                for _, row in df_prod.iterrows():
                    sku_v = str(row.get("sku", "")).strip()
                    if sku_v:
                        db.upsert_produto(
                            sku_v,
                            str(row.get("nome", "")),
                            float(str(row.get("custo", row.get("custo_unitario", 0))).replace(",", ".") or 0),
                            str(row.get("fornecedor", "")),
                            str(row.get("categoria", "")),
                            str(row.get("observacao", row.get("obs", "")))
                        )
                        count += 1
                db.recalcular_financeiro()
                st.success(f"✅ {count} produtos importados!")
            except Exception as e:
                st.error(f"Erro: {e}")


# ─────────────────────────────────────────────────────────────────
# PÁGINA: RELATÓRIOS
# ─────────────────────────────────────────────────────────────────
elif pagina == "📈 Relatórios":
    st.markdown('<div class="page-title">📈 Relatórios Analíticos</div>', unsafe_allow_html=True)

    disputas = db.get_disputas()
    df = pd.DataFrame(disputas)

    if df.empty:
        st.info("Sem dados. Importe uma planilha primeiro.")
        st.stop()

    produtos = db.get_produtos()
    dfp = pd.DataFrame(produtos) if produtos else pd.DataFrame(columns=["sku", "fornecedor"])

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏆 Por Produto", "💡 Por Motivo", "🚚 Por Fornecedor",
        "📅 Mensal", "🔑 SKUs Problemáticos", "💰 Financeiro"
    ])

    # ── Por Produto ──
    with tab1:
        rank_prod = (df.groupby(["sku_principal", "nome_produto"])
                     .agg(disputas=("id", "count"),
                          ganhou=("resultado_disputa", lambda x: (x == "Ganhou").sum()),
                          perdeu=("resultado_disputa", lambda x: (x == "Perdeu").sum()),
                          val_perdido=("valor_perdido", "sum"),
                          prejuizo=("prejuizo_estimado", "sum"))
                     .reset_index()
                     .sort_values("prejuizo", ascending=False))

        fig = px.bar(rank_prod.head(15), x="nome_produto", y="prejuizo",
                     title="Top 15 Produtos – Prejuízo Estimado",
                     labels={"nome_produto": "Produto", "prejuizo": "Prejuízo (R$)"},
                     color="prejuizo", color_continuous_scale="Reds")
        fig.update_xaxes(tickangle=45)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        rank_prod["prejuizo_fmt"] = rank_prod["prejuizo"].apply(fmt_brl)
        rank_prod["val_perdido_fmt"] = rank_prod["val_perdido"].apply(fmt_brl)
        st.dataframe(rank_prod[["sku_principal", "nome_produto", "disputas",
                                 "ganhou", "perdeu", "val_perdido_fmt", "prejuizo_fmt"]]
                     .rename(columns={"sku_principal": "SKU", "nome_produto": "Produto",
                                      "disputas": "Total", "ganhou": "✅ Ganhou",
                                      "perdeu": "❌ Perdeu", "val_perdido_fmt": "Val. Perdido",
                                      "prejuizo_fmt": "Prejuízo Est."}),
                     use_container_width=True, hide_index=True)

    # ── Por Motivo ──
    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            mot_freq = df["motivo_devolucao"].value_counts().head(10).reset_index()
            mot_freq.columns = ["Motivo", "Qtd"]
            mot_freq["Motivo"] = mot_freq["Motivo"].str[:50]
            fig2 = px.bar(mot_freq, x="Qtd", y="Motivo", orientation="h",
                          title="Motivos Mais Frequentes", color="Qtd",
                          color_continuous_scale="Blues")
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)

        with c2:
            cat_prej = (df.groupby("categoria_motivo")
                        .agg(prejuizo=("prejuizo_estimado", "sum"), qtd=("id", "count"))
                        .reset_index().sort_values("prejuizo", ascending=False))
            fig3 = px.pie(cat_prej, values="prejuizo", names="categoria_motivo",
                          title="Prejuízo por Categoria", hole=0.4,
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(height=400)
            st.plotly_chart(fig3, use_container_width=True)

        mot_prej = (df.groupby("motivo_devolucao")
                    .agg(prejuizo=("prejuizo_estimado", "sum"), qtd=("id", "count"))
                    .reset_index().sort_values("prejuizo", ascending=False).head(10))
        mot_prej["prejuizo_fmt"] = mot_prej["prejuizo"].apply(fmt_brl)
        mot_prej["motivo_devolucao"] = mot_prej["motivo_devolucao"].str[:70]
        st.dataframe(mot_prej[["motivo_devolucao", "qtd", "prejuizo_fmt"]]
                     .rename(columns={"motivo_devolucao": "Motivo", "qtd": "Ocorrências",
                                      "prejuizo_fmt": "Prejuízo Est."}),
                     use_container_width=True, hide_index=True)

    # ── Por Fornecedor ──
    with tab3:
        if not dfp.empty and "fornecedor" in dfp.columns:
            merged = df.merge(dfp[["sku", "fornecedor"]], left_on="sku_principal", right_on="sku", how="left")
            merged["fornecedor"] = merged["fornecedor"].fillna("Sem cadastro")
            forn_rank = (merged.groupby("fornecedor")
                         .agg(disputas=("id", "count"),
                              prejuizo=("prejuizo_estimado", "sum"),
                              val_perdido=("valor_perdido", "sum"))
                         .reset_index().sort_values("prejuizo", ascending=False))
            fig4 = px.bar(forn_rank.head(10), x="fornecedor", y="prejuizo",
                          title="Fornecedores – Prejuízo Estimado", color="disputas",
                          color_continuous_scale="Oranges")
            fig4.update_layout(height=350)
            st.plotly_chart(fig4, use_container_width=True)

            forn_rank["prejuizo_fmt"] = forn_rank["prejuizo"].apply(fmt_brl)
            st.dataframe(forn_rank[["fornecedor", "disputas", "val_perdido", "prejuizo_fmt"]]
                         .rename(columns={"fornecedor": "Fornecedor", "disputas": "Disputas",
                                          "val_perdido": "Val. Perdido", "prejuizo_fmt": "Prejuízo Est."}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Cadastre fornecedores na tela de **Cadastro de Produtos** para ver este relatório.")

    # ── Mensal ──
    with tab4:
        df["mes_dt"] = pd.to_datetime(df["data_criacao"], errors="coerce").dt.to_period("M").astype(str)
        mensal = (df.groupby("mes_dt")
                  .agg(total=("id", "count"),
                       ganhou=("resultado_disputa", lambda x: (x == "Ganhou").sum()),
                       perdeu=("resultado_disputa", lambda x: (x == "Perdeu").sum()),
                       reimb=("valor_reembolsado", "sum"),
                       comp=("compensacao_vendedor", "sum"),
                       perd=("valor_perdido", "sum"),
                       prej=("prejuizo_estimado", "sum"))
                  .reset_index().sort_values("mes_dt"))

        fig5 = go.Figure()
        fig5.add_trace(go.Bar(x=mensal["mes_dt"], y=mensal["ganhou"], name="Ganhou", marker_color="#28a745"))
        fig5.add_trace(go.Bar(x=mensal["mes_dt"], y=mensal["perdeu"], name="Perdeu", marker_color="#dc3545"))
        fig5.add_trace(go.Scatter(x=mensal["mes_dt"], y=mensal["prej"], name="Prejuízo (R$)",
                                   yaxis="y2", line=dict(color="#fd7e14", width=3)))
        fig5.update_layout(barmode="stack", title="Evolução Mensal",
                           yaxis2=dict(overlaying="y", side="right", title="R$ Prejuízo"),
                           height=380)
        st.plotly_chart(fig5, use_container_width=True)

        mensal_disp = mensal.copy()
        for col in ["reimb", "comp", "perd", "prej"]:
            mensal_disp[col] = mensal_disp[col].apply(fmt_brl)
        st.dataframe(mensal_disp.rename(columns={
            "mes_dt": "Mês", "total": "Total", "ganhou": "Ganhou",
            "perdeu": "Perdeu", "reimb": "Reembolsado", "comp": "Compensação",
            "perd": "Val. Perdido", "prej": "Prejuízo Est."
        }), use_container_width=True, hide_index=True)

    # ── SKUs Problemáticos ──
    with tab5:
        sku_rank = (df.groupby("sku_principal")
                    .agg(disputas=("id", "count"),
                         nome=("nome_produto", "first"),
                         perdeu=("resultado_disputa", lambda x: (x == "Perdeu").sum()),
                         prejuizo=("prejuizo_estimado", "sum"),
                         taxa_perda=("resultado_disputa", lambda x: (x == "Perdeu").sum() / max(len(x), 1) * 100))
                    .reset_index()
                    .sort_values("disputas", ascending=False))

        fig6 = px.scatter(sku_rank, x="disputas", y="prejuizo", size="taxa_perda",
                          hover_name="nome", color="taxa_perda",
                          color_continuous_scale="RdYlGn_r",
                          title="SKUs: Disputas × Prejuízo (tamanho = taxa de perda)",
                          labels={"disputas": "Nº Disputas", "prejuizo": "Prejuízo Est. (R$)",
                                  "taxa_perda": "Taxa Perda %"})
        fig6.update_layout(height=400)
        st.plotly_chart(fig6, use_container_width=True)

        sku_rank["prejuizo_fmt"]  = sku_rank["prejuizo"].apply(fmt_brl)
        sku_rank["taxa_perda_fmt"] = sku_rank["taxa_perda"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(sku_rank[["sku_principal", "nome", "disputas", "perdeu", "taxa_perda_fmt", "prejuizo_fmt"]]
                     .rename(columns={"sku_principal": "SKU", "nome": "Produto",
                                      "disputas": "Total", "perdeu": "Perdeu",
                                      "taxa_perda_fmt": "Taxa Perda", "prejuizo_fmt": "Prejuízo Est."}),
                     use_container_width=True, hide_index=True)

    # ── Financeiro ──
    with tab6:
        fin_counts = df["resultado_financeiro"].value_counts().reset_index()
        fin_counts.columns = ["Resultado", "Qtd"]
        fin_sum = df.groupby("resultado_financeiro")["prejuizo_estimado"].sum().reset_index()
        fin_sum.columns = ["Resultado", "Total R$"]

        c1, c2 = st.columns(2)
        with c1:
            fig7 = px.pie(fin_counts, values="Qtd", names="Resultado",
                          title="Distribuição de Resultados Financeiros",
                          color="Resultado",
                          color_discrete_map={"prejuízo": "#dc3545", "recuperado": "#28a745", "neutro": "#6c757d"},
                          hole=0.4)
            fig7.update_layout(height=320)
            st.plotly_chart(fig7, use_container_width=True)
        with c2:
            fig8 = px.bar(fin_sum, x="Resultado", y="Total R$",
                          title="Total em R$ por Resultado Financeiro",
                          color="Resultado",
                          color_discrete_map={"prejuízo": "#dc3545", "recuperado": "#28a745", "neutro": "#6c757d"})
            fig8.update_layout(height=320, showlegend=False)
            st.plotly_chart(fig8, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# PÁGINA: ALERTAS
# ─────────────────────────────────────────────────────────────────
elif pagina == "🚨 Alertas":
    st.markdown('<div class="page-title">🚨 Alertas Automáticos</div>', unsafe_allow_html=True)

    disputas = db.get_disputas()
    df = pd.DataFrame(disputas)

    if df.empty:
        st.info("Sem dados para analisar.")
        st.stop()

    df["mes_dt"] = pd.to_datetime(df["data_criacao"], errors="coerce").dt.to_period("M")
    mes_atual = pd.Period(datetime.today(), "M")
    mes_ant   = mes_atual - 1

    df_atual = df[df["mes_dt"] == mes_atual]
    df_ant   = df[df["mes_dt"] == mes_ant]

    alertas_encontrados = 0

    # ── SKU com mais de 3 disputas no mês ──
    st.markdown("#### 🔴 SKUs com mais de 3 disputas no mês atual")
    if not df_atual.empty:
        sku_mes = df_atual.groupby("sku_principal").size().reset_index(name="qtd")
        sku_alerta = sku_mes[sku_mes["qtd"] > 3]
        if not sku_alerta.empty:
            for _, row in sku_alerta.iterrows():
                alert(f"⚠️ SKU <b>{row['sku_principal']}</b> tem <b>{row['qtd']} disputas</b> este mês!", "danger")
                alertas_encontrados += 1
        else:
            alert("✅ Nenhum SKU com mais de 3 disputas este mês.", "info")
    else:
        alert("Sem dados para o mês atual.", "info")

    # ── Produto com prejuízo > R$ 100 no mês ──
    st.markdown("#### 🟠 Produtos com prejuízo acima de R$ 100 no mês")
    if not df_atual.empty:
        prej_mes = (df_atual.groupby(["sku_principal", "nome_produto"])
                    ["prejuizo_estimado"].sum().reset_index())
        prej_alerta = prej_mes[prej_mes["prejuizo_estimado"] > 100]
        if not prej_alerta.empty:
            for _, row in prej_alerta.iterrows():
                alert(f"⚠️ <b>{row['nome_produto']}</b> (SKU: {row['sku_principal']}) – prejuízo de <b>{fmt_brl(row['prejuizo_estimado'])}</b> este mês", "danger")
                alertas_encontrados += 1
        else:
            alert("✅ Nenhum produto com prejuízo acima de R$ 100 este mês.", "info")
    else:
        alert("Sem dados para o mês atual.", "info")

    # ── Motivo que aumentou vs mês anterior ──
    st.markdown("#### 🟡 Motivos que aumentaram vs. mês anterior")
    if not df_atual.empty and not df_ant.empty:
        cat_atual = df_atual["categoria_motivo"].value_counts()
        cat_ant   = df_ant["categoria_motivo"].value_counts()
        for cat in cat_atual.index:
            q_atual = cat_atual.get(cat, 0)
            q_ant   = cat_ant.get(cat, 0)
            if q_atual > q_ant and q_ant > 0:
                variacao = ((q_atual - q_ant) / q_ant * 100)
                alert(f"📈 Categoria <b>{cat}</b>: {q_ant} → {q_atual} ocorrências (+{variacao:.0f}%)", "warning")
                alertas_encontrados += 1
    else:
        alert("Dados insuficientes para comparar meses.", "info")

    # ── Fornecedor com muitas ocorrências ──
    st.markdown("#### 🟣 Fornecedores com muitas ocorrências")
    produtos = db.get_produtos()
    if produtos:
        dfp = pd.DataFrame(produtos)
        merged = df.merge(dfp[["sku", "fornecedor"]], left_on="sku_principal", right_on="sku", how="left")
        merged["fornecedor"] = merged["fornecedor"].fillna("Sem cadastro")
        forn_count = merged[merged["fornecedor"] != "Sem cadastro"].groupby("fornecedor").size()
        for forn, qtd in forn_count.items():
            if qtd >= 5:
                alert(f"⚠️ Fornecedor <b>{forn}</b> tem <b>{qtd} disputas</b> no total.", "warning")
                alertas_encontrados += 1
    else:
        alert("Cadastre fornecedores para monitorar ocorrências.", "info")

    if alertas_encontrados == 0:
        st.success("🎉 Nenhum alerta crítico encontrado!")
    else:
        st.warning(f"⚠️ {alertas_encontrados} alerta(s) identificado(s). Verifique os itens acima.")


# ─────────────────────────────────────────────────────────────────
# PÁGINA: EXPORTAR
# ─────────────────────────────────────────────────────────────────
elif pagina == "💾 Exportar":
    st.markdown('<div class="page-title">💾 Exportar Relatórios</div>', unsafe_allow_html=True)

    disputas = db.get_disputas()
    produtos = db.get_produtos()

    if not disputas:
        st.info("Sem dados para exportar. Importe uma planilha primeiro.")
        st.stop()

    st.markdown("Baixe os relatórios nos formatos prontos para análise:")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Relatório Geral")
        st.caption("Todas as disputas com campos financeiros calculados")
        data_geral = ex.exportar_geral(disputas)
        st.download_button(
            "⬇️ Baixar Relatório Geral",
            data=data_geral,
            file_name=f"shopee_disputas_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.markdown("#### 🏆 Ranking por Produto")
        st.caption("Produtos ordenados por prejuízo estimado")
        data_prod = ex.exportar_ranking_produto(disputas)
        st.download_button(
            "⬇️ Baixar Ranking por Produto",
            data=data_prod,
            file_name=f"shopee_ranking_produto_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col2:
        st.markdown("#### 🚚 Ranking por Fornecedor")
        st.caption("Fornecedores com maior prejuízo acumulado")
        data_forn = ex.exportar_ranking_fornecedor(disputas, produtos)
        st.download_button(
            "⬇️ Baixar Ranking por Fornecedor",
            data=data_forn,
            file_name=f"shopee_ranking_fornecedor_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.markdown("#### 📅 Resumo Mensal")
        st.caption("Consolidado mês a mês de disputas e perdas")
        data_mensal = ex.exportar_resumo_mensal(disputas)
        st.download_button(
            "⬇️ Baixar Resumo Mensal",
            data=data_mensal,
            file_name=f"shopee_resumo_mensal_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("#### 🗃️ Backup do Banco de Dados")
    st.caption("Faça backup do banco SQLite para não perder seus dados")
    import os
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shopee_disputes.db")
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            st.download_button(
                "⬇️ Baixar Banco de Dados (.db)",
                data=f.read(),
                file_name="shopee_disputes_backup.db",
                mime="application/octet-stream",
                use_container_width=True
            )


# ─────────────────────────────────────────────────────────────────
# PÁGINA: HISTÓRICO
# ─────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────
elif pagina == "📦 Devoluções":
    st.markdown('<div class="page-title">📦 Gestão de Devoluções</div>', unsafe_allow_html=True)
    st.info("Registre aqui as devoluções recebidas. Informe o ID do pedido e o sistema vincula automaticamente à disputa correspondente.")
    FRETE_DEV = 20.0
    with st.form("form_devolucao"):
        st.markdown("### Registrar Nova Devolução")
        fc1, fc2 = st.columns(2)
        with fc1:
            rastreamento = st.text_input("Número de Rastreamento", placeholder="BR123456789BR")
            id_pedido = st.text_input("ID do Pedido / ID Solicitação", placeholder="Ex: 2312345678901")
        with fc2:
            prod_quebrado_opt = st.radio(
                "Estado do Produto Recebido:",
                ["Produto chegou INTEIRO (não computa custo)", "Produto chegou QUEBRADO (computa custo)"],
                index=0
            )
            obs_dev = st.text_area("Observações", placeholder="Observações sobre a devolução...")
        submit_dev = st.form_submit_button("Registrar Devolução", type="primary")
        if submit_dev:
            if not rastreamento and not id_pedido:
                st.error("Informe pelo menos o rastreamento ou ID do pedido.")
            else:
                quebrado_bool = "QUEBRADO" in prod_quebrado_opt
                disputa_id = db.registrar_devolucao(
                    rastreamento=rastreamento or "",
                    id_pedido=id_pedido or "",
                    produto_quebrado=quebrado_bool,
                    observacoes=obs_dev or ""
                )
                if disputa_id:
                    st.success(f"Devolução registrada e vinculada à disputa #{disputa_id}!")
                    if quebrado_bool:
                        st.warning("Produto marcado como QUEBRADO - custo será somado ao prejuízo!")
                    else:
                        st.info("Produto INTEIRO - apenas frete de R$20,00 será computado.")
                else:
                    st.success("Devolução registrada (sem disputa vinculada encontrada).")
                st.rerun()
    st.markdown("---")
    st.markdown("### Histórico de Devoluções")
    devs = db.get_devolucoes()
    if not devs:
        st.info("Nenhuma devolução registrada ainda.")
    else:
        df_dev = pd.DataFrame(devs)
        col_map = {"rastreamento": "Rastreamento", "id_pedido": "ID Pedido", "disputa_id": "Disputa #",
                   "produto_quebrado": "Produto", "data_registro": "Data", "sku_principal": "SKU",
                   "nome_produto": "Produto Nome", "observacoes": "Obs"}
        df_show = df_dev[[c for c in col_map if c in df_dev.columns]].rename(columns=col_map)
        if "Produto" in df_show.columns:
            df_show["Produto"] = df_show["Produto"].apply(lambda x: "QUEBRADO" if x else "INTEIRO")
        if "Data" in df_show.columns:
            df_show["Data"] = df_show["Data"].astype(str).str[:16]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        total_devs = len(devs)
        qb = sum(1 for d in devs if d.get("produto_quebrado"))
        st.markdown(f"**Total:** {total_devs} | **Quebrados:** {qb} | **Inteiros:** {total_devs-qb} | **Frete total:** R$ {total_devs * FRETE_DEV:.2f}")

elif pagina == "📋 Histórico":
    st.markdown('<div class="page-title">📋 Histórico de Importações</div>', unsafe_allow_html=True)

    importacoes = db.get_importacoes()
    if not importacoes:
        st.info("Nenhuma importação realizada ainda.")
    else:
        df_imp = pd.DataFrame(importacoes)
        df_imp["data_importacao"] = pd.to_datetime(df_imp["data_importacao"]).dt.strftime("%d/%m/%Y %H:%M")
        df_imp["taxa_sucesso"] = df_imp.apply(
            lambda r: f"{r['novas_linhas']}/{r['total_linhas']}" if r["total_linhas"] else "—", axis=1
        )
        st.dataframe(
            df_imp[["id", "nome_arquivo", "data_importacao", "total_linhas",
                     "novas_linhas", "duplicadas", "taxa_sucesso"]].rename(columns={
                "id": "#", "nome_arquivo": "Arquivo", "data_importacao": "Data/Hora",
                "total_linhas": "Total", "novas_linhas": "Novas",
                "duplicadas": "Duplicadas", "taxa_sucesso": "Sucesso"
            }),
            use_container_width=True, hide_index=True
        )
        st.markdown(f"**Total de importações:** {len(importacoes)}")
