"""Criptografia das senhas de e-mail (IMAP/SMTP) salvas no banco.

Mesmo espírito do módulo Procuração do ERP ContFácil: a senha em claro
nunca fica gravada — só o valor cifrado. A chave fica no `.env`, gerada
sozinha no primeiro boot (ver config.py).
"""
from cryptography.fernet import Fernet


def cifrar(senha_em_claro: str, chave: str) -> str:
    return Fernet(chave.encode()).encrypt(senha_em_claro.encode()).decode()


def decifrar(senha_cifrada: str, chave: str) -> str:
    return Fernet(chave.encode()).decrypt(senha_cifrada.encode()).decode()


def gerar_chave() -> str:
    return Fernet.generate_key().decode()
