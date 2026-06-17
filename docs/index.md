# GameReviewGraph

Sistema de detecção automática de tópicos em comentários de jogos via grafos hierárquicos e corte progressivo de arestas.

---

## Sobre o projeto

O **GameReviewGraph** transforma um corpus de ~200 reviews de jogos em português em uma estrutura de grafo hierárquica de três níveis — palavras → frases → comentários — e detecta comunidades semânticas (tópicos) por corte progressivo de arestas.

Implementado em Python puro, sem bibliotecas externas de grafos. Disciplina **FGA0030 — Estruturas de Dados 2 / UnB 2026/1**.

---

## Quick Start — por onde começar

Entrou no projeto e vai implementar um filtro? A trilha de leitura mínima, **nesta ordem**:

1. **`CLAUDE.md` (raiz)** — panorama, arquitetura e regras inegociáveis.
2. **[Guia de Implementação](guia_implementacao.md)** — documento-âncora: receita passo a passo por filtro, contratos e *definition of done*.
3. **`src/CLAUDE.md`** — template do filtro, `S3_KEYS`, I/O e cache.
4. **`src/shared/CLAUDE.md`** — contratos GoF (`AbstractFilter`, multi-input, `FilterChain`).

Mantenha abertos como referência: `src/shared/graph/CLAUDE.md` (ferramentas de grafo) e `tests/conftest.py` (fixtures). O passo a passo completo está no [Guia de Contribuição](contributing.md#0-quick-start-do-zero-ao-primeiro-filtro).

---

## Pipeline

| Etapa | Módulo | Descrição |
|-------|--------|-----------|
| 1 | `preprocessing/` | Tokenização, stopwords, normalização |
| 2 | `tree.py` | Árvore N-ária: Dataset → Comentário → Frase → Palavra |
| 3 | `word_graph.py` | Grafo de co-ocorrência posicional de palavras |
| 4 | `sentence_graph.py` | Grafo de frases derivado do grafo de palavras |
| 5 | `comment_graph.py` | Grafo de comentários derivado do grafo de frases |
| 6 | `final_graph.py` | Grafo unificado com os 3 níveis + arestas hierárquicas |
| 7 | `community_detection.py` | Corte progressivo de arestas + BFS/DFS |
| 8 | `metrics.py` | Centralidade de grau ponderada + Modularidade Q |
| 9 | `analysis.py` | Geração do relatório final |

---

## Tópicos detectados

`Desempenho` · `Narrativa` · `Multiplayer` · `Interface` · `Progressão` · `Áudio` · `Gráficos` · `Controles` · `Conteúdo Pós-lançamento` · `Suporte Técnico`

---

## Tecnologias

- **Python 3.11+**
- **NLTK** — pré-processamento
- **BFS / DFS** — implementados do zero
- **Modularidade Q** — implementada do zero
- **Árvore N-ária** — implementada do zero
