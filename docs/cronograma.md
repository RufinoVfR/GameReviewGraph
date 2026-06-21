# Cronograma e Entregas

Esta seção define as principais etapas e prazos do projeto, garantindo a entrega pontual e dentro do escopo estabelecido. O desenvolvimento é organizado em **4 ondas de trabalho** sequenciais, determinadas pela dependência técnica entre os módulos do pipeline.

---

## Visão Geral

| Onda | Período | Foco Principal |
|------|---------|----------------|
| Onda 1 | 11/06 – 13/06/2026 | Infraestrutura, dados e estrutura hierárquica |
| Onda 2 | 14/06 – 17/06/2026 | Construção e integração dos grafos |
| Onda 3 | 18/06 – 20/06/2026 | Algoritmos de detecção e métricas |
| Onda 4 | 21/06 – 22/06/2026 | Análise, relatório e entrega final |

---

## Detalhamento das Ondas

| Onda | Início | Fim | Objetivos | Histórias | Entregas Esperadas |
|------|--------|-----|-----------|-----------|-------------------|
| **1** | 11/06/2026 | 13/06/2026 | Gerar o dataset fictício via LLM; implementar o pipeline de pré-processamento; construir a Árvore N-ária com navegação bidirecional; configurar repositório GitHub e GitPages. | US01, US02, US03, US04 | Dataset de ~200 comentários gerado e validado; `preprocessing/` funcional com saída estruturada; `tree/` implementado e testado; repositório e documentação iniciais publicados. |
| **2** | 14/06/2026 | 17/06/2026 | Construir o grafo de palavras com peso posicional; construir o grafo de frases e o de comentários; integrar os três grafos e as arestas hierárquicas da árvore no grafo final unificado. | US05, US06, US07, US08, US09 | `word_graph.py`, `sentence_graph.py`, `comment_graph.py` e `final_graph.py` implementados, testados individualmente e integrados; estrutura de adjacência do grafo final validada com o dataset. |
| **3** | 18/06/2026 | 20/06/2026 | Implementar o corte progressivo de arestas com restrição de grau mínimo; implementar BFS e DFS para detecção de componentes; calcular centralidade de grau ponderada e modularidade Q. | US10, US11, US12, US13 | `community_detection.py` e `metrics.py` implementados e executados sobre o grafo final; K = 10 comunidades detectadas (ou resultado documentado se não atingível); modularidade Q calculada. |
| **4** | 21/06/2026 | 22/06/2026 | Finalizar `analysis.py` e `main.py`; gerar o relatório completo de saída; elaborar os slides da apresentação final; realizar a última atualização obrigatória no GitHub. | US14 | `main.py` executável de ponta a ponta sem erros; relatório de análise com tópicos, termos centrais e métricas; slides da apresentação final elaborados; **última atualização no GitHub até 22/06/2026 às 23h59**. |

---

## Marcos Críticos

| Data | Marco | Risco se não cumprido |
|------|-------|-----------------------|
| 13/06/2026 | Dataset gerado e pré-processamento validado | Onda 2 não pode iniciar — bloqueia todo o pipeline |
| 17/06/2026 | Todos os grafos construídos e integrados | Onda 3 não pode iniciar — algoritmos sem entrada |
| 20/06/2026 | Algoritmos de detecção e métricas finalizados | Onda 4 sem insumo para análise e relatório |
| **22/06/2026** | **Última atualização obrigatória no GitHub** | **-2,0 pontos por dia de atraso** |
| 08/07/2026 | Apresentação final | Ausência implica nota zero |

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 11/06/2026 | 1.0 | Criação inicial do documento | [Vinícius Rufino](https://github.com/RufinoVfR) |
