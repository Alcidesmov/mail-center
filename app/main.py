import json
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from starlette.datastructures import FormData

from app import db, imap_sync, smtp_send
from app.config import obter_intervalo_sync_minutos
from app.crypto import cifrar
from app.config import obter_chave_cifra
from app.normalizar import normalizar
from app.web import render

app = FastAPI(title="Mail Center")

CORES_SUGERIDAS = ["#262e44", "#5c73c1", "#8a6e43", "#1f7a5c", "#a13d3d", "#6b3fa0"]


# --------------------------------------------------------------------------
# Painel principal / caixa de entrada
# --------------------------------------------------------------------------

@app.get("/")
def raiz():
    with db.sessao() as con:
        conta = con.execute("SELECT * FROM contas WHERE ativo=1 ORDER BY id LIMIT 1").fetchone()
    if not conta:
        return RedirectResponse("/contas")
    with db.sessao() as con:
        pasta = con.execute(
            "SELECT * FROM pastas WHERE conta_id=? AND tipo='INBOX' LIMIT 1", (conta["id"],)
        ).fetchone()
    if pasta:
        return RedirectResponse(f"/caixa/{conta['id']}/{pasta['id']}")
    return RedirectResponse(f"/contas?destaque={conta['id']}")


def _barra_lateral(con) -> list[dict]:
    contas = [dict(r) for r in con.execute("SELECT * FROM contas WHERE ativo=1 ORDER BY nome_exibicao")]
    for conta in contas:
        pastas = [dict(r) for r in con.execute(
            """SELECT p.*, (SELECT COUNT(*) FROM mensagens m WHERE m.pasta_id=p.id AND m.lida=0) AS nao_lidas
               FROM pastas p WHERE p.conta_id=?
               ORDER BY CASE p.tipo WHEN 'INBOX' THEN 0 WHEN 'ENVIADOS' THEN 1
                                     WHEN 'RASCUNHOS' THEN 2 ELSE 3 END, p.nome_exibicao""",
            (conta["id"],),
        )]
        conta["pastas"] = pastas
    return contas


@app.get("/caixa/{conta_id}/{pasta_id}")
def caixa(request: Request, conta_id: int, pasta_id: int, msg: int | None = None, q: str | None = None):
    with db.sessao() as con:
        contas = _barra_lateral(con)
        conta = con.execute("SELECT * FROM contas WHERE id=?", (conta_id,)).fetchone()
        pasta = con.execute("SELECT * FROM pastas WHERE id=? AND conta_id=?", (pasta_id, conta_id)).fetchone()
        if not conta or not pasta:
            return RedirectResponse("/")

        if q:
            termo = normalizar(q)
            mensagens = con.execute(
                """SELECT * FROM mensagens WHERE pasta_id=? AND texto_busca LIKE ?
                   ORDER BY data_hora DESC LIMIT 200""",
                (pasta_id, f"%{termo}%"),
            ).fetchall()
        else:
            mensagens = con.execute(
                "SELECT * FROM mensagens WHERE pasta_id=? ORDER BY data_hora DESC LIMIT 200", (pasta_id,)
            ).fetchall()
        mensagens = [dict(m) for m in mensagens]
        for m in mensagens:
            m["destinatarios"] = json.loads(m["destinatarios"] or "[]")

        mensagem_aberta = None
        anexos = []
        if msg:
            linha = con.execute("SELECT * FROM mensagens WHERE id=? AND pasta_id=?", (msg, pasta_id)).fetchone()
            if linha:
                mensagem_aberta = dict(linha)
                mensagem_aberta["destinatarios"] = json.loads(mensagem_aberta["destinatarios"] or "[]")
                mensagem_aberta["cc"] = json.loads(mensagem_aberta["cc"] or "[]")
                anexos = [dict(a) for a in con.execute("SELECT * FROM anexos WHERE mensagem_id=?", (msg,))]
                if not mensagem_aberta["lida"]:
                    con.execute("UPDATE mensagens SET lida=1 WHERE id=?", (msg,))
                    if mensagem_aberta["uid_imap"]:
                        threading.Thread(
                            target=imap_sync.marcar_como_lida,
                            args=(conta_id, pasta["caminho_imap"], mensagem_aberta["uid_imap"]),
                            daemon=True,
                        ).start()

    return render(request, "caixa.html", {
        "contas": contas, "conta": dict(conta), "pasta": dict(pasta),
        "mensagens": mensagens, "mensagem_aberta": mensagem_aberta, "anexos": anexos,
        "termo_busca": q or "",
    })


@app.post("/contas/{conta_id}/sincronizar")
def sincronizar_conta_rota(conta_id: int):
    ok, texto = imap_sync.sincronizar_conta(conta_id)
    with db.sessao() as con:
        pasta = con.execute(
            "SELECT * FROM pastas WHERE conta_id=? AND tipo='INBOX' LIMIT 1", (conta_id,)
        ).fetchone()
    destino = f"/caixa/{conta_id}/{pasta['id']}" if pasta else "/contas"
    separador = "&" if "?" in destino else "?"
    return RedirectResponse(f"{destino}{separador}sync_ok={int(ok)}&sync_msg={texto}", status_code=303)


# --------------------------------------------------------------------------
# Contas (multi-conta: Movbank, Movcont, Clavion, ...)
# --------------------------------------------------------------------------

@app.get("/contas")
def contas_listar(request: Request, destaque: int | None = None):
    with db.sessao() as con:
        contas = [dict(r) for r in con.execute("SELECT * FROM contas ORDER BY ativo DESC, nome_exibicao")]
    return render(request, "contas.html", {"contas": contas, "destaque": destaque, "cores": CORES_SUGERIDAS})


@app.post("/contas")
def contas_criar(
    nome_exibicao: str = Form(...), email: str = Form(...), cor: str = Form("#262e44"),
    imap_host: str = Form(...), imap_porta: int = Form(993), imap_usuario: str = Form(...),
    smtp_host: str = Form(...), smtp_porta: int = Form(587), smtp_usuario: str = Form(...),
    senha: str = Form(...),
):
    ok_imap, erro_imap = imap_sync.testar_conexao(imap_host, imap_porta, imap_usuario, senha)
    ok_smtp, erro_smtp = smtp_send.testar_conexao_smtp(smtp_host, smtp_porta, smtp_usuario, senha)

    if not ok_imap or not ok_smtp:
        erro = "; ".join(filter(None, [
            f"IMAP: {erro_imap}" if not ok_imap else "",
            f"SMTP: {erro_smtp}" if not ok_smtp else "",
        ]))
        return RedirectResponse(f"/contas?erro={erro}", status_code=303)

    senha_cifrada = cifrar(senha, obter_chave_cifra())
    with db.sessao() as con:
        cur = con.execute(
            """INSERT INTO contas (nome_exibicao, email, cor, imap_host, imap_porta, imap_usuario,
                                    smtp_host, smtp_porta, smtp_usuario, senha_cifrada)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome_exibicao, email, cor, imap_host, imap_porta, imap_usuario,
             smtp_host, smtp_porta, smtp_usuario, senha_cifrada),
        )
        conta_id = cur.lastrowid

    imap_sync.sincronizar_conta(conta_id)
    return RedirectResponse(f"/contas?destaque={conta_id}", status_code=303)


@app.post("/contas/{conta_id}/ativo")
def contas_alternar_ativo(conta_id: int):
    with db.sessao() as con:
        con.execute("UPDATE contas SET ativo = 1 - ativo WHERE id=?", (conta_id,))
    return RedirectResponse("/contas", status_code=303)


@app.post("/contas/{conta_id}/excluir")
def contas_excluir(conta_id: int):
    with db.sessao() as con:
        con.execute("DELETE FROM contas WHERE id=?", (conta_id,))
    return RedirectResponse("/contas", status_code=303)


# --------------------------------------------------------------------------
# Compor / responder / encaminhar / enviar
# --------------------------------------------------------------------------

@app.get("/compor")
def compor(request: Request, conta_id: int, mensagem_id: int | None = None, modo: str | None = None):
    with db.sessao() as con:
        contas = [dict(r) for r in con.execute("SELECT * FROM contas WHERE ativo=1 ORDER BY nome_exibicao")]
        original = None
        if mensagem_id:
            linha = con.execute("SELECT * FROM mensagens WHERE id=?", (mensagem_id,)).fetchone()
            if linha:
                original = dict(linha)
                original["destinatarios"] = json.loads(original["destinatarios"] or "[]")

    prefill = {"para": "", "assunto": "", "corpo": "", "em_resposta_a": ""}
    if original and modo == "responder":
        prefill["para"] = original["remetente_email"]
        prefill["assunto"] = _com_prefixo(original["assunto"], "Re:")
        prefill["corpo"] = _corpo_citado(original)
        prefill["em_resposta_a"] = original["message_id"] or ""
    elif original and modo == "encaminhar":
        prefill["assunto"] = _com_prefixo(original["assunto"], "Fwd:")
        prefill["corpo"] = _corpo_citado(original)

    return render(request, "compor.html", {"contas": contas, "conta_id": conta_id, "prefill": prefill})


def _com_prefixo(assunto: str, prefixo: str) -> str:
    assunto = assunto or "(sem assunto)"
    return assunto if assunto.lower().startswith(prefixo.lower()) else f"{prefixo} {assunto}"


def _corpo_citado(original: dict) -> str:
    corpo = original.get("corpo_html") or (original.get("corpo_texto") or "").replace("\n", "<br>")
    return (
        f'<br><br><div style="border-left:2px solid #d6d8d5;padding-left:12px;color:#40444D">'
        f'Em {original.get("data_hora","")}, {original.get("remetente_nome") or original.get("remetente_email")} escreveu:'
        f'<br>{corpo}</div>'
    )


@app.post("/enviar")
async def enviar(request: Request):
    form: FormData = await request.form()
    conta_id = int(form["conta_id"])
    destinatarios = [e.strip() for e in form.get("para", "").split(",") if e.strip()]
    cc = [e.strip() for e in form.get("cc", "").split(",") if e.strip()]
    bcc = [e.strip() for e in form.get("bcc", "").split(",") if e.strip()]
    assunto = form.get("assunto", "")
    corpo_html = form.get("corpo", "")
    em_resposta_a = form.get("em_resposta_a") or None

    anexos = []
    for valor in form.getlist("anexos"):
        if isinstance(valor, UploadFile) and valor.filename:
            conteudo = await valor.read()
            if conteudo:
                anexos.append((valor.filename, conteudo))

    ok, texto = smtp_send.enviar_email(conta_id, destinatarios, cc, bcc, assunto, corpo_html, anexos, em_resposta_a)

    with db.sessao() as con:
        pasta = con.execute(
            "SELECT * FROM pastas WHERE conta_id=? AND tipo='INBOX' LIMIT 1", (conta_id,)
        ).fetchone()
    destino = f"/caixa/{conta_id}/{pasta['id']}" if pasta else "/contas"
    return RedirectResponse(f"{destino}?envio_ok={int(ok)}&envio_msg={texto}", status_code=303)


# --------------------------------------------------------------------------
# Anexos
# --------------------------------------------------------------------------

@app.get("/anexo/{anexo_id}")
def baixar_anexo(anexo_id: int):
    with db.sessao() as con:
        linha = con.execute("SELECT * FROM anexos WHERE id=?", (anexo_id,)).fetchone()
    if not linha:
        return RedirectResponse("/")
    caminho = Path(linha["caminho_disco"])
    if not caminho.exists():
        return RedirectResponse("/")
    return FileResponse(caminho, filename=linha["nome_arquivo"], media_type=linha["content_type"])


# --------------------------------------------------------------------------
# Boot: banco + sincronização automática em segundo plano
# --------------------------------------------------------------------------

def _rotina_sincronizacao_automatica():
    while True:
        intervalo_min = obter_intervalo_sync_minutos()
        time.sleep(intervalo_min * 60)
        try:
            with db.sessao() as con:
                ids = [r["id"] for r in con.execute("SELECT id FROM contas WHERE ativo=1")]
            for conta_id in ids:
                imap_sync.sincronizar_conta(conta_id)
        except Exception:
            continue  # best-effort — próximo ciclo tenta de novo, nunca derruba o servidor


@app.on_event("startup")
def iniciar():
    db.iniciar_banco()
    threading.Thread(target=_rotina_sincronizacao_automatica, daemon=True).start()
