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


# ---------------------------------------------------------------------------
# Expressões regulares
# ---------------------------------------------------------------------------

# Limpeza do HTML que vem nas descrições
TAG_RE = re.compile(r"<[^>]+>")
SPACES_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Comunicação com a API
# ---------------------------------------------------------------------------

def fail(message):
    """Mostra uma mensagem de erro e termina o programa com código 1."""
    typer.echo(f"Erro: {message}", err=True)
    raise typer.Exit(code=1)


def get_json(url, params=None, not_found="recurso não encontrado na API (404)"):
    """Faz um pedido GET e devolve o JSON. Verifica erros de rede e o status code."""
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as error:
        fail(f"não foi possível contactar a API ({error})")

    if response.status_code == 404:
        fail(not_found)
    if response.status_code != 200:
        fail(f"a API respondeu com o status code {response.status_code}")
    return response.json()


def paginate(endpoint, params=None):
    """
    Percorre todas as páginas de uma rota, devolvendo um resultado de cada vez.

    A API devolve {"count", "next", "previous", "results"}. Enquanto existir
    "next", pedimos a página seguinte. Como é um gerador (yield), quem chama
    pode parar a meio e as páginas seguintes nunca chegam a ser pedidas.
    """
    url = BASE_URL + endpoint
    params = {"limit": PAGE_SIZE, **(params or {})}
    while url:
        data = get_json(url, params)
        yield from data["results"]
        url = data["next"]   # o link "next" já traz os parâmetros todos
        params = None


# ---------------------------------------------------------------------------
# Tratamento dos dados
# ---------------------------------------------------------------------------

def clean_text(text):
    """Remove tags HTML, converte entidades (&nbsp; &amp; ...) e espaços a mais."""
    text = TAG_RE.sub(" ", text or "")
    text = html.unescape(text)
    return SPACES_RE.sub(" ", text).strip()


def simplify(raw):
    """
    Converte um exercício da API num dicionário pequeno só com o que precisamos.
    Devolve None se o exercício não tiver tradução em inglês.
    """
    english = [t for t in raw["translations"] if t["language"] == LANGUAGE]
    if not english:
        return None
    translation = english[0]

    muscles = raw["muscles"] + raw["muscles_secondary"]
    return {
        "id": raw["id"],
        "name": translation["name"].strip(),
        "category": raw["category"]["name"],
        "muscles": [m["name_en"] or m["name"] for m in muscles],
        "equipment": [e["name"] for e in raw["equipment"]],
        "description": clean_text(translation["description"]),
    }


def fetch_exercises(params=None, limit=None):
    """Devolve exercícios em inglês (já simplificados), no máximo `limit`."""
    exercises = []
    params = {"language": LANGUAGE, **(params or {})}
    if limit:
        params["limit"] = min(limit, PAGE_SIZE)   # não pedir mais do que é preciso
    for raw in paginate("exerciseinfo/", params):
        exercise = simplify(raw)
        if exercise is None:
            continue
        exercises.append(exercise)
        if limit and len(exercises) >= limit:
            break
    return exercises


def print_json(data):
    """Escreve os dados no terminal em formato JSON."""
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


def pick(exercise, fields):
    """Devolve um dicionário só com os campos pedidos (para o output)."""
    return {field: exercise[field] for field in fields}


# ---------------------------------------------------------------------------
# Comandos da CLI
# ---------------------------------------------------------------------------

@app.command()
def top(n: int = typer.Argument(10, min=1, help="Número de exercícios a listar.")):
    """a) Lista os N exercícios mais recentes da base de dados."""
    exercises = fetch_exercises({"ordering": "-created"}, limit=n)
    print_json([pick(e, ["id", "name", "category", "equipment"]) for e in exercises])


if __name__ == "__main__":
    app()
