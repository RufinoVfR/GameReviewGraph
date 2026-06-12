# Backlog do Produto

O backlog reúne todas as funcionalidades previstas para o **GameReviewGraph** na forma de histórias de usuário, elaboradas com base nos requisitos funcionais definidos. Ele representa a visão consolidada do produto e é organizado em uma hierarquia de três níveis: **Temas Estratégicos (TE)**, **Épicos (E)** e **Histórias de Usuário (US)**.

---

## 9.1 Backlog Geral

### Temas Estratégicos

| ID | Descrição |
|----|-----------|
| TE01 | Processamento e Representação dos Dados Textuais |
| TE02 | Construção e Integração dos Grafos Hierárquicos |
| TE03 | Detecção de Comunidades e Análise de Resultados |

---

### Épicos

| Tema | ID | Épico | Descrição |
|------|----|-------|-----------|
| TE01 | E01 | Pré-processamento Textual | Implementar o pipeline de limpeza e normalização dos comentários brutos, produzindo tokens estruturados prontos para inserção na árvore e nos grafos. |
| TE01 | E02 | Estrutura Hierárquica (Árvore N-ária) | Representar explicitamente a hierarquia Dataset → Comentário → Frase → Palavra por meio de uma Árvore N-ária implementada do zero, com navegação bidirecional entre níveis. |
| TE02 | E03 | Construção dos Grafos por Nível | Construir os três grafos independentes — palavras, frases e comentários — com suas respectivas fórmulas de peso e estruturas de adjacência. |
| TE02 | E04 | Integração em Grafo Final Unificado | Unificar os três grafos e as arestas hierárquicas da árvore em uma única estrutura, identificando vértices por tipo via prefixo. |
| TE03 | E05 | Detecção de Comunidades | Implementar o algoritmo de corte progressivo de arestas com BFS/DFS para fragmentar o grafo final em K = 10 comunidades semânticas. |
| TE03 | E06 | Métricas de Qualidade e Relatório | Calcular centralidade de grau ponderada e modularidade Q, e gerar o relatório final com os tópicos identificados e suas métricas. |

---

### Histórias de Usuário

| ID | História de Usuário | Tema | Épico |
|----|---------------------|------|-------|
| US01 | Como pesquisador, eu quero que o sistema converta comentários brutos em tokens normalizados para que os dados estejam prontos para modelagem em grafos sem ruído linguístico. | TE01 | E01 |
| US02 | Como pesquisador, eu quero que o sistema remova stopwords e termos de baixa frequência para que apenas as palavras semanticamente relevantes compõam os grafos. | TE01 | E01 |
| US03 | Como pesquisador, eu quero que o sistema organize os dados pré-processados em uma Árvore N-ária com quatro níveis hierárquicos para que as relações de pertencimento entre palavras, frases e comentários sejam representadas explicitamente. | TE01 | E02 |
| US04 | Como pesquisador, eu quero que a árvore permita navegação bidirecional entre os níveis para que a construção dos grafos derivados possa acessar o contexto hierárquico de cada elemento. | TE01 | E02 |
| US05 | Como pesquisador, eu quero que o sistema construa um grafo de palavras com arestas ponderadas por proximidade posicional para que pares de palavras frequentemente próximas recebam pesos mais altos. | TE02 | E03 |
| US06 | Como pesquisador, eu quero que o sistema construa um grafo de frases derivado das relações entre palavras para que a similaridade semântica entre frases seja propagada a partir do nível lexical. | TE02 | E03 |
| US07 | Como pesquisador, eu quero que o sistema construa um grafo de comentários derivado das relações entre frases para que comentários tematicamente similares sejam conectados com pesos proporcionais à sua semelhança. | TE02 | E03 |
| US08 | Como pesquisador, eu quero que os três grafos sejam integrados em um grafo final unificado com vértices identificados por prefixo de tipo para que palavras, frases e comentários coexistam na mesma estrutura sem conflito de chaves. | TE02 | E04 |
| US09 | Como pesquisador, eu quero que as arestas hierárquicas da árvore sejam incorporadas ao grafo final para que as relações de pertencimento estrutural complementem as relações semânticas nos algoritmos subsequentes. | TE02 | E04 |
| US10 | Como pesquisador, eu quero que o sistema aplique corte progressivo de arestas com restrição de grau mínimo para que nenhum vértice fique isolado durante o processo de fragmentação do grafo. | TE03 | E05 |
| US11 | Como pesquisador, eu quero que o sistema execute BFS ou DFS após cada remoção de aresta para que o número de componentes conexos seja monitorado e o critério de parada (K = 10) seja detectado com precisão. | TE03 | E05 |
| US12 | Como pesquisador, eu quero que o sistema calcule a centralidade de grau ponderada de cada vértice dentro de sua comunidade para que os termos mais representativos de cada tópico sejam identificados. | TE03 | E06 |
| US13 | Como pesquisador, eu quero que o sistema calcule a modularidade Q ao final do processo de corte para que a qualidade dos agrupamentos possa ser avaliada objetivamente. | TE03 | E06 |
| US14 | Como pesquisador, eu quero que o sistema gere um relatório de saída com os tópicos detectados, seus termos centrais, comentários associados e a modularidade Q para que os resultados sejam interpretáveis e documentáveis. | TE03 | E06 |

---

## 9.2 Priorização do Backlog

A priorização foi conduzida com base em uma análise de **dependência técnica** — que é o principal critério ordenador em sistemas de pipeline — combinada a uma avaliação de **Benefício (B)**, **Urgência (U)**, **Esforço (E)** e **Risco (R)** em escala de 1 a 5.

A fórmula aplicada foi: **(B × 2 + U) − (E + R)**

Histórias com maior dependência de outras foram posicionadas primeiro independentemente da pontuação, pois bloqueiam o avanço das ondas seguintes.

| US | Descrição resumida | B | U | E | R | Pontuação | Dependência | Onda |
|----|--------------------|---|---|---|---|-----------|-------------|------|
| US01 | Pré-processar comentários | 5 | 5 | 2 | 1 | 12 | Nenhuma | 1 |
| US02 | Remover stopwords e termos irrelevantes | 5 | 5 | 1 | 1 | 13 | US01 | 1 |
| US03 | Construir Árvore N-ária | 5 | 5 | 3 | 3 | 9 | US01, US02 | 1 |
| US04 | Navegação bidirecional na árvore | 4 | 4 | 2 | 2 | 8 | US03 | 1 |
| US05 | Grafo de palavras com peso posicional | 5 | 5 | 3 | 3 | 9 | US03, US04 | 2 |
| US06 | Grafo de frases | 5 | 5 | 3 | 2 | 10 | US05 | 2 |
| US07 | Grafo de comentários | 5 | 5 | 3 | 2 | 10 | US06 | 2 |
| US08 | Grafo final integrado (estrutura) | 5 | 5 | 4 | 3 | 8 | US05, US06, US07 | 2 |
| US09 | Arestas hierárquicas no grafo final | 4 | 4 | 2 | 2 | 8 | US03, US08 | 2 |
| US10 | Corte progressivo com restrição de grau | 5 | 5 | 4 | 4 | 8 | US08, US09 | 3 |
| US11 | BFS/DFS para contagem de componentes | 5 | 5 | 3 | 3 | 9 | US10 | 3 |
| US12 | Centralidade de grau ponderada | 4 | 4 | 2 | 2 | 8 | US10, US11 | 3 |
| US13 | Modularidade Q | 4 | 4 | 3 | 3 | 6 | US10, US11 | 3 |
| US14 | Relatório de saída com tópicos e métricas | 5 | 5 | 2 | 1 | 12 | US12, US13 | 4 |

---

## 9.3 MVP

O MVP do **GameReviewGraph** corresponde ao pipeline completo e funcional — da entrada de comentários brutos à saída dos tópicos detectados com métricas de qualidade. Dado que o projeto é um sistema de análise acadêmica com entrega única, **todas as histórias de usuário compõem o MVP**, pois cada uma representa uma etapa obrigatória do pipeline sem a qual as etapas subsequentes não podem ser executadas.

| US | Descrição resumida | Onda | MVP |
|----|---------------------|------|-----|
| US01 | Pré-processar comentários | 1 | ✅ |
| US02 | Remover stopwords e termos irrelevantes | 1 | ✅ |
| US03 | Construir Árvore N-ária | 1 | ✅ |
| US04 | Navegação bidirecional na árvore | 1 | ✅ |
| US05 | Grafo de palavras com peso posicional | 2 | ✅ |
| US06 | Grafo de frases | 2 | ✅ |
| US07 | Grafo de comentários | 2 | ✅ |
| US08 | Grafo final integrado | 2 | ✅ |
| US09 | Arestas hierárquicas no grafo final | 2 | ✅ |
| US10 | Corte progressivo com restrição de grau | 3 | ✅ |
| US11 | BFS/DFS para contagem de componentes | 3 | ✅ |
| US12 | Centralidade de grau ponderada | 3 | ✅ |
| US13 | Modularidade Q | 3 | ✅ |
| US14 | Relatório de saída com tópicos e métricas | 4 | ✅ |

---

## 9.4 Critérios de Aceitação do MVP

**US01 — Pré-processar comentários**

- O sistema converte todos os tokens para letras minúsculas
- Pontuação e caracteres especiais são removidos antes da tokenização
- Cada comentário é segmentado em frases antes de ser tokenizado em palavras
- A saída é uma estrutura de dados com comentários → frases → listas de tokens

**US02 — Remover stopwords e termos irrelevantes**

- Stopwords da língua portuguesa são removidas após a tokenização
- Termos com frequência abaixo do limiar definido pelo grupo são descartados
- Normalização (stemming ou lematização) é aplicada aos tokens restantes

**US03 — Construir Árvore N-ária**

- A árvore é implementada sem uso de bibliotecas externas
- Cada nó armazena referências para seus filhos e para seu pai
- A estrutura representa corretamente os quatro níveis: Dataset, Comentário, Frase, Palavra
- É possível recuperar todas as palavras de uma frase e todas as frases de um comentário em O(d), onde d ≤ 3

**US04 — Navegação bidirecional na árvore**

- A partir de um nó Palavra, é possível acessar sua Frase pai e seu Comentário avô
- A partir de um nó Comentário, é possível percorrer todas as suas Frases e Palavras descendentes

**US05 — Grafo de palavras com peso posicional**

- O grafo é representado como `dict[str, dict[str, float]]`
- Duas palavras são conectadas se e somente se coocorrem na mesma frase
- O peso acumulado é calculado pela fórmula `Σ 1 / (1 + |pos(wi) - pos(wj)|)` sobre todas as frases do dataset
- Palavras adjacentes (distância = 1) contribuem com 0,5 por ocorrência

**US06 — Grafo de frases**

- O grafo é representado como `dict[int, dict[int, float]]`
- Duas frases são conectadas se compartilham ao menos um par de palavras relacionadas no grafo de palavras
- O peso é calculado por `Σ PesoPalavra(wi, wj) / (|fa| × |fb|)` com `wi ∈ fa` e `wj ∈ fb`

**US07 — Grafo de comentários**

- O grafo é representado como `dict[int, dict[int, float]]`
- Dois comentários são conectados se possuem ao menos um par de frases relacionadas no grafo de frases
- O peso é calculado por `Σ PesoFrase(fi, fj) / (|ca| × |cb|)` com `fi ∈ ca` e `fj ∈ cb`

**US08 — Grafo final integrado**

- Vértices são identificados pelos prefixos `w_`, `s_` e `c_` sem conflito de chaves
- O grafo contém todos os vértices e arestas relacionais dos três grafos anteriores (após aplicação do limiar de corte)
- Palavras, frases e comentários coexistem na mesma estrutura de adjacência

**US09 — Arestas hierárquicas no grafo final**

- Arestas `Palavra → Frase` e `Frase → Comentário` são extraídas diretamente da Árvore N-ária
- Essas arestas não possuem peso numérico — representam apenas pertencimento estrutural
- Estão presentes no grafo final sem interferir nos pesos das arestas relacionais

**US10 — Corte progressivo com restrição de grau**

- As arestas do grafo final são ordenadas em ordem crescente de peso antes do início do corte
- Uma aresta (u, v) só é removida se `grau(u) > 1` E `grau(v) > 1`
- Arestas que violariam a restrição são puladas sem interromper o processo
- O algoritmo encerra quando K = 10 componentes são atingidos ou não restam arestas removíveis

**US11 — BFS/DFS para contagem de componentes**

- BFS ou DFS é executado a partir de um vértice arbitrário após cada remoção de aresta
- O algoritmo retorna o número exato de componentes conexos no grafo atual
- O critério de parada (K = 10) é verificado após cada execução

**US12 — Centralidade de grau ponderada**

- A centralidade de cada vértice é calculada como `Σ peso(v, u)` para todos os vizinhos `u` de `v`
- Os N termos com maior centralidade em cada comunidade são identificados como termos centrais do tópico

**US13 — Modularidade Q**

- Q é calculado pela fórmula `Q = (1/2m) × Σ [Aij − (ki × kj / 2m)] × δ(ci, cj)`
- O cálculo considera os pesos das arestas e os graus ponderados de cada vértice
- O valor de Q é exibido no relatório final como indicador objetivo da qualidade dos agrupamentos

**US14 — Relatório de saída**

- O relatório lista todas as comunidades detectadas com ID e rótulo de tópico
- Cada comunidade exibe seus termos centrais, os IDs dos comentários associados e o valor de Q
- A saída é produzida no terminal e/ou em arquivo de texto conforme definido pelo grupo

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 11/06/2026 | 1.0 | Criação do documento | Equipe GameReviewGraph |
