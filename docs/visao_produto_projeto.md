# GameReviewGraph
# VISÃO DO PRODUTO E PROJETO

**Disciplina:** FGA0030 — Estruturas de Dados 2 · Turma 03 · 2026/1  
**Temática:** D — Processamento de Linguagem Natural com Grafos  
**Apresentação:** 08/07/2026  
**Versão:** 1.0  

---

## Sumário

1. [Cenário Atual e Contexto do Problema](#1-cenário-atual-e-contexto-do-problema)
2. [Solução Proposta](#2-solução-proposta)
3. [Estratégias de Engenharia de Software](#3-estratégias-de-engenharia-de-software)
4. [Cronograma e Entregas](#4-cronograma-e-entregas)
5. [Interação entre Equipe](#5-interação-entre-equipe)
6. [Lições Aprendidas](#6-lições-aprendidas)
7. [Referências Bibliográficas](#7-referências-bibliográficas)

---

## 1. Cenário Atual e Contexto do Problema

### 1.1 Introdução ao Contexto

A indústria de jogos digitais é uma das que mais cresce globalmente, movimentando bilhões de dólares anuais e concentrando comunidades massivas de jogadores. Plataformas como Steam, Metacritic e Reddit recebem diariamente milhares de comentários, avaliações e discussões produzidos por esses jogadores. Esse volume contínuo de texto não estruturado representa uma fonte riquíssima de informação sobre a percepção dos usuários em relação a diferentes aspectos dos jogos — desempenho técnico, narrativa, jogabilidade, entre muitos outros.

Do ponto de vista acadêmico e científico, essa massa de dados textuais é um campo fértil para aplicação de técnicas de Processamento de Linguagem Natural (PLN) combinadas a estruturas de dados avançadas. O projeto **GameReviewGraph** está inserido nesse contexto, utilizando comentários de jogadores como matéria-prima para construção e análise de grafos hierárquicos.

### 1.2 Identificação do Problema

Jogos digitais recebem diariamente milhares de comentários em plataformas especializadas. A análise manual desse volume de conteúdo é inviável em termos de tempo e escala. Como consequência, pesquisadores e desenvolvedores têm dificuldade em identificar, de forma sistemática, quais assuntos são recorrentes e relevantes para a comunidade.

**Problema central:** como identificar automaticamente os principais tópicos de discussão presentes em uma coleção de comentários de jogadores, sem supervisão humana e sem categorias predefinidas?

A ausência de ferramentas automatizadas que operem sobre texto livre e extraiam padrões temáticos cria uma lacuna entre o volume de dados produzido pela comunidade e a capacidade de interpretá-lo de maneira eficiente e escalável.

### 1.3 Desafios do Projeto

| Categoria | Desafio |
|-----------|---------|
| **Técnico** | Implementar todos os algoritmos principais de grafos sem uso de bibliotecas prontas, conforme exigido pela disciplina |
| **Técnico** | Construir uma hierarquia de grafos em três níveis (palavras, frases, comentários) de forma coerente e eficiente |
| **Técnico** | Garantir que o algoritmo de corte progressivo de arestas produza comunidades semanticamente interpretáveis |
| **Dados** | Gerar dados fictícios via LLM que sejam suficientemente coerentes e diversificados para validar o sistema |
| **Prazo** | Desenvolver, testar e documentar o projeto integralmente em aproximadamente 11 dias úteis |
| **Avaliativo** | Cumprir todos os critérios avaliativos da disciplina, incluindo análise dos resultados e apresentação final |

### 1.4 Perfil dos Usuários e Stakeholders

| Perfil | Descrição |
|--------|-----------|
| **Equipe de desenvolvimento** | Os 5 integrantes do grupo, responsáveis pela implementação, testes e documentação |
| **Professor avaliador** | Responsável por avaliar o trabalho segundo os critérios definidos na disciplina FGA0030 |
| **Comunidade acadêmica** | Potenciais interessados na abordagem de detecção de tópicos via grafos hierárquicos |
| **Desenvolvedores de jogos** (contexto fictício) | Representam o público-alvo simulado que se beneficiaria da análise automática de comentários |

---

## 2. Solução Proposta

### 2.1 Objetivos do Produto

O **GameReviewGraph** tem como objetivo desenvolver um sistema em Python capaz de transformar uma coleção de comentários textuais de jogos em uma estrutura hierárquica de grafos e identificar automaticamente comunidades semânticas que representam os principais tópicos discutidos pelos jogadores — sem necessidade de supervisão humana ou categorias predefinidas.

**Objetivos específicos:**

- Realizar o pré-processamento dos comentários (tokenização, remoção de stopwords, normalização)
- Construir uma **Árvore N-ária de Representação Textual** para organizar a hierarquia: Dataset → Comentário → Frase → Palavra
- Construir um **grafo de palavras** baseado em relações de coocorrência e proximidade textual
- Construir um **grafo de frases** derivado das relações entre palavras
- Construir um **grafo de comentários** derivado das relações entre frases
- Integrar os três níveis em um **grafo final unificado**
- Aplicar **corte progressivo de arestas** como técnica de filtragem e detecção de comunidades
- Usar **BFS/DFS** para verificar conectividade durante o processo de corte
- Implementar cálculo de **centralidade de grau ponderada** para identificar os termos mais relevantes por comunidade
- Avaliar a qualidade das comunidades pela métrica de **modularidade (Q)**
- Analisar e interpretar os tópicos identificados

### 2.2 Características da Solução

**Pipeline de processamento:**

```
Entrada (comentários em texto) 
    → Pré-processamento (limpeza, tokenização, remoção de stopwords)
    → Árvore N-ária de Representação Textual
    → Grafo de Palavras (coocorrência ponderada por distância posicional)
    → Grafo de Frases (derivado das relações entre palavras)
    → Grafo de Comentários (derivado das relações entre frases)
    → Grafo Final Integrado (três níveis + arestas hierárquicas da árvore)
    → Corte Progressivo de Arestas + BFS/DFS (detecção de K=10 comunidades)
    → Cálculo de Modularidade Q e Centralidade de Grau
    → Saída: Relatório de tópicos detectados com métricas de qualidade
```

**Estrutura hierárquica dos dados:**

```
Dataset
└── Comentário
    └── Frase
        └── Palavra
```

**Modelagem dos grafos:**

| Grafo | Vértices | Arestas | Peso |
|-------|----------|---------|------|
| Palavras | Termos relevantes após pré-processamento | Coocorrência na mesma frase | `Σ 1/(1 + distância posicional)` |
| Frases | Frases do dataset | Ao menos um par de palavras relacionado | Média ponderada das relações de palavras, normalizada pelo tamanho |
| Comentários | Comentários/reviews | Ao menos um par de frases relacionado | Média ponderada das relações de frases, normalizada pelo tamanho |
| Final Integrado | Palavras + Frases + Comentários | Relacionais (com peso) + Hierárquicas da árvore (sem peso) | Pesos propagados dos grafos anteriores |

**Algoritmos implementados pelo grupo (sem bibliotecas externas):**

- Corte progressivo de arestas com restrição de grau mínimo
- BFS/DFS para detecção de componentes conexos
- Centralidade de grau ponderada
- Cálculo de modularidade Q

### 2.3 Tecnologias Utilizadas

| Tecnologia | Uso |
|------------|-----|
| **Python 3.x** | Linguagem principal de implementação |
| **NLTK / spaCy** | Pré-processamento de linguagem natural (permitido pela disciplina) |
| **LLM (ChatGPT/Claude)** | Geração dos dados fictícios de entrada (~200 comentários) |
| **GitHub** | Hospedagem do código-fonte e controle de versão |
| **GitPages** | Publicação da documentação do projeto |
| **Markdown** | Formato da documentação |
| **WhatsApp** | Comunicação informal e rápida entre os membros |
| **Discord** | Reuniões formais e sincronização da equipe |
| **Claude Code** | Ferramenta para auxiliar o desenvolvimento do produto |

### 2.4 Análise da Solução no Contexto Acadêmico

A abordagem adotada pelo GameReviewGraph se diferencia de soluções convencionais de detecção de tópicos (como LDA ou NMF) pelos seguintes aspectos:

| Aspecto | Abordagem convencional (LDA/NMF) | GameReviewGraph |
|---------|----------------------------------|-----------------|
| Estrutura de dados | Matrizes documento-termo | Grafos hierárquicos em três níveis |
| Detecção de tópicos | Modelos probabilísticos | Detecção de comunidades por corte de arestas |
| Relações semânticas | Coocorrência global no corpus | Coocorrência local com peso posicional |
| Hierarquia textual | Não representada explicitamente | Árvore N-ária + arestas hierárquicas |
| Implementação | Bibliotecas prontas | Algoritmos implementados pelo grupo |

### 2.5 Análise de Viabilidade

**Técnica:** A equipe tem familiaridade com Python e os conceitos de grafos abordados na disciplina. Os algoritmos escolhidos (BFS/DFS, corte de arestas, centralidade de grau) têm complexidade gerenciável para o volume de dados previsto (~200 comentários, ~10 tópicos).

**Prazo:** O projeto deve ser concluído em aproximadamente 11 dias úteis (até 22/06/2026). Para isso, o desenvolvimento será organizado em **ondas de trabalho** com escopo bem definido por onda, priorizando os componentes de maior risco técnico nas primeiras ondas.

**Dados:** Os dados serão gerados artificialmente via LLM (permitido pela disciplina), o que elimina riscos de coleta, scraping ou problemas de acesso a APIs externas.

**Avaliativo:** Todos os critérios de avaliação da disciplina foram mapeados e há correspondência direta com os componentes do sistema planejado.

### 2.6 Impacto Esperado da Solução

- **Acadêmico:** Demonstração prática da aplicação conjunta de grafos hierárquicos e PLN para detecção de tópicos, atendendo integralmente aos requisitos da disciplina FGA0030
- **Técnico:** Sistema modular e bem documentado, com algoritmos implementados do zero, que pode servir como referência para trabalhos futuros na área
- **Avaliativo:** Obtenção de nota máxima nos critérios de implementação, algoritmos em grafos e análise de resultados, que juntos representam 7,5 dos 10 pontos disponíveis

---

## 3. Estratégias de Engenharia de Software

### 3.1 Estratégia Priorizada

| Dimensão | Escolha |
|----------|---------|
| **Abordagem de Desenvolvimento** | Híbrida (predominantemente ágil, com planejamento inicial detalhado dado o prazo fixo) |
| **Ciclo de Vida** | Incremental com ondas de trabalho sequenciais |
| **Processo** | Adaptação leve do XP — entregas frequentes, integração contínua via GitHub, sem cerimônias formais do Scrum dado o prazo curto |

**Justificativa da abordagem híbrida:** o prazo curto e fixo (11 dias) exige planejamento antecipado do escopo total (característica de abordagens dirigidas por plano), mas a natureza exploratória do desenvolvimento — especialmente na calibração do algoritmo de corte e na análise dos resultados — demanda flexibilidade e ciclos curtos de feedback (características ágeis). A combinação de planejamento inicial com ondas curtas de desenvolvimento é a resposta mais adequada a esse contexto.

### 3.2 Quadro Comparativo de Processos

| Característica | XP (Extreme Programming) | Scrum |
|----------------|--------------------------|-------|
| **Estrutura de iterações** | Ciclos curtos e flexíveis, sem cerimônias fixas pesadas | Sprints de 1–4 semanas com cerimônias definidas (planning, review, retro) |
| **Foco principal** | Qualidade técnica do código (TDD, pair programming, integração contínua) | Gerenciamento e organização do trabalho da equipe |
| **Papéis** | Flexíveis — toda a equipe é responsável pelo código | Definidos: Product Owner, Scrum Master, Time de Desenvolvimento |
| **Documentação** | Mínima, focada no código funcionando | Artefatos definidos: backlog, definition of done, etc. |
| **Adaptação ao projeto** | Mais adequado: equipe pequena (5 pessoas), prazo curto, foco em código de qualidade sem estrutura pesada | Menos adequado: cerimônias formais consomem tempo precioso em um prazo de 11 dias |
| **Integração contínua** | Nativa no processo | Opcional, depende da maturidade do time |
| **Adequação ao prazo** | Alta — ciclos rápidos sem overhead de gestão | Média — o Sprint Planning e Reviews formais são custosos para 11 dias |

### 3.3 Justificativa

O processo escolhido é uma **adaptação leve do XP**, pelos seguintes motivos:

1. **Equipe pequena e coesa (5 pessoas):** o XP foi concebido para equipes pequenas e co-localizadas (ou bem conectadas), o que corresponde ao perfil da equipe
2. **Foco em qualidade técnica:** dado que 5,5 dos 10 pontos do trabalho avaliam implementação e algoritmos, a ênfase do XP em código bem escrito, modular e testável é a mais adequada
3. **Prazo curto:** a ausência de cerimônias pesadas (sem Sprint Planning formal, sem retrospectivas extensas) permite que todo o tempo disponível seja dedicado ao desenvolvimento
4. **Integração contínua via GitHub:** o XP incentiva commits frequentes e integração contínua, o que é essencial para garantir que o repositório esteja sempre atualizado e que o prazo final (22/06/2026) seja cumprido
5. **Sem Product Owner externo:** não há cliente real — a equipe decide coletivamente as prioridades, o que se alinha melhor à filosofia colaborativa do XP do que à hierarquia de papéis do Scrum

---

## 4. Cronograma e Entregas

O projeto é organizado em **4 ondas de trabalho**, cada uma com escopo e entregáveis bem definidos. As ondas são sequenciais por dependência técnica, mas algumas tarefas dentro de cada onda podem ser paralelizadas entre os membros da equipe.

| Onda | Período | Foco | Entregáveis |
|------|---------|------|-------------|
| **Onda 1** | 11/06 – 13/06 | Infraestrutura e dados | Dataset gerado, módulo `preprocessing.py` funcional, `tree.py` (Árvore N-ária) implementado, repositório GitHub configurado, documentação inicial no GitPages |
| **Onda 2** | 14/06 – 17/06 | Construção dos grafos | `word_graph.py`, `sentence_graph.py`, `comment_graph.py` e `final_graph.py` implementados e testados com o dataset gerado |
| **Onda 3** | 18/06 – 20/06 | Algoritmos e métricas | `community_detection.py` (corte progressivo + BFS/DFS) e `metrics.py` (centralidade + modularidade) implementados, comunidades detectadas e validadas |
| **Onda 4** | 21/06 – 22/06 | Análise, relatório e entrega | `analysis.py` e `main.py` finalizados, relatório de análise dos resultados, slides da apresentação, última atualização no GitHub até 22/06/2026 |

**Marcos críticos:**

| Data | Marco |
|------|-------|
| 13/06/2026 | Dataset gerado e pré-processamento validado |
| 17/06/2026 | Todos os grafos construídos e integrados |
| 20/06/2026 | Algoritmos de detecção finalizados com métricas calculadas |
| **22/06/2026** | **Última atualização obrigatória no GitHub** |
| 08/07/2026 | Apresentação final |

---

## 5. Interação entre Equipe

### 5.1 Composição da Equipe

| Membro | Responsabilidades Principais |
|--------|------------------------------|
| **Vinícius Rufino** | — |
| **Luis Guilherme Borges** | — |
| **Lucas Antunes** | — |
| **Mateus Vieira** | — |
| **Julia Patricio** | — |

> _A distribuição detalhada de responsabilidades por módulo será definida na reunião de kick-off da Onda 1 e registrada aqui._

### 5.2 Comunicação

| Canal | Tipo | Uso |
|-------|------|-----|
| **WhatsApp** | Informal e assíncrono | Comunicação diária, dúvidas rápidas, avisos, compartilhamento de atualizações |
| **Discord** | Formal e síncrono | Reuniões de alinhamento entre ondas, revisão de código, resolução de bloqueios técnicos |
| **GitHub** | Técnico e assíncrono | Controle de versão, revisão de pull requests, rastreamento de tarefas via Issues |
| **GitPages** | Documentação | Publicação e atualização contínua da documentação do projeto |

**Frequência de sincronização:**
- **Daily assíncrono (WhatsApp):** cada membro reporta o que fez, o que vai fazer e se há algum bloqueio
- **Reunião de fechamento de onda (Discord):** ao final de cada onda, a equipe revisa o que foi entregue e planeja a onda seguinte
- **Commits diários no GitHub:** todos os membros devem commitar progresso ao menos uma vez por dia

### 5.3 Processo de Validação

A validação do produto ocorre em dois momentos dentro de cada onda:

1. **Validação técnica (ao final de cada módulo):** o módulo implementado é executado com o dataset gerado e a saída é verificada manualmente pela equipe quanto à correção dos dados estruturais (grafo construído corretamente, arestas com pesos esperados, etc.)

2. **Validação semântica (Onda 3 e 4):** as comunidades detectadas são avaliadas qualitativamente — os termos centrais de cada comunidade formam um tópico interpretável e coerente com os dados de entrada? Essa avaliação é documentada no relatório de análise.

**Critérios de conclusão de cada módulo (Definition of Done):**
- Código executável sem erros
- Saída consistente com os exemplos documentados no planejamento
- Código versionado no GitHub com mensagem de commit descritiva
- Módulo documentado com docstrings

---

## 6. Referências Bibliográficas

1. SOMMERVILLE, Ian. **Engenharia de Software**. 10. ed. São Paulo: Pearson, 2018.

2. PRESSMAN, Roger S.; MAXIM, Bruce R. **Engenharia de Software: uma abordagem profissional**. 8. ed. Porto Alegre: AMGH, 2016.

3. GERLACH, M. et al. **A network approach to topic models**. Science Advances, v. 4, n. 7, 2018. Disponível em: https://advances.sciencemag.org/content/4/7/eaaq1360

4. NEWMAN, M. E. J. **Modularity and community structure in networks**. Proceedings of the National Academy of Sciences, v. 103, n. 23, p. 8577–8582, 2006.

5. CHOWDHURY, M. R. et al. **Topic Modeling Using Community Detection on a Word Association Graph**. In: Proceedings of RANLP 2023. ACL Anthology, 2023.

6. BIRD, Steven; KLEIN, Ewan; LOPER, Edward. **Natural Language Processing with Python**. O'Reilly Media, 2009. Disponível em: https://www.nltk.org/book/

7. BECK, Kent. **Extreme Programming Explained: Embrace Change**. 2. ed. Addison-Wesley, 2004.

8. MANIFESTO ÁGIL. **Manifesto para Desenvolvimento Ágil de Software**, 2001. Disponível em: https://agilemanifesto.org/iso/ptbr/manifesto.html

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 11/06/2026 | 1.0 | Criação inicial do documento | [Vinícius Rufino](https://github.com/RufinoVfR) |