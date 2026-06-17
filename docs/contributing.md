# Guia de Contribuição

Este documento define o processo de trabalho colaborativo no **GameReviewGraph**: fluxo Git, padrões de código, como executar o pipeline e os critérios de conclusão de cada módulo.

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

1. Descomente os imports no arquivo `tests/unit/test_<modulo>.py` correspondente
2. Substitua o `test_placeholder` por testes reais que cobrem a função principal e casos de borda
3. Use as fixtures de `tests/conftest.py` (`raw_comments`, `processed_comments`, `small_word_graph`) como ponto de partida

O CI executa `make test` automaticamente em todo PR para `main` ou `dev`. O PR só pode ser mergeado se todos os testes passarem.

---

## 6. Adicionando um Novo Filtro

1. Crie `src/<nome>.py` herdando de `AbstractFilter` (importado de `src/shared/filter_base.py`)
2. Declare `name`, `input_key` e `output_key` como atributos de classe
3. Implemente apenas `process(data)` — o I/O e o cache são herdados
4. Adicione o bloco `if __name__ == "__main__"` para execução isolada
5. Instancie o filtro e registre-o na `FilterChain` em `src/main.py` na posição correta
6. Descomente e implemente `tests/unit/test_<nome>.py`
7. Documente o contrato de interface (tipos de entrada/saída) em `docs/arquitetura.md`
8. Adicione o `make <filtro>` ao `Makefile` e o arquivo de saída à estrutura `data/`

**Template de filtro concreto:**

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
| **Bibliotecas de PLN** | NLTK e spaCy são permitidas exclusivamente em `preprocessing.py` |

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
