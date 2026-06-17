# Guia de Contribuição

Este documento define o processo de trabalho colaborativo no **GameReviewGraph**: fluxo Git, padrões de código, como executar o pipeline e os critérios de conclusão de cada módulo.

---

## 0. Quick Start — do zero ao primeiro filtro

Entrou no projeto hoje e vai implementar um filtro? Siga esta trilha de leitura
**nesta ordem** — é o mínimo suficiente, não "leia tudo".

**Caminho crítico (ler em ordem):**

1. **[`CLAUDE.md`](https://github.com/RufinoVfR/GameReviewGraph/blob/main/CLAUDE.md) (raiz)** — panorama, arquitetura pipe-and-filter, fórmulas dos algoritmos e as **regras inegociáveis** (sem libs de grafo, docstrings, inglês no código).
2. **[Guia de Implementação](guia_implementacao.md)** — o documento-âncora: receita passo a passo por filtro, contratos que todo filtro respeita, contrato de artefatos JSON (já fechado, inclui `tree.json` e `metrics.json`), trilhas paralelas e *definition of done*. Se ler só um arquivo, é este.
3. **`src/CLAUDE.md`** — template do filtro, mapa de módulos, `S3_KEYS`, contratos de tipo, como I/O e cache funcionam por baixo do `execute()`.
4. **`src/shared/CLAUDE.md`** — contratos GoF que você herda/usa: `AbstractFilter`, tabela de filtros multi-input (`extra_input_keys`), `FilterChain`, regras de import.

**Referência (deixar aberto enquanto codifica):**

5. **`src/shared/graph/CLAUDE.md`** — API das ferramentas de grafo (`build_graph_from_deltas`, `serialize_graph`, `iter_edges`, `assert_valid`…).
6. **`tests/conftest.py`** — fixtures prontas (`make_graph`, `clustered_graph`, `mock_storage`, `mock_cache`) — ver §5 deste guia.

**Contexto, se sobrar tempo (não bloqueia implementar):** [Arquitetura](arquitetura.md), [Padrões de Projeto](padroes_projeto.md), [Decisões de Projeto](decisions.md).

> Resumo: raiz `CLAUDE.md` → Guia de Implementação → `src/CLAUDE.md` → `src/shared/CLAUDE.md`, com `src/shared/graph/CLAUDE.md` e `conftest.py` abertos ao lado. Os quatro `CLAUDE.md` formam uma árvore (cada subpasta aprofunda a anterior) — leitura de cima para baixo.

Depois da leitura, o passo a passo prático está em **§6 (Adicionando um Novo Filtro)** e a receita por filtro na Parte C do Guia de Implementação.

---

## 1. Fluxo Git

**Regra absoluta: nunca commitar diretamente na branch `main`.**

```text
main        ← branch protegida; só recebe merges via PR aprovado
  └── feat/preprocessing     ← uma branch por módulo ou história de usuário
  └── feat/word-graph
  └── fix/sentence-weight
  └── docs/arquitetura
```

### Passo a passo

```bash
# 1. Atualize main antes de criar sua branch
git checkout main && git pull origin main

# 2. Crie uma branch descritiva
git checkout -b feat/nome-do-modulo

# 3. Commite com mensagem em inglês, imperativa
git commit -m "Add word graph co-occurrence weight formula"

# 4. Abra PR para main; solicite revisão de ao menos 1 membro
gh pr create --title "Add word_graph.py filter" --base main
```

**Formato de mensagem de commit:**

```text
<tipo>: <descrição curta em inglês> (máx. 72 chars)

Tipos: feat | fix | docs | refactor | test | chore
```

---

## 2. Configurando o ambiente

O pipeline roda inteiramente dentro de Docker. Pré-requisitos: Docker Engine 24+ e Docker Compose v2.

```bash
# 1. Instale dependências locais (só para docs e linting — não para o pipeline)
make install

# 2. Copie as variáveis de ambiente
cp .env.example .env

# 3. Construa a imagem e suba os serviços
make docker-up

# 4. Faça upload do arquivo de entrada bruta para MinIO (uma única vez)
make init-data
```

Consulte `docs/infraestrutura.md` para detalhes sobre MinIO, Redis e variáveis de ambiente.

---

## 3. Executando o Pipeline Completo

```bash
make run
```

`main.py` instancia a `FilterChain` com todos os 9 filtros e os executa em sequência. Cada filtro lê seu artefato de entrada do MinIO, processa, grava o resultado de volta no MinIO e armazena em cache no Redis. O relatório final fica disponível em `s3://game-review-graph/pipeline/report.txt` e é impresso no terminal.

---

## 4. Executando um Filtro em Isolamento

Cada módulo pode ser executado individualmente via `make`. O filtro lê seu artefato de entrada do MinIO e grava a saída sem rodar o pipeline inteiro.

```bash
make preprocessing        # Filtro 1 — pré-processamento
make tree                 # Filtro 2 — árvore N-ária
make word-graph           # Filtro 3 — grafo de palavras
make sentence-graph       # Filtro 4 — grafo de frases
make comment-graph        # Filtro 5 — grafo de comentários
make final-graph          # Filtro 6 — grafo unificado
make community-detection  # Filtro 7 — detecção de comunidades
make metrics              # Filtro 8 — centralidade e modularidade
make analysis             # Filtro 9 — relatório
```

**Pré-condição:** o artefato de entrada do filtro deve existir no MinIO (gerado pelos filtros anteriores ou pelo `make init-data` para o Filtro 1). Inspecione os artefatos disponíveis em `http://localhost:9001`.

**Template obrigatório para cada módulo:**

```python
if __name__ == "__main__":
    NomeDoFiltro().execute()
```

O `execute()` herdado de `AbstractFilter` cuida de todo o I/O com MinIO e Redis automaticamente.

---

## 5. Executando os Testes

```bash
make test      # roda todos os testes
make test-cov  # roda com relatório de cobertura por linha
```

Os testes ficam em `tests/unit/test_<modulo>.py` (um arquivo por filtro) e `tests/integration/test_pipeline.py`.

**Ao implementar um filtro:**

1. Substitua o `test_placeholder` por testes reais que cobrem a função principal e casos de borda
2. Use as fixtures de `tests/conftest.py` como ponto de partida (listadas abaixo)
3. Nunca suba testes que dependem de MinIO ou Redis reais — use `mock_storage` e `mock_cache`

O CI executa `make test` automaticamente em todo PR para `main` ou `dev`. O PR só pode ser mergeado se todos os testes passarem.

### Fixtures disponíveis em `tests/conftest.py`

| Fixture / Função | Tipo | Descrição |
|------------------|------|-----------|
| `raw_comments` | fixture | 4 comentários brutos em 2 tópicos (`list[dict]`) |
| `processed_comments` | fixture | Versão pré-tokenizada dos comentários acima |
| `small_word_graph` | fixture | Grafo de palavras com 6 nós e 2 componentes implícitos |
| `clustered_graph` | fixture | Grafo com 2 clusters densos e uma ponte fraca — ideal para testar corte de arestas |
| `mock_storage` | fixture | `S3Storage` com backend moto (sem MinIO real); reseta o singleton após o teste |
| `mock_cache` | fixture | `RedisCache` com backend fakeredis (sem Redis real); reseta o singleton após o teste |
| `make_graph(edges)` | função | Constrói um `Graph` simétrico a partir de uma lista `[(u, v, weight), ...]` |

**Exemplo — testando um filtro sem infraestrutura:**

```python
from tests.conftest import make_graph

class TestWordGraph:
    def test_co_occurrence_weight(self, mock_storage, mock_cache):
        # mock_storage e mock_cache garantem que execute() não tenta
        # conectar em http://minio:9000 nem em redis://redis:6379
        ...

    def test_graph_is_symmetric(self, small_word_graph):
        for u, neighbors in small_word_graph.items():
            for v, w in neighbors.items():
                assert small_word_graph[v][u] == w

    def test_bridge_cut_splits_graph(self, clustered_graph):
        # clustered_graph tem ponte (w_a1—w_b1, peso 0.1)
        # remover ela deve resultar em 2 componentes
        ...
```

---

## 6. Adicionando um Novo Filtro

1. Crie `src/<nome>.py` herdando de `AbstractFilter` (importado de `src/shared/filter_base.py`)
2. Declare `name`, `input_key`, `output_key` e, se necessário, `extra_input_keys` como atributos de classe
3. Implemente apenas `process(data)` — o I/O e o cache são herdados
4. Adicione o bloco `if __name__ == "__main__"` para execução isolada
5. Instancie o filtro e registre-o na `FilterChain` em `src/main.py` na posição correta
6. Implemente `tests/unit/test_<nome>.py` (substitua `test_placeholder`)
7. Documente o contrato de interface (tipos de entrada/saída) em `docs/arquitetura.md`
8. Adicione o `make <filtro>` ao `Makefile`

**Template — filtro de entrada única:**

```python
from src.shared.filter_base import AbstractFilter
from src.types import Graph

class WordGraphFilter(AbstractFilter):
    """Build word co-occurrence graph from the N-ary tree."""

    name = "word_graph"
    input_key = "tree"
    output_key = "word_graph"

    def process(self, data: dict) -> Graph:
        """Transform N-ary tree into word co-occurrence graph.

        Args:
            data: Serialized NaryTree loaded from tree.json.

        Returns:
            Adjacency dict mapping word node → {neighbor: weight}.
        """
        ...
```

**Template — filtro de múltiplas entradas (`extra_input_keys`):**

```python
from src.shared.filter_base import AbstractFilter
from src.types import Graph

class SentenceGraphFilter(AbstractFilter):
    """Build sentence graph from word graph and N-ary tree."""

    name = "sentence_graph"
    input_key = "word_graph"        # artefato primário
    extra_input_keys = ["tree"]     # artefatos secundários
    output_key = "sentence_graph"

    def process(self, data: dict) -> Graph:
        """Derive sentence graph from word co-occurrence weights.

        Args:
            data: Dict with keys "primary" (word_graph) and "tree".

        Returns:
            Adjacency dict mapping sentence node → {neighbor: weight}.
        """
        word_graph = data["primary"]
        tree = data["tree"]
        ...
```

---

## 7. Usando os Padrões de Projeto

Os cinco padrões GoF são infraestrutura do pipeline. Seguir as regras abaixo garante que o sistema permaneça extensível sem violar o contrato entre os filtros. Veja [Padrões de Projeto](padroes_projeto.md) para a especificação completa.

### Regra geral: não modifique `src/shared/` sem revisão da equipe

PRs que alteram qualquer arquivo em `src/shared/` requerem aprovação de **todos os membros da equipe** antes do merge — esses arquivos afetam todos os filtros simultaneamente.

### Template Method — como usar `AbstractFilter`

| Faça | Não faça |
|------|----------|
| Herde `AbstractFilter` em todo filtro concreto | Implementar I/O de JSON manualmente no filtro |
| Implemente apenas `process(data)` | Sobrescrever `execute()`, `_load_input()` ou `_write_output()` |
| Declare `name`, `input_key`, `output_key` como atributos de classe | Definir esses atributos no `__init__` |
| Chame `super().__init__()` se adicionar um `__init__` próprio | Duplicar a lógica de cache em `process()` |

### Chain of Responsibility — como registrar filtros

O único lugar onde filtros são instanciados e encadeados é `src/main.py`. A ordem da lista é a ordem de execução.

```python
# src/main.py
from src.shared.pipeline import FilterChain
from src.preprocessing import PreprocessingFilter
from src.word_graph import WordGraphFilter

chain = FilterChain(
    filters=[
        PreprocessingFilter(),
        WordGraphFilter(),
        # ... demais filtros em ordem
    ],
    observers=[LoggingObserver()],
)
chain.run(from_filter=args.from_filter)
```

Nunca instancie um filtro fora de `main.py` a não ser em testes.

### Observer — como adicionar um listener

Crie uma subclasse de `PipelineObserver` em `src/shared/observers.py` e registre-a na `FilterChain` em `main.py`. Não modifique `FilterChain._notify_*` para adicionar comportamentos novos.

```python
class MetricsObserver(PipelineObserver):
    """Record per-filter elapsed times for benchmarking."""

    def on_start(self, filter_name: str) -> None:
        self._start = time.perf_counter()

    def on_complete(self, filter_name: str, elapsed: float) -> None:
        print(f"{filter_name}: {elapsed:.2f}s")

    def on_skip(self, filter_name: str) -> None:
        pass
```

### Strategy — quando criar uma nova estratégia

Crie uma subclasse de `CommunityDetectionStrategy` em `src/shared/strategies.py` apenas para algoritmos de detecção de comunidades alternativos ao corte progressivo de arestas. Injete a estratégia no construtor de `CommunityDetectionFilter`.

```python
# src/community_detection.py
class CommunityDetectionFilter(AbstractFilter):
    def __init__(self, strategy: CommunityDetectionStrategy | None = None) -> None:
        super().__init__()
        self._strategy = strategy or ProgressiveEdgeCuttingStrategy()
```

Não use `Strategy` para outros tipos de variação algorítmica — crie funções auxiliares privadas dentro do filtro correspondente.

---

## 9. Padrões de Código

| Regra | Detalhe |
|-------|---------|
| **Linguagem** | Python 3.11+ |
| **Type hints** | Obrigatórios em toda função pública |
| **Docstrings** | Obrigatórias em toda função — propósito, `Args:`, `Returns:` |
| **Comentários** | Apenas quando o *porquê* é não-óbvio; jamais descrever o que o código faz |
| **Imports** | Ordem: stdlib → third-party → local; separados por linha em branco |
| **Chaves S3/Redis** | Use `S3_KEYS` de `src/config.py`; nunca hardcode nomes de artefatos ou chaves Redis |
| **Idioma** | Código, comentários, docstrings e commits em **inglês**; dados e relatório em **português** |
| **Bibliotecas proibidas** | NetworkX, igraph, graph-tool e equivalentes — penalidade de −5,0 pontos |
| **Bibliotecas de PLN** | NLTK é permitida exclusivamente no pacote `preprocessing/` (spaCy não é usado) |

---

## 10. Definition of Done (por módulo)

Um módulo está concluído quando **todos** os critérios abaixo são verdadeiros:

- [ ] Executa sem erros via `make <nome-do-filtro>` (dentro de Docker)
- [ ] `make test` passa sem falhas (todos os `test_placeholder` substituídos por testes reais)
- [ ] Artefato JSON de saída gravado corretamente no MinIO (verificável em `http://localhost:9001`)
- [ ] Saída consistente com os exemplos documentados em `docs/arquitetura.md`
- [ ] Toda função pública tem type hints e docstring
- [ ] Filtro concreto herda `AbstractFilter` e implementa apenas `process()`
- [ ] Filtro registrado na `FilterChain` em `src/main.py`
- [ ] Nenhuma importação direta entre filtros de domínio (somente `src/shared/`, `src/config.py`, `src/types.py`)
- [ ] Código commitado em branch própria e PR aberto para `main` ou `dev`
- [ ] PR aprovado por ao menos 1 outro membro da equipe e CI verde
- [ ] PRs em `src/shared/` aprovados por **todos** os membros da equipe

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 12/06/2026 | 1.0 | Criação inicial do documento | Lucas Antunes |
| 12/06/2026 | 1.1 | Seções de padrões GoF, template de filtro concreto, DoD atualizado | Lucas Antunes |
| 12/06/2026 | 1.2 | Migração para Docker + MinIO + Redis: seções 2, 3, 4 e DoD atualizados | Lucas Antunes |
| 12/06/2026 | 1.3 | Fixtures de teste (mock_storage, mock_cache, clustered_graph, make_graph); template multi-input com extra_input_keys | Lucas Antunes |
| 16/06/2026 | 1.4 | Seção Quick Start com a trilha de leitura do zero ao primeiro filtro | Equipe |
| 16/06/2026 | 1.5 | PLN restrita ao pacote `preprocessing/` (NLTK; spaCy não usado) | Equipe |
