# Eleições 2026 — resultados, API do TSE e relatórios

> Documento do módulo Eleições do Mail Center. Complementa a seção 6.1 do
> `CLAUDE.md`. Dados de **1º turno (04/10/2026)**, 100% das seções apuradas
> (arquivo do TSE de 05/10/2026). 2º turno: 25/10/2026 (ver "Pendências").

## 1. API do TSE (pública, sem chave)

Índice das eleições: `https://resultados.tse.jus.br/oficial/comum/config/ele-c.json`
(em 05/10 ainda mostrava 02/10 — não confiar nele para saber se há resultado).

Arquivos de resultado (formato que **funciona**):

```
https://resultados.tse.jus.br/oficial/ele2026/<eleição>/dados/<uf>/<uf>-c<cargo>-e00<eleição>-u.json
```

| Cargo | Eleição | Cargo no arquivo | Abrangência |
|---|---|---|---|
| Presidente | 6257 | `0001` | `br` |
| Governador | 6259 | `0003` | `<uf>` (27 arquivos) |
| Senador | 6259 | `0005` | `<uf>` |
| Deputado Federal | 6259 | `0006` | `<uf>` |

- O caminho `dados-simplificados/…-r.json` dá **404** nesta eleição.
- O arquivo é uma árvore `carg[0].agr[].par[].cand[]`: agrupamento (federação/
  coligação) → partido → candidato. Campos úteis: `vap` (votos), `pvapn`
  (% dos votos válidos), `st` (situação), `e` (`s` = eleito), `n` (número).
- Totais do cargo: `v.vvc` (votos válidos), `v.vb` (brancos), `v.tvn`
  (nulos), `e.c` (comparecimento), `e.te` (eleitorado), `s.pst` (% seções).
- Fora do navegador (CORS 403): só dá para ler pelo servidor, como faz
  `app/eleicoes.py` (cache de 2 min).
- Situação de Dep. Federal (Eleito, Suplente…) pode vir **vazia** até a
  totalização final: em 05/10 só 390 de 513 vinham marcados.

## 2. Resultado: Presidente, 1º turno

100% apurado; comparecimento 125.275.835 (78,92% de 158.745.502); votos
válidos 119.300.788; brancos 2.300.798; nulos 3.669.003.

| Candidato | Partido | Votos | % válidos |
|---|---|---|---|
| Flávio Bolsonaro | PL | 56.104.503 | 47,03% |
| Lula | PT | 53.879.538 | 45,16% |
| Augusto Cury | Agir/Avante | 3.448.569 | 2,89% |
| Renan Santos | Missão | 2.675.887 | 2,24% |
| Ronaldo Caiado | PSD | 2.605.148 | 2,18% |
| Romeu Zema | Novo | 326.488 | 0,27% |
| Samara Martins | UP | 122.911 | 0,10% |
| Hertz Dias | PSTU | 43.103 | 0,04% |
| Clariana Zacarkim | DC | 40.043 | 0,03% |
| Edmilson Costa | PCB | 22.693 | 0,02% |
| Wilson Grassi | Democrata | 16.881 | 0,01% |
| Rui Costa Pimenta | PCO | 15.024 | 0,01% |

Flávio e Lula disputam o 2º turno em 25/10/2026.

## 3. Dep. Federal, Brasil (soma dos 27 estados)

Votos **nominais** em candidatos (sem votos de legenda). Total de votos
válidos do cargo: 114.059.101. Principais partidos:

| Partido | Votos | % válidos |
|---|---|---|
| PL | 25.206.796 | 22,10% |
| PT | 13.783.223 | 12,08% |
| PSD | 9.229.863 | 8,09% |
| Republicanos | 7.852.325 | 6,88% |
| União | 7.750.929 | 6,80% |
| MDB | 7.745.890 | 6,79% |
| PP | 7.392.286 | 6,48% |
| Podemos (PODE) | 5.835.697 | 5,12% |
| PSOL | 5.212.639 | 4,57% |
| PSB | 4.915.936 | 4,31% |
| Novo | 2.855.354 | 2,50% |
| PRD | 1.163.862 | 1,02% |

**Patriota não existe mais**: fundiu com o PTB em 2023 e virou o **PRD**.

## 4. Blocos e relatório (classificação editável — não é dado do TSE)

- **Conservadores (pedido do Alcides):** PL + PODE + PRD = **32.206.355**
  votos = **28,24%** dos válidos de Dep. Federal.
- **Direita ampla (sugestão da IA):** + Republicanos, PP, União, Novo, Missão,
  DC = 59.326.635 (52,01%).
- **Progressistas (sugestão da IA):** PT, PSOL, PSB, PDT, PCdoB, PV, Rede,
  PSTU, UP, PCO = 28.442.116.

**Relatório 1 — Deputados federais ÷ voto presidencial**
(votos do bloco × 0,98) ÷ votos do candidato do campo. "Menos 2%" foi
entendido como desconto de 2% sobre o total do bloco (alternativa não
adotada: 2 pontos percentuais dos votos válidos — confirmar com o Alcides).

| Bloco | Votos dep. fed. | − 2% | Candidato | Razão |
|---|---|---|---|---|
| Conservadores (PL, PODE, PRD) | 32.206.355 | 31.562.228 | Flávio: 56.104.503 | **0,563** (sem desconto 0,574) |
| Progressistas | 28.442.116 | 27.873.274 | Lula: 53.879.538 | **0,517** (sem desconto 0,528) |

"Direita ampla" ÷ Flávio dá 1,036 — **não usar como "votos de Flávio"**:
Republicanos, PP e União têm candidatos fora do campo dele.

## 5. Onde está o quê

- Módulo no Mail Center: aba `/eleicoes` (`app/eleicoes.py`,
  `app/templates/eleicoes.html`) — abas de cargo, filtros, "Por partido",
  "Blocos", CSV. **Falta portar o "Relatório 1"** para o módulo.
- Retrato mobile (Apuração + Blocos + Relatórios, dados embutidos de
  05/10/2026, não atualiza sozinho): artefato privado no claude.ai
  <https://claude.ai/artifact/X5aVkPWE9P7sxTNap3a1dB>. Não está no Git nem na
  VPS.
- Código: PR #1 (`feat/modulo-eleicoes`), ainda em rascunho. Nada no ar.

## 6. Pendências

1. Levar o Relatório 1 para o módulo do Mail Center.
2. Confirmar a leitura de "menos 2%".
3. 2º turno (25/10): achar os novos códigos de eleição em `ele-c.json`.
4. Publicar na VPS (ver `docs/DEPLOY_VPS.md`); sem VPS, o módulo e o link do
   artefato são as únicas formas de ver isso.
