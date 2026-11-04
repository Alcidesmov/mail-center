# Relatório 1 — Deputados federais ÷ voto presidencial (1º turno 2026)

> Gerado em 07/10/2026 a partir da API do TSE (arquivo de 06/10/2026 16:58:18,
> 100% das seções). Reproduzível: aba **Relatórios**
> do módulo `/eleicoes` do Mail Center, ou `eleicoes.relatorio_dep_vs_presidente()`.

## Pergunta
Para cada campo político: quantos votos de Deputado Federal o bloco de partidos
recebeu, descontados 2%, em relação aos votos do candidato a presidente do campo?

**Fórmula:** `(soma dos votos nominais dos partidos do bloco × 0,98) ÷ votos do candidato`.
"Menos 2%" foi lido como desconto de 2% sobre o total do bloco. Leitura
alternativa (2 pontos percentuais dos votos válidos) **não adotada** — confirmar
com o Alcides.

## Resultado

| Bloco | Votos dep. fed. | − 2% | Candidato | Votos do candidato | Razão | Sem desconto |
|---|---|---|---|---|---|---|
| Conservadores (PL, PODE, PRD) | 32.206.355 | 31.562.228 | Flávio Bolsonaro | 56.104.503 | **0,563** | 0,574 |
| Progressistas | 28.441.344 | 27.872.517 | Lula | 53.879.538 | **0,517** | 0,528 |

Leitura: a cada 100 votos de Flávio, cerca de 56 foram para
deputados do núcleo conservador; a cada 100 votos de Lula, cerca de 52 foram
para deputados dos partidos progressistas.

## Composição dos blocos (votos nominais, Dep. Federal, Brasil)

Total de votos válidos de Dep. Federal: 114.058.329.

### Conservadores (definição do Alcides; Patriota = PRD desde 2023)
| Partido | Votos | % válidos |
|---|---|---|
| PL | 25.206.796 | 22.10% |
| PODE | 5.835.697 | 5.12% |
| PRD | 1.163.862 | 1.02% |

### Progressistas (classificação da IA, editável)
| Partido | Votos | % válidos |
|---|---|---|
| PT | 13.783.223 | 12.08% |
| PSOL | 5.212.639 | 4.57% |
| PSB | 4.915.164 | 4.31% |
| PDT | 1.664.840 | 1.46% |
| PCDOB | 1.271.806 | 1.12% |
| PV | 1.325.085 | 1.16% |
| REDE | 213.953 | 0.19% |
| PSTU | 12.578 | 0.01% |
| UP | 39.312 | 0.03% |
| PCO | 2.744 | 0.00% |

### Direita ampla (sugestão da IA, só para comparação)
Soma 59.326.635 (52.01% dos válidos); ÷ Flávio = 1,057 (sem desconto) /
1,036 (com desconto). **Não usar como "votos de Flávio"**: Republicanos, PP e União
têm candidatos fora do campo dele. Partidos: PL, PODE, PRD, REPUBLICANOS, PP, UNIÃO, NOVO, MISSÃO, DC.

## Limites
- Só votos em candidatos (sem legenda), por partido — federações não são
  somadas como unidade.
- Eleitores votam em cargos distintos; a razão é um indicador, não uma
  transferência de votos.
- PSD, MDB, PSDB e outros ficaram fora dos dois blocos.
- Dados do TSE mudam ao longo da apuração (ex.: PSB variou entre duas leituras
  de 05/10 e 07/10).
