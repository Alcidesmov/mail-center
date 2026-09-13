"""Configuração local (.env) — chave de cifra das senhas + intervalo de sync.

Segue o mesmo padrão de `app/config_local.py` do ERP ContFácil: `.env` na
raiz do projeto, nunca versionado, gerado/atualizado em linha em vez de
exigir edição manual.
"""
from pathlib import Path

from app.crypto import gerar_chave

CAMINHO_ENV = Path(__file__).resolve().parent.parent / ".env"


def carregar() -> dict:
    valores = {}
    if CAMINHO_ENV.exists():
        for linha in CAMINHO_ENV.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores


def gravar(chave: str, valor: str):
    valores = carregar()
    valores[chave] = valor
    linhas = [f"{k}={v}" for k, v in valores.items()]
    CAMINHO_ENV.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def obter_chave_cifra() -> str:
    valores = carregar()
    chave = valores.get("MAIL_CENTER_CHAVE_CIFRA", "")
    if not chave:
        chave = gerar_chave()
        gravar("MAIL_CENTER_CHAVE_CIFRA", chave)
    return chave


def obter_intervalo_sync_minutos() -> int:
    valores = carregar()
    try:
        return max(1, int(valores.get("MAIL_CENTER_INTERVALO_SYNC_MIN", "5")))
    except ValueError:
        return 5
