# Requisitos de Software

Esta seção apresenta os requisitos funcionais e não funcionais que fundamentam o desenvolvimento do **GameReviewGraph**, derivados diretamente dos objetivos específicos do projeto.

---

## 1. Requisitos Funcionais

Os requisitos funcionais descrevem as funcionalidades que o sistema deve implementar para transformar comentários textuais em comunidades semânticas interpretáveis como tópicos.

### Objetivo Específico 1 — Processamento e Representação dos Dados

**RF01 — Pré-processar comentários:** O sistema deve receber uma coleção de comentários em texto e aplicar as etapas de conversão para minúsculas, remoção de pontuação, segmentação em frases, tokenização, remoção de stopwords e normalização (stemming ou lematização), produzindo tokens limpos como saída.

**RF02 — Construir Árvore N-ária de Representação Textual:** O sistema deve organizar os dados textuais pré-processados em uma árvore N-ária com quatro níveis hierárquicos — Dataset, Comentário, Frase e Palavra —, implementada pelo grupo sem uso de bibliotecas externas, com suporte a navegação bidirecional entre os níveis.

### Objetivo Específico 2 — Construção dos Grafos

**RF03 — Construir grafo de palavras:** O sistema deve construir um grafo onde cada vértice representa uma palavra relevante e as arestas conectam palavras que coocorrem na mesma frase, com peso calculado pelo somatório de `1 / (1 + distância posicional)` sobre todas as ocorrências do par no dataset.

**RF04 — Construir grafo de frases:** O sistema deve construir um grafo onde cada vértice representa uma frase e as arestas conectam frases que compartilham ao menos um par de palavras relacionadas no grafo de palavras, com peso dado pela média ponderada das relações entre palavras normalizada pelo produto dos tamanhos das frases.

**RF05 — Construir grafo de comentários:** O sistema deve construir um grafo onde cada vértice representa um comentário e as arestas conectam comentários que possuem ao menos um par de frases relacionadas no grafo de frases, com peso calculado de forma análoga ao grafo de frases.

**RF06 — Integrar os grafos em um grafo final unificado:** O sistema deve unificar os três grafos em uma única estrutura de adjacência, identificando vértices pelo prefixo de tipo (`w_`, `s_`, `c_`), incorporando arestas relacionais com pesos e arestas hierárquicas sem peso provenientes da Árvore N-ária.

### Objetivo Específico 3 — Detecção de Comunidades e Análise

**RF07 — Detectar comunidades por corte progressivo de arestas:** O sistema deve implementar um algoritmo que ordena todas as arestas do grafo final em ordem crescente de peso e as remove iterativamente — respeitando a restrição de grau mínimo maior que 1 para ambos os vértices —, executando BFS ou DFS após cada remoção para contar os componentes conexos, até atingir K = 10 comunidades ou esgotar as arestas removíveis.

**RF08 — Calcular centralidade de grau ponderada:** O sistema deve calcular, para cada vértice, a soma dos pesos de todas as suas arestas, identificando os termos mais representativos dentro de cada comunidade detectada.

**RF09 — Calcular modularidade Q:** O sistema deve calcular a métrica de modularidade Q ao final do processo de corte, avaliando objetivamente a qualidade dos agrupamentos obtidos com base na fórmula `Q = (1/2m) × Σ [Aij − (ki × kj / 2m)] × δ(ci, cj)`.

**RF10 — Gerar relatório de análise:** O sistema deve produzir uma saída estruturada listando cada comunidade detectada com seus termos centrais, comentários associados e o valor de modularidade Q, no formato definido no planejamento do projeto.

---

## 2. Requisitos Não Funcionais

Os requisitos não funcionais definem restrições técnicas e de qualidade que o sistema deve satisfazer, derivadas das exigências da disciplina e das decisões arquiteturais do grupo.

### Implementação

**RNF01 — Proibição de bibliotecas externas para grafos e algoritmos principais:** Nenhuma biblioteca externa de grafos (NetworkX, igraph, graph-tool ou equivalentes) pode ser utilizada. Os algoritmos de BFS, DFS, corte de arestas, centralidade de grau e modularidade devem ser implementados integralmente pelo grupo. O descumprimento desta restrição implica penalização de -5,0 pontos na avaliação.

**RNF02 — Linguagem de implementação:** O sistema deve ser implementado inteiramente em Python 3.11 ou superior.

**RNF03 — Bibliotecas de PLN permitidas:** Bibliotecas externas como NLTK e spaCy são permitidas exclusivamente para as etapas de pré-processamento linguístico (tokenização, remoção de stopwords, normalização).

### Organização do Código

**RNF04 — Modularização:** Cada nível do pipeline deve ser implementado em um módulo Python independente (`preprocessing.py`, `tree.py`, `word_graph.py`, `sentence_graph.py`, `comment_graph.py`, `final_graph.py`, `community_detection.py`, `metrics.py`, `analysis.py`, `main.py`), sem mistura de responsabilidades entre arquivos.

**RNF05 — Documentação inline:** Toda função deve conter docstring descrevendo seu propósito, parâmetros e retorno, como critério de legibilidade avaliado na disciplina.

### Disponibilidade

**RNF06 — Hospedagem no GitHub:** O código-fonte completo deve estar hospedado em repositório público no GitHub de ao menos um integrante do grupo, com a última atualização realizada até **22/06/2026**. A ausência do repositório implica nota zero; atrasos implicam -2,0 pontos por dia.

**RNF07 — Execução sem falhas:** O sistema deve executar completamente sem erros a partir do comando `python main.py`, produzindo todas as saídas previstas. Código que não executa ou apresenta falhas graves implica nota zero.

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 11/06/2026 | 1.0 | Criação inicial do documento | [Vinícius Rufino](https://github.com/RufinoVfR) |
