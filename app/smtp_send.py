"""Envio de e-mail via SMTP + cópia na pasta Enviados via IMAP APPEND.

Depois de enviar, tenta gravar a cópia na pasta Enviados do provedor (APPEND)
e sincronizar só aquela pasta na hora — assim a mensagem enviada aparece na
UI com o UID real do servidor, sem duplicar quando a sincronização periódica
rodar de novo.
"""
import imaplib
import mimetypes
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from app import db
from app.config import obter_chave_cifra
from app.crypto import decifrar
from app.imap_sync import conectar_imap, sincronizar_pasta


def _montar_mensagem(conta: dict, destinatarios: list[str], cc: list[str], bcc: list[str],
                      assunto: str, corpo_html: str, anexos: list[tuple], em_resposta_a: str | None):
    msg = MIMEMultipart("mixed")
    msg["From"] = f'{conta["nome_exibicao"]} <{conta["email"]}>'
    msg["To"] = ", ".join(destinatarios)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = assunto or "(sem assunto)"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if em_resposta_a:
        msg["In-Reply-To"] = em_resposta_a
        msg["References"] = em_resposta_a

    alternativo = MIMEMultipart("alternative")
    texto_simples = corpo_html.replace("<br>", "\n").replace("<br/>", "\n")
    import re as _re
    texto_simples = _re.sub("<[^>]+>", "", texto_simples)
    alternativo.attach(MIMEText(texto_simples, "plain", "utf-8"))
    alternativo.attach(MIMEText(corpo_html, "html", "utf-8"))
    msg.attach(alternativo)

    for nome_arquivo, conteudo in anexos:
        tipo, _ = mimetypes.guess_type(nome_arquivo)
        tipo = tipo or "application/octet-stream"
        parte = MIMEApplication(conteudo, Name=nome_arquivo)
        parte["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
        msg.attach(parte)

    return msg


def enviar_email(conta_id: int, destinatarios: list[str], cc: list[str], bcc: list[str],
                  assunto: str, corpo_html: str, anexos: list[tuple] | None = None,
                  em_resposta_a: str | None = None) -> tuple[bool, str]:
    anexos = anexos or []
    with db.sessao() as con:
        linha = con.execute("SELECT * FROM contas WHERE id=?", (conta_id,)).fetchone()
    if not linha:
        return False, "Conta não encontrada"
    conta = dict(linha)
    senha = decifrar(conta["senha_cifrada"], obter_chave_cifra())

    msg = _montar_mensagem(conta, destinatarios, cc, bcc, assunto, corpo_html, anexos, em_resposta_a)
    todos_destinos = destinatarios + cc + bcc

    try:
        if int(conta["smtp_porta"]) == 465:
            servidor = smtplib.SMTP_SSL(conta["smtp_host"], conta["smtp_porta"], timeout=30)
        else:
            servidor = smtplib.SMTP(conta["smtp_host"], conta["smtp_porta"], timeout=30)
            servidor.starttls()
        servidor.login(conta["smtp_usuario"], senha)
        servidor.sendmail(conta["email"], todos_destinos, msg.as_bytes())
        servidor.quit()
    except Exception as exc:  # noqa: BLE001
        return False, f"Falha ao enviar: {exc}"

    _copiar_para_enviados(conta, msg.as_bytes())
    return True, "Enviado com sucesso"


def testar_conexao_smtp(smtp_host, smtp_porta, smtp_usuario, senha_em_claro) -> tuple[bool, str]:
    try:
        smtp_porta = int(smtp_porta)
        if smtp_porta == 465:
            servidor = smtplib.SMTP_SSL(smtp_host, smtp_porta, timeout=15)
        else:
            servidor = smtplib.SMTP(smtp_host, smtp_porta, timeout=15)
            servidor.starttls()
        servidor.login(smtp_usuario, senha_em_claro)
        servidor.quit()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _copiar_para_enviados(conta: dict, mensagem_bruta: bytes) -> None:
    try:
        with db.sessao() as con:
            pasta = con.execute(
                "SELECT * FROM pastas WHERE conta_id=? AND tipo='ENVIADOS'", (conta["id"],)
            ).fetchone()
        if not pasta:
            return
        pasta = dict(pasta)
        conn = conectar_imap(conta)
        conn.append(f'"{pasta["caminho_imap"]}"', "\\Seen", imaplib.Time2Internaldate(__import__("time").time()),
                    mensagem_bruta)
        sincronizar_pasta(conn, conta["id"], pasta)
        conn.logout()
    except Exception:
        pass  # best-effort — o e-mail já foi enviado; só a cópia local na UI pode atrasar até o próximo sync
