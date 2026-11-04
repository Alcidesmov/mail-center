# Mail Center

Sistema de mensageria (e-mail) próprio, multi-conta, publicado na VPS —
sem depender de webmail de terceiros para o dia a dia da Movbank, Movcont e
Clavion. Inclui a aba **Eleições 2026** (resultados do TSE).

> 🤖 Se você é o Claude Code (ou outra IA) entrando neste projeto pela
> primeira vez: leia [`CLAUDE.md`](CLAUDE.md) primeiro.

## O que faz

- **Múltiplas contas** — uma caixa de e-mail por empresa (ou quantas quiser),
  cada uma com sua cor de identificação.
- **Receber** — sincroniza via IMAP (Entrada, Enviados, Rascunhos detectados
  automaticamente), manual ou automática a cada N minutos.
- **Enviar / Escrever** — compositor com formatação básica (negrito, itálico,
  listas, link), Cc/Cco, anexos, responder/encaminhar com citação do
  original.
- **Pesquisar** — busca por assunto/remetente/corpo dentro da pasta atual.
- **Leitura ao clicar** — layout de 3 painéis (contas/pastas · lista ·
  leitura), marca como lida no clique (local e no servidor via IMAP).
- **Eleições 2026** — aba com Presidente, Governador, Senador e Dep. Federal
  por voto, % e partido, direto da API do TSE.
- **Segurança** — senha de acesso com login; senha de e-mail nunca fica em texto puro no banco (cifrada
  com `cryptography`/Fernet); corpo HTML de mensagens recebidas é renderizado
  num `<iframe sandbox>` isolado, sem executar script embutido.

## Publicando (caminho principal)

Siga [`docs/DEPLOY_VPS.md`](docs/DEPLOY_VPS.md): clonar na VPS, **definir a
senha de acesso** (passo 1.1, obrigatório), serviço systemd e Nginx com
HTTPS. Depois do primeiro acesso: **Gerenciar contas** → adicionar a
primeira caixa (Gmail/Workspace exigem uma
[senha de app](https://myaccount.google.com/apppasswords), nunca a senha
normal).

> Uso local (`python run.py`, `localhost:8010`) está em segundo plano por
> decisão do dono do projeto; segue funcionando para testes.

## Stack

Python 3.9+ / FastAPI + SQLite (arquivo único `mail_center.db`) — HTML +
Jinja2 + Tailwind (via CDN), sem build step, sem npm. Mesmo espírito dos
outros projetos do Alcides (ERP ContFácil): rodar com poucos comandos, sem
serviços pagos além da VPS que já existe.
