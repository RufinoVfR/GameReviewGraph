# Guia de Implementação — Testes Compartilhados e Filtros em Paralelo

Este guia leva do estado atual (camada compartilhada pronta) até a implementação
dos nove filtros do pipeline **em paralelo**, sem que um time bloqueie o outro.
Está dividido em quatro partes:

- **Parte A** — Plano de testes da camada compartilhada (o que já existe, o que falta).
- **Parte B** — Contratos que **todo** filtro precisa respeitar (Template Method, GoF, serialização).
- **Parte C** — Guia passo a passo por filtro, com divisão de trabalho paralela.
- **Parte D** — Fluxo de trabalho, validação e *definition of done*.

> Todos os comandos passam por `make` (Docker). Nunca chame `python`/`python3` direto.

---

## Estado atual (ponto de partida)

A camada `src/shared/` está completa e testada (96 testes unitários passando):

| Camada | Módulos | Situação |
|--------|---------|----------|
| Infraestrutura GoF | `filter_base.py`, `pipeline.py`, `observers.py`, `strategies.py` | Pronta |
| Adaptadores de I/O | `storage.py` (S3/MinIO), `cache.py` (Redis) | Prontos |
| Utilitários de grafo | `graph/ops.py`, `graph/metrics.py`, `graph/traversal.py`, `graph/validate.py` | Prontos |
| Tipos | `types/` (`Graph`, `Queue`, aliases) | Prontos |

**Nenhum filtro concreto foi implementado ainda** — `src/` contém apenas
`config.py`, `types/` e `shared/`. É exatamente esse o trabalho a paralelizar.

---

# Parte A — Plano de testes da camada compartilhada

## A.1 — Cobertura atual

| Módulo | Arquivo de teste | Casos |
|--------|------------------|-------|
| `graph/ops.py` | `test_graph_ops.py` | CRUD, `iter_edges`, `copy_graph`, `build_graph_from_deltas`, **serialize/deserialize** |
| `graph/metrics.py` | `test_graph_metrics.py` | `neighbor_count`, `total_edge_weight`, contagens, `density`, `average_edge_weight` |
| `graph/traversal.py` | `test_graph_traversal.py` | BFS, DFS, componentes, `is_connected`, MST (Prim) |
| `graph/validate.py` | `test_graph_validate.py` | simetria, prefixos, nós isolados, `assert_valid` |

## A.2 — Lacunas a cobrir (camada compartilhada)

Estes testes ainda **não existem** e devem ser escritos antes/junto dos filtros,
pois são a rede de segurança que permite paralelizar com confiança:

1. **`strategies.py` — `ProgressiveEdgeCuttingStrategy`**
   Usar a fixture `clustered_graph` (dois clusters + ponte fraca).
   - `detect(graph, k=2)` separa nos dois clusters esperados.
   - Não muta o grafo de entrada (comparar antes/depois).
   - Para em `k` componentes (não corta além do necessário).
   - Reduz à MST antes de cortar (o resultado é estável mesmo com grafo denso).

2. **`filter_base.py` — `AbstractFilter` (Template Method)**
   Usar `mock_storage` (moto) + `mock_cache` (fakeredis) do `conftest.py`.
   Criar um filtro-dummy de teste e verificar:
   - Miss no cache → `process()` é chamado → grava no S3 → grava no cache.
   - Hit no cache → `process()` **não** é chamado → resultado vai ao S3 mesmo assim.
   - Multi-input (`extra_input_keys`) → `process()` recebe `{"primary": ..., "<key>": ...}`.
   - `output_format == "text"` → usa `write_text`.

3. **`pipeline.py` — `FilterChain` (Chain of Responsibility + Facade)**
   - Executa filtros na ordem da lista.
   - `from_filter` pula os anteriores (dispara `on_skip`) e começa no nome dado.
   - `from_filter` inválido → `ValueError`.
   - Exceção em um filtro aborta o restante (fail-fast).

4. **`observers.py` — `LoggingObserver`**
   - `on_start`/`on_complete`/`on_skip` não levantam exceção e não mutam estado.
   - Exceção dentro de observer é engolida (não aborta o pipeline).

## A.3 — Dois níveis de teste

| Nível | Marcador | Onde roda | Usa |
|-------|----------|-----------|-----|
| **Unit** | (default) | qualquer lugar via `make test` | fixtures + `mock_storage`/`mock_cache` (sem MinIO/Redis reais) |
| **Integração** | `@pytest.mark.env` ou `tests/integration/` | Docker com serviços de pé | MinIO + Redis reais |

- `make test` → `pytest` (deselect de `-m env`): unit, offline, rápido.
- `make test-cov` → `pytest` (deselect de `-m env`) com relatório de cobertura.
- `tests/integration/test_pipeline.py` → ponta-a-ponta, só faz sentido quando
  todos os filtros existirem e `data/comments.json` estiver no MinIO (`make init-data`).

## A.4 — Fixtures já disponíveis (`tests/conftest.py`)

Reaproveite — **não** recrie grafos à mão em cada teste:

| Fixture | O que entrega |
|---------|---------------|
| `make_graph(edges)` | helper: constrói `Graph` simétrico a partir de `[(u, v, w), ...]` |
| `raw_comments` | 4 comentários crus (2 tópicos) |
| `processed_comments` | 4 comentários já tokenizados (contrato do pacote `preprocessing/`) |
| `small_word_graph` | word graph mínimo para testar sentence/comment graph |
| `clustered_graph` | 2 clusters densos + 1 ponte fraca (community detection / traversal) |
| `mock_storage` | `S3Storage` sobre moto (S3 fake, offline) |
| `mock_cache` | `RedisCache` sobre fakeredis (offline) |

---

# Parte B — Contratos que todo filtro precisa respeitar

## B.1 — Template Method (`AbstractFilter`)

Todo filtro herda de `AbstractFilter` e implementa **apenas** `process()`. Todo o
I/O (ler do S3, gravar no S3, cache no Redis) já está em `execute()` — não
sobrescreva `execute()`, `_load_input()`, `_write_output()`, `_load_cache()` nem
`_save_cache()`.

```python
from src.shared.filter_base import AbstractFilter

class WordGraphFilter(AbstractFilter):
    name = "word_graph"        # slug único; também é a chave de cache Redis
    input_key = "tree"         # chave em S3_KEYS (config.py)
    output_key = "word_graph"  # chave em S3_KEYS

    def process(self, data):
        ...                    # única coisa que você escreve
        return resultado       # objeto JSON-serializável (ver B.3)

if __name__ == "__main__":
    WordGraphFilter().execute()
```

Rode isolado com `make word-graph` (cada filtro tem seu alvo no Makefile).

## B.2 — Filtros multi-input (`extra_input_keys`)

Quando um filtro precisa de mais de um artefato, declare `extra_input_keys`. Aí
`process()` recebe um **dict** `{"primary": <input_key>, "<extra>": <artefato>, ...}`.

A tabela de contrato (autoritativa — bata com isto, não com diagramas soltos):

| Filtro | `input_key` | `extra_input_keys` |
|--------|-------------|--------------------|
| `sentence_graph` | `"word_graph"` | `["tree"]` |
| `comment_graph` | `"sentence_graph"` | `["preprocessed"]` |
| `final_graph` | `"comment_graph"` | `["word_graph", "sentence_graph"]` |
| `metrics` | `"communities"` | `["final_graph"]` |

```python
class SentenceGraphFilter(AbstractFilter):
    name = "sentence_graph"
    input_key = "word_graph"
    extra_input_keys = ["tree"]
    output_key = "sentence_graph"

    def process(self, data: dict):
        word_graph = deserialize_graph(data["primary"])  # ver B.3
        tree = data["tree"]
        ...
```

## B.3 — Serialização de grafos (OBRIGATÓRIO)

`Graph` é um `dataclass` e **não** é serializável por `json.dumps`. Como
`execute()` grava a saída de `process()` via `write_json` (e cacheia o mesmo
objeto), todo filtro que mexe com grafo precisa traduzir nas duas pontas:

```python
from src.shared.graph import serialize_graph, deserialize_graph

# CONSUMIR um grafo recebido do S3 (dict → Graph):
graph = deserialize_graph(data)            # single-input
word_graph = deserialize_graph(data["primary"])  # multi-input

# PRODUZIR um grafo para o S3 (Graph → dict):
return serialize_graph(graph)
```

Mesma pegadinha em **`communities.json`**: as chaves de `dict[int, ...]` viram
**strings** no JSON. O consumidor (`metrics.py`) deve reconverter com `int(k)`.

## B.4 — Onde cada padrão GoF aparece (e o que você NÃO faz)

| Padrão | Classe | Seu papel ao implementar um filtro |
|--------|--------|-------------------------------------|
| **Template Method** | `AbstractFilter` | herdar e implementar só `process()` |
| **Chain of Responsibility + Facade** | `FilterChain` | registrar o filtro em `main.py`, na ordem do pipeline |
| **Observer** | `LoggingObserver` | nada — o `FilterChain` notifica sozinho |
| **Strategy** | `CommunityDetectionStrategy` | `community_detection.py` injeta a estratégia; **não** reimplemente BFS/MST/corte |

A `ProgressiveEdgeCuttingStrategy` **já está pronta** — `community_detection.py`
apenas a instancia e chama `detect(graph, K)`.

## B.5 — Regras não-negociáveis (valem nota)

- **Sem bibliotecas externas de grafo** (NetworkX, igraph, …) — −5,0 pontos.
- **BFS, DFS, MST, corte de arestas, centralidade, modularidade** implementados do zero (já estão em `shared/graph` e `strategies`; reutilize, não reescreva).
- **Filtros não importam uns aos outros** — só `src/shared/`, `src/config.py` e `src/types/`.
- **Sem S3/Redis dentro de `process()`** — isso é responsabilidade de `execute()`.
- **Docstring em toda função** (uma linha + `Args:` + `Returns:`) — vale nota.
- **Type hints em toda assinatura.**
- **NLP (NLTK) só no pacote `preprocessing/`** (spaCy não é usado).
- Código/comentários/commits em **inglês**; dados e relatório em **português**.

---

# Parte C — Guia passo a passo dos filtros (paralelizável)

## C.1 — Por que dá para paralelizar

Os filtros só conversam por **artefatos JSON de formato fixo**. Se os times
combinarem os formatos **antes** (a tabela abaixo), cada um implementa e testa o
seu filtro contra uma *fixture* do artefato de entrada — sem esperar o filtro de
cima ficar pronto. As fixtures de `conftest.py` já existem para isso.

### Contrato de artefatos (combine isto primeiro!)

| Artefato | Produtor | Formato JSON |
|----------|----------|--------------|
| `comments.json` | (dado) | `[{"id": int, "topic": str, "text": str}]` |
| `preprocessed.json` | `preprocessing` | `[{"id": int, "sentences": [[token, ...], ...]}]` (sem `topic` — ver nota abaixo) |
| `tree.json` | `tree` | árvore N-ária uniforme `{"type", "children", ...}` — formato completo no bloco abaixo |
| `word_graph.json` | `word_graph` | `serialize_graph()` → `{"nodes": [str, ...], "index": {str: int}, "matrix": [[float, ...], ...]}` |
| `sentence_graph.json` | `sentence_graph` | `serialize_graph()` → `{"nodes": [str, ...], "index": {str: int}, "matrix": [[float, ...], ...]}` |
| `comment_graph.json` | `comment_graph` | `serialize_graph()` → `{"nodes": [str, ...], "index": {str: int}, "matrix": [[float, ...], ...]}` |
| `final_graph.json` | `final_graph` | `serialize_graph()` → `{"nodes": [str, ...], "index": {str: int}, "matrix": [[float, ...], ...]}` |
| `communities.json` | `community_detection` | `{"<id>": [node_key, ...]}` (chaves string!) |
| `metrics.json` | `metrics` | dict com `modularity` + `communities` — formato completo no bloco abaixo |
| `report.txt` | `analysis` | texto (português) |

Os dois artefatos não-triviais ficam **totalmente definidos aqui** — nada é
deixado em aberto "para o dono do módulo decidir depois".

> **`topic` não circula no pipeline.** O rótulo de tópico é o *gabarito* (gold
> label): a detecção de comunidades é não supervisionada, então o `topic` é
> removido já no `preprocessing` e **não** aparece em `preprocessed.json` nem em
> `tree.json`/grafos. Ele permanece em `comments.json` e é reconciliado por `id`
> só na validação final (o `topic` em `metrics.json` é o tópico que **o sistema
> atribui** à comunidade, não o de entrada).

**`tree.json` — árvore N-ária uniforme** (nó genérico `{"type", "children"}`;
folhas carregam os dados de domínio). `sentence.index` é o índice global da
frase no dataset (vira o nó `s_<index>`); `comment.id` vira `c_<id>`;
`word.position` é a posição da palavra **dentro da frase** (insumo do peso
posicional do `word_graph`):

```json
{
  "type": "dataset",
  "children": [
    {
      "type": "comment", "id": 3,
      "children": [
        {
          "type": "sentence", "index": 12,
          "children": [
            {"type": "word", "value": "jogo",  "position": 0},
            {"type": "word", "value": "trava", "position": 1}
          ]
        }
      ]
    }
  ]
}
```

**`metrics.json` — métricas por comunidade + Q global:**

```json
{
  "modularity": 0.74,
  "communities": {
    "1": {
      "topic": "desempenho",
      "central_terms": ["fps", "travamento", "lag"],
      "comments": ["c_3", "c_17", "c_42"],
      "size": 18
    }
  }
}
```

- `modularity`: Q global do particionamento (um único float).
- `communities`: chaves string (`int(k)` ao reconverter), uma entrada por comunidade.
- `central_terms`: nós `w_` ordenados por `total_edge_weight` decrescente (top-N).
- `comments`: nós `c_` da comunidade. `size`: total de nós da comunidade.

## C.2 — Divisão em trilhas paralelas

```
Trilha 1 (NLP):     preprocessing → tree         [definem preprocessed.json e tree.json]
Trilha 2 (grafos):  word_graph → sentence_graph → comment_graph → final_graph
Trilha 3 (análise): community_detection → metrics → analysis
```

Todos podem começar **no dia 1** trabalhando contra fixtures. A ordem dentro de
cada trilha é só a ordem de **integração final**, não de início.

## C.3 — Receita por filtro

Para **cada** filtro, o passo a passo é o mesmo:

1. Crie a branch: `git checkout -b feat/<nome-do-filtro>`.
2. Escreva o esqueleto herdando `AbstractFilter` (declare `name`/`input_key`/`output_key` e `extra_input_keys` se preciso).
3. Implemente `process()` usando as ferramentas de `src.shared.graph`.
4. Substitua o teste placeholder em `tests/unit/test_<filtro>.py` por testes reais (use as fixtures).
5. `make test` (rebuild da imagem se mexeu em `src/` — ver Parte D).
6. Registre o filtro em `src/main.py` (posição = ordem no pipeline).
7. Rode isolado: `make <filtro>` e confirme o artefato no MinIO.
8. Abra PR.

### Filtro 1 — `preprocessing/` (pacote)
- **In:** `raw` → **Out:** `preprocessed`. NLP permitido aqui (e só aqui). É um **pacote** (`filter.py`, `clean.py`, `normalize.py`, `__main__.py`), não um arquivo — ver `src/preprocessing/CLAUDE.md` para o design completo.
- `process(data: list[RawComment]) -> list[ProcessedComment]`: caixa-baixa → **segmentar frases** (regex `[.!?]+`) → por frase: remover pontuação (preservando acento) → tokenizar (`\w+`) → dropar numéricos e `len<3` → remover stopwords PT (NLTK). A segmentação vem **antes** da remoção de pontuação — remover pontuação primeiro apagaria os terminadores `.!?` e colapsaria tudo numa única frase.
- **Normalização A1'** (decisão fechada — ver `docs/decisions.md`): o radical RSLP é só **chave de agrupamento**; emite-se a **forma de superfície mais frequente do grupo, com acento** (`{atualização, atualizações}` → nó `w_atualização`). O mapa radical→representante é montado numa passada de corpus dentro do `process()` e **não** sai do filtro. Corte por `MIN_FREQ` (de `src/config.py`) é por grupo.
- Frase vazia após filtragem é descartada; o comentário é mantido (pelo `id`).
- **`topic` é removido** (gabarito não supervisionado): a saída tem só `id` + `sentences`. Ver nota em C.1.
- **Infra:** o `Dockerfile` precisa baixar os corpora NLTK `stopwords` e `rslp` em build.
- Testes: usar `raw_comments`; verificar shape, `id` preservado, `topic` ausente, remoção de stopwords/ruído, agrupamento e representante (com acento).

### Filtro 2 — `tree.py`
- **In:** `preprocessed` → **Out:** `tree`. Árvore N-ária: Dataset → Comentário → Frase → Palavra.
- O formato de `tree.json` **já está fechado** no bloco "Contrato de artefatos" (C.1): nó uniforme `{"type", "children"}`, folhas `word` com `value` + `position`, `sentence.index` global, `comment.id`. Implemente exatamente esse formato — a Trilha 2 consome `position`/`index`/`id` dele.
- Testes: usar `processed_comments`; verificar hierarquia, contagem de nós por nível e que cada palavra carrega `position`.

### Filtro 3 — `word_graph.py`
- **In:** `tree` → **Out:** `word_graph`.
- Fórmula posicional, acumulada por co-ocorrência:
  ```python
  from src.shared.graph import build_graph_from_deltas, serialize_graph, assert_valid

  def _word_pair_deltas(tree):
      for sentence in iter_sentences(tree):          # palavras com posição
          for (wi, pos_i), (wj, pos_j) in pairs(sentence):
              if wi != wj:
                  yield (f"w_{wi}", f"w_{wj}", 1.0 / (1.0 + abs(pos_i - pos_j)))

  def process(self, data):
      graph = build_graph_from_deltas(_word_pair_deltas(data))
      assert_valid(graph)
      return serialize_graph(graph)
  ```
- Testes: simetria (`is_symmetric`), peso de pares conhecidos, prefixos `w_`.

### Filtro 4 — `sentence_graph.py`
- **In:** `word_graph` (+ `tree`) → **Out:** `sentence_graph`.
- Acumular `weight(wi, wj)` para `wi∈sa, wj∈sb` e **normalizar** por `|sa|·|sb|`:
  ```python
  word_graph = deserialize_graph(data["primary"])
  tree = data["tree"]
  # acumula via build_graph_from_deltas; depois normaliza com iter_edges + add_edge
  ```
- A **fórmula e a normalização vivem aqui** (domínio), nunca em `shared/graph`.
- Testes: usar `small_word_graph`; conferir um peso normalizado calculado à mão.

### Filtro 5 — `comment_graph.py`
- **In:** `sentence_graph` (+ `preprocessed`) → **Out:** `comment_graph`.
- Acumular `weight(si, sj)` para `si∈ca, sj∈cb` e **normalizar** por `|ca|·|cb|`:
  ```python
  sentence_graph = deserialize_graph(data["primary"])
  preprocessed = data["preprocessed"]
  # acumula via build_graph_from_deltas; depois normaliza com iter_edges + add_edge
  ```
- A **fórmula e a normalização vivem aqui** (domínio), nunca em `shared/graph`.
- Testes: conferir à mão um peso normalizado entre dois comentários; prefixos `c_`.

### Filtro 6 — `final_graph.py`
- **In:** `comment_graph` (+ `word_graph`, `sentence_graph`) → **Out:** `final_graph`.
- Unir os três níveis num só grafo + arestas hierárquicas (palavra↔frase↔comentário).
- `merge_graphs` é **helper privado deste arquivo** — não vai para `shared/graph`.
- Testes: nós dos três prefixos presentes; `assert_valid`.

### Filtro 7 — `community_detection.py`
- **In:** `final_graph` → **Out:** `communities`.
- Usa a **Strategy pronta**:
  ```python
  from src.shared.strategies import ProgressiveEdgeCuttingStrategy
  from src.shared.graph import deserialize_graph
  from src.config import K

  class CommunityDetectionFilter(AbstractFilter):
      def __init__(self, strategy=None):
          super().__init__()
          self._strategy = strategy or ProgressiveEdgeCuttingStrategy()

      def process(self, data):
          graph = deserialize_graph(data)
          communities = self._strategy.detect(graph, K)
          return {str(cid): nodes for cid, nodes in communities.items()}  # chaves string
  ```
- Testes: usar `clustered_graph`; conferir nº de comunidades e composição.

### Filtro 8 — `metrics.py`
- **In:** `communities` (+ `final_graph`) → **Out:** `metrics`.
- Centralidade de grau ponderada (`total_edge_weight`) + **modularidade Q** (do zero).
- Lembre: chaves de `communities.json` são string → `int(k)`.
- O schema de `metrics.json` **já está fechado** no bloco "Contrato de artefatos" (C.1): `modularity` (float global) + `communities` com `topic`/`central_terms`/`comments`/`size` por comunidade. Produza exatamente esse formato — a Trilha 3 (`analysis`) consome esses campos.

### Filtro 9 — `analysis.py`
- **In:** `metrics` (+ `communities`) → **Out:** `report` (texto, PT).
- `output_format = "text"`; usa `write_text` (já tratado por `execute()`).
- Formato do relatório: ver "Expected Output Format" no `CLAUDE.md` raiz.

## C.4 — Integração final (`main.py`)

Registrar todos os filtros na ordem do pipeline:

```python
chain = FilterChain(
    filters=[
        PreprocessingFilter(), TreeFilter(),
        WordGraphFilter(), SentenceGraphFilter(), CommentGraphFilter(), FinalGraphFilter(),
        CommunityDetectionFilter(), MetricsFilter(), AnalysisFilter(),
    ],
    observers=[LoggingObserver()],
)
chain.run()
```

---

# Parte D — Fluxo de trabalho e *definition of done*

## D.1 — Comandos

```bash
make docker-up      # sobe MinIO + Redis + app (primeira vez)
make init-data      # envia data/comments.json ao MinIO (primeira vez)
make test           # testes unitários (rebuild da imagem se mexeu em src/!)
make test-cov       # testes + cobertura
make <filtro>       # roda um filtro isolado dentro do Docker
make run            # pipeline completo
make clean          # limpa cache Redis + artefatos S3 (force reprocessamento)
```

> **Importante:** a imagem `app` copia `src/` e `tests/` no build (sem volume
> mount). Depois de alterar código, **rebuilde** antes de testar:
> `docker compose -f docker-compose.yml -f docker-compose.ci.yml build app && make test`.

> Mudou a **lógica** de um filtro mas o teste usa cache antigo? `make clean`
> esvazia as chaves `filter:*` do Redis e força o reprocessamento.

## D.2 — Definition of Done (por filtro)

- [ ] Herda `AbstractFilter`, implementa só `process()`.
- [ ] `name`/`input_key`/`output_key` (+ `extra_input_keys`) corretos.
- [ ] Grafos: `deserialize_graph` na entrada, `serialize_graph` na saída.
- [ ] Docstrings + type hints em tudo.
- [ ] Nenhum import de outro filtro; nenhuma chamada de S3/Redis em `process()`.
- [ ] Testes unitários reais (placeholder removido) passando com fixtures.
- [ ] `make <filtro>` gera o artefato esperado no MinIO.
- [ ] Registrado em `main.py` na posição certa.
- [ ] Branch + PR (nunca commit direto na `main`).

## D.3 — Ordem de merge sugerida

1. Camada de testes compartilhados (Parte A.2) — primeiro, é a rede de segurança.
2. `preprocessing` + `tree` (definem os formatos da Trilha 1).
3. `word_graph` → `sentence_graph` → `comment_graph` → `final_graph`.
4. `community_detection` → `metrics` → `analysis`.
5. `main.py` + teste de integração ponta-a-ponta (`tests/integration/test_pipeline.py`).

---

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 2026-06-16 | 1.0 | Versão inicial: plano de testes compartilhados + guia de filtros paralelos | Equipe |
| 2026-06-16 | 1.1 | Remove back-references ("idem"/"mesmo que"); fecha os contratos de `tree.json` e `metrics.json` sem deferir ao dono do módulo | Equipe |
| 2026-06-16 | 1.2 | Filtro 1 reescrito: pacote `preprocessing/`, pipeline por regex, normalização A1', descarte de ruído e requisito de dados NLTK no Docker | Equipe |
| 2026-06-16 | 1.3 | `topic` removido de `preprocessed.json` e `tree.json` (rótulo-ouro fica só no raw, reconciliado por `id` na validação) | Equipe |
