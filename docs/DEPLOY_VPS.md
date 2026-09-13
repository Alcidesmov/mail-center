# Deploy na VPS Hostinger — runbook

Mesmo servidor que já hospeda o ERP ContFácil (`/opt/erp-contfacil`,
porta 8000) e o MecOS. Mail Center entra do mesmo jeito: usuário
dedicado, systemd, Nginx como proxy reverso, HTTPS via Certbot.

**Setup único** — feito uma vez, colando os comandos abaixo no
**Terminal do painel Hostinger** (hpanel.hostinger.com → VPS →
Gerenciar → Terminal, mesmo caminho já usado no ERP ContFácil, seção 4
do `RUNBOOK_INFRA_E_BACKUP.md` de lá). Não precisa de SSH nem chave —
o terminal do painel já conecta como root.

## 1. Clonar + preparar o ambiente Python

```bash
useradd --system --create-home --home-dir /opt/mail-center mailapp || true

cd /opt
git clone https://github.com/Alcidesmov/mail-center.git
cd mail-center

apt update -y
apt install -y python3-venv python3-pip

python3 -m venv .venv
./.venv/bin/pip install --upgrade pip -q
./.venv/bin/pip install -r requirements.txt -q

chown -R mailapp:mailapp /opt/mail-center
```

> ⚠️ Repositório **privado** — o `git clone` acima vai pedir usuário/senha.
> Gerar um Personal Access Token classic no GitHub (escopo `repo`) e usar
> como senha (mesmo caminho documentado na seção 6.6 do `CLAUDE.md` do
> MecOS). Depois de confirmar que o clone funcionou, pode revogar o
> token — não fica salvo em lugar nenhum do servidor.

## 2. Serviço systemd (mantém rodando, reinicia sozinho)

```bash
cat > /etc/systemd/system/mail-center.service <<'EOF'
[Unit]
Description=Mail Center
After=network.target

[Service]
Type=simple
User=mailapp
Group=mailapp
WorkingDirectory=/opt/mail-center
ExecStart=/opt/mail-center/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now mail-center
systemctl status mail-center --no-pager
```

Deve aparecer **"Active: active (running)"** em verde.

## 3. Nginx (proxy reverso) + HTTPS

```bash
cat > /etc/nginx/sites-available/mail-center <<'EOF'
server {
    listen 80;
    server_name mail.srv1697060.hstgr.cloud;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/mail-center /etc/nginx/sites-enabled/mail-center
nginx -t && systemctl reload nginx

certbot --nginx -d mail.srv1697060.hstgr.cloud --non-interactive --agree-tos -m alcides@movbank.com.br --redirect
```

Depois disso, **https://mail.srv1697060.hstgr.cloud** deve abrir o
Mail Center de qualquer lugar.

## Atualizar depois de uma mudança no código (rotina normal)

No terminal do servidor:

```bash
cd /opt/mail-center
git pull
./.venv/bin/pip install -r requirements.txt -q
systemctl restart mail-center
```

## Backup do banco

`mail_center.db` vive em `/opt/mail-center/` — mesmo princípio do ERP
ContFácil: nunca sobrescrever sem copiar antes:

```bash
cp /opt/mail-center/mail_center.db /opt/mail-center/mail_center.db.bak.$(date +%Y%m%d_%H%M%S)
```

## Não fazer

- Não trocar a porta `8010` nem tirar o `127.0.0.1` do `ExecStart` — expõe
  o sistema direto na internet, sem passar pelo Nginx/HTTPS.
- Não editar `/opt/mail-center/.env` fora do servidor — é lá que fica a
  chave de cifra das senhas de e-mail (`MAIL_CENTER_CHAVE_CIFRA`), gerada
  sozinha no primeiro boot do serviço.
