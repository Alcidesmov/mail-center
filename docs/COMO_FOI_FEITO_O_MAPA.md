# Como foi feito o mapa do 2º turno por estado

> Explicação do mapa **"Mapa do 2º turno"** do módulo Eleições do Mail Center
> (`/eleicoes/mapa-2turno`) e do artefato equivalente no claude.ai. Escrito em
> 04/11/2026. Para dados e resultados, ver `docs/ELEICOES_2026.md`.

## 1. O que o mapa mostra

- Três botões: **Lula**, **Flávio** e **Vencedor**.
  - **Lula** e **Flávio**: o percentual dos votos válidos de cada um em cada
    estado, em tons de vermelho (Lula) e de azul (Flávio). Quanto mais escuro,
    mais voto.
  - **Vencedor**: quem ganhou no estado e por quantos pontos percentuais.
- Ao lado do mapa: um quadro com os números do estado que o mouse está em cima,
  o ranking dos 27 estados e, se você pedir, a tabela completa.
- No topo: o placar nacional (Lula 51,79% × Flávio 48,21%).

## 2. De onde vêm os números

Os votos vêm da **API pública do TSE**, os mesmos arquivos que o site do TSE
carrega quando você clica em "Presidente / 2º turno". Não precisa de login.

```
https://resultados.tse.jus.br/oficial/ele2026/6258/dados/<uf>/<uf>-c0001-e006258-u.json
```

- `6258` é a eleição "Federal, 2º turno" (o 1º turno de Presidente é `6257`).
- `<uf>` é a sigla em minúsculas (`sp`, `pi`…), mais dois arquivos especiais:
  `br` (Brasil inteiro) e `zz` (votos no exterior).
- São 29 arquivos por leitura. Cada um traz, por candidato, o número (`n`), o nome
  (`nm`) e os votos (`vap`), e os totais de brancos, nulos e comparecimento.

**Como evitamos erro** (`app/eleicoes.py`, funções `_ler_2t` e `mapa_turno2`):

1. O código confere que o arquivo tem **só dois candidatos**, o 13 com "LULA" no
   nome e o 22 com "BOLSONARO". Se vier outra coisa, ele para com erro, em vez
   de trocar os candidatos.
2. Confere que **soma dos 27 estados + exterior = total do Brasil**, para Lula e
   para Flávio. No dia 04/11 a diferença deu **zero**. Se algum dia der
   diferente, a página mostra um aviso no rodapé.
3. O TSE às vezes devolve erro 403 de passagem. A leitura tenta até 3 vezes e
   guarda o resultado por 2 minutos (cache), para não sobrecarregar o servidor.

## 3. O desenho dos estados

- Os contornos vêm de um arquivo público de estados do Brasil
  (`click_that_hood`, derivado do IBGE). O site do IBGE recusou a conexão do
  ambiente, então usei esse espelho.
- Passos (feitos uma vez; o resultado está em `app/dados/br_estados_geo.json`):
  1. **Projeção**: cada ponto (longitude, latitude) vira um ponto plano:
     `x = (lon + 74,1) × cos(14°) × 15` e `y = (5,4 − lat) × 15`. O `cos(14°)`
     evita que o Brasil fique "esticado" para os lados.
  2. **Simplificação**: tolerância de 0,045 grau (cerca de 5 km), para a página
     ficar leve (35 KB os 27 estados). Os pontos viram caminhos SVG (`M x,y L x,y …`).
  3. **Limpeza**: ilhas oceânicas distantes (Fernando de Noronha, Trindade) foram
     retiradas, para o mapa não ficar largo demais.
  4. Para cada estado guardei também um ponto de rótulo dentro dele.
- Rótulos: sigla dentro de cada estado. Os pequenos do litoral do Nordeste
  (**RN, PB, PE, AL, SE**) ganham um quadradinho de cor e uma linha que sai para o
  mar, espaçados de 15 em 15 unidades para não se sobreporem.

## 4. As cores (e por que azul e vermelho)

- Seguem o método de gráficos com cores **validadas por script** para daltonismo
  e contraste. O par azul × vermelho passou em todos os testes, nos modos claro e
  escuro (distância de cor 21,6 para daltônicos e 32,3 para visão normal; o
  mínimo exigido é 8 e 15).
- **Lula = vermelho, Flávio = azul**.
- **Mapas de cada candidato** (escala "sequencial"): 6 faixas de % dos votos
  válidos, com a mesma régua para os dois, para dar para comparar:
  `menos de 30% · 30–40 · 40–50 · 50–60 · 60–70 · 70% ou mais`.
  A rampa vermelha foi derivada da azul, mantendo a mesma luminosidade em cada
  degrau (cálculo em espaço de cor OKLCH), então os dois mapas "pesam" igual.
- **Mapa "Vencedor"** (escala "divergente"): cinza no meio (menos de 2 pontos de
  diferença, só Minas Gerais), e 4 degraus de cada lado: `2–10 · 10–20 · 20–35 ·
  35 pontos ou mais`.
- A cor do **texto da sigla** (branco ou preto) é escolhida pela luminosidade do
  fundo do estado, para sempre ler bem (função `lum`).
- No modo escuro, as rampas são invertidas: valores baixos ficam escuros (somem
  no fundo) e os altos ficam claros.

## 5. A página (`app/dados/mapa_turno2.html`)

- É **um arquivo só**, sem biblioteca externa: HTML, CSS e um JavaScript
  pequeno. Os dados chegam no lugar de `__DATA__`, como JSON dentro da página
  (o servidor faz isso em `pagina_mapa_turno2()`).
- O mapa é um **SVG desenhado pelo JavaScript**: para cada estado, um `<g>` com
  um `<path>`. Tudo que vem do TSE entra com `textContent`, nunca como HTML.
- Os botões Lula/Flávio/Vencedor só trocam a **função de cor** (`cor()`),
  repintam, trocam a legenda e reordenam o ranking.
- Funciona no celular (a página empilha em uma coluna) e tem modo claro e escuro
  automáticos.

## 6. O efeito ao passar o mouse ("ficar branquinho")

É isto que você gostou. O estado **não muda de cor de preenchimento**: ele ganha
um **contorno forte**, e esse contorno usa a cor do texto do tema
(`--ink`: **escuro no tema claro e branco no tema escuro**). No tema escuro,
por isso, parece que o estado "acende" de branco.

O que acontece, em ordem (`mapa_turno2.html`, função `marcar`):

1. O mouse entra no estado (`mouseenter`) e o código chama `setHov(uf)`.
2. O estado recebe a classe `hov`. O CSS dessa classe faz o contorno ficar mais
   grosso e da cor do texto:
   ```css
   .uf.sel path, .uf.hov path { stroke: var(--ink); stroke-width: 2.2 }
   ```
3. O estado é **levado para o topo** do desenho (`gp.append(gs[hov])`), senão o
   contorno ficaria escondido atrás dos vizinhos.
4. A mesma linha no **ranking** ao lado ganha um fundo cinza claro
   (`.rank li.hov`), e o **quadro de detalhe** passa a mostrar os votos, o %, a
   margem, o comparecimento, os brancos e os nulos daquele estado.
5. Quando o mouse sai (`mouseleave`), tudo volta: o quadro mostra o Brasil de novo
   (ou o estado que você tiver **clicado**, que fica marcado até clicar de novo).

Funciona também no sentido contrário: passar o mouse numa **linha do ranking**
acende o estado correspondente no mapa. No celular, o **toque** faz o papel do
mouse. Pelo teclado, a tecla Tab chega em cada estado e Enter o seleciona.

Se você quiser que o estado realmente **clareie** (fique mais branco) em vez de só
ganhar contorno, é uma mudança pequena: acrescentar à regra `.uf.hov path` algo
como `filter: brightness(1.25)`. É só pedir.

## 7. Onde estão os arquivos

| O quê | Onde |
|---|---|
| Leitura do TSE e conferência | `app/eleicoes.py` (`_ler_2t`, `mapa_turno2`, `pagina_mapa_turno2`) |
| Rota da página | `app/main.py` (`/eleicoes/mapa-2turno`) |
| Página (HTML + CSS + JS) | `app/dados/mapa_turno2.html` |
| Contornos dos estados | `app/dados/br_estados_geo.json` |
| Botão de acesso | `app/templates/eleicoes.html` ("🗺 Mapa do 2º turno") |
| Cópia em artefato (dados embutidos de 25/10) | <https://claude.ai/artifact/Di3tsCie3fzhrVjLFQb2Fe> |

## 8. Como refazer para outra eleição

1. Descobrir o código da eleição em
   `https://resultados.tse.jus.br/oficial/comum/config/ele-c.json`
   (para o 1º turno de Presidente é `6257`).
2. Trocar `ELEICAO_PRES_2T` em `app/eleicoes.py` e ajustar `_ler_2t`: no 1º turno
   há **12 candidatos**, e hoje a função exige só 2.
3. Com mais de 2 candidatos, o mapa "Vencedor" precisa de **uma cor por
   candidato** (no máximo 3 cores distintas por mapa, pelo método de cores
   validado) ou de um mapa por candidato, como já são os de Lula e de Flávio.

## 9. Limites que ficam

- **Exterior** não aparece no mapa (não é um estado). Ele entra no total do
  Brasil e na tabela (Lula 200.154 × Flávio 171.497).
- O **desenho é simplificado**: serve para ler o resultado, não para medir
  fronteiras.
- Nomes dos estados **pequenos** (DF, ES, RJ) ficam pequenos no celular. O
  quadro de detalhe e o ranking resolvem.
- A página **não foi testada** com outro navegador além do Chromium, e não
  está publicada na VPS.
