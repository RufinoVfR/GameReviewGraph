# Questão de projeto — arestas hierárquicas na detecção de comunidades

> Branch: `feat/final-report` · Relacionado: Filtro 7 (`community_detection.py`),
> [`docs/decisions.md`](../docs/decisions.md) (decisão "Arestas hierárquicas excluídas do corte progressivo")
> e [`planning/us14_final_report.md`](./us14_final_report.md).
>
> **Status: RESOLVIDA (22/06/2026).** O documento descreve o problema; a resolução está na
> seção [Resolução](#resolucao) ao final. A decisão correspondente foi registrada em
> [`docs/decisions.md`](../docs/decisions.md).

---

## Contexto

O grafo final (Filtro 6) une três níveis num só grafo, com dois tipos de aresta:

- **Relacionais** — ligam nós do mesmo nível (`w_↔w_`, `s_↔s_`, `c_↔c_`) e representam
  **similaridade semântica** (coocorrência / relação calculada pelas fórmulas de peso).
- **Hierárquicas** — ligam níveis diferentes (`w_→s_`, `s_→c_`) e representam
  **contenção estrutural** (uma palavra *pertence a* uma frase; uma frase *pertence a* um comentário).

A detecção de comunidades atual (método 1: MST de Prim + corte progressivo) **exclui as arestas
hierárquicas do corte** — só arestas relacionais são candidatas a serem cortadas (predicado
`_is_relational`). A justificativa registrada foi preservar o "esqueleto" de contenção entre níveis,
garantindo que cada comunidade pudesse conter nós dos três níveis relacionados tematicamente.

---

## O problema observado

Ao excluir as arestas hierárquicas do corte, **a pertinência de uma palavra (ou frase) a uma
comunidade passa a ser determinada pela contenção, não pela similaridade.** Na MST, uma palavra
entra na árvore quase só por uma aresta hierárquica (a que a liga a uma frase); como essa aresta
nunca é cortada, a palavra fica presa, de forma rígida, à comunidade da frase à qual está contida —
independentemente de sua relação semântica com o resto do grafo.

A consequência, medida no dataset canônico de 200 comentários:

- Uma única comunidade absorve **todas as 344 palavras e 279 frases** (blob de ~700 nós);
  as outras 9 comunidades recebem **0 ou 1 palavra** cada.
- Distribuição de comentários por comunidade: `[80, 47, 21, 20, 16, 8, 3, 3, 1, 1]`.
- Composição (comentários, frases, palavras) por comunidade:
  `(80,279,344)`, `(47,8,0)`, `(21,3,0)`, `(20,4,1)`, `(16,4,0)`, `(8,1,1)`, `(3,2,0)`,
  `(3,1,1)`, `(1,1,0)`, `(1,1,1)`.

Ou seja: as arestas hierárquicas estão sendo **determinantes** para a entrada de palavras/frases
na comunidade — exatamente o oposto do que se espera de um agrupamento por similaridade.

---

## A posição em discussão

> **As arestas hierárquicas não devem ser determinantes para a entrada de um nó na comunidade.
> Elas devem ter um peso definido que apenas *influencia* a decisão, não que a *impõe*.**

Em outras palavras: a contenção é um sinal legítimo (uma palavra que pertence a uma frase tende
a compartilhar o tópico dela), mas deveria ser **um fator ponderado** entre outros — e não um
vínculo inquebrável que fixa a comunidade do nó antes de qualquer consideração semântica.

---

## Evidências adicionais (simulações nesta sessão)

Tentativas de impor um mínimo de nós por tipo em cada comunidade esbarram justamente na rigidez
das arestas hierárquicas:

- Guard exigindo **≥2 palavras, ≥2 frases e ≥2 comentários** por lado de cada corte →
  só **3 comunidades** possíveis (as palavras não se separam de jeito nenhum).
- Guard exigindo **≥2 comentários e ≥2 frases** (sem restrição de palavras) → 10 comunidades
  viáveis, mas o blob de palavras permanece numa única comunidade.

A impossibilidade de distribuir as palavras é um **sintoma direto** de as arestas hierárquicas
serem tratadas como esqueleto inviolável.

---

## Perguntas em aberto (a decidir depois)

1. As arestas hierárquicas deveriam ser **cortáveis** (entrar no corte progressivo como qualquer
   outra), em vez de excluídas?
2. Se devem apenas **pesar** na decisão, **qual peso** elas carregam em relação às arestas
   relacionais? Como esse peso é calibrado?
3. Se uma palavra/frase puder mudar de comunidade por similaridade, é aceitável que uma comunidade
   **não contenha** a frase/comentário que estruturalmente a contém? Qual o impacto na
   interpretabilidade do resultado (cada comunidade representando um tópico)?
4. Esta questão afeta apenas o método 1 (corte na MST do grafo unificado), ou redefine o próprio
   modelo do grafo final usado por todos os métodos? Como dialoga com o método 2 (subgrafo de
   comentários, que ignora palavras) e o método 3 (maximização gulosa de Q)?
5. A decisão registrada em `docs/decisions.md` ("Arestas hierárquicas excluídas do corte
   progressivo") precisaria ser revista/revertida?

---

## Causa raiz (diagnóstico complementar)

A análise inicial atribuía o blob apenas à exclusão das arestas hierárquicas do corte. Há, porém,
uma **segunda metade da causa**, na interação entre o tipo do MST e a escala do peso hierárquico:

- O grafo é de **similaridade** (peso alto = relação forte), mas a árvore construída em
  `community_detection.py` é a de peso **mínimo** (`minimum_spanning_tree`, Prim com
  `weight < min_weight[v]`). Prim de mínimo seleciona sempre as arestas **mais fracas**.
- As arestas hierárquicas têm peso `1/|filhos|` (ex.: `1/10` para uma palavra numa frase de 10
  tokens) — a **menor escala de peso do grafo inteiro**.

Encadeando: como o MST é de mínimo, ele **prefere** as arestas hierárquicas (são as mais baratas);
toda palavra entra na árvore por sua aresta de contenção, quase nunca por uma `w_↔w_`; e como essas
arestas são não-cortáveis, a palavra fica colada. Ou seja, é a **escala** do peso hierárquico — não
só sua não-cortabilidade — que está impondo a comunidade do nó. Isso é exatamente o que a posição em
discussão antecipa: o peso hierárquico deveria *influenciar*, não *impor*.

<a id="resolucao"></a>
## Resolução

**Não** se altera o método 1 in loco. O resultado desbalanceado do método 1 é **evidência** de que a
contenção estrutural não pode determinar pertinência — e por isso ele é **preservado como baseline**.
As correções entram como **métodos adicionais** no comparativo do relatório final (US14), cada um uma
`CommunityDetectionStrategy` plugável, medidos por modularidade Q e balanceamento. O relatório passa a
contar uma narrativa **causa → correção**, em vez de escolher silenciosamente um algoritmo.

Lineup decidido (5 métodos — ver `planning/us14_final_report.md` e `docs/decisions.md`):

| # | Método | Papel na narrativa |
|---|--------|--------------------|
| 1 | Min-MST, hierárquicas não-cortáveis *(atual, intocado)* | **O problema** — blob de ~700 nós, comunidades `size=1`. |
| 2 | Min-MST, **peso hierárquico recalibrado** (escala alta) | Fix mínimo: o peso *influencia*; a palavra entra pela `w_↔w_`, não pela contenção. |
| 3 | **Max-MST** + pesos normalizados por tipo + arestas cortáveis | Fix principista: backbone = similaridades fortes; corta as fracas. |
| 4 | Subgrafo de comentários (`c_↔c_`) | Contorna o blob de palavras de vez. |
| 5 | Maximização gulosa de Q | Baseline padrão da literatura. |

Respostas às perguntas em aberto:

1. **Hierárquicas cortáveis?** No método 1, **não** (preservado). No método 3, **sim** (todas cortáveis).
2. **Qual peso?** O método 2 mantém não-cortável mas inverte a escala (peso alto), de modo que o
   min-MST deixe de preferir a contenção; o método 3 normaliza por tipo e aplica um fator `λ`
   tunável. A calibração concreta é definida na implementação de cada estratégia.
3. **Comunidade sem a frase/comentário que contém a palavra?** Tornou-se aceitável **apenas nos
   métodos 3–5**; o método 1 (baseline) preserva a interpretabilidade da contenção. A comparação
   por Q/balanceamento expõe esse tradeoff explicitamente, em vez de escondê-lo.
4. **Escopo:** afeta a **modelagem do peso** consumida pelas estratégias, mas o `final_graph`
   (Filtro 6) permanece a fonte única; cada estratégia aplica sua própria transformação de peso
   (recalibração, normalização, `λ`) sobre a cópia que recebe — sem reescrever o Filtro 6.
5. **Decisão registrada:** a decisão "Arestas hierárquicas excluídas do corte progressivo" **não é
   revertida** — ela passa a descrever especificamente o **método 1 (baseline)**. Os métodos 2–3 são
   registrados como entrada **nova** em `docs/decisions.md`, sem reescrever a história.

---

## Não-objetivo deste documento

Registrar **a questão e sua resolução de design** (qual lineup de métodos, qual papel de cada um), não
a implementação. A calibração concreta dos pesos (`λ`, normalização por tipo) e o código das novas
estratégias são definidos na implementação da US14.
