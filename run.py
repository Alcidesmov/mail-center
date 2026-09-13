"""Ponto de entrada único: `python run.py` sobe o servidor e abre o navegador
em localhost:8010 — mesmo padrão do run.py do ERP ContFácil."""
import threading
import time
import webbrowser

import uvicorn

PORTA = 8010


def abrir_navegador():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORTA}")


if __name__ == "__main__":
    threading.Thread(target=abrir_navegador, daemon=True).start()
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORTA, reload=False)
