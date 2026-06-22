# [US07] Construir grafo de comentários

**Descrição:**
Implementar o módulo `src/comment_graph.py` — **Filtro 5** (`CommentGraphFilter`) — que constrói o grafo de comentários derivado do grafo de frases. Análogo ao grafo de frases, um nível acima: dois comentários (`c_<id>`) são ligados se têm pares de frases relacionadas, com peso `Σ weight(si, sj) / (|ca| × |cb|)`, `si ∈ ca`, `sj ∈ cb`.

`CommentGraphFilter` herda `AbstractFilter`. Atributos: `name="comment_graph"`, `input_key="sentence_graph"`, `extra_input_keys=["preprocessed"]`, `output_key="comment_graph"`. Multi-input: `process()` recebe `{"primary": ..., "preprocessed": ...}`.

---

### 🎓 Newbie Guide

**Analogia com o grafo de frases:** mesma estrutura, trocando palavras-em-frases por frases-em-comentários. Se entendeu o Filtro 4, este é direto.

**De onde vem o pertencimento comentário → frases?** Do `preprocessed.json` (`list[{"id","sentences"}]`): percorrendo-o **na mesma ordem** em que o `tree` numerou as frases, recupera-se `id do comentário → [índices globais de frase]` e `|ca|` = nº de frases. **Representação:** dataclass `Graph` (não `dict[int, dict]`); fórmula e normalização **vivem neste filtro**.

---

### Contrato de I/O

- **Entrada primária** `input_key="sentence_graph"` → `sentence_graph.json`; **extra** `["preprocessed"]` → `preprocessed.json`.
  `process()` recebe `{"primary": sentence_graph_serializado, "preprocessed": [{"id","sentences"}, ...]}`.
- **Saída** `output_key="comment_graph"` → `comment_graph.json` = `serialize_graph(graph)`.

---

### Passos

1. Desserializar o grafo de frases e reconstruir o pertencimento por comentário:
   ```python
   from src.shared.graph import deserialize_graph, get_edge_weight, build_graph_from_deltas, serialize_graph, assert_valid

   def process(self, data):
       sentence_graph = deserialize_graph(data["primary"])
       preprocessed = data["preprocessed"]
       # mesmo walk sequencial do tree → comment id -> [s_index], na ordem
       ...
   ```
2. Para cada par de comentários `(ca, cb)`, acumular `Σ get_edge_weight(sentence_graph, f"s_{i}", f"s_{j}")` sobre `si ∈ ca`, `sj ∈ cb`, e **normalizar** por `|ca| × |cb|`.
3. Criar a aresta `(f"c_{id_a}", f"c_{id_b}")` só quando o peso normalizado for `> 0`.
4. Acumular via `build_graph_from_deltas`; normalizar com `iter_edges` + `add_edge`.
5. `assert_valid`; registrar `CommentGraphFilter()` em `src/main.py`.
6. Substituir o placeholder em `tests/unit/test_comment_graph.py`.

---

### Links úteis

- [Planejamento — seção 11: Grafo de Comentários](GameReviewGraph_Planejamento.pdf)
- [`CLAUDE.md` — fórmulas de peso](CLAUDE.md)
- [`src/shared/CLAUDE.md` — filtros multi-input](src/shared/CLAUDE.md)

---

### Tarefas

- [ ] `CommentGraphFilter(AbstractFilter)` com `input_key="sentence_graph"` + `extra_input_keys=["preprocessed"]`
- [ ] Pertencimento comentário → frases reconstruído na ordem do `preprocessed`
- [ ] Peso `Σ weight(si, sj) / (|ca| × |cb|)`, normalização **dentro do filtro**
- [ ] Arestas com peso 0 não entram; grafo dataclass `Graph`
- [ ] Saída via `serialize_graph`; `assert_valid` passa
- [ ] `CommentGraphFilter` registrado em `src/main.py`
- [ ] Testes: peso normalizado à mão entre dois comentários; prefixos `c_`

---

### ✅ Definition of Done

- [ ] Grafo representado pelo dataclass `Graph`, vértices prefixados `c_`
- [ ] Dois comentários ligados sse têm ao menos um par de frases relacionado
- [ ] Peso por `Σ weight(si, sj) / (|ca| × |cb|)`, simétrico
- [ ] `make comment-graph` roda sem exceções e grava `comment_graph.json` no MinIO
- [ ] Todas as funções com docstring; código e commit em inglês
