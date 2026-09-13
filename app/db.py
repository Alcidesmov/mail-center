import sqlite3
from contextlib import contextmanager
from pathlib import Path

CAMINHO_DB = Path(__file__).resolve().parent.parent / "mail_center.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_exibicao TEXT NOT NULL,
    email TEXT NOT NULL,
    cor TEXT NOT NULL DEFAULT '#262e44',
    imap_host TEXT NOT NULL,
    imap_porta INTEGER NOT NULL DEFAULT 993,
    imap_usuario TEXT NOT NULL,
    smtp_host TEXT NOT NULL,
    smtp_porta INTEGER NOT NULL DEFAULT 587,
    smtp_usuario TEXT NOT NULL,
    senha_cifrada TEXT NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1,
    ultima_sincronizacao TEXT,
    ultimo_erro_sync TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pastas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    nome_exibicao TEXT NOT NULL,
    caminho_imap TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'OUTRA',
    ultimo_uid_sincronizado INTEGER NOT NULL DEFAULT 0,
    UNIQUE(conta_id, caminho_imap)
);

CREATE TABLE IF NOT EXISTS mensagens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conta_id INTEGER NOT NULL REFERENCES contas(id) ON DELETE CASCADE,
    pasta_id INTEGER NOT NULL REFERENCES pastas(id) ON DELETE CASCADE,
    uid_imap INTEGER,
    message_id TEXT,
    em_resposta_a TEXT,
    remetente_nome TEXT,
    remetente_email TEXT,
    destinatarios TEXT NOT NULL DEFAULT '[]',
    cc TEXT NOT NULL DEFAULT '[]',
    bcc TEXT NOT NULL DEFAULT '[]',
    assunto TEXT NOT NULL DEFAULT '(sem assunto)',
    corpo_texto TEXT NOT NULL DEFAULT '',
    corpo_html TEXT,
    data_hora TEXT NOT NULL,
    lida INTEGER NOT NULL DEFAULT 0,
    texto_busca TEXT NOT NULL DEFAULT '',
    UNIQUE(conta_id, pasta_id, uid_imap)
);
CREATE INDEX IF NOT EXISTS idx_mensagens_pasta ON mensagens(pasta_id, data_hora DESC);
CREATE INDEX IF NOT EXISTS idx_mensagens_busca ON mensagens(texto_busca);

CREATE TABLE IF NOT EXISTS anexos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mensagem_id INTEGER NOT NULL REFERENCES mensagens(id) ON DELETE CASCADE,
    nome_arquivo TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    tamanho INTEGER NOT NULL DEFAULT 0,
    caminho_disco TEXT NOT NULL
);
"""


def conectar():
    con = sqlite3.connect(CAMINHO_DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def iniciar_banco():
    with conectar() as con:
        con.executescript(SCHEMA)


@contextmanager
def sessao():
    con = conectar()
    try:
        yield con
        con.commit()
    finally:
        con.close()
