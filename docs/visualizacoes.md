# Visualizações

## Grafo de Co-ocorrência de Palavras

Visualização interativa do grafo de palavras construído pelo Filtro 3. Cada nó é uma palavra do corpus (após pré-processamento); cada aresta representa co-ocorrência na mesma frase, com espessura proporcional ao peso posicional.

**Controles:**

| Ação | Efeito |
|------|--------|
| Clique em um nó | Destaca o nó e seus vizinhos; abre painel de inspeção |
| Duplo clique | Desfixa o nó (retoma posição livre na simulação) |
| Arraste | Fixa a posição do nó |
| Scroll | Zoom in / zoom out |
| Clique na legenda | Filtra por cluster semântico |
| Campo de busca | Localiza e centraliza uma palavra |

Os 7 clusters semânticos visíveis (Áudio/Efeitos, Otimização/Final, Partidas Online, Progressão/Visual, Controles/Suporte, Estado da Sessão, Menu/Campanha) foram identificados com base nas 20 avaliações do dataset de desenvolvimento — o corpus completo de 200 comentários pode produzir distribuições diferentes.

<div style="width:100%; height:680px; border:1px solid #2a2d3a; border-radius:6px; overflow:hidden; margin-top: 1rem;">
  <iframe
    src="word_graph_vis.html"
    style="width:100%; height:100%; border:none;"
    title="Grafo de Co-ocorrência de Palavras — GameReviewGraph"
  ></iframe>
</div>

---

## Histórico de Revisão

| Data | Versão | Descrição | Autor |
|------|--------|-----------|-------|
| 22/06/2026 | 1.0 | Criação da página com visualização interativa D3.js do grafo de co-ocorrência (57 nós, 7 clusters semânticos, busca e inspeção de nó) | [Vinícius Rufino](https://github.com/RufinoVfR) |
