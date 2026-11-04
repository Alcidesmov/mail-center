"""Resultados das urnas (TSE) — Presidente, Governador, Senador e Dep. Federal.

Lê os JSONs públicos de `resultados.tse.jus.br` (os mesmos do app Resultados
do TSE) e devolve uma lista plana de candidatos, pronta para a tela filtrar
por nome, partido, voto e percentual. `urllib` da biblioteca padrão — zero
dependência nova, mesmo espírito do `imap_sync`.
"""
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://resultados.tse.jus.br/oficial/ele2026"
TTL_SEGUNDOS = 120  # apuração pode ser republicada; 2 min evita martelar o TSE

# cargo -> (código da eleição, código do cargo no nome do arquivo, rótulo)
CARGOS = {
    "presidente": ("6257", "0001", "Presidente"),
    "governador": ("6259", "0003", "Governador"),
    "senador": ("6259", "0005", "Senador"),
    "deputado_federal": ("6259", "0006", "Deputado Federal"),
}

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

_cache: dict = {}
_trava = threading.Lock()


class ErroTSE(Exception):
    pass


def _baixar(url: str) -> dict:
    with _trava:
        item = _cache.get(url)
        if item and time.time() - item[0] < TTL_SEGUNDOS:
            return item[1]
    ultimo_erro = None
    for tentativa in range(3):  # o TSE devolve 403/5xx esporádico sob carga; 27 UFs em paralelo
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MailCenter/0.2"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
            break
        except Exception as exc:
            ultimo_erro = exc
            time.sleep(0.8 * (tentativa + 1))
    else:
        raise ErroTSE(f"TSE não respondeu ({url.rsplit('/', 1)[-1]}): {ultimo_erro}") from ultimo_erro
    with _trava:
        _cache[url] = (time.time(), dados)
    return dados


def _num(txt) -> float:
    try:
        return float(str(txt).replace(",", "."))
    except ValueError:
        return 0.0


def _url(cargo: str, uf: str) -> str:
    ele, cod, _ = CARGOS[cargo]
    uf = uf.lower()
    return f"{BASE}/{ele}/dados/{uf}/{uf}-c{cod}-e00{ele}-u.json"


def _achatar(dados: dict, cargo: str, uf: str) -> tuple[list, dict]:
    carg = dados["carg"][0]
    candidatos = []
    for agr in carg.get("agr", []):
        for par in agr.get("par", []):
            for c in par.get("cand", []):
                vices = [v.get("nmu") or v.get("nm") for v in c.get("vs", [])]
                candidatos.append({
                    "uf": uf.upper(),
                    "cargo": cargo,
                    "numero": c.get("n", ""),
                    "nome": c.get("nm", ""),
                    "nome_urna": c.get("nmu") or c.get("nm", ""),
                    "partido": par.get("sg", ""),
                    "agrupamento": agr.get("nm", ""),
                    "composicao": agr.get("com", ""),
                    "votos": int(c.get("vap") or 0),
                    "pct": _num(c.get("pvapn") or c.get("pvap")),
                    "situacao": c.get("st") or "",
                    "eleito": c.get("e") == "s",
                    "vices": [v for v in vices if v],
                })
    v, s, e = dados.get("v", {}), dados.get("s", {}), dados.get("e", {})
    resumo = {
        "atualizado": f"{dados.get('dt', '')} {dados.get('ht', '')}".strip(),
        "secoes_apuradas_pct": _num(s.get("pst")),
        "comparecimento": int(e.get("c") or 0),
        "comparecimento_pct": _num(e.get("pcn") or e.get("pc")),
        "eleitorado": int(e.get("te") or 0),
        "votos_validos": int(v.get("vvc") or 0),
        "brancos": int(v.get("vb") or 0),
        "nulos": int(v.get("tvn") or 0),
        "vagas": int(carg.get("nv") or 0),
    }
    return candidatos, resumo


def resultados(cargo: str, uf: str) -> dict:
    """`uf` = sigla, ou 'BR' (Presidente) / 'TODOS' (soma dos 27 estados)."""
    if cargo not in CARGOS:
        raise ErroTSE("Cargo inválido.")
    uf = uf.upper()
    if cargo == "presidente":
        uf = "BR"
    if uf == "TODOS" and cargo != "presidente":
        with ThreadPoolExecutor(max_workers=9) as pool:
            partes = list(pool.map(lambda u: _achatar(_baixar(_url(cargo, u)), cargo, u), UFS))
        candidatos = [c for cands, _ in partes for c in cands]
        resumos = [r for _, r in partes]
        resumo = {
            "atualizado": max(r["atualizado"] for r in resumos),
            "secoes_apuradas_pct": min(r["secoes_apuradas_pct"] for r in resumos),
            "comparecimento": sum(r["comparecimento"] for r in resumos),
            "eleitorado": sum(r["eleitorado"] for r in resumos),
            "votos_validos": sum(r["votos_validos"] for r in resumos),
            "brancos": sum(r["brancos"] for r in resumos),
            "nulos": sum(r["nulos"] for r in resumos),
            "vagas": sum(r["vagas"] for r in resumos),
        }
        resumo["comparecimento_pct"] = round(100 * resumo["comparecimento"] / max(resumo["eleitorado"], 1), 2)
        # no agregado nacional o % é sobre os válidos do cargo no país, não do estado
        for c in candidatos:
            c["pct"] = round(100 * c["votos"] / max(resumo["votos_validos"], 1), 2)
    else:
        if uf != "BR" and uf not in UFS:
            raise ErroTSE("UF inválida.")
        candidatos, resumo = _achatar(_baixar(_url(cargo, uf)), cargo, uf)
    candidatos.sort(key=lambda c: c["votos"], reverse=True)
    if cargo == "presidente" and candidatos and candidatos[0]["pct"] <= 50:
        for c in candidatos[:2]:
            c["situacao"] = c["situacao"] or "2º turno"
    return {"candidatos": candidatos, "resumo": resumo, "cargo": cargo, "uf": uf}


def relatorio_dep_vs_presidente() -> dict:
    """Relatório 1: votos nominais por partido (Dep. Federal, Brasil) e votos
    dos dois presidenciáveis que disputam o 2º turno. Os blocos (quem é
    "conservador"/"progressista") e o desconto são escolhidos na tela."""
    pres = resultados("presidente", "BR")
    dep = resultados("deputado_federal", "TODOS")
    partidos: dict = {}
    for c in dep["candidatos"]:
        partidos[c["partido"]] = partidos.get(c["partido"], 0) + c["votos"]

    def achar(trecho: str):
        for c in pres["candidatos"]:
            if trecho in c["nome"].upper():
                return {"nome": c["nome_urna"], "votos": c["votos"], "partido": c["partido"]}
        return None

    return {
        "partidos": partidos,
        "flavio": achar("BOLSONARO"),
        "lula": achar("LULA"),
        "votos_validos_dep": dep["resumo"]["votos_validos"],
        "atualizado": dep["resumo"]["atualizado"],
        "secoes_apuradas_pct": min(dep["resumo"]["secoes_apuradas_pct"], pres["resumo"]["secoes_apuradas_pct"]),
    }


# --------------------------------------------------------------------------
# Mapa do 2º turno (Presidente) — eleição 6258, 25/10/2026
# --------------------------------------------------------------------------

ELEICAO_PRES_2T = "6258"
_DADOS = Path(__file__).resolve().parent / "dados"


def _url_2t(chave: str) -> str:
    c = chave.lower()  # uf em minúsculo, "br" ou "zz" (exterior)
    return f"{BASE}/{ELEICAO_PRES_2T}/dados/{c}/{c}-c0001-e00{ELEICAO_PRES_2T}-u.json"


def _ler_2t(dados: dict, chave: str) -> dict:
    """Lula (13) e Flávio Bolsonaro (22) num arquivo de 2º turno. Confere
    número e nome para nunca trocar os candidatos."""
    nomes, votos = {}, {}
    for agr in dados["carg"][0].get("agr", []):
        for par in agr.get("par", []):
            for c in par.get("cand", []):
                votos[c["n"]] = int(c.get("vap") or 0)
                nomes[c["n"]] = c.get("nm", "").upper()
    if set(votos) != {"13", "22"} or "LULA" not in nomes["13"] or "BOLSONARO" not in nomes["22"]:
        raise ErroTSE(f"Candidatos inesperados no arquivo de {chave}: {nomes}")
    v, e, s = dados.get("v", {}), dados.get("e", {}), dados.get("s", {})
    return {
        "lula": votos["13"], "flavio": votos["22"],
        "brancos": int(v.get("vb") or 0), "nulos": int(v.get("tvn") or 0),
        "compar": int(e.get("c") or 0), "eleitorado": int(e.get("te") or 0),
        "comparecimento_pct": _num(e.get("pcn") or e.get("pc")),
        "secoes_pct": _num(s.get("pst")), "hora": dados.get("ht", ""), "data": dados.get("dt", ""),
    }


def mapa_turno2() -> dict:
    """Votos de Lula e Flávio por UF + Brasil + exterior, e a conferência de
    que UFs + exterior fecham com o total do Brasil."""
    geo = json.loads((_DADOS / "br_estados_geo.json").read_text(encoding="utf-8"))
    chaves = UFS + ["BR", "ZZ"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        lidos = dict(zip(chaves, pool.map(lambda k: _ler_2t(_baixar(_url_2t(k)), k), chaves)))
    br, zz = lidos["BR"], lidos["ZZ"]
    res = {u: {k: lidos[u][k] for k in ("lula", "flavio", "brancos", "nulos", "compar", "eleitorado")} for u in UFS}
    soma_l = sum(res[u]["lula"] for u in UFS) + zz["lula"]
    soma_f = sum(res[u]["flavio"] for u in UFS) + zz["flavio"]
    dif_l, dif_f = br["lula"] - soma_l, br["flavio"] - soma_f
    return {
        "geo": geo,
        "res": res,
        "br": {
            "lula": br["lula"], "flavio": br["flavio"], "brancos": br["brancos"], "nulos": br["nulos"],
            "compar": br["compar"], "comparecimento_pct": br["comparecimento_pct"],
            "secoes_pct": min(x["secoes_pct"] for x in lidos.values()),
            "hora": br["hora"], "data": br["data"],
        },
        "ext": {"lula": zz["lula"], "flavio": zz["flavio"]},
        "verificacao": {"ok": dif_l == 0 and dif_f == 0, "dif_lula": dif_l, "dif_flavio": dif_f},
    }


def pagina_mapa_turno2() -> str:
    """Página completa (HTML) do mapa, com os dados de agora embutidos."""
    dados = json.dumps(mapa_turno2(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    miolo = (_DADOS / "mapa_turno2.html").read_text(encoding="utf-8").replace("__DATA__", dados)
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
            '<body style="margin:0">' + miolo + "</body></html>")
