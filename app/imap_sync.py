"""Sincronização IMAP: conecta na caixa de e-mail, descobre as pastas
(Entrada/Enviados/Rascunhos/Lixeira) e baixa mensagens novas para o
SQLite local. Best-effort por conta — uma conta com erro (senha expirada,
provedor fora do ar) não derruba a sincronização das demais, mesmo padrão
do sync do Notion no ERP ContFácil: loga o erro em `contas.ultimo_erro_sync`
e segue.
"""
import email
import imaplib
import json
import re
from datetime import datetime, timezone
from email.header import decode_header, make_header
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from pathlib import Path

from app import db
from app.config import obter_chave_cifra
from app.crypto import decifrar
from app.normalizar import normalizar

RAIZ_ANEXOS = Path(__file__).resolve().parent.parent / "anexos"
LIMITE_PRIMEIRA_SINCRONIZACAO = 150

PALAVRAS_ENVIADOS = ("sent", "enviad")
PALAVRAS_RASCUNHOS = ("draft", "rascunho")
PALAVRAS_LIXEIRA = ("trash", "lixeira", "deleted", "exclu")
PALAVRAS_SPAM = ("spam", "junk", "lixo eletr")


def _tipo_da_pasta(nome_imap: str) -> str:
    baixo = nome_imap.lower()
    if baixo in ("inbox",):
        return "INBOX"
    if any(p in baixo for p in PALAVRAS_ENVIADOS):
        return "ENVIADOS"
    if any(p in baixo for p in PALAVRAS_RASCUNHOS):
        return "RASCUNHOS"
    if any(p in baixo for p in PALAVRAS_LIXEIRA):
        return "LIXEIRA"
    if any(p in baixo for p in PALAVRAS_SPAM):
        return "SPAM"
    return "OUTRA"


def _decodificar_cabecalho(valor) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except Exception:
        return str(valor)


def _decodificar_payload(parte) -> str:
    bruto = parte.get_payload(decode=True) or b""
    charset = parte.get_content_charset() or "utf-8"
    try:
        return bruto.decode(charset, errors="replace")
    except (LookupError, TypeError):
        return bruto.decode("utf-8", errors="replace")


def _enderecos(campo: str) -> list[dict]:
    if not campo:
        return []
    return [{"nome": nome, "email": end} for nome, end in getaddresses([campo]) if end]


def conta_para_dict(linha) -> dict:
    return dict(linha)


def conectar_imap(conta: dict) -> imaplib.IMAP4_SSL:
    senha = decifrar(conta["senha_cifrada"], obter_chave_cifra())
    conn = imaplib.IMAP4_SSL(conta["imap_host"], conta["imap_porta"])
    conn.login(conta["imap_usuario"], senha)
    return conn


def testar_conexao(imap_host, imap_porta, imap_usuario, senha_em_claro) -> tuple[bool, str]:
    try:
        conn = imaplib.IMAP4_SSL(imap_host, int(imap_porta))
        conn.login(imap_usuario, senha_em_claro)
        conn.logout()
        return True, ""
    except Exception as exc:  # noqa: BLE001 — reportar qualquer falha de login/rede pro usuário
        return False, str(exc)


def _listar_pastas_imap(conn) -> list[str]:
    status, dados = conn.list()
    nomes = []
    if status != "OK":
        return nomes
    for linha in dados:
        if not linha:
            continue
        texto = linha.decode(errors="replace") if isinstance(linha, bytes) else str(linha)
        m = re.search(r'"([^"]*)"\s*$', texto)
        if m:
            nomes.append(m.group(1))
        else:
            nomes.append(texto.split()[-1].strip('"'))
    return nomes


def detectar_e_gravar_pastas(conta_id: int, conn) -> list[dict]:
    nomes = _listar_pastas_imap(conn)
    pastas = []
    with db.sessao() as con:
        for nome in nomes:
            tipo = _tipo_da_pasta(nome)
            nome_exibicao = {
                "INBOX": "Entrada", "ENVIADOS": "Enviados",
                "RASCUNHOS": "Rascunhos", "LIXEIRA": "Lixeira", "SPAM": "Spam",
            }.get(tipo, nome)
            con.execute(
                """INSERT INTO pastas (conta_id, nome_exibicao, caminho_imap, tipo)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(conta_id, caminho_imap) DO UPDATE SET tipo=excluded.tipo""",
                (conta_id, nome_exibicao, nome, tipo),
            )
        pastas = [dict(r) for r in con.execute(
            "SELECT * FROM pastas WHERE conta_id=? ORDER BY (tipo='INBOX') DESC, nome_exibicao",
            (conta_id,),
        )]
    return pastas


def _parsear_mensagem(bruto: bytes, uid: int) -> dict:
    msg = email.message_from_bytes(bruto)
    assunto = _decodificar_cabecalho(msg.get("Subject")) or "(sem assunto)"
    nome_de, email_de = parseaddr(_decodificar_cabecalho(msg.get("From", "")))
    destinatarios = _enderecos(_decodificar_cabecalho(msg.get("To", "")))
    cc = _enderecos(_decodificar_cabecalho(msg.get("Cc", "")))
    bcc = _enderecos(_decodificar_cabecalho(msg.get("Bcc", "")))
    message_id = msg.get("Message-ID", "") or ""
    em_resposta_a = msg.get("In-Reply-To", "") or ""

    try:
        data_hora = parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc).isoformat()
    except Exception:
        data_hora = datetime.now(timezone.utc).isoformat()

    corpo_texto, corpo_html, anexos = "", None, []
    if msg.is_multipart():
        for parte in msg.walk():
            disposicao = str(parte.get("Content-Disposition") or "")
            tipo = parte.get_content_type()
            nome_arquivo = parte.get_filename()
            if "attachment" in disposicao or (nome_arquivo and tipo not in ("text/plain", "text/html")):
                if nome_arquivo:
                    conteudo = parte.get_payload(decode=True) or b""
                    anexos.append((_decodificar_cabecalho(nome_arquivo), tipo, conteudo))
            elif tipo == "text/plain" and not corpo_texto:
                corpo_texto = _decodificar_payload(parte)
            elif tipo == "text/html" and corpo_html is None:
                corpo_html = _decodificar_payload(parte)
    else:
        conteudo = _decodificar_payload(msg)
        if msg.get_content_type() == "text/html":
            corpo_html = conteudo
        else:
            corpo_texto = conteudo

    if not corpo_texto and corpo_html:
        corpo_texto = re.sub("<[^>]+>", " ", corpo_html)

    texto_busca = normalizar(f"{assunto} {nome_de} {email_de} {corpo_texto[:2000]}")

    return {
        "uid_imap": uid, "message_id": message_id, "em_resposta_a": em_resposta_a,
        "remetente_nome": nome_de, "remetente_email": email_de,
        "destinatarios": json.dumps(destinatarios, ensure_ascii=False),
        "cc": json.dumps(cc, ensure_ascii=False), "bcc": json.dumps(bcc, ensure_ascii=False),
        "assunto": assunto, "corpo_texto": corpo_texto, "corpo_html": corpo_html,
        "data_hora": data_hora, "texto_busca": texto_busca, "anexos": anexos,
    }


def _salvar_anexos_em_disco(conta_id: int, mensagem_id: int, anexos: list[tuple]) -> None:
    if not anexos:
        return
    pasta_destino = RAIZ_ANEXOS / str(conta_id) / str(mensagem_id)
    pasta_destino.mkdir(parents=True, exist_ok=True)
    with db.sessao() as con:
        for nome_arquivo, tipo, conteudo in anexos:
            nome_seguro = re.sub(r"[^\w.\-() ]", "_", nome_arquivo or "anexo")[:150] or "anexo"
            caminho = pasta_destino / nome_seguro
            caminho.write_bytes(conteudo)
            con.execute(
                """INSERT INTO anexos (mensagem_id, nome_arquivo, content_type, tamanho, caminho_disco)
                   VALUES (?, ?, ?, ?, ?)""",
                (mensagem_id, nome_seguro, tipo or "application/octet-stream", len(conteudo), str(caminho)),
            )


def sincronizar_pasta(conn, conta_id: int, pasta: dict) -> int:
    status, _ = conn.select(f'"{pasta["caminho_imap"]}"', readonly=True)
    if status != "OK":
        return 0

    ultimo_uid = pasta["ultimo_uid_sincronizado"] or 0
    if ultimo_uid == 0:
        status, dados = conn.uid("search", None, "ALL")
        todos_uids = [int(u) for u in dados[0].split()] if status == "OK" and dados[0] else []
        uids_para_buscar = sorted(todos_uids)[-LIMITE_PRIMEIRA_SINCRONIZACAO:]
    else:
        status, dados = conn.uid("search", None, f"UID {ultimo_uid + 1}:*")
        encontrados = [int(u) for u in dados[0].split()] if status == "OK" and dados[0] else []
        uids_para_buscar = [u for u in encontrados if u > ultimo_uid]

    novas = 0
    maior_uid = ultimo_uid
    for uid in uids_para_buscar:
        status, dados = conn.uid("fetch", str(uid), "(RFC822)")
        if status != "OK" or not dados or not dados[0]:
            continue
        bruto = dados[0][1]
        try:
            parsed = _parsear_mensagem(bruto, uid)
        except Exception:
            continue

        with db.sessao() as con:
            cur = con.execute(
                """INSERT OR IGNORE INTO mensagens
                   (conta_id, pasta_id, uid_imap, message_id, em_resposta_a, remetente_nome,
                    remetente_email, destinatarios, cc, bcc, assunto, corpo_texto, corpo_html,
                    data_hora, texto_busca, lida)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           CASE WHEN ? = 'ENVIADOS' THEN 1 ELSE 0 END)""",
                (conta_id, pasta["id"], parsed["uid_imap"], parsed["message_id"], parsed["em_resposta_a"],
                 parsed["remetente_nome"], parsed["remetente_email"], parsed["destinatarios"], parsed["cc"],
                 parsed["bcc"], parsed["assunto"], parsed["corpo_texto"], parsed["corpo_html"],
                 parsed["data_hora"], parsed["texto_busca"], pasta["tipo"]),
            )
            if cur.rowcount:
                novas += 1
                mensagem_id = cur.lastrowid
                _salvar_anexos_em_disco(conta_id, mensagem_id, parsed["anexos"])
        maior_uid = max(maior_uid, uid)

    if maior_uid != ultimo_uid:
        with db.sessao() as con:
            con.execute("UPDATE pastas SET ultimo_uid_sincronizado=? WHERE id=?", (maior_uid, pasta["id"]))
    return novas


def sincronizar_conta(conta_id: int) -> tuple[bool, str]:
    with db.sessao() as con:
        linha = con.execute("SELECT * FROM contas WHERE id=?", (conta_id,)).fetchone()
    if not linha:
        return False, "Conta não encontrada"
    conta = conta_para_dict(linha)

    try:
        conn = conectar_imap(conta)
    except Exception as exc:  # noqa: BLE001
        erro = f"Falha ao conectar: {exc}"
        with db.sessao() as con:
            con.execute("UPDATE contas SET ultimo_erro_sync=? WHERE id=?", (erro, conta_id))
        return False, erro

    try:
        pastas = detectar_e_gravar_pastas(conta_id, conn)
        total_novas = 0
        for pasta in pastas:
            if pasta["tipo"] in ("LIXEIRA", "SPAM"):
                continue
            total_novas += sincronizar_pasta(conn, conta_id, pasta)
        with db.sessao() as con:
            con.execute(
                "UPDATE contas SET ultima_sincronizacao=?, ultimo_erro_sync=NULL WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), conta_id),
            )
        return True, f"{total_novas} mensagem(ns) nova(s)"
    except Exception as exc:  # noqa: BLE001
        erro = f"Falha durante sincronização: {exc}"
        with db.sessao() as con:
            con.execute("UPDATE contas SET ultimo_erro_sync=? WHERE id=?", (erro, conta_id))
        return False, erro
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def marcar_como_lida(conta_id: int, pasta_caminho_imap: str, uid_imap: int) -> None:
    with db.sessao() as con:
        linha = con.execute("SELECT * FROM contas WHERE id=?", (conta_id,)).fetchone()
    if not linha:
        return
    conta = conta_para_dict(linha)
    try:
        conn = conectar_imap(conta)
        conn.select(f'"{pasta_caminho_imap}"', readonly=False)
        conn.uid("store", str(uid_imap), "+FLAGS", "(\\Seen)")
        conn.logout()
    except Exception:
        pass  # best-effort — o estado "lida" já foi gravado localmente antes desta chamada
