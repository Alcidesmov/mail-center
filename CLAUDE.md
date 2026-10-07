# Mail Center

> Arquivo de especificação para Claude Code. Lido no início de cada sessão
> neste projeto — atualizar a cada mudança relevante de schema, tela ou
> decisão de negócio, junto com o commit que a introduz. Mesmo modelo de
> documento usado no ERP ContFácil (Movbank) — é o "pilar" que sobrevive
> entre sessões, quando a conversa é descartada.

## ⚠️ Decisão de rumo (05/10/2026) — ler antes de continuar

**Prioridade: VPS primeiro, Git depois. O uso em `localhost` está abandonado
por enquanto** (decisão do Alcides). Não propor "testar local primeiro".

Estado atual:

1. **Nenhuma conta de e-mail real cadastrada ainda.** O fluxo real de
   IMAP/SMTP contra um provedor de verdade (Gmail ou e-mail próprio da
   Movbank/Movcont/Clavion) **nunca rodou** — validar logo após o deploy.
2. **Nada está no ar.** O código existe no GitHub (`Alcidesmov/mail-center`,
   privado), no PR #1 (branch `feat/modulo-eleicoes`: módulo Eleições +
   senha de acesso, ainda em rascunho) e no container descartável das
   sessões. O Alcides não baixou nem rodou nada.
3. **Deploy na VPS: só o runbook está pronto.** Ver `docs/DEPLOY_VPS.md`
   (Terminal do painel Hostinger, sem SSH). Sessões na nuvem **não alcançam**
   a VPS nem o Chrome do Alcides: quem cola os comandos é ele, em blocos
   que a IA entrega e confere. Sessão no app desktop/Mac, com a extensão
   Claude in Chrome, pode conduzir direto.
4. **Senha de acesso é pré-requisito do deploy** (passo 1.1 do runbook) —
   sem ela o sistema fica aberto na internet com as caixas das empresas.
5. **Git:** o clone na VPS precisa de PAT do GitHub (repositório privado;
   Alcides ainda não gerou). Fazer merge do PR #1 quando ele aprovar.
6. Subdomínio sugerido (não confirmado nem criado):
   `mail.srv1697060.hstgr.cloud`.
7. Eleições: dados, API do TSE, resultados e o "Relatório 1" estão em
   `docs/ELEICOES_2026.md`. O retrato mobile (artefato privado no claude.ai)
   ainda não está no Git; salvar em `docs/apuracao_mobile.html` só se o
   Alcides pedir.

## 1. Contexto

Sistema de mensageria (e-mail) próprio para o Alcides usar no dia a dia das
três empresas — **Movbank** (consultoria tributária), **Movcont**
(contábil/fiscal) e **Clavion** (clube de apoio ao vinicultor). Nasceu de um
pedido direto: "quero um sistema de mensageira de enviar, receber, escrever,
pesquisar e leitura ao clicar, organização, algo super profissional".

Multi-conta desde a primeira versão — cada empresa é uma caixa de e-mail
conectada separadamente (uma linha na tabela `contas`), não existe login
único nem tenant compartilhado entre elas.

Usuário é **não-programador**. Rodar na VPS é o caminho principal (ver
"Decisão de rumo" no topo); o `python run.py` continua existindo, mas não é
mais o foco. Sem serviços pagos além da VPS que já existe.

## 2. Stack (decisões tomadas — mesmo espírito do ERP ContFácil)

- **Python 3.9+ / FastAPI + SQLite** (arquivo único `mail_center.db`).
- Frontend: **HTML + Jinja2 + Tailwind (via CDN)**, servido pelo próprio
  FastAPI. Sem build step, sem npm, sem framework de componente.
- Fonte: **Poppins** (Google Fonts CDN) — mesma tipografia da identidade
  Movbank (ver `BRAND_GUIDE.md` do ERP ContFácil), ainda que este projeto
  não seja exclusivo da Movbank.
- **IMAP** (receber): `imaplib` da biblioteca padrão — zero dependência nova.
- **SMTP** (enviar): `smtplib` da biblioteca padrão, mesmo padrão do
  `app/notificacoes.py` do ERP ContFácil.
- **Cifra de senha**: `cryptography` (Fernet) — única dependência "pesada"
  nova, necessária porque senha de e-mail em texto puro no banco não é
  aceitável (mesmo princípio do módulo Procuração do ERP ContFácil, que usa
  PBKDF2 para a senha de acesso; aqui é simétrico porque a senha original
  precisa ser recuperada para autenticar no IMAP/SMTP a cada sincronização).
- Produção: serviço systemd na VPS atrás do Nginx (`docs/DEPLOY_VPS.md`).
  Desenvolvimento: `python run.py` → `localhost:8010` (abandonado como
  rotina; manter só para testes da IA).

## 3. Modelo de dados

```
contas(id, nome_exibicao, email, cor,
       imap_host, imap_porta, imap_usuario,
       smtp_host, smtp_porta, smtp_usuario,
       senha_cifrada,            -- Fernet, chave em MAIL_CENTER_CHAVE_CIFRA (.env)
       ativo, ultima_sincronizacao, ultimo_erro_sync)
  # 1 linha = 1 caixa de e-mail conectada (1 por empresa, hoje).

pastas(id, conta_id FK, nome_exibicao, caminho_imap, tipo,
       ultimo_uid_sincronizado)
  # tipo: INBOX | ENVIADOS | RASCUNHOS | LIXEIRA | SPAM | OUTRA — detectado
  # por heurística de nome (`imap_sync._tipo_da_pasta`), não pelo usuário.
  # `ultimo_uid_sincronizado` é o ponteiro de onde a sincronização parou —
  # sincronizações seguintes só buscam UID maior que esse (nunca reimporta).

mensagens(id, conta_id FK, pasta_id FK, uid_imap, message_id, em_resposta_a,
          remetente_nome, remetente_email, destinatarios (JSON), cc (JSON),
          bcc (JSON), assunto, corpo_texto, corpo_html, data_hora, lida,
          texto_busca)
  # UNIQUE(conta_id, pasta_id, uid_imap) — dedupe de sincronização.
  # texto_busca = normalizar(assunto + remetente + início do corpo), mesma
  # função normalize() (uppercase, sem acento) usada no autocomplete do ERP
  # ContFácil — busca é LIKE sobre essa coluna, sem FTS5 (risco de não estar
  # compilado no SQLite do ambiente do usuário).

anexos(id, mensagem_id FK, nome_arquivo, content_type, tamanho, caminho_disco)
  # Conteúdo vai pro disco (`anexos/<conta_id>/<mensagem_id>/`), nunca pro
  # banco — mesmo motivo do certificado digital no ERP ContFácil (evitar
  # SQLite inchado com BLOB grande).
```

## 4. Sincronização IMAP (`app/imap_sync.py`)

- **Detecção de pasta por heurística de nome** (`_tipo_da_pasta`): procura
  palavras-chave em inglês/português (`sent`/`enviad`, `draft`/`rascunho`,
  `trash`/`lixeira`/`deleted`, `spam`/`junk`) no nome retornado pelo `LIST`
  do IMAP. Não usa os atributos especiais RFC 6154 (`\Sent`, `\Drafts`) —
  simplificação deliberada do MVP; se algum provedor tiver nome de pasta
  muito fora do padrão, ela cai em `OUTRA` e ainda aparece na UI, só sem
  contar como caixa "oficial".
- **Primeira sincronização de uma conta nova**: limitada aos últimos
  `LIMITE_PRIMEIRA_SINCRONIZACAO` (150) e-mails de cada pasta, para não
  travar o cadastro de uma conta com anos de histórico. Sincronizações
  seguintes pegam só o que é nUID > `ultimo_uid_sincronizado`.
- **Pastas Lixeira/Spam nunca sincronizam automaticamente** (`sincronizar_conta`
  pula explicitamente) — decisão de escopo do MVP: não vale a pena trazer
  lixo eletrônico pro banco local.
- **Best-effort por conta**: uma conta com erro (senha revogada, IMAP fora
  do ar) grava o erro em `contas.ultimo_erro_sync` e não impede a
  sincronização das outras contas — mesmo padrão do sync do Notion no ERP
  ContFácil (`_rotina_sincronizacao_notion`).
- **Rotina automática** (`_rotina_sincronizacao_automatica` em `main.py`):
  thread daemon, roda em loop, intervalo configurável via
  `MAIL_CENTER_INTERVALO_SYNC_MIN` no `.env` (padrão 5 minutos).
- **Marcar como lida**: grava local na hora (resposta rápida da UI) e
  dispara `\Seen` no IMAP em thread separada, sem bloquear a renderização
  da página — se o IMAP falhar nesse momento, o estado "lida" já está
  correto localmente (o servidor fica dessincronizado até a próxima vez que
  alguém abrir a mensagem de novo, efeito colateral aceito no MVP).

## 5. Envio (`app/smtp_send.py`)

- Monta MIME `multipart/mixed` com `multipart/alternative` (texto+HTML)
  dentro, mais anexos como `MIMEApplication`.
- **Cópia em Enviados**: depois de mandar via SMTP, tenta `APPEND` a mesma
  mensagem na pasta `ENVIADOS` do IMAP e sincroniza só aquela pasta na hora
  — assim a mensagem aparece na UI com o UID real do servidor, sem duplicar
  quando o ciclo automático rodar de novo. Best-effort: se o APPEND falhar,
  o e-mail já foi enviado mesmo assim, só a cópia local atrasa até o
  próximo sync completo.
- Detecção SSL vs. STARTTLS pela porta: `465` → `SMTP_SSL` direto; qualquer
  outra porta → `SMTP` + `starttls()` (cobre 587, o mais comum).

## 6. Segurança

- Senha de e-mail **nunca em texto puro** no banco — cifrada com Fernet
  (`app/crypto.py`), chave em `MAIL_CENTER_CHAVE_CIFRA` no `.env` (gerada
  sozinha no primeiro boot, nunca escrever à mão).
- **Corpo HTML de mensagem recebida é conteúdo não-confiável** — renderizado
  em `<iframe sandbox="">` (sandbox vazio bloqueia script, formulário,
  popup, mesma origem) via `srcdoc`, nunca injetado direto no DOM da página
  (`caixa.html`). Autoescape do Jinja garante que o HTML entra corretamente
  escapado no atributo `srcdoc`. Não remover o sandbox por conveniência
  visual — é a única barreira contra e-mail malicioso executando JS na
  sessão do usuário.
- `.env` nunca vai pro Git (`.gitignore`), mesmo padrão do ERP ContFácil.

- **Senha de acesso** (`app/auth.py`): se `MAIL_CENTER_SENHA_HASH` existe no
  `.env`, toda rota exige login (cookie assinado HMAC, 12 h, `HttpOnly`;
  bloqueio de 10 min após 10 falhas). Sem o hash o app roda aberto — só
  aceitável em `localhost`. **Na VPS é obrigatório** definir via
  `python -m app.definir_senha` (passo 1.1 do `docs/DEPLOY_VPS.md`).

## 6.1 Módulo Eleições 2026 (`/eleicoes`, `app/eleicoes.py`)

- Aba separada da caixa de e-mail (link "🗳 Eleições 2026" no rodapé da barra
  lateral). Não depende de nenhuma conta de e-mail cadastrada.
- Lê a API pública do TSE, sem chave:
  `https://resultados.tse.jus.br/oficial/ele2026/<eleição>/dados/<uf>/<uf>-c<cargo>-e00<eleição>-u.json`
  (`br` para Presidente). Eleição `6257` = Presidente; `6259` = Governador
  (cargo `0003`), Senador (`0005`) e Dep. Federal (`0006`). O sufixo é `-u`;
  o caminho `dados-simplificados/…-r.json` dá 404 nesta eleição.
- Cache em memória de 2 min por URL; "Brasil" para Governador/Senador/Dep.
  Federal baixa os 27 estados em paralelo e soma. Biblioteca padrão
  (`urllib`), nenhuma dependência nova.
- Tela: abas de cargo, filtro por UF/partido/votos/%, busca sem acento
  (nome, número, partido), ordenação por coluna, visão "Por partido" e CSV.
  Tudo filtrado no navegador; dados do TSE entram via `textContent`, nunca
  `innerHTML`.
- **Visão "Blocos"**: soma de votos nominais (sem legenda) dos partidos
  marcados, com atalhos "Conservadores (PL, Podemos, PRD)", "Direita ampla"
  e "Esquerda". As listas são **classificação do Alcides/da IA, editável**
  na tela, não dado do TSE. Patriota não existe mais (fundiu com o PTB em
  2023 e virou PRD). Seleção lembrada no navegador (localStorage).
- "%" = percentual sobre os votos válidos do cargo (`pvapn` do TSE). A
  situação (Eleito, Suplente…) vem do TSE e pode estar vazia até a
  totalização final — em 05/10/2026 vários estados ainda vinham sem
  situação de Dep. Federal.
- Detalhes, números e relatórios: `docs/ELEICOES_2026.md`.
- Só 1º turno (04/10/2026). Para o 2º turno (25/10) será preciso descobrir
  os novos códigos de eleição em `comum/config/ele-c.json`.

## 7. Não fazer

- Não trazer e-mail de Lixeira/Spam pra sincronização automática sem pedido
  explícito — ver seção 4.
- Não tirar o `sandbox=""` do iframe de leitura de corpo HTML — risco de
  XSS via e-mail recebido.
- Não gravar senha de e-mail em texto puro em lugar nenhum (log, print,
  commit) — só cifrada, e só decifrada em memória na hora de autenticar.
- Não adicionar framework de frontend (React, build step, npm) — mesma
  decisão do ERP ContFácil, o usuário não programa e o app precisa
  continuar rodando com 1 comando.

## 8. Roadmap / próximos passos (não iniciados)

- Conectar as contas reais (Movbank, Movcont, Clavion) — hoje o projeto
  nasce sem nenhuma conta cadastrada, aguardando as credenciais reais/senhas
  de app de cada uma.
- **Deploy na VPS (prioridade 1):** blocos 1 a 3 do runbook, já com senha de
  acesso; depois conectar as contas reais.
- Depois do deploy: merge do PR #1 e salvar o retrato mobile no Git.
- Rótulos/etiquetas além das pastas padrão, se a organização por pasta não
  bastar no uso real.
- Anexar assinatura de e-mail por conta.

## 9. Histórico de versões

- **v0.1** (13/09/2026) — Primeira versão: multi-conta, sincronização IMAP
  (manual + automática a cada 5 min), envio SMTP com cópia em Enviados,
  compositor com formatação básica + Cc/Cco + anexos + responder/encaminhar,
  busca por pasta, layout de 3 painéis com leitura ao clicar (marca lida
  local + `\Seen` no servidor). Testado localmente com dados fictícios
  (inserção direta no banco) — fluxo real de IMAP/SMTP ainda não testado
  contra um provedor de verdade, porque nenhuma conta real foi cadastrada
  ainda nesta sessão. Também nesta versão: lançador de duplo clique
  (`INICIAR_MAIL_CENTER.command`, mesmo padrão dos outros dois projetos) e
  `docs/DEPLOY_VPS.md` (runbook de deploy, não executado ainda — ver
  callout de pendências no topo deste arquivo).
- **v0.2** (05/10/2026) — Módulo Eleições 2026 (ver 6.1): Presidente,
  Governador, Senador e Dep. Federal por voto, % e partido. Testado contra a
  API real do TSE e no navegador (Playwright); fluxo de e-mail continua sem
  teste real.
- **v0.3** (05/10/2026) — Senha de acesso (login por cookie assinado) para
  poder publicar na VPS com segurança. Testado com TestClient (sem senha →
  aberto; com senha → 303 para /login; cookie falso, senha errada e
  bloqueio por tentativas).
- **v0.4** (05/10/2026) — Rumo redefinido: VPS primeiro, Git depois, local
  abandonado por enquanto. Documentação (CLAUDE.md, README, runbook)
  atualizada; nenhum código alterado.
- **v0.5** (05/10/2026) — Visão "Blocos" no módulo Eleições e no retrato
  mobile. Dep. Federal, Brasil, 100% apurado: PL + PODE + PRD = 32.206.355
  votos nominais (28,24% dos válidos). Testado contra a API real.
- **v0.6** (07/10/2026) — Documentação das eleições (`docs/ELEICOES_2026.md`):
  API, resultados do 1º turno, blocos e Relatório 1 (0,563 conservadores ×
  Flávio; 0,517 progressistas × Lula, com desconto de 2%). Sem mudança de
  código.
