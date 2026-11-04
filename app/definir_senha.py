"""Define (ou troca) a senha de acesso: `python -m app.definir_senha`."""
import getpass
import sys

from app import auth

senha = getpass.getpass("Nova senha de acesso (mín. 12 caracteres): ")
if len(senha) < 12:
    sys.exit("Senha curta demais — use pelo menos 12 caracteres.")
if senha != getpass.getpass("Repita a senha: "):
    sys.exit("As senhas não conferem.")
auth.definir_senha(senha)
print("Senha definida. Reinicie o serviço para valer (systemctl restart mail-center).")
