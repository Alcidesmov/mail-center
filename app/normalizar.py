import unicodedata


def normalizar(texto: str) -> str:
    """Uppercase, sem acento, espaços colapsados — mesmo padrão de busca
    usado no autocomplete de clientes do ERP ContFácil."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(sem_acento.upper().split())
