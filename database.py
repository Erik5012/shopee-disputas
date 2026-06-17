import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "shopee_disputes.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS importacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_arquivo TEXT NOT NULL,
        data_importacao TEXT NOT NULL,
        total_linhas INTEGER DEFAULT 0,
        novas_linhas INTEGER DEFAULT 0,
        duplicadas INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS disputas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_devolucao TEXT,
        id_pedido TEXT NOT NULL,
        data_criacao TEXT,
        nome_comprador TEXT,
        nome_produto TEXT,
        sku_principal TEXT,
        nome_variacao TEXT,
        sku_variacao TEXT,
        preco_unitario REAL DEFAULT 0,
        status_devolucao TEXT,
        tipo_devolucao TEXT,
        quantidade INTEGER DEFAULT 1,
        solucao TEXT,
        motivo_devolucao TEXT,
        observacao_devolucao TEXT,
        valor_reembolsado REAL DEFAULT 0,
        compensacao_vendedor REAL DEFAULT 0,
        motivo_disputa TEXT,
        observacao_vendedor TEXT,
        valor_pago_comprador REAL DEFAULT 0,
        metodo_pagamento TEXT,
        resultado_disputa TEXT,
        categoria_motivo TEXT,
        valor_perdido REAL DEFAULT 0,
        custo_produto REAL DEFAULT 0,
        prejuizo_estimado REAL DEFAULT 0,
        resultado_financeiro TEXT,
        importacao_id INTEGER,
        UNIQUE(id_pedido, id_devolucao),
        FOREIGN KEY(importacao_id) REFERENCES importacoes(id)
    );

    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE NOT NULL,
        nome TEXT,
        custo_unitario REAL DEFAULT 0,
        fornecedor TEXT,
        categoria TEXT,
        observacao TEXT,
        data_cadastro TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_disputas_sku ON disputas(sku_principal);
    CREATE INDEX IF NOT EXISTS idx_disputas_data ON disputas(data_criacao);
    CREATE INDEX IF NOT EXISTS idx_disputas_status ON disputas(status_devolucao);
    CREATE INDEX IF NOT EXISTS idx_disputas_resultado ON disputas(resultado_disputa);
    """)

    conn.commit()
    conn.close()


def upsert_produto(sku, nome, custo, fornecedor, categoria, observacao):
    conn = get_conn()
    conn.execute("""
        INSERT INTO produtos (sku, nome, custo_unitario, fornecedor, categoria, observacao, data_cadastro)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(sku) DO UPDATE SET
            nome=excluded.nome,
            custo_unitario=excluded.custo_unitario,
            fornecedor=excluded.fornecedor,
            categoria=excluded.categoria,
            observacao=excluded.observacao
    """, (sku, nome, custo, fornecedor, categoria, observacao, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def delete_produto(sku):
    conn = get_conn()
    conn.execute("DELETE FROM produtos WHERE sku=?", (sku,))
    conn.commit()
    conn.close()


def get_produtos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM produtos ORDER BY sku").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_custo_sku(sku):
    conn = get_conn()
    row = conn.execute(
        "SELECT custo_unitario, fornecedor FROM produtos WHERE sku=?", (sku,)
    ).fetchone()
    conn.close()
    if row:
        return row["custo_unitario"], row["fornecedor"]
    return 0.0, None


def insert_disputa(data: dict, importacao_id: int):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO disputas (
                id_devolucao, id_pedido, data_criacao, nome_comprador,
                nome_produto, sku_principal, nome_variacao, sku_variacao,
                preco_unitario, status_devolucao, tipo_devolucao, quantidade,
                solucao, motivo_devolucao, observacao_devolucao, valor_reembolsado,
                compensacao_vendedor, motivo_disputa, observacao_vendedor,
                valor_pago_comprador, metodo_pagamento, resultado_disputa,
                categoria_motivo, valor_perdido, custo_produto, prejuizo_estimado,
                resultado_financeiro, importacao_id
            ) VALUES (
                :id_devolucao, :id_pedido, :data_criacao, :nome_comprador,
                :nome_produto, :sku_principal, :nome_variacao, :sku_variacao,
                :preco_unitario, :status_devolucao, :tipo_devolucao, :quantidade,
                :solucao, :motivo_devolucao, :observacao_devolucao, :valor_reembolsado,
                :compensacao_vendedor, :motivo_disputa, :observacao_vendedor,
                :valor_pago_comprador, :metodo_pagamento, :resultado_disputa,
                :categoria_motivo, :valor_perdido, :custo_produto, :prejuizo_estimado,
                :resultado_financeiro, :importacao_id
            )
        """, {**data, "importacao_id": importacao_id})
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def create_importacao(nome_arquivo):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO importacoes (nome_arquivo, data_importacao) VALUES (?, ?)",
        (nome_arquivo, datetime.now().isoformat())
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def update_importacao(iid, total, novas, duplicadas):
    conn = get_conn()
    conn.execute(
        "UPDATE importacoes SET total_linhas=?, novas_linhas=?, duplicadas=? WHERE id=?",
        (total, novas, duplicadas, iid)
    )
    conn.commit()
    conn.close()


def get_importacoes():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM importacoes ORDER BY data_importacao DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_disputas(filtros=None):
    conn = get_conn()
    sql = "SELECT * FROM disputas WHERE 1=1"
    params = []
    if filtros:
        if filtros.get("data_inicio"):
            sql += " AND data_criacao >= ?"
            params.append(filtros["data_inicio"])
        if filtros.get("data_fim"):
            sql += " AND data_criacao <= ?"
            params.append(filtros["data_fim"] + " 23:59:59")
        if filtros.get("sku"):
            sql += " AND (sku_principal LIKE ? OR sku_variacao LIKE ?)"
            params += [f"%{filtros['sku']}%", f"%{filtros['sku']}%"]
        if filtros.get("produto"):
            sql += " AND nome_produto LIKE ?"
            params.append(f"%{filtros['produto']}%")
        if filtros.get("status"):
            sql += " AND status_devolucao = ?"
            params.append(filtros["status"])
        if filtros.get("resultado"):
            sql += " AND resultado_disputa = ?"
            params.append(filtros["resultado"])
        if filtros.get("motivo"):
            sql += " AND categoria_motivo = ?"
            params.append(filtros["motivo"])
        if filtros.get("fornecedor"):
            sql += " AND id IN (SELECT d.id FROM disputas d JOIN produtos p ON d.sku_principal=p.sku WHERE p.fornecedor LIKE ?)"
            params.append(f"%{filtros['fornecedor']}%")
    sql += " ORDER BY data_criacao DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def recalcular_financeiro():
    """Recalcula campos financeiros usando custos cadastrados"""
    conn = get_conn()
    disputas = conn.execute("SELECT * FROM disputas").fetchall()
    for d in disputas:
        d = dict(d)
        custo_unit, _ = get_custo_sku(d["sku_principal"] or "")
        qtd = d["quantidade"] or 1
        custo_prod = custo_unit * qtd
        val_perdido = max(0, (d["valor_reembolsado"] or 0) - (d["compensacao_vendedor"] or 0))
        prejuizo = val_perdido + custo_prod
        if prejuizo > 0:
            res_fin = "prejuízo"
        elif (d["compensacao_vendedor"] or 0) > 0:
            res_fin = "recuperado"
        else:
            res_fin = "neutro"
        conn.execute("""
            UPDATE disputas SET custo_produto=?, valor_perdido=?, prejuizo_estimado=?, resultado_financeiro=?
            WHERE id=?
        """, (custo_prod, val_perdido, prejuizo, res_fin, d["id"]))
    conn.commit()
    conn.close()
