# Decisões de Projeto

Este documento reúne, em um só lugar, as decisões arquiteturais e algorítmicas do GameReviewGraph e a justificativa de cada uma. As decisões já aparecem espalhadas em `arquitetura.md`, `padroes_projeto.md`, `grafos.md` e `requisitos.md` — esta página existe para registrar o **porquê** de cada uma, não para repetir o **o quê**.

---

## Arquitetura geral

### Pipe-and-filter com 9 filtros sequenciais

**Decisão:** o pipeline é modelado como uma cadeia de filtros independentes (`preprocessing.py` → ... → `analysis.py`), cada um lendo seu artefato de entrada do MinIO e escrevendo sua saída de volta, sem comunicação direta entre filtros.

**Por quê:** o problema é naturalmente uma sequência de transformações de dados (texto → árvore → grafos → comunidades → métricas → relatório), e cada etapa tem uma responsabilidade única e testável isoladamente. Isolar os filtros via I/O em S3/Redis (em vez de import direto entre módulos Python) impõe a regra "nenhum filtro conhece a implementação de outro", o que facilita testes unitários (mockar o artefato de entrada) e permite re-executar uma etapa isolada via `make <filtro>` sem rodar o pipeline inteiro.

### MinIO (S3) para artefatos + Redis para cache

**Decisão:** cada filtro lê/escreve JSON em MinIO sob `pipeline/<nome>.json`; o resultado também é cacheado em Redis (`filter:<nome>`) para pular reprocessamento.

**Por quê:** simula um ambiente de produção real (storage de objetos + cache) sem exigir infraestrutura cloud paga — ambos rodam localmente via Docker Compose. O cache em Redis evita reprocessar filtros caros (ex: `word_graph.py` em corpus grande) quando apenas um filtro downstream muda durante o desenvolvimento.

### GoF Patterns: Template Method, Chain of Responsibility + Facade, Observer, Strategy

**Decisão:** `AbstractFilter` (Template Method) fixa o ciclo load → process → save; `FilterChain` (Chain of Responsibility + Facade) orquestra a execução; `PipelineObserver` (Observer) reage a eventos sem acoplar lógica aos filtros; `CommunityDetectionStrategy` (Strategy) isola o algoritmo de particionamento.

**Por quê:** a disciplina exige aplicação de padrões de projeto GoF; os quatro escolhidos resolvem problemas reais do pipeline (não foram forçados): toda transformação segue o mesmo esqueleto (Template Method), a ordem de execução precisa ser centralizada e configurável (Chain of Responsibility), logging/observação não deve viver dentro da lógica de domínio (Observer), e o algoritmo de detecção de comunidades precisa ser trocável sem alterar o filtro que o chama (Strategy — usado, por exemplo, para permitir comparar `ProgressiveEdgeCuttingStrategy` com variações futuras).

### Filtros multi-input via `extra_input_keys`

**Decisão:** filtros que precisam de mais de um artefato (`sentence_graph`, `comment_graph`, `final_graph`, `metrics`) declaram `extra_input_keys` em vez de o Template Method ganhar um novo método.

**Por quê:** mantém `execute()` com uma única forma de carregar dados (dict com `"primary"` + chaves extras) em vez de cada filtro implementar seu próprio I/O — preserva a garantia de que `process()` nunca toca em I/O diretamente.

---

## Representação do grafo

### `Graph` como matriz de adjacência + mapeamento nome→índice (não dict de adjacências)

**Decisão:** `Graph` (em `src/types/graph.py`) é uma dataclass com `nodes: list[str]`, `index: dict[str, int]` e `matrix: list[list[float]]`, em vez do dict aninhado `dict[str, dict[str, float]]` usado na primeira versão da spec.

**Por quê:** decisão explícita do time de trocar para uma representação vetorial com um mapeamento nome→índice (um `dict` simples — estrutura nativa da linguagem, não uma tabela hash implementada pelo grupo). A matriz cresce um nó por vez (sem pré-alocação de capacidade) porque a estrutura já é O(n²) no tamanho final — crescer incrementalmente custa, no total, o mesmo que alocar tudo de uma vez, então não há ganho em reservar espaço extra como se faz em arrays 1D. `0.0` foi escolhido como sentinela de "sem aresta" porque toda fórmula de peso do projeto produz valores estritamente positivos (nunca há ambiguidade entre "peso zero real" e "aresta inexistente").

### `src/types/` como pacote dividido por semântica

**Decisão:** `src/types.py` foi convertido em pacote (`comments.py`, `graph.py`, `communities.py`, `metrics.py`, re-exportados em `__init__.py`), em vez de um único arquivo com todos os aliases.

**Por quê:** consequência direta da decisão anterior — `Graph` deixou de ser um alias de uma linha e passou a ser uma dataclass com docstring própria; agrupar por semântica evita um arquivo monolítico crescendo sem organização à medida que mais tipos são necessários (ex: tipos da árvore N-ária).

### `Queue` própria (lista ligada) em vez de `collections.deque`

**Decisão:** `bfs` (em `src/shared/graph/traversal.py`) usa `Queue` — uma fila FIFO implementada do zero em `src/types/queue.py` como lista ligada simples (ponteiros `head`/`tail`, O(1) `enqueue`/`dequeue`) — em vez de `collections.deque` da biblioteca padrão.

**Por quê:** decisão explícita do time de não depender da estrutura pronta da linguagem para a fila usada no algoritmo de travessia, mesmo sem ser estritamente exigido pelo RNF01 (que cobre os algoritmos de grafo, não estruturas de apoio genéricas — ver decisão "Por que nenhum algoritmo usa biblioteca externa"). `Queue` vive em `src/types/`, não em `src/shared/graph/`, porque é uma estrutura genérica sem semântica de grafo (não conhece nós, arestas ou pesos) — fica junto dos outros tipos genéricos do pacote, não junto das operações específicas de grafo.

### DFS com pilha explícita, visitado marcado no `pop` (não no `push`)

**Decisão:** `dfs` usa uma pilha explícita (`list` do Python) em vez de recursão, e marca um nó como visitado somente quando ele é removido da pilha (`pop`), não quando é inserido (`push`).

**Por quê:** evita o limite de recursão do Python em grafos maiores. Marcar visitado no `push` (o mesmo padrão usado no BFS) parece equivalente à primeira vista, mas produz uma ordem de visita diferente da DFS recursiva real — testado manualmente com `w_a-w_b, w_a-w_c, w_b-w_d`: marcar no push dá `[a, b, c, d]` (ordem tipo BFS invertido), enquanto marcar no pop dá `[a, b, d, c]`, igual à recursão (`visita a → primeiro vizinho b → primeiro vizinho de b que é d → backtrack → c`). Os vizinhos são empurrados em ordem reversa (`reversed(_neighbors(...))`) exatamente para preservar essa correspondência com a ordem de visita recursiva.

---

## Algoritmos implementados do zero

### Por que nenhum algoritmo usa biblioteca externa

**Decisão:** BFS, DFS, MST (Prim), corte progressivo de arestas, centralidade de grau ponderada e modularidade Q são implementados manualmente, sem NetworkX/igraph/graph-tool.

**Por quê:** requisito não-negociável da disciplina (RNF01, penalização de -5,0 pontos) — o objetivo de avaliação é a implementação de estruturas de dados e algoritmos de grafo, não o uso de uma biblioteca pronta. NLP (NLTK/spaCy) é a única exceção, e só no pré-processamento, porque tokenização/stopwords não são o objeto de avaliação em estrutura de dados.

### Prim (denso) em vez de Kruskal para a MST

**Decisão:** a árvore geradora mínima usada na detecção de comunidades é construída com a variante densa/array de Prim (O(V²), sem fila de prioridade), não com Kruskal.

**Por quê:** os grafos do projeto (word/sentence/comment) tendem a ser densos — cada par que co-ocorre gera uma aresta, em um corpus pequeno (~200 comentários). Em grafo denso, Kruskal custaria O(E log E) ≈ O(V² log V) (E ≈ V²/2), e ainda exigiria extrair e ordenar todas as arestas da matriz mais uma estrutura Union-Find. Prim denso é O(V²) e opera diretamente sobre a matriz de adjacência já existente — sem heap, sem Union-Find, sem extrair lista de arestas primeiro. Foi a opção de menor custo assintótico que também é a mais simples de implementar dado o tipo de dado já escolhido.

### MST + corte progressivo, em vez de corte progressivo direto no grafo denso

**Decisão:** `community_detection.py` primeiro reduz o `final_graph` a uma MST via Prim, e só então aplica o corte progressivo de arestas (ordenar por peso ascendente, cortar se `degree(u) > 1 e degree(v) > 1`, parar em K componentes) sobre essa árvore — em vez de cortar arestas direto no grafo completo.

**Por quê:** decisão de integrar os dois algoritmos: reduzir primeiro a V−1 arestas torna o corte progressivo mais barato (menos arestas para ordenar e avaliar) e mais previsível, já que a MST já captura as conexões de menor custo total entre os nós antes de qualquer corte. A condição `degree > 1` foi mantida mesmo sobre uma árvore (onde cortar qualquer aresta sempre separa em exatamente 2 componentes) para proteger nós-folha (grau 1) de virarem comunidades de tamanho 1 prematuramente — preservando o comportamento já validado do corte progressivo original.

### K = 10 comunidades

**Decisão:** `K=10` é uma constante global em `src/config.py`, não hardcoded nos filtros.

**Por quê:** corresponde exatamente ao número de tópicos do dataset (desempenho, narrativa, multiplayer, etc.) — o objetivo é que a detecção de comunidades recupere esses 10 tópicos a partir da estrutura do grafo, sem que o algoritmo "veja" os rótulos de tópico originais. Mantê-lo como constante (em vez de espalhado pelo código) facilita ajustar o experimento sem alterar lógica de filtro.

---

## Convenções de linguagem e execução

### Código em inglês, dados/relatórios em português

**Decisão:** todo código, docstring e mensagem de commit é em inglês; os dados de entrada e os relatórios gerados (`report.txt`) são em português.

**Por quê:** o código é avaliado academicamente com padrões de engenharia de software (inglês é convenção de mercado), mas o produto final (relatório de comunidades) é consumido por um avaliador brasileiro analisando comentários em português — traduzir os termos centrais/tópicos para inglês só adicionaria ruído à interpretação semântica, que é parte avaliada (Análise de Resultados, peso 2.0).

### Tudo via Docker + `make`, nunca `python`/`python3` direto

**Decisão:** toda execução (`make run`, `make word-graph`, `make test`, ...) passa por `docker compose run`.

**Por quê:** garante que todo membro do grupo (e o avaliador, se necessário) execute o pipeline com as mesmas versões de Python/dependências e com MinIO/Redis já configurados — elimina "funciona na minha máquina" e mantém o ambiente reprodutível até a entrega final.

### `uv` em vez de `requirements.txt`

**Decisão:** dependências são gerenciadas via `pyproject.toml` + `uv`.

**Por quê:** lockfile determinístico e instalação mais rápida que pip puro, sem custo de complexidade adicional para um projeto deste tamanho.

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 16/06/2026 | 1.0 | Criação do documento, consolidando decisões já tomadas no projeto | Lucas Antunes |
| 16/06/2026 | 1.1 | `traversal.py` implementado (BFS, DFS, componentes conectados, MST); adicionada `Queue` própria em `src/types/queue.py`; justificada a marcação de visitado no `pop` da DFS | Lucas Antunes |
