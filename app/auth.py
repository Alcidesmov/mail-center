"""Senha de acesso ao Mail Center (obrigatória na VPS).

Sem `MAIL_CENTER_SENHA_HASH` no `.env` o app roda aberto — só é aceitável
em `localhost`. Na VPS, definir com `python -m app.definir_senha` antes de
subir o serviço. A senha nunca é gravada: só hash PBKDF2 + sal.
"""
import hashlib
import hmac
import secrets
import time

from app.config import carregar, gravar, obter_chave_cifra

COOKIE = "mc_sessao"
DURACAO_SEGUNDOS = 12 * 3600
_ITERACOES = 600_000
_falhas: list[float] = []  # janela global: brute force contra um painel de 1 usuário


def _hash(senha: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, _ITERACOES).hex()


def definir_senha(senha: str):
    sal = secrets.token_bytes(16)
    gravar("MAIL_CENTER_SENHA_HASH", f"{sal.hex()}${_hash(senha, sal)}")


def exigida() -> bool:
    return bool(carregar().get("MAIL_CENTER_SENHA_HASH"))


def senha_confere(senha: str) -> bool:
    guardado = carregar().get("MAIL_CENTER_SENHA_HASH", "")
    sal_hex, _, esperado = guardado.partition("$")
    if not esperado:
        return False
    return hmac.compare_digest(_hash(senha, bytes.fromhex(sal_hex)), esperado)


def bloqueado() -> bool:
    agora = time.time()
    _falhas[:] = [t for t in _falhas if agora - t < 600]
    return len(_falhas) >= 10


def registrar_falha():
    _falhas.append(time.time())


def _assinar(corpo: str) -> str:
    return hmac.new(obter_chave_cifra().encode(), corpo.encode(), hashlib.sha256).hexdigest()


def criar_sessao() -> str:
    expira = str(int(time.time()) + DURACAO_SEGUNDOS)
    return f"{expira}.{_assinar(expira)}"


def sessao_valida(valor: str | None) -> bool:
    if not valor or "." not in valor:
        return False
    expira, _, assinatura = valor.partition(".")
    if not expira.isdigit() or int(expira) < time.time():
        return False
    return hmac.compare_digest(assinatura, _assinar(expira))
