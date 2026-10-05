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
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MailCenter/0.2"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise ErroTSE(f"TSE não respondeu ({url.rsplit('/', 1)[-1]}): {exc}") from exc
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
