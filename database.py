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

def reset_db():
    """Apaga todos os dados para comecar do zero"""
    conn = get_conn()
    conn.execute("DELETE FROM devolucoes")
    conn.execute("DELETE FROM disputas")
    conn.execute("DELETE FROM importacoes")
    try:
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('disputas','importacoes','devolucoes')")
    except:
        pass
    conn.commit()
    conn.close()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS importacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_arquivo TEXT,
            data_importacao TEXT,
            total_linhas INTEGER DEFAULT 0,
            novas_linhas INTEGER DEFAULT 0,
            duplicadas INTEGER DEFAULT 0,
            taxa_sucesso REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS disputas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            importacao_id INTEGER REFERENCES importacoes(id),
            id_solicitacao TEXT,
            sku_principal TEXT,
            nome_produto TEXT,
            data_criacao TEXT,
            data_resposta TEXT,
            status_devolucao TEXT DEFAULT 'pendente',
            resultado_disputa TEXT DEFAULT 'em_aberto',
            categoria_motivo TEXT,
            valor_pago_comprador REAL DEFAULT 0,
            custo_produto REAL DEFAULT 0,
            metodo_pagamento TEXT,
            valor_perdido REAL DEFAULT 0,
            prejuizo_estimado REAL DEFAULT 0,
            frete_devolucao REAL DEFAULT 20.0,
            produto_quebrado INTEGER DEFAULT 0,
            resultado_financeiro TEXT DEFAULT 'neutro',
            observacoes TEXT,
            fornecedor TEXT,
            categoria TEXT,
            custo_unitario REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS devolucoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rastreamento TEXT UNIQUE,
            id_pedido TEXT,
            disputa_id INTEGER REFERENCES disputas(id),
            produto_quebrado INTEGER DEFAULT 0,
            data_registro TEXT,
            observacoes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_disputas_sku ON disputas(sku_principal);
        CREATE INDEX IF NOT EXISTS idx_disputas_data ON disputas(data_criacao);
        CREATE INDEX IF NOT EXISTS idx_disputas_status ON disputas(status_devolucao);
        CREATE INDEX IF NOT EXISTS idx_disputas_resultado ON disputas(resultado_disputa);
        CREATE INDEX IF NOT EXISTS idx_devolucoes_rastreamento ON devolucoes(rastreamento);
        CREATE INDEX IF NOT EXISTS idx_devolucoes_pedido ON devolucoes(id_pedido);
    """)
    conn.commit()
    conn.close()

def _migrate_db():
    """Adiciona colunas novas se nao existirem"""
    conn = get_conn()
    c = conn.cursor()
    existing = {row[1] for row in c.execute("PRAGMA table_info(disputas)")}
    migrations = {
        "id_solicitacao": "TEXT",
        "frete_devolucao": "REAL DEFAULT 20.0",
        "produto_quebrado": "INTEGER DEFAULT 0",
        "observacoes": "TEXT",
    }
    for col, col_type in migrations.items():
        if col not in existing:
            c.execute(f"ALTER TABLE disputas ADD COLUMN {col} {col_type}")
    # tabela devolucoes
    try:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS devolucoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rastreamento TEXT UNIQUE,
                id_pedido TEXT,
                disputa_id INTEGER REFERENCES disputas(id),
                produto_quebrado INTEGER DEFAULT 0,
                data_registro TEXT,
                observacoes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_devolucoes_rastreamento ON devolucoes(rastreamento);
            CREATE INDEX IF NOT EXISTS idx_devolucoes_pedido ON devolucoes(id_pedido);
        """)
    except:
        pass
    conn.commit()
    conn.close()

def create_importacao(nome_arquivo):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO importacoes (nome_arquivo, data_importacao) VALUES (?,?)",
        (nome_arquivo, datetime.now().isoformat())
    )
    iid = c.lastrowid
    conn.commit()
    conn.close()
    return iid

def update_importacao(iid, total, novas, duplicadas):
    conn = get_conn()
    taxa = round(novas / total * 100, 1) if total else 0
    conn.execute(
        "UPDATE importacoes SET total_linhas=?, novas_linhas=?, duplicadas=?, taxa_sucesso=? WHERE id=?",
        (total, novas, duplicadas, taxa, iid)
    )
    conn.commit()
    conn.close()

def get_importacoes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM importacoes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_disputa(data: dict, importacao_id: int):
    conn = get_conn()
    data["importacao_id"] = importacao_id
    cols = [
        "importacao_id","id_solicitacao","sku_principal","nome_produto",
        "data_criacao","data_resposta","status_devolucao","resultado_disputa",
        "categoria_motivo","valor_pago_comprador","custo_produto","metodo_pagamento",
        "valor_perdido","prejuizo_estimado","frete_devolucao","produto_quebrado",
        "resultado_financeiro","observacoes","fornecedor","categoria","custo_unitario"
    ]
    vals = [data.get(c) for c in cols]
    placeholders = ",".join(["?" for _ in cols])
    conn.execute(
        f"INSERT OR IGNORE INTO disputas ({','.join(cols)}) VALUES ({placeholders})",
        vals
    )
    conn.commit()
    conn.close()

def get_disputas(filtros=None):
    conn = get_conn()
    q = "SELECT * FROM disputas WHERE 1=1"
    params = []
    if filtros:
        if filtros.get("status"):
            q += " AND status_devolucao=?"
            params.append(filtros["status"])
        if filtros.get("resultado"):
            q += " AND resultado_disputa=?"
            params.append(filtros["resultado"])
        if filtros.get("data_ini"):
            q += " AND data_criacao>=?"
            params.append(filtros["data_ini"])
        if filtros.get("data_fim"):
            q += " AND data_criacao<=?"
            params.append(filtros["data_fim"])
    q += " ORDER BY id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_disputa_campo(disputa_id: int, campo: str, valor):
    campos_permitidos = {
        "status_devolucao","resultado_disputa","categoria_motivo",
        "valor_perdido","custo_produto","prejuizo_estimado","resultado_financeiro",
        "produto_quebrado","frete_devolucao","id_solicitacao","observacoes"
    }
    if campo not in campos_permitidos:
        return
    conn = get_conn()
    conn.execute(f"UPDATE disputas SET {campo}=? WHERE id=?", (valor, disputa_id))
    conn.commit()
    conn.close()

def recalcular_financeiro():
    conn = get_conn()
    disputas = conn.execute("SELECT * FROM disputas").fetchall()
    for d in disputas:
        d = dict(d)
        custo_prod = d.get("custo_produto") or 0
        frete = d.get("frete_devolucao") or 20.0
        quebrado = d.get("produto_quebrado") or 0
        res = d.get("resultado_disputa", "em_aberto")

        if res in ("perdida", "sem_resposta"):
            val_perdido = d.get("valor_pago_comprador") or 0
            if quebrado:
                prejuizo = val_perdido + frete + custo_prod
            else:
                prejuizo = val_perdido + frete
            res_fin = "prejuizo"
        elif res == "ganha":
            val_perdido = 0
            if quebrado:
                prejuizo = frete + custo_prod
            else:
                prejuizo = frete
            res_fin = "recuperado" if prejuizo == 0 else "prejuizo_parcial"
        else:
            val_perdido = 0
            prejuizo = frete
            res_fin = "neutro"

        conn.execute("""
            UPDATE disputas SET valor_perdido=?, prejuizo_estimado=?, resultado_financeiro=?
            WHERE id=?
        """, (val_perdido, prejuizo, res_fin, d["id"]))
    conn.commit()
    conn.close()

# ── Devoluções ──────────────────────────────────────────────────────────────

def registrar_devolucao(rastreamento: str, id_pedido: str, produto_quebrado: bool, observacoes: str = ""):
    """Registra devolucao e vincula ao relatorio de disputa automaticamente"""
    conn = get_conn()
    # busca disputa pelo id_solicitacao ou sku
    disputa_id = None
    if id_pedido:
        row = conn.execute(
            "SELECT id FROM disputas WHERE id_solicitacao=? OR sku_principal=? LIMIT 1",
            (id_pedido, id_pedido)
        ).fetchone()
        if row:
            disputa_id = row[0]

    conn.execute("""
        INSERT OR REPLACE INTO devolucoes (rastreamento, id_pedido, disputa_id, produto_quebrado, data_registro, observacoes)
        VALUES (?,?,?,?,?,?)
    """, (rastreamento, id_pedido, disputa_id, 1 if produto_quebrado else 0,
          datetime.now().isoformat(), observacoes))

    # Se encontrou disputa, atualiza campo produto_quebrado e recalcula
    if disputa_id:
        conn.execute(
            "UPDATE disputas SET produto_quebrado=?, status_devolucao='devolvido' WHERE id=?",
            (1 if produto_quebrado else 0, disputa_id)
        )
    conn.commit()
    conn.close()

    # recalcula financeiro
    if disputa_id:
        recalcular_financeiro()

    return disputa_id

def get_devolucoes():
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, dis.sku_principal, dis.nome_produto, dis.id_solicitacao
        FROM devolucoes d
        LEFT JOIN disputas dis ON d.disputa_id = dis.id
        ORDER BY d.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Inicializa o banco
init_db()
_migrate_db()
