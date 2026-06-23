# Planejamento — US14: Relatório final (`analysis.py` + página no frontend)

> Branch: `feat/final-report` · Issue: [#11 (US14)](../../issues/11)
> Status: **desbloqueado (22/06/2026)** — US12 (#9, centralidade) e US13 (#10, Q)
> mergeadas na `main` e já puxadas para esta branch. Backend pronto para implementar.
> A parte de **frontend fica na branch de front** — não é escopo desta branch.
> Nota de trabalho (não publicada no MkDocs). Remover ao concluir a US14.

---

## Decisões estruturais (22/06/2026)

- **Onde rodam os 5 métodos:** dentro do **`analysis.py` (Filtro 9)** — ele roda as 5
  `CommunityDetectionStrategy`, calcula Q/centralidade/estatísticas por método e monta o
  `report.json`. Não haverá filtro de comparação separado.
- **Reuso das funções de score:** as funções puras hoje em `metrics.py`
  (`weighted_degree_centrality`, `calculate_modularity`, `_community_centrality`,
  `get_top_terms`, `_normalize_communities`) são **extraídas para `src/shared/scoring.py`**,
  para que `metrics.py` (Filtro 8) e `analysis.py` (Filtro 9) as importem sem que um filtro
  importe de outro (regra do projeto). Acrescenta-se `partition_stats()` (tamanhos, singletons).
- **`report.txt`:** projeção textual do `report.json`, gerada por um **filtro 10 dedicado**
  (`ReportTextFilter`, `output_format="text"`) — mantém o Template Method limpo (um artefato
  por filtro, sem I/O dentro de `process()`).

---

## Objetivo (escopo revisado)

O relatório final tem **duas partes**:

1. **Backend — `report.json`**: `analysis.py` (Filtro 9) gera um relatório **estruturado em JSON**
   (não apenas o `report.txt` textual da seção 14). Conteúdo por comunidade: tópico, termos
   centrais, comentários associados e modularidade Q — **para cada um dos 5 métodos** de detecção.
2. **Frontend — última página**: uma **nova página final** consome o `report.json` e o renderiza
   (comparação lado a lado dos 5 métodos, métricas e comunidades).

O `report.txt` legível (formato seção 14) pode continuar como saída secundária para a entrega
acadêmica, derivado do mesmo `report.json`.

```
=== Comunidade 1 — Tópico: Desempenho ===
Termos centrais: fps, travamento, lag, otimizacao, queda
Comentários associados: c_3, c_17, c_42
Modularidade Q: 0.74
```

---

## Comparação de 5 métodos de detecção de comunidades

**Motivação:** o método atual (MST mínima + corte progressivo ascendente) produz forte
desbalanceamento — uma comunidade absorve todas as palavras (blob de 703 nós) e surgem
comunidades de 1 comentário. Distribuição medida (200 comentários): `[80,47,21,20,16,8,3,3,1,1]`.
A causa raiz é estrutural (min-MST + escala minúscula do peso hierárquico — ver
`planning/questao_arestas_hierarquicas.md`). Em vez de esconder esse resultado, o relatório o
**preserva como baseline** e compara correções, contando uma narrativa **causa → correção**,
justificando objetivamente cada uma via Q e balanceamento.

**Lineup definido (5 métodos — cada um uma `CommunityDetectionStrategy`; restrição: tudo do zero, sem libs de grafo):**

| # | Método | Ideia | Papel |
|---|--------|-------|-------|
| 1 | Corte progressivo na min-MST, hierárquicas não-cortáveis *(atual, intocado)* | Baseline do enunciado | **O problema** — blob/`size=1` |
| 2 | Min-MST, **peso hierárquico recalibrado** (escala alta) | Inverte a escala p/ a palavra entrar pela `w_↔w_`, não pela contenção | Fix mínimo: peso *influencia*, não impõe |
| 3 | **Max-MST** + pesos normalizados por tipo + arestas cortáveis | Backbone = similaridades fortes; corta as fracas | Fix principista |
| 4 | Detecção no subgrafo de comentários (`c_↔c_`) | Particiona só comentários, ignora o blob de palavras | Contorna o blob de vez |
| 5 | Maximização gulosa da modularidade Q | Aglomerativo estilo Louvain, otimiza a própria métrica | Baseline da literatura |

**Métricas de comparação (por método):** nº de comunidades, distribuição de tamanhos
(min/max), nº de singletons, e **modularidade Q** (US13) como critério objetivo de qualidade.

> ✅ Decisão tomada (22/06/2026): lineup de **5 métodos** acima. Detalhe e justificativa em
> `planning/questao_arestas_hierarquicas.md` e `docs/decisions.md`.

---

## Dependências (todas resolvidas)

| Insumo | Origem | Estado |
|---|---|---|
| Comentários associados (`c_` por comunidade) | `communities.json` (Filtro 7) | ✅ pronto |
| Tópico dominante da comunidade | `comments.json` (gold) + partição | ✅ derivável (voto de maioria sobre os `c_`) |
| Termos centrais | centralidade ponderada (`weighted_degree_centrality` + `get_top_terms`) | ✅ US12 mergeada |
| Modularidade Q (por método) | `calculate_modularity` em `metrics.py` | ✅ US13 mergeada |
| 5 partições para comparar | 5 `CommunityDetectionStrategy` | ⚠️ 1 pronto; 2/3/5 rascunhos; 4 a realizar |

---

## Estado atual do código (para retomar)

- `main.py`: `FILTERS` vai até `MetricsFilter` (Filtro 8). Falta o Filtro 9 (`analysis`) e 10 (`report_text`).
- `src/metrics.py` **existe** (US12+US13): `weighted_degree_centrality`, `calculate_modularity`,
  `_community_centrality`, `get_top_terms`, `_normalize_communities` — funções puras a extrair p/ `shared/scoring.py`.
- `src/analysis.py` **não existe**.
- `src/shared/strategies.py`: método 1 (`ProgressiveEdgeCuttingStrategy`) pronto; métodos 2/3/5
  (`RecalibratedHierarchy`, `MaxSpanningTree`, `GreedyModularity`) são **rascunhos** com constantes
  provisórias (`_HIERARCHY_RECALIBRATION_FACTOR`, `_HIERARCHY_DAMPING_LAMBDA`); método 4 (subgrafo
  `c_↔c_`) **ainda não realizado**.
- `community_detection.py` (Filtro 7): **ainda usa BFS/`_cut_edges`/`_is_relational` duplicados
  localmente** — não injeta a Strategy de `shared/strategies.py`. Refatorar para eliminar divergência
  (e garantir que o "método 1" do relatório seja exatamente a baseline).
- `S3_KEYS` tem `"report": "report.txt"` e `"metrics": "metrics.json"` —
  **falta a chave `report_json`** (`report.json`).
- `src/types/metrics.py`: `Metrics = dict`. Falta um `Report` (schema do `report.json`).

---

## Plano de implementação — Backend (escopo desta branch)

### Fase 0 — Refactors habilitadores
1. **`src/shared/scoring.py`** (novo): mover de `metrics.py` as funções puras de score
   (`weighted_degree_centrality`, `calculate_modularity`, `_community_centrality`,
   `get_top_terms`, `_normalize_communities`) e adicionar
   `partition_stats(communities) -> {n_communities, size_min, size_max, singletons, n_comments}`.
   `metrics.py` passa a importar de `shared.scoring`. Atualizar `src/shared/CLAUDE.md` (documentar o
   módulo como "métricas de score de comunidade, implementadas do zero, reusadas por dois filtros")
   e o mapa de módulos em `src/CLAUDE.md`.
2. **Refatorar `community_detection.py`** para injetar `CommunityDetectionStrategy`
   (`__init__(self, strategy=ProgressiveEdgeCuttingStrategy())`) e delegar o corte à Strategy —
   remover `bfs`/`dfs`/`count_components`/`get_components`/`_is_relational`/`_cut_edges` duplicados.

### Fase 1 — Fechar os 5 métodos em `strategies.py`
3. **Método 4** — `CommentSubgraphStrategy`: helper que extrai o subgrafo `c_↔c_` do grafo final e
   roda o corte progressivo (ou greedy) só sobre comentários; devolve `Communities` sobre `c_`.
4. **Métodos 2/3/5** — validar e calibrar as constantes provisórias rodando a comparação com Q;
   fixar defaults. Garantir que cada `detect()` devolve partição válida (cada nó uma vez; respeita K
   ou para no pico de Q).
5. **Registro de métodos** — `DETECTION_METHODS` (lista de `{id, label, strategy}`) como fonte única
   do line-up, consumida pelo `analysis.py`.

### Fase 2 — Config + tipos
6. `S3_KEYS`: adicionar `"report_json": "report.json"` (mantém `"report": "report.txt"`).
7. `src/types/report.py` (novo): `Report` (TypeAlias dict) documentando o shape do `report.json`;
   re-exportar em `src/types/__init__.py`.

### Fase 3 — `analysis.py` (Filtro 9) e projeção texto (Filtro 10)
8. `AnalysisFilter(AbstractFilter)`: `name="analysis"`, `input_key="final_graph"`,
   `extra_input_keys=["communities", "raw"]`, `output_key="report_json"`. `process()`:
   - deserializa o grafo final; constrói o mapa `id → tópico-ouro` a partir de `raw`;
   - para cada método em `DETECTION_METHODS`: `partition = strategy.detect(graph, K)`;
   - por comunidade: centralidade intra (`_community_centrality`), termos centrais
     (`get_top_terms`, prefixo `w_`), comentários associados (`c_`), tópico dominante
     (maioria-ouro sobre os `c_`); por método: `calculate_modularity` (Q global) e `partition_stats`;
   - monta o `report.json`: `{ methods: [{ id, label, modularity_q, stats,
     communities: [{ id, topic, central_terms, comments }] }], comparison: [...] }`.
     **Sem `chosen_method`** — o resultado final é a **matriz comparativa dos 5 métodos**
     (Q, nº comunidades, balanceamento), sem eleger um vencedor.
9. `ReportTextFilter` (Filtro 10): `input_key="report_json"`, `output_key="report"`,
   `output_format="text"` — renderiza a projeção legível (formato da seção 14) a partir do
   `report.json`. Sem recomputar nada.
10. `main.py`: anexar `AnalysisFilter()` e `ReportTextFilter()` ao fim de `FILTERS`.

### Fase 4 — Testes
11. `tests/unit/test_scoring.py` (mover/expandir os de métrica), `test_strategies.py` (5 métodos sobre
    fixture pequena de partição conhecida), `test_analysis.py` (shape do `report.json` a partir de
    grafo+gold fixos), e ajustar `test_community_detection.py` ao refactor (comportamento inalterado).

### Fase 5 — Docs
12. Atualizar `docs/decisions.md` (decisões: comparação dentro do `analysis`, extração p/ `shared/scoring`,
    `report.txt` como filtro de projeção), `docs/arquitetura.md` (tabela de filtros: 9 e 10) e o
    mapa de módulos em `src/CLAUDE.md`.

---

## Frontend (FORA do escopo desta branch — vai na branch de front)
- Incluir `report.json` no bundle (`scripts/build_bundle.py` → `bundle/report.json`); estender
  `loader.ts` + `schemas.ts` (`ReportData`).
- Nova última página em `app.tsx` renderizando a comparação dos 5 métodos (tabela Q / nº comunidades /
  balanceamento + visual das comunidades), com fallback mock quando o `report.json` faltar; testes vitest.

---

## Decisões pendentes
1. ~~**Q por comunidade no `report.txt`**~~ — **resolvido (22/06/2026)**: exibir o **Q global do método**
   repetido em cada bloco de comunidade (não a contribuição por comunidade).
2. ~~**Algoritmo-base do método 4**~~ — **resolvido (22/06/2026)**: **corte progressivo** na MST do
   subgrafo `c_↔c_` (mesma mecânica do método 1, restrita a comentários).
3. ~~**`chosen_method`**~~ — **resolvido (22/06/2026)**: **não haverá método escolhido**. O `report.json`
   entrega a **matriz comparativa dos 5 métodos** (Q, nº comunidades, balanceamento); a interpretação
   fica para a análise textual/apresentação, sem o pipeline eleger um vencedor.

---

## Checklist de retomada
- [x] US12 (#9) e US13 (#10) mergeadas (centralidade + Q disponíveis)
- [x] Métodos de detecção escolhidos (5 — ver "Comparação de 5 métodos")
- [x] Fase 0: `shared/scoring.py` + refactor do Filtro 7 (Strategy injetável; testes verdes)
- [x] Fase 1: método 4 (`CommentSubgraphStrategy`) + `DETECTION_METHODS` (calibração 2/3 fica para depois)
- [x] Fase 2: `report_json` em `S3_KEYS` + `types/report.py`
- [x] Fase 3: `analysis.py` + `ReportTextFilter` + wire no `main.py` (pipeline roda e gera os artefatos)
- [x] Fase 4: testes (`test_scoring`, `test_strategies` 2–5, `test_analysis`, `test_report_text`) — 256 verdes
- [x] Fase 5: docs (`arquitetura.md`, `decisions.md`, `src/CLAUDE.md`, `shared/CLAUDE.md`, `types/CLAUDE.md`)
- [ ] Frontend (branch de front)
- [ ] Remover este arquivo de planejamento
