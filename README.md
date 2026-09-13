# Mail Center

Sistema de mensageria (e-mail) próprio, multi-conta, rodando local com um
único comando — sem depender de webmail de terceiros para o dia a dia da
Movbank, Movcont e Clavion.

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
- **Segurança** — senha de e-mail nunca fica em texto puro no banco (cifrada
  com `cryptography`/Fernet); corpo HTML de mensagens recebidas é renderizado
  num `<iframe sandbox>` isolado, sem executar script embutido.

## Rodando

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

Abre sozinho em `http://localhost:8010`. Primeiro acesso: **Gerenciar
contas** → adicionar a primeira caixa de e-mail (para Gmail/Workspace, use
uma [senha de app](https://myaccount.google.com/apppasswords), nunca a senha
normal).

## Stack

Python 3.9+ / FastAPI + SQLite (arquivo único `mail_center.db`) — HTML +
Jinja2 + Tailwind (via CDN), sem build step, sem npm. Mesmo espírito dos
outros projetos do Alcides (ERP ContFácil): rodar local com 1 comando, sem
deploy obrigatório, sem serviços pagos.
