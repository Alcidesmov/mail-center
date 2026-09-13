#!/bin/bash
# Mail Center — duplo clique para iniciar
cd "$(dirname "$0")"

echo "=============================================="
echo "  MAIL CENTER — Mensageria Movbank/Movcont/Clavion"
echo "=============================================="

# cria ambiente virtual na primeira execução
if [ ! -d ".venv" ]; then
  echo "Primeira execução: preparando ambiente (2-3 min)..."
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip -q
  ./.venv/bin/pip install -r requirements.txt -q
  echo "Ambiente pronto."
fi

echo "Iniciando... o navegador abre sozinho em localhost:8010."
echo "Para encerrar: feche esta janela ou pressione Ctrl+C."
./.venv/bin/python run.py
