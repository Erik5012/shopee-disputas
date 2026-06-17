import pandas as pd
import re
from database import get_custo_sku

# ──────────────────────────────────────────────
# Mapeamento padrão: campo interno → possíveis nomes de coluna na planilha
# ──────────────────────────────────────────────
COLUMN_MAP = {
    "id_devolucao":          ["ID da Devolução", "id devolucao", "ID Devolução", "Nº Solicitação"],
    "id_pedido":             ["ID do pedido", "ID Pedido", "Nº Pedido", "Order ID"],
    "data_criacao":          ["Data de criação do pedido", "Data Criação", "Data do Pedido"],
    "nome_comprador":        ["Nome de usuário (Comprador)", "Comprador"],
    "nome_produto":          ["Nome do Produto", "Produto"],
    "sku_principal":         ["SKU principal", "SKU Principal", "SKU"],
    "nome_variacao":         ["Nome da variação", "Variação"],
    "sku_variacao":          ["SKU da Variação", "SKU Variação"],
    "preco_unitario":        ["Preço da unidade", "Preço Unitário", "Preço"],
    "status_devolucao":      ["Status da Devolução / Reembolso", "Status Devolução", "Status"],
    "tipo_devolucao":        ["Tipo de Devolução"],
    "quantidade":            ["Quantidade de Devoluções", "Quantidade"],
    "solucao":               ["Solução para Retorno e Reembolso", "Solução"],
    "motivo_devolucao":      ["Motivo da Devolução", "Motivo da devolução revisado", "Motivo Devolução"],
    "observacao_devolucao":  ["Observações da Devolução", "Observação da Devolução"],
    "valor_reembolsado":     ["Quantia total de reembolsos", "Valor Reembolsado", "Reembolso"],
    "compensacao_vendedor":  ["Compensação ao Vendedor (Disputa bem sucedida/Ajuste em carteira)", "Compensação Vendedor"],
    "motivo_disputa":        ["Motivo da disputa", "Motivo Disputa"],
    "observacao_vendedor":   ["Observação do vendedor"],
    "valor_pago_comprador":  ["Valor pago pelo comprador", "Valor Pago"],
    "metodo_pagamento":      ["Método de pagamento"],
}

CATEGORIA_MAP = {
    "Erro interno": [
        "produto errado", "tamanho errado", "cor errada", "produto diferente",
        "faltando item", "faltando", "embalagem incorreta", "embalagem errada",
        "item faltando", "não recebi", "produto não corresponde",
    ],
    "Transporte": [
        "avariado", "quebrado", "amassado", "arranhado", "danos físicos",
        "extraviado", "perdido", "danificado", "dano", "defeito de fabricação",
    ],
    "Cliente": [
        "arrependimento", "não gostei", "compra errada", "não quero mais",
        "desisti", "não preciso", "mudei de ideia", "comprei errado",
    ],
    "Plataforma/Shopee": [
        "reembolso sem devolução", "decisão shopee", "shopee decidiu",
        "plataforma", "política shopee",
    ],
}


def classificar_motivo(texto: str) -> str:
    if not texto:
        return "Outros"
    t = texto.lower()
    for categoria, palavras in CATEGORIA_MAP.items():
        for p in palavras:
            if p in t:
                return categoria
    return "Outros"


def determinar_resultado(status: str) -> str:
    if not status:
        return "Em análise"
    s = status.lower()
    if any(x in s for x in ["aprovada", "aprovado", "reembolso concluído", "concluída", "concluido"]):
        return "Perdeu"
    if any(x in s for x in ["rejeitada", "rejeitado", "vendedor ganhou", "disputa encerrada"]):
        return "Ganhou"
    if any(x in s for x in ["disputa", "em análise", "aguardando", "pendente", "em aberto"]):
        return "Em análise"
    return "Em análise"


def parse_valor(v) -> float:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    s = str(v).replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def detect_columns(df: pd.DataFrame) -> dict:
    """Tenta detectar automaticamente as colunas do df"""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    result = {}
    for field, candidates in COLUMN_MAP.items():
        for cand in candidates:
            if cand.lower() in cols_lower:
                result[field] = cols_lower[cand.lower()]
                break
        if field not in result:
            result[field] = None
    return result


def load_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    import io
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "csv":
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc)
                return df
            except Exception:
                pass
    elif ext in ("xls",):
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        return df
    else:  # xlsx
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        return df
    raise ValueError(f"Não foi possível ler o arquivo: {filename}")


def processar_linhas(df: pd.DataFrame, col_map: dict, importacao_id: int):
    from database import insert_disputa, update_importacao
    total = len(df)
    novas = 0
    duplicadas = 0

    def get(row, field):
        col = col_map.get(field)
        if col and col in row.index:
            val = row[col]
            if pd.isna(val) if not isinstance(val, str) else False:
                return None
            return val
        return None

    for _, row in df.iterrows():
        id_dev   = str(get(row, "id_devolucao") or "").strip()
        id_ped   = str(get(row, "id_pedido") or "").strip()
        if not id_ped:
            continue

        nome_prod = str(get(row, "nome_produto") or "")
        sku_pri   = str(get(row, "sku_principal") or "").strip()
        sku_var   = str(get(row, "sku_variacao") or "").strip()
        qtd       = int(parse_valor(get(row, "quantidade")) or 1)
        val_reimb = parse_valor(get(row, "valor_reembolsado"))
        comp_vend = parse_valor(get(row, "compensacao_vendedor"))
        val_pago  = parse_valor(get(row, "valor_pago_comprador"))
        preco_u   = parse_valor(get(row, "preco_unitario"))
        status    = str(get(row, "status_devolucao") or "")
        motivo    = str(get(row, "motivo_devolucao") or "")
        motivo_d  = str(get(row, "motivo_disputa") or "")

        categoria = classificar_motivo(motivo or motivo_d)
        resultado = determinar_resultado(status)

        custo_unit, _ = get_custo_sku(sku_pri or sku_var)
        custo_prod = custo_unit * qtd
        val_perdido = max(0.0, val_reimb - comp_vend)
        prejuizo = val_perdido + custo_prod

        if prejuizo > 0:
            res_fin = "prejuízo"
        elif comp_vend > 0:
            res_fin = "recuperado"
        else:
            res_fin = "neutro"

        data_c = str(get(row, "data_criacao") or "").strip()

        record = {
            "id_devolucao":        id_dev or None,
            "id_pedido":           id_ped,
            "data_criacao":        data_c,
            "nome_comprador":      str(get(row, "nome_comprador") or ""),
            "nome_produto":        nome_prod,
            "sku_principal":       sku_pri,
            "nome_variacao":       str(get(row, "nome_variacao") or ""),
            "sku_variacao":        sku_var,
            "preco_unitario":      preco_u,
            "status_devolucao":    status,
            "tipo_devolucao":      str(get(row, "tipo_devolucao") or ""),
            "quantidade":          qtd,
            "solucao":             str(get(row, "solucao") or ""),
            "motivo_devolucao":    motivo,
            "observacao_devolucao":str(get(row, "observacao_devolucao") or ""),
            "valor_reembolsado":   val_reimb,
            "compensacao_vendedor":comp_vend,
            "motivo_disputa":      motivo_d,
            "observacao_vendedor": str(get(row, "observacao_vendedor") or ""),
            "valor_pago_comprador":val_pago,
            "metodo_pagamento":    str(get(row, "metodo_pagamento") or ""),
            "resultado_disputa":   resultado,
            "categoria_motivo":    categoria,
            "valor_perdido":       val_perdido,
            "custo_produto":       custo_prod,
            "prejuizo_estimado":   prejuizo,
            "resultado_financeiro":res_fin,
        }

        ok = insert_disputa(record, importacao_id)
        if ok:
            novas += 1
        else:
            duplicadas += 1

    update_importacao(importacao_id, total, novas, duplicadas)
    return total, novas, duplicadas
