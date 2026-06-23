# Algoritmos

Todos os algoritmos descritos nesta página são implementados pelo grupo sem uso de bibliotecas externas de grafos. O código vive em `src/shared/graph/` (primitivas) e nos filtros de domínio (`community_detection.py`, `metrics.py`).

---

## 1. Centralidade de Grau Ponderada

Para cada vértice v, a centralidade de grau ponderada é a soma dos pesos de todas as suas arestas:

```
CentralidadePonderada(v) = Σ peso(v, u)    para todo u vizinho de v
```

**Variáveis:**

| Variável | Significado |
|----------|-------------|
| `v` | vértice cujo grau ponderado está sendo calculado |
| `u` | vértice vizinho de v (conectado por uma aresta) |
| `peso(v, u)` | peso da aresta entre v e u |
| `Σ` | somatório sobre todos os vizinhos u de v |

**Uso no sistema:** identifica os vértices mais influentes dentro de cada comunidade. Para nós do tipo `w_`, indica os termos mais representativos do tópico. Implementado em `src/shared/graph/metrics.py` como `total_edge_weight(graph, node)`.

---

## 2. Detecção de Comunidades — Corte Progressivo de Arestas

O algoritmo identifica K comunidades semânticas a partir do grafo final, removendo progressivamente as arestas de menor peso.

**Entrada:** grafo final integrado G = (V, A), número alvo de comunidades K = 10.

**Procedimento:**

```
1. Construir a MST (Árvore Geradora Mínima) de G via algoritmo de Prim
   (variante densa O(V²) — adequada pois G já é uma matriz de adjacência)
2. Ordenar as arestas da MST em ordem crescente de peso
3. Para cada aresta (u, v):
       se grau(u) > 1 E grau(v) > 1 → remover a aresta
       caso contrário → pular
4. Após cada remoção → executar BFS/DFS para contar componentes conexos
5. Parar quando componentes == K ou não restar arestas removíveis
```

**Por que reduzir à MST primeiro:** o grafo final é denso (V² arestas possíveis). Cortar diretamente sobre ele seria custoso e instável. A MST tem exatamente V−1 arestas e preserva a conectividade mínima — é o esqueleto sobre o qual o corte opera.

**Justificativa da restrição de grau:** a condição `grau > 1` garante que nenhum vértice fique isolado como singleton. Vértices isolados degradam a interpretabilidade dos tópicos.

**Condição de parada alternativa:** se K = 10 comunidades não for atingível sem violar a restrição de grau, o algoritmo encerra com o número de comunidades formadas até aquele ponto.

**Complexidade:** O(V²) para Prim + O(E log E) para ordenação da MST + O(V + E) por BFS/DFS após cada corte.

---

## 3. Modularidade Q

A qualidade das comunidades detectadas é avaliada pela métrica de modularidade Q, que mede o quanto a densidade interna de cada comunidade supera o esperado por acaso:

```
Q = (1 / 2m) × Σ [ Aij − (ki × kj / 2m) ] × δ(ci, cj)
```

**Variáveis:**

| Variável | Significado |
|----------|-------------|
| `m` | número total de arestas no grafo |
| `Aij` | peso da aresta entre i e j (0 se não houver aresta) |
| `ki, kj` | grau ponderado (soma dos pesos) dos vértices i e j |
| `ki × kj / 2m` | valor esperado da aresta (i, j) em grafo aleatório com os mesmos graus |
| `δ(ci, cj)` | 1 se i e j pertencem à mesma comunidade, 0 caso contrário |
| `Σ` | somatório sobre todos os pares de vértices do grafo |

**Interpretação:** Q varia entre −1 e 1. Valores próximos a 1 indicam comunidades com alta densidade interna e baixa densidade entre grupos — resultado desejável. Valores próximos a 0 indicam estrutura próxima à aleatória. Implementado em `src/metrics.py`.

---

## 4. Fórmulas de Peso das Arestas

### Grafo de Palavras — peso posicional

```
peso(wi, wj) = Σ  1 / (1 + |pos(wi) − pos(wj)|)
```

Somatório sobre todas as frases do corpus onde wi e wj co-ocorrem. Palavras adjacentes (distância = 1) contribuem com 0,5; palavras na mesma posição contribuem com 1,0.

### Grafo de Frases — média normalizada

```
peso(sa, sb) = Σ peso(wi, wj) / (|sa| × |sb|)    wi ∈ sa, wj ∈ sb
```

A divisão por |sa| × |sb| evita viés em frases longas.

### Grafo de Comentários — média normalizada

```
peso(ca, cb) = Σ peso(si, sj) / (|ca| × |cb|)    si ∈ ca, sj ∈ cb
```

Propaga as relações lexicais do nível das palavras até o nível dos documentos.

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 22/06/2026 | 1.0 | Criação da página com fórmulas de centralidade ponderada, corte progressivo de arestas (MST + BFS/DFS) e modularidade Q | [Vinícius Rufino](https://github.com/RufinoVfR) |
