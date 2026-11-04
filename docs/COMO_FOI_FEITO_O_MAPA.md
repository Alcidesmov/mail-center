# Como foi feito o mapa do 2º turno — guia para reaproveitar em outro projeto

> Escrito em 04/11/2026. Descreve o mapa **"Mapa do 2º turno"** do Mail Center
> (`/eleicoes/mapa-2turno`) e do artefato equivalente no claude.ai.
> **Todos os blocos de código (CSS e JavaScript) abaixo foram copiados automaticamente do arquivo real**
> `app/dados/mapa_turno2.html`, por script, e não digitados à mão (exceto o esquema da seção 2.1,
> que é um resumo meu). Se o arquivo mudar,
> o arquivo é a verdade e este guia precisa ser regerado.
> Dados e resultados da eleição: `docs/ELEICOES_2026.md`.

## 0. Resumo rápido (o que levar para o outro projeto)

| Para quê | O que copiar |
|---|---|
| A página inteira (HTML + CSS + JS, sem biblioteca externa) | `app/dados/mapa_turno2.html` (os dados entram no lugar de `__DATA__`) |
| Os contornos dos 27 estados | `app/dados/br_estados_geo.json` (ou refaça com `scripts/mapa/gerar_geo.py`) |
| As rampas de cor | os `:root` do CSS (seção 6) e `scripts/mapa/rampas.py` |
| Leitura e conferência dos dados do TSE | `app/eleicoes.py` (`_ler_2t`, `mapa_turno2`, `pagina_mapa_turno2`) |

**Aviso de versão:** a primeira versão (artefato "versão 1" e commit `a411570`) tinha um erro de
teclado: o código movia o estado dentro do desenho para ele ficar por cima, e o navegador
**tirava o foco** do estado. Está corrigido com um contorno em camada própria (seção 5.3).
Se você copiou a versão antiga, troque pela atual.

## 1. O que o mapa mostra

- Três botões: **Lula**, **Flávio** e **Vencedor**.
  - **Lula** e **Flávio**: o % dos votos válidos de cada um em cada estado, em tons de
    vermelho (Lula) e de azul (Flávio). Mais escuro = mais voto (no tema claro).
  - **Vencedor**: quem ganhou e por quantos pontos percentuais (pp).
- Ao lado: um quadro com os números do estado sob o mouse, o ranking dos 27 estados e, a pedido,
  a tabela completa (botão "Ver tabela completa").
- No topo: o placar nacional, uma barra vermelha/azul e uma frase-resumo.

## 2. De onde vêm os números

API pública do TSE (os mesmos arquivos que o site do TSE carrega), sem login:

```
https://resultados.tse.jus.br/oficial/ele2026/6258/dados/<uf>/<uf>-c0001-e006258-u.json
```

- `6258` = eleição "Federal, 2º turno" (o 1º turno de Presidente é `6257`).
- `<uf>` em minúsculas (`sp`…), mais `br` (Brasil) e `zz` (exterior). São 29 arquivos por leitura.
- De cada arquivo o código usa: número do candidato (`n`), nome (`nm`), votos (`vap`), brancos (`v.vb`),
  nulos (`v.tvn`), comparecimento (`e.c`, `e.pcn`), eleitorado (`e.te`), seções apuradas (`s.pst`),
  data e hora do arquivo (`dt`, `ht`).

**Conferências automáticas** (`app/eleicoes.py`):

1. O arquivo precisa ter **exatamente dois candidatos**: o `13` com "LULA" no nome e o `22` com
   "BOLSONARO". Se vier outra coisa, a leitura falha com erro; nunca troca os candidatos.
2. **Soma dos 27 estados + exterior = total do Brasil**, para cada candidato. Em 04/11/2026 a
   diferença deu **zero**. Se algum dia der diferente, a página escreve um aviso no rodapé.
3. O TSE às vezes devolve erro 403 de passagem: a leitura tenta até 3 vezes e guarda o resultado
   por 2 minutos.

**Conferência feita na preparação deste guia:** os percentuais que a página calcula
(`100 × votos ÷ (Lula + Flávio)`) foram comparados com o `pvap` que o próprio TSE informa, em
**28 de 28 arquivos** (27 estados + Brasil), arredondados em 2 casas: **todos iguais**.

### 2.1 Formato dos dados que a página recebe (`D`)

```
D = {
  geo: { W, H, maxx, uf: { SP: { nome, d, cx, cy }, ... } },   // contornos (seção 3)
  res: { SP: { lula, flavio, brancos, nulos, compar, eleitorado }, ... },   // 27 UFs
  br:  { lula, flavio, brancos, nulos, compar, comparecimento_pct, secoes_pct, hora, data },
  ext: { lula, flavio },                                            // exterior
  verificacao: { ok, dif_lula, dif_flavio }                         // conferência dos totais
}
```

## 3. O desenho dos estados

- Contornos: arquivo público `click_that_hood` (derivado do IBGE). O site do IBGE recusou a
  conexão do ambiente, por isso o espelho.
- Script: `scripts/mapa/gerar_geo.py` (refeito neste guia: **o resultado é idêntico** ao
  `br_estados_geo.json` em uso). Parâmetros exatos:
  - **Projeção:** `x = (lon + 74,1) × cos(14°) × 15` e `y = (5,4 − lat) × 15`. O `cos(14°)` evita o
    Brasil "esticado" para os lados. `15` = unidades do desenho por grau.
  - **Simplificação:** tolerância `0,045` grau (cerca de 5 km), com `preserve_topology`. Resultado:
    cerca de 35 KB para os 27 estados.
  - **Limpeza:** descartam-se polígonos com centro a leste de −34,8° (Noronha, Trindade) e os com
    área menor que `0,04` grau².
  - **Ponto do rótulo:** `representative_point()` do maior polígono (sempre dentro do estado).
  - **Caixa do desenho:** `W` = maior x + 70 (sobra à direita para os rótulos do mar), `H` = maior y + 4.
- **Rótulos:** a sigla fica dentro do estado. Os pequenos do litoral do Nordeste (**RN, PB, PE, AL, SE**)
  ganham quadradinho de cor + linha até o mar, a 10 unidades da costa e espaçados de, no mínimo, 15
  unidades na vertical. O **DF** fica com rótulo dentro (é pequeno e se sobrepõe um pouco ao GO).
- Tudo é SVG desenhado pelo JavaScript: um `<g class="uf">` com um `<path>` por estado. O que vem do
  TSE entra sempre com `textContent`, nunca como HTML.

## 4. Formato dos números

Há **três funções**, todas em português do Brasil (`toLocaleString('pt-BR')`):

```js
const nI=v=>Number(v).toLocaleString('pt-BR');
const nP=v=>Number(v).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})+'%';
const nM=v=>(v>0?'+':v<0?'−':'')+Math.abs(v).toLocaleString('pt-BR',{minimumFractionDigits:1,maximumFractionDigits:1})+' pp';
```

| Função | Regra | Exemplos (conferidos no Chromium) |
|---|---|---|
| `nI` (votos, inteiros) | ponto a cada 3 casas, sem decimais | `0` → `0` · `999` → `999` · `1000` → `1.000` · `64256232` → `64.256.232` |
| `nP` (percentual) | **sempre 2 casas**, vírgula, `%` colado no número | `0` → `0,00%` · `48.205` → `48,21%` · `51.79` → `51,79%` · `100` → `100,00%` · `0.004` → `0,00%` · `0.005` → `0,01%` |
| `nM` (margem em pontos percentuais) | **1 casa**, sinal `+` ou `−`, espaço e `pp` | `3.6` → `+3,6 pp` · `-7.7` → `−7,7 pp` · `51.76` → `+51,8 pp` · `0` → `0,0 pp` |

Detalhes que importam (e pegadinhas):

1. O sinal de menos de `nM` é o **menos tipográfico `−` (U+2212)**, não o hífen `-`. O espaço antes de
   `pp` é um espaço comum.
2. **Pegadinha conhecida:** uma margem muito pequena mostra o sinal mesmo quando o número arredonda
   para zero: `0.04` → `+0,0 pp` e `-0.04` → `−0,0 pp`. Só `0` exato vira `0,0 pp`. No resultado real
   isso não apareceu (a menor margem foi Minas Gerais, `+0,9 pp`), mas pode aparecer em outra eleição.
3. Arredondamento: é o do `Intl` do navegador (meio sempre para cima, em valor absoluto), sobre o
   número calculado em ponto flutuante. Para comparar com outra fonte, confira a 3ª casa.
4. **Base do percentual:** votos válidos = Lula + Flávio (sem brancos e nulos).
5. No quadro de detalhe a frase "à frente por X pp" usa a margem **sem sinal**:
   `nM(Math.abs(r.m)).replace('+','')` → `7,7 pp`.
6. Comparecimento de um estado = `compar ÷ eleitorado × 100`; o do Brasil usa o `pcn` do TSE
   (`80,781133379` → `80,78%`).
7. Larguras das barras usam o número **sem arredondar**.
8. **Constante escondida:** na barra do ranking "Vencedor" o tamanho é `|margem| ÷ 52 × 50 %` (máximo
   metade da barra para cada lado). `52` é a maior margem arredondada desta eleição (PI, `+51,8`).
   **Em outra eleição, troque o 52.**

Onde cada formato aparece: votos (`nI`) no placar, no detalhe, na tabela e no rodapé; percentual (`nP`)
no placar, no detalhe, no ranking, na tabela e no `aria-label` dos estados; margem (`nM`) no ranking
"Vencedor" e na tabela. A diferença nacional (`4.430.191 votos`) usa `nI`.

## 5. Regras do mouse, do toque e do teclado

### 5.1 Tabela de regras (o que acontece, em ordem)

| Ação | O que acontece |
|---|---|
| **Mouse entra num estado** | `hov` = esse estado. Aparece um **contorno** em volta dele (cor `--ink`: escuro no tema claro, quase branco no tema escuro). O quadro de detalhe passa a mostrar o estado. A linha dele no ranking ganha fundo cinza (`--neutral`). |
| **Mouse sai** | o contorno de hover some e o quadro volta ao estado **clicado** ou, se não houver, ao **Brasil** |
| **Clique num estado** | `sel` = esse estado; **clicar de novo no mesmo desmarca**. Fica marcado (contorno fixo + linha do ranking com fundo) até desmarcar ou escolher outro |
| **Hover e clique ao mesmo tempo** | o quadro mostra o que está **sob o mouse** (`hov` tem prioridade sobre `sel`); os dois contornos aparecem |
| **Mouse numa linha do ranking** | faz o mesmo que passar o mouse no estado do mapa (e vice-versa). Clique na linha seleciona o estado |
| **Teclado: Tab** | passa de estado em estado, na ordem do arquivo (AC, AL, AM, AP…; DF por último). O foco **já mostra** o contorno e o detalhe, como o hover |
| **Teclado: Enter ou Espaço** | seleciona/desmarca o estado focado (`preventDefault` evita a rolagem da página no Espaço) |
| **Teclado: sair do estado** | o foco sai (`blur`) → some o contorno de hover |
| **Toque (celular)** | o navegador converte o toque em mouse + clique: mostra o detalhe e seleciona (testado só em emulação de toque do Chromium, não em celular de verdade). O detalhe deve permanecer até tocar em outro lugar |
| **Troca de botão (Lula/Flávio/Vencedor)** | repinta o mapa, troca legenda e título, reordena o ranking; **a seleção continua**. A escolha fica no `localStorage` (`mapa2t_view`) |
| **Mudança de tema** (claro/escuro) | as siglas são repintadas (a cor do texto depende da cor resolvida do fundo) |

O estado **não muda de cor de preenchimento** no hover; só ganha o contorno. No tema escuro o contorno é
quase branco (`#f0efec`) e, como a rampa escura é invertida (seção 6), os estados de votação alta ficam
claros: é isso que dá o ar de "branquinho" ao passar o mouse na Bahia ou no Piauí.

### 5.2 O CSS dessas regras

```css
.uf path{stroke:var(--surface);stroke-width:1.1;stroke-linejoin:round;cursor:pointer;transition:opacity .12s}
.uf:focus-visible{outline:none}
.ring{fill:none;stroke:var(--ink);stroke-width:2.2;stroke-linejoin:round;pointer-events:none}
.oc{pointer-events:none}
.rot{font:700 12.5px var(--font);pointer-events:none}
.rank li{display:grid;grid-template-columns:2.4em 1fr 5.2em;gap:8px;align-items:center;padding:3px 4px;border-radius:6px;cursor:pointer}
.rank li.hov,.rank li.sel{background:var(--neutral)}
:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.seg button{font:600 14px var(--font);padding:9px 14px;border:0;background:transparent;color:var(--ink2);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--ink);color:var(--bg)}
```

Notas:

- `.ring` é um **contorno desenhado em camada própria**; tem `pointer-events:none`, então nunca
  rouba o mouse do estado de baixo. `.oc` (rótulos do mar e linhas) e `.rot` (siglas) também não
  capturam o mouse.
- `.uf:focus-visible{outline:none}`: o contorno `.ring` é o indicador de foco do teclado. O retângulo
  padrão do navegador ficava torto num SVG.
- `.ring` tem `stroke-width:2.2` em **unidades do desenho**: ele acompanha o tamanho do mapa. Em tela
  larga fica perto de 2 px; no celular (mapa com ~340 px) fica perto de 1,2 px. Se quiser espessura
  fixa, acrescente `vector-effect:non-scaling-stroke` (não foi feito).
- Os cursores `pointer` estão nos estados e nas linhas do ranking.

### 5.3 O JavaScript dessas regras (e por que o contorno é uma camada à parte)

Eventos nos estados e criação das camadas:

```js
const gp=sv('g',{}),gl=sv('g',{}),go=sv('g',{class:'oc'});
// contornos de destaque: camada própria por cima dos estados (nunca mover o estado de lugar: isso tira o foco do teclado)
const rs=sv('path',{class:'ring'}),rh=sv('path',{class:'ring'});
svg.append(gp,rs,rh,go,gl);
const OCEAN=['RN','PB','PE','AL','SE'].sort((a,b)=>G.uf[a].cy-G.uf[b].cy);
let ly=-1e9;const oy={};OCEAN.forEach(u=>{ly=Math.max(G.uf[u].cy,ly+15);oy[u]=ly});
const gs={},ps={},ts={},sw={};
UFS.forEach(uf=>{
  const g=sv('g',{class:'uf',tabindex:'0',role:'button'}),p=sv('path',{d:G.uf[uf].d});g.append(p);gp.append(g);gs[uf]=g;ps[uf]=p;
  g.addEventListener('mouseenter',()=>setHov(uf));g.addEventListener('mouseleave',()=>setHov(null));
  g.addEventListener('focus',()=>setHov(uf));g.addEventListener('blur',()=>setHov(null));
  g.addEventListener('click',()=>setSel(uf));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();setSel(uf)}});
  if(OCEAN.includes(uf)){
    const x=G.maxx+10,y=oy[uf];
    go.append(sv('line',{x1:G.uf[uf].cx,y1:G.uf[uf].cy,x2:x-2,y2:y}));
    const s=sv('rect',{x:x,y:y-5.5,width:11,height:11,rx:2,class:'sw'});go.append(s);sw[uf]=s;
    const t=sv('text',{x:x+15,y:y+4.5});t.textContent=uf;go.append(t);
  }else{
    const t=sv('text',{x:G.uf[uf].cx,y:G.uf[uf].cy+4,'text-anchor':'middle',class:'rot'});t.textContent=uf;gl.append(t);ts[uf]=t;
  }
});
$('mapa').append(svg);
```

O destaque e o quadro de detalhe:

```js
function marcar(){
  UFS.forEach(u=>{gs[u].classList.toggle('sel',u===sel);gs[u].classList.toggle('hov',u===hov)});
  document.querySelectorAll('#rank li').forEach(li=>{li.classList.toggle('sel',li.dataset.uf===sel);li.classList.toggle('hov',li.dataset.uf===hov)});
  rs.setAttribute('d',sel?G.uf[sel].d:'');rh.setAttribute('d',hov?G.uf[hov].d:'');
  detalhe(hov||sel);
}
function setHov(u){hov=u;marcar()}
function setSel(u){sel=(sel===u?null:u);marcar()}
```

**Por que as duas camadas `rs` e `rh`:** a primeira versão movia o `<g>` do estado para o fim do
desenho (`append`) para o contorno não ficar escondido atrás dos vizinhos. No mouse funcionava, mas
**no Chromium, mover um elemento que está com o foco tira o foco dele** (testado: o teclado "morria" na
hora). Está corrigido: agora os estados **nunca mudam de lugar**; o contorno é um `<path>`
extra, por cima (`rs` = selecionado, `rh` = sob o mouse/foco). **Regra para o outro projeto:** nunca
reordene no DOM um elemento que pode estar focado.

### 5.4 O que NÃO foi feito (deliberadamente)

- As linhas do ranking **não** são focáveis pelo teclado (os estados do mapa são). Quem usa teclado
  percorre os estados.
- Não há animação de entrada do contorno. Existe `transition:opacity .12s` em `.uf path`, mas nenhum
  código muda a opacidade; é uma sobra inofensiva.
- Não há tooltip flutuante: o "tooltip" é o quadro de detalhe ao lado (funciona igual para mouse, toque
  e teclado, e é lido por leitor de tela via `aria-live="polite"`).
- Cada estado tem `aria-label`, por exemplo `Bahia: Lula 71,31%, Flávio 28,69%`.

## 6. Cores, faixas e rótulos

### 6.1 Por que azul e vermelho

Lula = vermelho, Flávio = azul. O par passou na validação de cores para daltonismo (distância de cor
21,6 para daltônicos e 32,3 para visão normal no tema claro; os mínimos do método são 8 e 15) e nos
dois temas. A rampa vermelha é **derivada da azul**, mantendo a luminosidade de cada degrau
(`scripts/mapa/rampas.py`, em espaço OKLCH), para os dois mapas "pesarem" igual.

### 6.2 As cores (copiadas do arquivo)

```css
:root{
  --bg:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7;
  --lula:#c74845; --flavio:#2a78d6; --neutral:#f0efec;
  --f1:#cde2fb; --f2:#9ec5f4; --f3:#6da7ec; --f4:#2a78d6; --f5:#1c5cab; --f6:#0d366b;
  --l1:#fad6d2; --l2:#f1aea8; --l3:#e4857e; --l4:#c74845; --l5:#9e3432; --l6:#621b1a;
  --dl1:#f1aea8; --dl2:#e4857e; --dl3:#c74845; --dl4:#892b2a;
  --df1:#9ec5f4; --df2:#6da7ec; --df3:#2a78d6; --df4:#184f95;
  --font:system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --axis:#383835;
  --lula:#e66767; --flavio:#3987e5; --neutral:#383835;
  --f1:#104281; --f2:#1c5cab; --f3:#2a78d6; --f4:#5598e7; --f5:#86b6ef; --f6:#b7d3f6;
  --l1:#762221; --l2:#9e3432; --l3:#c74845; --l4:#dd716a; --l5:#ea9a93; --l6:#f4c2be;
  --dl1:#9e3432; --dl2:#c74845; --dl3:#dd716a; --dl4:#ea9a93;
  --df1:#1c5cab; --df2:#2a78d6; --df3:#5598e7; --df4:#86b6ef; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0d0d0d; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --axis:#383835;
  --lula:#e66767; --flavio:#3987e5; --neutral:#383835;
  --f1:#104281; --f2:#1c5cab; --f3:#2a78d6; --f4:#5598e7; --f5:#86b6ef; --f6:#b7d3f6;
  --l1:#762221; --l2:#9e3432; --l3:#c74845; --l4:#dd716a; --l5:#ea9a93; --l6:#f4c2be;
  --dl1:#9e3432; --dl2:#c74845; --dl3:#dd716a; --dl4:#ea9a93;
  --df1:#1c5cab; --df2:#2a78d6; --df3:#5598e7; --df4:#86b6ef; color-scheme:dark}
```

Leitura: `--f1..--f6` = rampa azul do mapa de Flávio; `--l1..--l6` = rampa vermelha do mapa de Lula;
`--df1..--df4` e `--dl1..--dl4` = braços azul e vermelho do mapa "Vencedor"; `--neutral` = cinza do
meio. No **tema escuro** as rampas **invertem**: valores baixos ficam escuros (somem no fundo) e os
altos ficam claros. Os temas mudam sozinhos pelo sistema, ou à força pelo atributo `data-theme` no `<html>`.

### 6.3 As faixas e a função de cor

```js
// --- escalas
const SEQ=[30,40,50,60,70],SEQL=['menos de 30%','30 a 40%','40 a 50%','50 a 60%','60 a 70%','70% ou mais'];
const DIV=[2,10,20,35],DIVL=['2 a 10 pp','10 a 20 pp','20 a 35 pp','35 pp ou mais'];
const seqIdx=v=>SEQ.filter(e=>v>=e).length;
const divIdx=m=>{const a=Math.abs(m);return a<DIV[0]?-1:DIV.filter(e=>a>=e).length-1};
function cor(view,r){
  if(view==='lula')return 'var(--l'+(seqIdx(r.lp)+1)+')';
  if(view==='flavio')return 'var(--f'+(seqIdx(r.fp)+1)+')';
  const i=divIdx(r.m);return i<0?'var(--neutral)':(r.m>0?'var(--dl':'var(--df')+(i+1)+')';
}
// cor do texto sobre o preenchimento (luminância do valor resolvido)
function lum(c){const m=c.match(/#([0-9a-f]{6})/i);if(!m)return 1;const n=parseInt(m[1],16),f=x=>{x/=255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)};return .2126*f(n>>16)+.7152*f((n>>8)&255)+.0722*f(n&255)}
```

- **Mapas de cada candidato:** 6 faixas, mesma régua para os dois (para comparar): `< 30`, `30–40`,
  `40–50`, `50–60`, `60–70`, `≥ 70` (limite inferior inclusivo: 40,00 cai em `40 a 50%`).
- **Mapa "Vencedor":** menos de 2 pp = cinza (só Minas Gerais, `+0,9 pp`); depois 4 degraus de cada
  lado: `2–10`, `10–20`, `20–35`, `≥ 35` pp.
- **Cor da sigla sobre o estado:** branco ou preto, pela luminosidade relativa do fundo (fórmula
  padrão da acessibilidade). O limite `0,42` foi **escolhido por mim olhando as cores**; não é o
  ponto matemático de melhor contraste. Revise se mudar as rampas.

### 6.4 Legenda

```js
function legenda(){
  const L=$('legenda');L.replaceChildren();
  const item=(c,t)=>{const s=el('span','i');const b=el('b');b.style.background=c;s.append(b,t);L.append(s)};
  if(view==='vencedor'){
    L.append(el('div','t','Margem entre os dois, em pontos percentuais (pp)'));
    for(let i=3;i>=0;i--)item('var(--df'+(i+1)+')','Flávio '+DIVL[i]);
    item('var(--neutral)','menos de 2 pp');
    for(let i=0;i<4;i++)item('var(--dl'+(i+1)+')','Lula '+DIVL[i]);
  }else{
    L.append(el('div','t','% dos votos válidos de '+(view==='lula'?'Lula':'Flávio Bolsonaro')+' no estado'));
    for(let i=0;i<6;i++)item('var(--'+(view==='lula'?'l':'f')+(i+1)+')',SEQL[i]);
  }
}
```

## 7. Layout e responsividade

```css
.grid{display:grid;grid-template-columns:1fr;gap:18px;margin-top:14px}
@media (min-width:900px){.grid{grid-template-columns:1.12fr .88fr;align-items:start}}
@media (max-width:420px){.placar{grid-template-columns:1fr}}
@media (max-width:640px){.rot,.oc text{font-size:15px}}
.rank{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:3px;max-height:520px;overflow:auto}
.legenda{display:flex;flex-wrap:wrap;gap:4px 14px;margin:8px 4px 2px;font-size:12.5px;color:var(--ink2)}
```

- A partir de **900 px** de largura: duas colunas (mapa 1,12 × painel 0,88).
- Até **640 px**: as siglas do mapa sobem para 15 unidades (ficam legíveis).
- Até **420 px**: o placar (Lula/Flávio) vira uma coluna.
- Fonte do sistema (`system-ui…`); nenhuma fonte externa, nenhum script externo.

## 8. Quadro de detalhe, ranking e tabela

```js
// --- detalhe
function detalhe(uf){
  const C=$('detalhe');C.replaceChildren();
  let r;
  if(!uf){r={nome:'Brasil',lula:B.lula,flavio:B.flavio,validos:vb,lp:100*B.lula/vb,fp:100*B.flavio/vb,m:100*(B.lula-B.flavio)/vb,brancos:B.brancos,nulos:B.nulos,compar:B.compar,cp:B.comparecimento_pct}}
  else r=byUf[uf];
  C.append(el('h2','',r.nome+(uf?' ('+uf+')':'')));
  [['Lula','--lula',r.lula,r.lp],['Flávio Bolsonaro','--flavio',r.flavio,r.fp]].forEach(([n,v,vt,p])=>{
    const l=el('div','linha'),d=el('span','dot');d.style.background='var('+v+')';
    l.append(d,el('span','',n),el('span','v',nP(p)),el('span','s',nI(vt)+' votos'));C.append(l)});
  C.append(el('div','nota',(r.m>0?'Lula à frente por ':'Flávio à frente por ')+nM(Math.abs(r.m)).replace('+','')+' ('+nI(Math.abs(r.lula-r.flavio))+' votos). Comparecimento '+nP(r.cp)+'. Brancos '+nI(r.brancos)+' · nulos '+nI(r.nulos)+'.'));
  if(!uf)C.append(el('div','nota','Toque ou passe o mouse sobre um estado para ver os números dele.'));
}
```

```js
// --- ranking
function ranking(){
  const R=$('rank');R.replaceChildren();
  let lista,t;
  if(view==='lula'){lista=[...rows].sort((a,b)=>b.lp-a.lp);t='Lula: % dos votos válidos, por estado'}
  else if(view==='flavio'){lista=[...rows].sort((a,b)=>b.fp-a.fp);t='Flávio: % dos votos válidos, por estado'}
  else{lista=[...rows].sort((a,b)=>b.m-a.m);t='Margem por estado (vermelho = Lula, azul = Flávio)'}
  $('tituloRank').textContent=t;
  lista.forEach(r=>{
    const li=el('li');li.dataset.uf=r.uf;li.append(el('span','u',r.uf));
    const tr=el('div','tr'),b=el('i');
    if(view==='vencedor'){const w=Math.min(50,Math.abs(r.m)/52*50);b.style.width=w+'%';b.style.background=r.m>0?'var(--lula)':'var(--flavio)';if(r.m>0)b.style.left='50%';else b.style.right='50%';tr.append(b,el('span','m'))}
    else{const v=view==='lula'?r.lp:r.fp;b.style.left='0';b.style.width=v+'%';b.style.background=view==='lula'?'var(--lula)':'var(--flavio)';tr.append(b,el('span','m'))}
    li.append(tr,el('span','n',view==='vencedor'?nM(r.m):nP(view==='lula'?r.lp:r.fp)));
    li.addEventListener('mouseenter',()=>setHov(r.uf));li.addEventListener('mouseleave',()=>setHov(null));li.addEventListener('click',()=>setSel(r.uf));
    R.append(li);
  });
  marcar();
}
```

```js
// --- tabela
let ord={k:'nome',asc:true};
const COLS=[['nome','Estado'],['uf','UF'],['lula','Lula (votos)'],['lp','Lula %'],['flavio','Flávio (votos)'],['fp','Flávio %'],['m','Margem'],['v','Venceu']];
function tabela(){
  const cab=$('cab');cab.replaceChildren();
  COLS.forEach(([k,n])=>{const th=el('th','',n+(ord.k===k?(ord.asc?' ▲':' ▼'):''));th.onclick=()=>{ord={k,asc:ord.k===k?!ord.asc:(k==='nome'||k==='uf'||k==='v')};tabela()};cab.append(th)});
  const L=rows.map(r=>Object.assign({v:r.m>0?'Lula':'Flávio'},r));
  L.sort((a,b)=>{const x=a[ord.k],y=b[ord.k];const c=typeof x==='string'?x.localeCompare(y,'pt-BR'):x-y;return ord.asc?c:-c});
  const T=$('corpo');T.replaceChildren();
  const add=(cls,a)=>{const tr=el('tr',cls);a.forEach(x=>tr.append(el('td','',x)));T.append(tr)};
  L.forEach(r=>add('',[r.nome,r.uf,nI(r.lula),nP(r.lp),nI(r.flavio),nP(r.fp),nM(r.m),r.v]));
  const ex=D.ext,ev=ex.lula+ex.flavio;
  add('',['Exterior','ZZ',nI(ex.lula),nP(100*ex.lula/ev),nI(ex.flavio),nP(100*ex.flavio/ev),nM(100*(ex.lula-ex.flavio)/ev),ex.lula>ex.flavio?'Lula':'Flávio']);
  add('tot',['Brasil','BR',nI(B.lula),nP(100*B.lula/vb),nI(B.flavio),nP(100*B.flavio/vb),nM(100*(B.lula-B.flavio)/vb),'Lula']);
}
```

- **Detalhe:** com nenhum estado, mostra **Brasil** + a dica "Toque ou passe o mouse sobre um estado
  para ver os números dele."
- **Ranking:** ordenado pelo critério do botão (Lula: maior % primeiro; Flávio: idem; Vencedor: maior
  margem de Lula primeiro). A caixa rola (`max-height:520px`).
- **Tabela:** 8 colunas, ordena ao clicar no título (▲/▼); texto em ordem alfabética `pt-BR`, números
  do maior para o menor na 1ª vez. Mais as linhas **Exterior (ZZ)** e **Brasil (BR)** no fim.

## 9. Textos exatos da tela

- Cabeçalho: `2º turno · 25/10/2026` · `Mapa do segundo turno por estado`.
- Frase-resumo: `Lula venceu em 13 estados e Flávio em 14 (o DF conta como estado). Diferença nacional:
  4.430.191 votos. Comparecimento 80,78%, 100,00% das seções apuradas.`
- Títulos do mapa: `Votos em Lula por estado` · `Votos em Flávio Bolsonaro por estado` ·
  `Quem venceu em cada estado`.
- Títulos do ranking: `Lula: % dos votos válidos, por estado` · `Flávio: % dos votos válidos, por estado` ·
  `Margem por estado (vermelho = Lula, azul = Flávio)`.
- Rodapé: fonte, hora e data do arquivo do TSE, base do percentual, aviso do exterior, créditos dos
  contornos e, se a conferência falhar, o aviso `ATENÇÃO: a soma dos estados e do exterior difere…`.

## 10. Checklist para aplicar em outro projeto

Itens que estão **fixos no código** e precisam ser trocados (em ordem de risco):

1. Os candidatos: `lula` / `flavio` aparecem como **chaves** em todo o JavaScript, nos ids (`vLula`,
   `plp`…) e nas cores (`--lula`, `--l*`, `--dl*`…).
2. **Constante `52`** da barra de margem (seção 4, item 8).
3. Na **tabela**, a linha "Brasil" escreve **`'Lula'` como vencedor fixo**, e o selo "Eleito" ao lado do
   Lula no placar é HTML fixo. Em outra eleição, calcule/retire.
4. Textos fixos: `2º turno · 25/10/2026`, `(o DF conta como estado)`, `2º turno de 25/10/2026` no rodapé.
5. Faixas `SEQ` e `DIV`: ajuste ao alcance dos seus dados (a escala do 1º turno, por exemplo, terá
   percentuais bem menores).
6. A lista de estados com rótulo no mar: `['RN','PB','PE','AL','SE']` (específica do mapa do Brasil).
7. Os contornos são do Brasil; para outro país/estado refaça com `scripts/mapa/gerar_geo.py`.
8. Mais de **dois** candidatos: o mapa "Vencedor" precisa de uma cor por candidato (e pelo método de
   cores validado, no máximo 3 por mapa em mapas coloridos). Veja `_ler_2t`, que hoje **exige** dois.
9. Mantenha: `textContent` (nunca `innerHTML` com dado externo), a camada `.ring` e a regra de nunca
   reordenar elemento focado.

## 11. O que foi testado (04/11/2026) e o que não foi

**Testado** (servidor local + Chromium automatizado, dados reais do TSE):

- hover em estado, saída do estado, hover em linha do ranking; contorno aparece e some;
- teclado: foco no estado, Tab, Enter, Enter de novo (desmarca) e Espaço;
- toque (emulação de toque do Chromium);
- botões Lula/Flávio/Vencedor; tabela com 29 linhas; link de volta e login;
- cor do contorno: `rgb(240,239,236)` no tema escuro e `rgb(11,11,11)` no tema claro;
- nenhum erro de JavaScript; sem rolagem lateral;
- formatos dos números (tabela da seção 4); percentuais iguais ao TSE em 28/28 arquivos;
- soma dos estados + exterior = total do Brasil (diferença zero);
- o script dos contornos regenera o arquivo em uso, **idêntico**.

**Não testado:** Safari e Firefox; celular de verdade (só a emulação); leitor de tela; modo de alto
contraste; impressão.

## 12. Onde está cada coisa

| O quê | Onde |
|---|---|
| Página (HTML, CSS, JS) | `app/dados/mapa_turno2.html` |
| Contornos dos estados | `app/dados/br_estados_geo.json` |
| Leitura do TSE e conferência | `app/eleicoes.py` (`_ler_2t`, `mapa_turno2`, `pagina_mapa_turno2`) |
| Rota | `app/main.py` (`/eleicoes/mapa-2turno`) |
| Script dos contornos | `scripts/mapa/gerar_geo.py` |
| Script das rampas de cor | `scripts/mapa/rampas.py` |
| Cópia em artefato (dados embutidos de 25/10) | <https://claude.ai/artifact/Di3tsCie3fzhrVjLFQb2Fe> |

### Apêndice A — pintura das cores e rótulos

```js
function pintar(){
  const cs=getComputedStyle(document.documentElement);
  UFS.forEach(uf=>{
    const c=cor(view,byUf[uf]);ps[uf].style.fill=c;
    const m=c.match(/var\((--[a-z0-9]+)\)/),hex=m?cs.getPropertyValue(m[1]).trim():c;
    if(ts[uf])ts[uf].style.fill=lum(hex)>0.42?'#0b0b0b':'#ffffff';
    if(sw[uf]){sw[uf].style.fill=c;sw[uf].style.stroke='var(--axis)'}
    const r=byUf[uf];gs[uf].setAttribute('aria-label',r.nome+': Lula '+nP(r.lp)+', Flávio '+nP(r.fp));
  });
}
```

### Apêndice B — botões e troca de mapa

```js
function titulo(){$('tituloMapa').textContent=view==='lula'?'Votos em Lula por estado':view==='flavio'?'Votos em Flávio Bolsonaro por estado':'Quem venceu em cada estado'}
function setView(v){view=v;try{localStorage.setItem('mapa2t_view',v)}catch(e){}
  $('vLula').setAttribute('aria-pressed',String(v==='lula'));$('vFlavio').setAttribute('aria-pressed',String(v==='flavio'));$('vVenc').setAttribute('aria-pressed',String(v==='vencedor'));
  titulo();pintar();legenda();ranking()}
$('vLula').onclick=()=>setView('lula');$('vFlavio').onclick=()=>setView('flavio');$('vVenc').onclick=()=>setView('vencedor');
```

### Apêndice C — mudança de tema

```js
// recolore rótulos se o tema mudar
try{matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>setTimeout(pintar,50))}catch(e){}
new MutationObserver(()=>setTimeout(pintar,50)).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
```
