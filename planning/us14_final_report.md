# Planejamento — US14: Relatório final (`analysis.py` + página no frontend)

> Branch: `feat/final-report` · Issue: [#11 (US14)](../../issues/11)
> Status: **planejado, sem implementação** — parcialmente bloqueado pela US12.
> Nota de trabalho (não publicada no MkDocs). Remover ao concluir a US14.

---

## Objetivo (escopo revisado)

O relatório final tem **duas partes**:

1. **Backend — `report.json`**: `analysis.py` (Filtro 9) gera um relatório **estruturado em JSON**
   (não apenas o `report.txt` textual da seção 14). Conteúdo por comunidade: tópico, termos
   centrais, comentários associados e modularidade Q — **para cada um dos 3 métodos** de detecção.
2. **Frontend — última página**: uma **nova página final** consome o `report.json` e o renderiza
   (comparação lado a lado dos 3 métodos, métricas e comunidades).

O `report.txt` legível (formato seção 14) pode continuar como saída secundária para a entrega
acadêmica, derivado do mesmo `report.json`.

```
=== Comunidade 1 — Tópico: Desempenho ===
Termos centrais: fps, travamento, lag, otimizacao, queda
Comentários associados: c_3, c_17, c_42
Modularidade Q: 0.74
```

---

## Comparação de 3 métodos de detecção de comunidades

**Motivação:** o método atual (MST mínima + corte progressivo ascendente) produz forte
desbalanceamento — uma comunidade absorve todas as palavras (blob de 703 nós) e surgem
comunidades de 1 comentário. Distribuição medida (200 comentários): `[80,47,21,20,16,8,3,3,1,1]`.
O relatório final vai **comparar 3 abordagens** e justificar a escolhida via Q e balanceamento.

**Candidatos (a confirmar com o grupo — restrição: tudo do zero, sem libs de grafo):**

| # | Método | Ideia | Notas |
|---|--------|-------|-------|
| 1 | Corte progressivo na MST (atual) | Baseline do enunciado | Tem o problema do blob/`size=1` |
| 2 | Detecção no subgrafo de comentários (`c↔c`) | Particiona só comentários, ignora o blob de palavras | Resolve o blob; muda o escopo do Filtro 7 |
| 3 | *A definir* | ex.: maximização gulosa de modularidade, label propagation, ou Girvan–Newman (remoção por betweenness) | Implementação from-scratch — escolher o de melhor custo/benefício |

**Métricas de comparação (por método):** nº de comunidades, distribuição de tamanhos
(min/max), nº de singletons, e **modularidade Q** (US13) como critério objetivo de qualidade.

> ⚠️ Decisão em aberto: **quais 3 métodos**. Definir antes de implementar (ver "Decisões pendentes").

---

## Dependências e bloqueio

| Insumo | Origem | Estado |
|---|---|---|
| Comentários associados (`c_` por comunidade) | `communities.json` (Filtro 7) | ✅ pronto |
| Tópico dominante da comunidade | `comments.json` (gold) + `communities.json` | ✅ derivável |
| Termos centrais | centralidade ponderada — **US12** (#9) | ⛔ em desenvolvimento (outra pessoa) |
| Modularidade Q (por método) | **US13** (#10), depende da US12 | ⛔ bloqueada por US12 |
| 3 partições para comparar | 3 métodos de detecção | ⚠️ 2 já viáveis; 3º a definir |

**Decisão tomada:** não definir o schema do `metrics.json` por conta própria — aguardar a US12
fixar o formato. `analysis.py` consome esse contrato.

---

## Estado atual do código (para retomar)

- `main.py`: `FILTERS` vai só até `CommunityDetectionFilter` (Filtro 7). Faltam Filtros 8 e 9.
- `src/metrics.py` e `src/analysis.py` **não existem**.
- `src/types/metrics.py`: `Metrics = dict` (schema a ser definido pela US12).
- `S3_KEYS` tem `"report": "report.txt"` e `"metrics": "metrics.json"` —
  **falta uma chave `report_json`** (`report.json`) para a saída estruturada.
- Frontend: bundle lido por `frontend/src/data/loader.ts`; páginas/níveis em `app.tsx`.
  **Não há** rota/página de relatório nem `report.json` no bundle.

---

## Plano de implementação (quando US12/US13 entregarem)

### Parte 1 — Backend (`analysis.py`, Filtro 9)
1. Ler o contrato do `metrics.json` (US12/US13) e anotar os campos.
2. Decidir onde rodam os 3 métodos: provavelmente o Filtro 7 (community_detection) passa a
   emitir as **3 partições** (ou um filtro de comparação dedicado), e o Filtro 8 (metrics)
   calcula Q de cada uma.
3. `AnalysisFilter(AbstractFilter)`: `input_key="communities"`,
   `extra_input_keys=["metrics","raw"]`, gera **`report.json`** (estruturado) e, opcionalmente,
   `report.txt`. Adicionar a chave `report_json` em `S3_KEYS`.
4. `generate_report(...) -> dict` monta o JSON: por método → comunidades (id, tópico,
   termos centrais, comentários, Q) + métricas agregadas de comparação.
5. Escrita via `AbstractFilter` (`output_format`), nunca dentro de `process()`.
6. Wire no `main.py`: `MetricsFilter()` + `AnalysisFilter()` ao fim de `FILTERS`.
7. Testes (`tests/unit/test_analysis.py`) com fixtures pequenas de resultado conhecido.

### Parte 2 — Frontend (nova última página)
8. Incluir `report.json` no bundle: `scripts/build_bundle.py` lê o artefato do MinIO e grava
   `bundle/report.json`; estender `loader.ts` + `schemas.ts` (`ReportData`).
9. Nova página/rota em `app.tsx` (ou componente dedicado) renderizando a comparação dos
   3 métodos: tabela de métricas (Q, nº comunidades, balanceamento) + visual das comunidades.
10. Fallback mock quando `report.json` ausente (consistente com o padrão atual do loader).
11. Testes (vitest) do parsing/render do relatório.

---

## Decisões pendentes

1. **Quais 3 métodos** de detecção comparar (o 3º precisa ser escolhido).
2. **Formato do `report.json`** — definir após o contrato do `metrics.json` da US12.
3. **Onde calcular as 3 partições** — estender o Filtro 7 vs. filtro de comparação novo.
4. **Página do frontend** — rota dedicada vs. nível extra na navegação atual; layout da comparação.

---

## Checklist de retomada

- [ ] US12 (#9) mergeada e `metrics.json` produzido
- [ ] Schema do `Metrics` definido em `src/types/metrics.py`
- [ ] US13 (#10) mergeada (Q disponível)
- [ ] 3º método de detecção escolhido
- [ ] Backend: passos 1–7
- [ ] Frontend: passos 8–11
- [ ] Remover este arquivo de planejamento
