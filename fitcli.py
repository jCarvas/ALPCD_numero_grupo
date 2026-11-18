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

# Alínea c) - palavras que indicam o tipo de esforço
CARDIO_RE = re.compile(
    r"\b(cardio|run(ning)?|jog(ging)?|sprints?|cycling|bike|swim(ming)?|"
    r"jump(ing)? (rope|jacks?)|skipping|treadmill|elliptical|rowing machine|burpees?)\b",
    re.IGNORECASE,
)
OTHER_RE = re.compile(r"\b(stretch(es|ing)?|yoga|mobility|warm[- ]?up)\b", re.IGNORECASE)
COMPOUND_DESC_RE = re.compile(r"\b(compound|multi[- ]?joint)\b", re.IGNORECASE)
ISOLATED_DESC_RE = re.compile(r"\b(isolat(ion|ed|es?|ing)|single[- ]?joint)\b", re.IGNORECASE)
COMPOUND_NAME_RE = re.compile(
    r"\b(squats?|deadlifts?|press(es)?|rows?|pull[- ]?ups?|chin[- ]?ups?|dips?|"
    r"lunges?|push[- ]?ups?|cleans?|snatch(es)?|thrusters?)\b",
    re.IGNORECASE,
)
ISOLATED_NAME_RE = re.compile(
    r"\b(curls?|extensions?|raises?|fly|flys|flyes|flies|kickbacks?|shrugs?|"
    r"crunch(es)?|push[- ]?downs?|pull[- ]?overs?)\b",
    re.IGNORECASE,
)

# Alínea d) - equipamento a procurar nas descrições
EQUIPMENT_PATTERNS = {
    "barbell": r"\bbarbells?\b",
    "dumbbell": r"\bdumb+ells?\b",          # apanha também o erro comum "dumbell"
    "cable": r"\bcables?\b",
    "machine": r"\bmachines?\b",
    "bodyweight": r"\bbody[- ]?weight\b",
    "bench": r"\bbench(es)?\b",
    "kettlebell": r"\bkettle[- ]?bells?\b",
    "band": r"\bbands?\b",
    "pull-up bar": r"\b(pull|chin)[- ]?up bars?\b",
    "ez-bar": r"\b(ez|sz)[- ]?bars?\b",
    "ball": r"\b(swiss|exercise|stability|medicine|gym) balls?\b",
    "mat": r"\bmats?\b",
    "rope": r"\bropes?\b",
    "plate": r"\bplates?\b",
}


class Effort(str, Enum):
    """Valores aceites no comando workout."""
    compound = "compound"
    isolated = "isolated"
    any = "any"


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


def find_filters(term):
    """
    Descobre a que músculos e/ou categorias corresponde o termo escrito.
    Devolve uma lista de filtros para a API, ex.: [{"muscles": 1}, {"category": 8}].
    Primeiro tenta o nome exato; se não houver, aceita nomes que contenham o termo.
    """
    term = term.strip().lower()
    muscles = list(paginate("muscle/"))
    categories = list(paginate("exercisecategory/"))

    exact, partial = [], []
    for muscle in muscles:
        names = [(muscle["name_en"] or "").lower(), muscle["name"].lower()]
        if term in names:
            exact.append({"muscles": muscle["id"]})
        elif any(term in name for name in names):
            partial.append({"muscles": muscle["id"]})
    for category in categories:
        name = category["name"].lower()
        if term == name:
            exact.append({"category": category["id"]})
        elif term in name:
            partial.append({"category": category["id"]})

    return exact or partial


def search_exercises(term, limit=None):
    """Pesquisa exercícios por músculo e/ou categoria (sem repetidos)."""
    filters = find_filters(term)
    if not filters:
        fail(f"'{term}' não é um músculo nem uma categoria. "
             "Use os comandos 'muscles' e 'categories' para ver os nomes válidos.")

    found = {}
    for api_filter in filters:
        for exercise in fetch_exercises(api_filter, limit):
            found.setdefault(exercise["id"], exercise)   # o id evita repetidos
    return list(found.values())[:limit]


def classify(exercise):
    """
    Alínea c) - infere o tipo de esforço: compound, isolated, cardio ou other.
    As regras são testadas por ordem, da mais fiável para a menos fiável:
    categoria -> nome do exercício -> descrição -> número de músculos.
    """
    name = exercise["name"]
    description = exercise["description"]

    # 1. Cardio: pela categoria ou por palavras no nome
    if exercise["category"] == "Cardio" or CARDIO_RE.search(name):
        return "cardio"

    # 2. Alongamentos, yoga, mobilidade... não são treino de força
    if OTHER_RE.search(name):
        return "other"

    # 3. Nome do movimento (squat, press, row... / curl, raise, fly...)
    if COMPOUND_NAME_RE.search(name):
        return "compound"
    if ISOLATED_NAME_RE.search(name):
        return "isolated"

    # 4. A própria descrição diz o tipo ("compound exercise", "isolation ...")
    says_compound = COMPOUND_DESC_RE.search(description)
    says_isolated = ISOLATED_DESC_RE.search(description)
    if says_compound and not says_isolated:
        return "compound"
    if says_isolated and not says_compound:
        return "isolated"

    # 5. Número de músculos envolvidos
    if len(exercise["muscles"]) >= 3:
        return "compound"
    if len(exercise["muscles"]) >= 1:
        return "isolated"
    return "other"


def count_equipment(exercises):
    """Alínea d) - conta as menções a cada equipamento nas descrições."""
    counts = {}
    for exercise in exercises:
        for equipment, pattern in EQUIPMENT_PATTERNS.items():
            mentions = re.findall(pattern, exercise["description"], re.IGNORECASE)
            if mentions:
                counts[equipment] = counts.get(equipment, 0) + len(mentions)
    ordered = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [{equipment: total} for equipment, total in ordered]


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


@app.command()
def search(
    term: str = typer.Argument(..., help="Nome do músculo ou da categoria (ex.: biceps, chest)."),
    n: int = typer.Argument(10, min=1, help="Número máximo de resultados."),
):
    """b) Pesquisa exercícios por músculo e/ou categoria."""
    exercises = search_exercises(term, limit=n)
    print_json([pick(e, ["id", "name", "category", "muscles", "equipment"]) for e in exercises])


@app.command("type")
def effort_type(exercise_id: int = typer.Argument(..., help="Id do exercício na API.")):
    """c) Indica o tipo de esforço de um exercício: compound, isolated, cardio ou other."""
    raw = get_json(f"{BASE_URL}exerciseinfo/{exercise_id}/",
                   not_found=f"não existe nenhum exercício com o id {exercise_id}")
    exercise = simplify(raw)
    if exercise is None:
        fail(f"o exercício {exercise_id} não tem tradução em inglês")
    typer.echo(classify(exercise))


@app.command()
def equipment(category: str = typer.Argument(..., help="Nome da categoria (ex.: chest).")):
    """d) Conta as menções a equipamento nas descrições de uma categoria."""
    categories = {c["name"].lower(): c["id"] for c in paginate("exercisecategory/")}
    category_id = categories.get(category.strip().lower())
    if category_id is None:
        fail(f"categoria '{category}' desconhecida. Categorias: {', '.join(categories)}")
    exercises = fetch_exercises({"category": category_id})
    print_json(count_equipment(exercises))


@app.command()
def workout(
    targets: str = typer.Argument(..., help="Músculos/categorias separados por vírgula (ex.: biceps,back)."),
    effort: Effort = typer.Argument(..., help="Tipo de esforço pretendido."),
    n: int = typer.Argument(..., min=1, help="Número máximo de exercícios por músculo/categoria."),
    csv_file: Optional[str] = typer.Option(None, "--csv", help="Exporta o plano para este ficheiro CSV."),
):
    """e) Gera um plano de treino a partir de músculos/categorias e tipo de esforço."""
    plan = {}
    for target in [t.strip() for t in targets.split(",") if t.strip()]:
        selected = []
        for exercise in search_exercises(target):
            exercise["type"] = classify(exercise)
            if effort == Effort.any or exercise["type"] == effort.value:
                selected.append(pick(exercise, ["name", "type", "category", "muscles", "equipment"]))
            if len(selected) >= n:
                break
        plan[target] = selected

    if csv_file is None:
        print_json(plan)
        return

    rows = 0
    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["target", "name", "type", "category", "muscles", "equipment"])
        for target, exercises in plan.items():
            for e in exercises:
                writer.writerow([target, e["name"], e["type"], e["category"],
                                 "; ".join(e["muscles"]), "; ".join(e["equipment"])])
                rows += 1
    typer.echo(f"Ficheiro exportado: {csv_file} ({rows} registos)")


# --- Extras -----------------------------------------------------------------

@app.command("categories")
def list_categories():
    """Extra: lista as categorias de exercícios disponíveis na API."""
    print_json([c["name"] for c in paginate("exercisecategory/")])


@app.command("muscles")
def list_muscles():
    """Extra: lista os músculos disponíveis na API (nome comum e nome em latim)."""
    print_json([{"name": m["name_en"] or m["name"], "latin": m["name"]} for m in paginate("muscle/")])


if __name__ == "__main__":
    app()
