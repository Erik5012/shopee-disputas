import io
import pandas as pd
from datetime import datetime


def _writer(buf):
    return pd.ExcelWriter(buf, engine="xlsxwriter")


def exportar_geral(disputas: list) -> bytes:
    buf = io.BytesIO()
    df = pd.DataFrame(disputas)
    cols_display = {
        "id_devolucao": "ID Devolução",
        "id_pedido": "ID Pedido",
        "data_criacao": "Data Criação",
        "nome_produto": "Produto",
        "sku_principal": "SKU",
        "quantidade": "Qtd",
        "status_devolucao": "Status",
        "resultado_disputa": "Resultado",
        "categoria_motivo": "Categoria",
        "motivo_devolucao": "Motivo",
        "valor_pago_comprador": "Valor Pago",
        "valor_reembolsado": "Reembolsado",
        "compensacao_vendedor": "Compensação",
        "valor_perdido": "Valor Perdido",
        "custo_produto": "Custo Produto",
        "prejuizo_estimado": "Prejuízo Est.",
        "resultado_financeiro": "Resultado Fin.",
    }
    df_exp = df[[c for c in cols_display if c in df.columns]].rename(columns=cols_display)
    with _writer(buf) as writer:
        df_exp.to_excel(writer, index=False, sheet_name="Disputas")
        ws = writer.sheets["Disputas"]
        for i, col in enumerate(df_exp.columns):
            ws.set_column(i, i, max(15, len(col) + 2))
    return buf.getvalue()


def exportar_ranking_produto(disputas: list) -> bytes:
    buf = io.BytesIO()
    df = pd.DataFrame(disputas)
    if df.empty:
        return buf.getvalue()
    rank = (
        df.groupby(["sku_principal", "nome_produto"])
        .agg(
            total_disputas=("id", "count"),
            valor_reembolsado=("valor_reembolsado", "sum"),
            compensacao=("compensacao_vendedor", "sum"),
            valor_perdido=("valor_perdido", "sum"),
            custo_produto=("custo_produto", "sum"),
            prejuizo_estimado=("prejuizo_estimado", "sum"),
        )
        .reset_index()
        .sort_values("prejuizo_estimado", ascending=False)
    )
    rank.columns = ["SKU", "Produto", "Disputas", "Reembolsado", "Compensação",
                    "Valor Perdido", "Custo Produto", "Prejuízo Est."]
    with _writer(buf) as writer:
        rank.to_excel(writer, index=False, sheet_name="Ranking Produto")
        ws = writer.sheets["Ranking Produto"]
        for i, col in enumerate(rank.columns):
            ws.set_column(i, i, max(15, len(col) + 2))
    return buf.getvalue()


def exportar_ranking_fornecedor(disputas: list, produtos: list) -> bytes:
    buf = io.BytesIO()
    df = pd.DataFrame(disputas)
    dfp = pd.DataFrame(produtos)
    if df.empty or dfp.empty:
        return buf.getvalue()
    merged = df.merge(dfp[["sku", "fornecedor"]], left_on="sku_principal", right_on="sku", how="left")
    merged["fornecedor"] = merged["fornecedor"].fillna("Sem cadastro")
    rank = (
        merged.groupby("fornecedor")
        .agg(
            total_disputas=("id", "count"),
            valor_perdido=("valor_perdido", "sum"),
            prejuizo_estimado=("prejuizo_estimado", "sum"),
        )
        .reset_index()
        .sort_values("prejuizo_estimado", ascending=False)
    )
    rank.columns = ["Fornecedor", "Disputas", "Valor Perdido", "Prejuízo Est."]
    with _writer(buf) as writer:
        rank.to_excel(writer, index=False, sheet_name="Ranking Fornecedor")
    return buf.getvalue()


def exportar_resumo_mensal(disputas: list) -> bytes:
    buf = io.BytesIO()
    df = pd.DataFrame(disputas)
    if df.empty:
        return buf.getvalue()
    df["mes"] = pd.to_datetime(df["data_criacao"], errors="coerce").dt.to_period("M").astype(str)
    rank = (
        df.groupby("mes")
        .agg(
            total_disputas=("id", "count"),
            ganhou=("resultado_disputa", lambda x: (x == "Ganhou").sum()),
            perdeu=("resultado_disputa", lambda x: (x == "Perdeu").sum()),
            em_analise=("resultado_disputa", lambda x: (x == "Em análise").sum()),
            valor_reembolsado=("valor_reembolsado", "sum"),
            compensacao=("compensacao_vendedor", "sum"),
            valor_perdido=("valor_perdido", "sum"),
            prejuizo=("prejuizo_estimado", "sum"),
        )
        .reset_index()
        .sort_values("mes")
    )
    rank.columns = ["Mês", "Total", "Ganhou", "Perdeu", "Em Análise",
                    "Reembolsado", "Compensação", "Valor Perdido", "Prejuízo Est."]
    with _writer(buf) as writer:
        rank.to_excel(writer, index=False, sheet_name="Resumo Mensal")
        ws = writer.sheets["Resumo Mensal"]
        for i, col in enumerate(rank.columns):
            ws.set_column(i, i, 14)
    return buf.getvalue()
