# Guia de Contribuição

Este documento define o processo de trabalho colaborativo no **GameReviewGraph**: fluxo Git, padrões de código, como executar o pipeline e os critérios de conclusão de cada módulo.

---

## 1. Fluxo Git

**Regra absoluta: nunca commitar diretamente na branch `main`.**

```text
main        ← branch protegida; só recebe merges via PR aprovado
  └── feat/preprocessing     ← uma branch por módulo ou história de usuário
  └── feat/word-graph
  └── fix/sentence-weight
  └── docs/arquitetura
```

### Passo a passo

```bash
# 1. Atualize main antes de criar sua branch
git checkout main && git pull origin main

# 2. Crie uma branch descritiva
git checkout -b feat/nome-do-modulo

# 3. Commite com mensagem em inglês, imperativa
git commit -m "Add word graph co-occurrence weight formula"

# 4. Abra PR para main; solicite revisão de ao menos 1 membro
gh pr create --title "Add word_graph.py filter" --base main
```

**Formato de mensagem de commit:**

```text
<tipo>: <descrição curta em inglês> (máx. 72 chars)

Tipos: feat | fix | docs | refactor | test | chore
```

---

## 2. Configurando o ambiente

```bash
# Instala todas as dependências (produção + dev) via uv
make install
```

Isso executa `uv sync --all-groups` e cria o virtualenv gerenciado pelo uv em `.venv/`. Não é necessário ativar o ambiente manualmente — todos os comandos abaixo passam por `uv run`.

---

## 3. Executando o Pipeline Completo

```bash
make run
```

O `main.py` executa os 9 filtros em sequência, lendo e gravando os arquivos em `data/`. A saída final aparece no terminal e em `data/report.txt`.

---

## 4. Executando um Filtro em Isolamento

Cada módulo pode ser executado individualmente via `make`. O filtro lê seus arquivos de entrada de `data/` e grava a saída sem rodar o pipeline inteiro.

```bash
make preprocessing        # Filtro 1 — pré-processamento
make tree                 # Filtro 2 — árvore N-ária
make word-graph           # Filtro 3 — grafo de palavras
make sentence-graph       # Filtro 4 — grafo de frases
make comment-graph        # Filtro 5 — grafo de comentários
make final-graph          # Filtro 6 — grafo unificado
make community-detection  # Filtro 7 — detecção de comunidades
make metrics              # Filtro 8 — centralidade e modularidade
make analysis             # Filtro 9 — relatório
```

**Pré-condição:** os arquivos de entrada do filtro devem existir em `data/` (gerados pelos filtros anteriores ou fornecidos manualmente).

**Template obrigatório para cada módulo:**

```python
if __name__ == "__main__":
    from pathlib import Path
    import json

    input_path = Path("data/<entrada>.json")
    output_path = Path("data/<saida>.json")

    data = json.loads(input_path.read_text(encoding="utf-8"))
    result = <função_principal>(data)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[<modulo>] Saída gravada em {output_path}")
```

---

## 5. Executando os Testes

```bash
make test      # roda todos os testes
make test-cov  # roda com relatório de cobertura por linha
```

Os testes ficam em `tests/unit/test_<modulo>.py` (um arquivo por filtro) e `tests/integration/test_pipeline.py`.

**Ao implementar um filtro:**

1. Descomente os imports no arquivo `tests/unit/test_<modulo>.py` correspondente
2. Substitua o `test_placeholder` por testes reais que cobrem a função principal e casos de borda
3. Use as fixtures de `tests/conftest.py` (`raw_comments`, `processed_comments`, `small_word_graph`) como ponto de partida

O CI executa `make test` automaticamente em todo PR para `main` ou `dev`. O PR só pode ser mergeado se todos os testes passarem.

---

## 6. Adicionando um Novo Filtro

1. Crie `src/<nome>.py` com a função principal tipada e docstring completa
2. Adicione o bloco `if __name__ == "__main__"` para execução isolada
3. Registre o filtro em `src/main.py` na posição correta do pipeline
4. Descomente e implemente `tests/unit/test_<nome>.py`
5. Documente o contrato de interface (tipos de entrada/saída) em `docs/arquitetura.md`
6. Adicione o `make <filtro>` ao `Makefile` e o arquivo de saída à estrutura `data/`

---

## 7. Padrões de Código

| Regra | Detalhe |
|-------|---------|
| **Linguagem** | Python 3.11+ |
| **Type hints** | Obrigatórios em toda função pública |
| **Docstrings** | Obrigatórias em toda função — propósito, `Args:`, `Returns:` |
| **Comentários** | Apenas quando o *porquê* é não-óbvio; jamais descrever o que o código faz |
| **Imports** | Ordem: stdlib → third-party → local; separados por linha em branco |
| **Caminhos** | Sempre `pathlib.Path`; nunca strings hardcoded com `/` ou `\\` |
| **Idioma** | Código, comentários, docstrings e commits em **inglês**; dados e relatório em **português** |
| **Bibliotecas proibidas** | NetworkX, igraph, graph-tool e equivalentes — penalidade de −5,0 pontos |
| **Bibliotecas de PLN** | NLTK e spaCy são permitidas exclusivamente em `preprocessing.py` |

---

## 8. Definition of Done (por módulo)

Um módulo está concluído quando **todos** os critérios abaixo são verdadeiros:

- [ ] Executa sem erros via `make <nome-do-filtro>`
- [ ] `make test` passa sem falhas (todos os `test_placeholder` substituídos por testes reais)
- [ ] Grava o arquivo JSON de saída correto em `data/`
- [ ] Saída consistente com os exemplos documentados em `docs/arquitetura.md`
- [ ] Toda função pública tem type hints e docstring
- [ ] Código commitado em branch própria e PR aberto para `main` ou `dev`
- [ ] PR aprovado por ao menos 1 outro membro da equipe e CI verde

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 12/06/2026 | 1.0 | Criação inicial do documento | Lucas Antunes |
