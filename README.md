# fitcli — TP1 de ALP (2026/27)

CLI em Python para explorar a API pública de exercício físico
[wger](https://wger.de/api/v2/), usando os módulos `requests`, `re` e `typer`.

**Grupo**

| Nome | Número |
|---|---|
| Miguel Athayde | a113498 |
| Guilherme Silva | a114993 |
| João Carvas | a113326 |

## Instalação

```bash
pip install -r requirements.txt
```

## Utilização

```bash
python fitcli.py --help
```

| Alínea | Comando | O que faz |
|---|---|---|
| a) | `python fitcli.py top 10` | Lista os 10 exercícios mais recentes (nome, categoria, equipamento) |
| b) | `python fitcli.py search biceps 5` | Pesquisa exercícios por músculo e/ou categoria |
| c) | `python fitcli.py type 73` | Indica o tipo de esforço: `compound`, `isolated`, `cardio` ou `other` |
| d) | `python fitcli.py equipment chest` | Conta menções a equipamento nas descrições de uma categoria |
| e) | `python fitcli.py workout biceps,back compound 5` | Gera um plano de treino em JSON |
| e) | `python fitcli.py workout chest,shoulders isolated 3 --csv treino.csv` | Exporta o plano para CSV |
| extra | `python fitcli.py categories` | Lista as categorias disponíveis |
| extra | `python fitcli.py muscles` | Lista os músculos disponíveis |

Os `id` mostrados pelos comandos `top` e `search` podem ser usados no comando `type`.

## Organização do código

Todo o código está em `fitcli.py`, dividido em secções:

1. **Configuração** — URL da API, cabeçalho `User-Agent`, língua (inglês = 2).
2. **Expressões regulares** — limpeza de HTML, tipo de esforço e equipamento.
3. **Comunicação com a API** — `get_json` (pedido + verificação do status code) e `paginate` (paginação).
4. **Tratamento dos dados** — `simplify`, `fetch_exercises`, `search_exercises`, `classify`, `count_equipment`.
5. **Comandos da CLI** — uma função por alínea, que reutiliza as funções anteriores.

## Boas práticas de utilização da API

- Todos os pedidos levam um cabeçalho `User-Agent` identificativo.
- O *status code* de cada resposta é verificado; os erros são mostrados de forma clara.
- A paginação segue o campo `next` da resposta até não existirem mais páginas.
