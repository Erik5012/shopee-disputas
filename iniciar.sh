#!/bin/bash
# ================================================
# Gestão de Disputas Shopee — Script de inicialização
# ================================================

echo ""
echo "🛍️  Gestão de Disputas Shopee"
echo "================================"

# Vai para o diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Instala dependências se necessário
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 Instalando dependências..."
    pip install -r requirements.txt
fi

echo "🚀 Iniciando o sistema..."
echo "   Acesse: http://localhost:8501"
echo ""
streamlit run app.py --server.port 8501
