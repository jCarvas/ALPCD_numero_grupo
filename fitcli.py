"""
fitcli - CLI para explorar a API pública de exercício físico wger.

ALP 2026/27 - Trabalho Prático, Parte 1
Grupo: Miguel Athayde (a113498), Guilherme Silva (a114993), João Carvas (a113326)

Exemplos:
    python fitcli.py top 10
    python fitcli.py search biceps 5
    python fitcli.py type 192
    python fitcli.py equipment chest
    python fitcli.py workout biceps,back compound 5
    python fitcli.py workout chest,shoulders isolated 3 --csv treino.csv
"""

import csv
import html
import json
import re
from enum import Enum
from typing import Optional

import requests
import typer

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

BASE_URL = "https://wger.de/api/v2/"
HEADERS = {
    "User-Agent": "fitcli/1.0 (TP1 ALP 2026/27 - Universidade do Minho)",
    "Accept": "application/json",
}
LANGUAGE = 2      # id da língua inglesa na API
PAGE_SIZE = 50    # resultados pedidos por página
TIMEOUT = 15      # segundos de espera por cada pedido

app = typer.Typer(help="Pesquisa de exercícios físicos na API wger.", add_completion=False)


if __name__ == "__main__":
    app()
