"""Generate a large, varied raw comments dataset that mimics a game-review forum.

Produces ``{"id", "topic", "text"}`` entries in Portuguese, balanced across the
ten project topics, by assembling forum-style openers, topic-coherent clauses
(positive/negative), connectors and closers. Output mirrors the on-disk style of
``data/comments.json`` (one object per line, accents preserved).

Run via:
    make gen-data                                   # 2000 comments -> data/comments_2000.json
    docker compose run --rm app uv run python -m scripts.generate_comments --count 2000

It is **dev tooling**, not a pipeline filter: it only writes a local JSON file.
Load it into the pipeline with ``make init-data ARGS=data/comments_2000.json``.
"""

import argparse
import json
import random
from pathlib import Path

# Forum-style openers (capitalized; the clause that follows stays lowercase).
_OPENERS = [
    "", "", "", "",  # weight the "no opener" case so it stays common
    "Cara,", "Gente,", "Sinceramente,", "Pra mim,", "Olha,", "Honestamente,",
    "No geral,", "Na minha experiência,", "Real,", "Confesso que",
    "Vou ser direto:", "Depois de umas horas,", "Comprei no lançamento e",
    "Joguei o fim de semana inteiro e", "Voltei depois do último patch e",
]

# Connectors that keep a single lowercase sentence flowing.
_SAME_CONNECTORS = [" e ", " e ainda ", ", ", " e também "]
_MIXED_CONNECTORS = [" mas ", " porém ", ", só que ", ", mas "]

_POS_CLOSERS = [
    "Recomendo demais.", "Vale cada centavo.", "Tô viciado.", "Nota 9.",
    "De longe um dos melhores do ano.", "Surpreendeu positivamente.",
    "Fica a recomendação.",
]
_NEG_CLOSERS = [
    "Não recomendo.", "Esperava muito mais.", "Decepcionante.", "Nota 4.",
    "Arrependido da compra.", "Passa longe.", "Fica o aviso.",
]
_NEUTRAL_CLOSERS = [
    "Alguém mais sentiu isso?", "Fica a opinião.", "Nota 7.",
    "No fim das contas, dá pro gasto.", "Depende muito do seu gosto.",
    "Vale esperar uma promoção.",
]

# Per-topic clause banks. Clauses start lowercase and carry no trailing period.
_TOPICS: dict[str, dict[str, list[str]]] = {
    "desempenho": {
        "pos": [
            "depois do último patch o jogo ficou muito mais fluido",
            "roda liso a 60 fps mesmo nas cenas mais cheias",
            "a otimização surpreendeu, nem esquenta minha placa antiga",
            "os tempos de carregamento ficaram quase instantâneos no ssd",
            "não tive um único crash em mais de quarenta horas",
            "a taxa de quadros se mantém estável até nas explosões",
            "rodou redondo no meu pc intermediário, sem stutter nenhum",
            "a última atualização resolveu as quedas de fps que eu sentia",
            "impressionante como roda bem até no portátil",
            "zero travamentos e o frametime é consistente",
            "o jogo escala bem, dá pra rodar em máquina fraca",
            "carregou rápido e manteve a performance o tempo todo",
        ],
        "neg": [
            "trava muito depois da atualização recente",
            "os quadros por segundo despencam quando enche a tela",
            "o jogo crasha pra área de trabalho do nada",
            "tá um stutter horrível mesmo com tudo no mínimo",
            "os carregamentos demoram uma eternidade",
            "minha placa esquenta absurdamente nesse game",
            "engasga feio nas áreas abertas",
            "depois de uma hora a memória vaza e começa a travar",
            "dá tela preta na inicialização e fecha sozinho",
            "a otimização é um desastre, nem trinta fps estável segura",
            "queda de frame constante nas partidas movimentadas",
            "roda mal até em pc bem acima do recomendado",
        ],
    },
    "narrativa": {
        "pos": [
            "a história é envolvente e me prendeu do começo ao fim",
            "os personagens têm uma profundidade rara nesse tipo de jogo",
            "a campanha principal tem um roteiro muito bem amarrado",
            "os diálogos são naturais e cheios de personalidade",
            "a reviravolta do segundo ato me pegou de surpresa",
            "o enredo trata de temas adultos sem ser apelativo",
            "as missões secundárias enriquecem demais o universo",
            "o final amarrou todas as pontas de forma satisfatória",
            "a ambientação narrativa é de tirar o fôlego",
            "cada personagem tem um arco que faz sentido",
        ],
        "neg": [
            "o enredo começa bem mas perde força no meio",
            "os personagens são rasos e esquecíveis",
            "a história é um clichê atrás do outro",
            "os diálogos são engessados e mal escritos",
            "o final é apressado e deixa um monte de pontas soltas",
            "a campanha é curta demais pra contar essa história",
            "as missões são repetitivas e sem propósito narrativo",
            "o ritmo da trama é arrastado, quase dormi",
            "o roteiro desperdiça uma premissa que era ótima",
            "as motivações dos vilões não convencem nada",
        ],
    },
    "multiplayer": {
        "pos": [
            "o matchmaking é rápido e quase sempre equilibrado",
            "os servidores são estáveis e o ping fica baixo",
            "o cooperativo com os amigos é viciante",
            "o crossplay funciona perfeitamente entre as plataformas",
            "raramente encontro trapaceiro nas partidas ranqueadas",
            "o balanceamento entre as classes está bem ajustado",
            "a fila pra encontrar partida é curtíssima",
            "o pvp é competitivo e recompensa habilidade",
            "dá pra montar grupo fácil e a comunicação flui",
        ],
        "neg": [
            "o modo online está cheio de bugs e a conexão cai toda hora",
            "o matchmaking joga você contra gente muito mais forte",
            "os servidores vivem fora do ar nos horários de pico",
            "tá impossível jogar de tanto trapaceiro solto",
            "o ping é altíssimo e tudo acontece com atraso",
            "o balanceamento é uma piada, só uma classe domina",
            "a fila demora minutos e ainda cai no meio da partida",
            "o cooperativo desconecta do nada e perde o progresso",
            "falta crossplay e a base de jogadores está dividida",
        ],
    },
    "interface": {
        "pos": [
            "os menus são limpos e fáceis de navegar",
            "o hud é discreto e mostra só o necessário",
            "o inventário é bem organizado e intuitivo",
            "dá pra customizar a interface do jeito que quiser",
            "o tutorial explica tudo sem ser cansativo",
            "as opções de acessibilidade são completíssimas",
            "o mapa é claro e a navegação é prática",
            "encontrei todas as configurações sem esforço",
        ],
        "neg": [
            "os menus são confusos e cheios de submenus inúteis",
            "o hud polui a tela com informação demais",
            "o inventário é um caos pra gerenciar",
            "a fonte é minúscula e ilegível na tv",
            "o tutorial é intrusivo e não deixa você jogar",
            "faltam opções básicas de acessibilidade",
            "o mapa é confuso e não dá pra marcar nada",
            "a navegação nos menus trava e responde mal",
        ],
    },
    "progressão": {
        "pos": [
            "a curva de progressão é bem dosada do início ao fim",
            "a árvore de habilidades dá liberdade real de build",
            "cada nível desbloqueia algo que muda o gameplay",
            "o sistema de recompensa mantém você sempre motivado",
            "o loot é variado e vale a pena caçar",
            "dá pra evoluir o personagem sem precisar de grind",
            "as recompensas de missão são justas pelo esforço",
        ],
        "neg": [
            "a progressão é um grind sem fim pra empurrar microtransação",
            "a árvore de habilidades é enganosa, quase tudo é inútil",
            "subir de nível não muda nada no gameplay",
            "o loot é repetitivo e nunca vem nada bom",
            "a curva de dificuldade dispara do nada e trava o avanço",
            "as recompensas são insignificantes pro tempo investido",
            "o sistema de progressão é claramente pago pra acelerar",
        ],
    },
    "áudio": {
        "pos": [
            "a trilha sonora é memorável e combina com cada cena",
            "os efeitos sonoros são imersivos e cheios de detalhe",
            "a dublagem em português está impecável",
            "a mixagem equilibra bem música, vozes e ambiente",
            "o áudio posicional ajuda demais a se localizar",
            "as músicas de combate elevam a adrenalina",
        ],
        "neg": [
            "a mixagem é péssima, a música abafa os diálogos",
            "os efeitos sonoros são genéricos e repetitivos",
            "a dublagem soa desinteressada e fora de sincronia",
            "a trilha é esquecível e some no meio do jogo",
            "o áudio buga e corta nas cenas mais intensas",
            "falta dublagem, só legenda em letra minúscula",
        ],
    },
    "gráficos": {
        "pos": [
            "as texturas são detalhadas e a iluminação é linda",
            "a direção de arte é deslumbrante em cada cenário",
            "o ray tracing deixa os reflexos impressionantes",
            "os modelos de personagem têm um nível de detalhe absurdo",
            "as paisagens são de parar pra tirar print",
            "roda em quatro k mantendo uma nitidez incrível",
        ],
        "neg": [
            "as texturas demoram a carregar e ficam borradas",
            "o pop-in de objetos é constante e quebra a imersão",
            "a iluminação é chapada e sem graça",
            "os modelos são datados pra um jogo de hoje",
            "a estética é genérica, nada se destaca",
            "tem serrilhado por toda parte mesmo no máximo",
        ],
    },
    "controles": {
        "pos": [
            "os controles são responsivos e precisos",
            "o mapeamento de botões é totalmente customizável",
            "a mira é gostosa e a sensibilidade é fácil de ajustar",
            "o suporte a controle funciona de primeira",
            "a resposta dos comandos é instantânea",
            "dá pra remapear tudo do jeito que preferir",
        ],
        "neg": [
            "os controles têm um input lag perceptível",
            "o mapeamento de botões é fixo e não dá pra mudar",
            "a mira é travada e parece presa na lama",
            "o suporte a controle vive desconectando",
            "a sensibilidade não tem ajuste fino nenhum",
            "os comandos não respondem direito nos momentos rápidos",
        ],
    },
    "conteúdo pós-lançamento": {
        "pos": [
            "os desenvolvedores entregam atualizações constantes e gratuitas",
            "o roadmap é transparente e cheio de conteúdo novo",
            "os eventos sazonais mantêm o jogo sempre fresco",
            "a dlc adiciona horas de conteúdo que valem o preço",
            "o suporte pós-lançamento é exemplar",
            "cada patch traz melhorias que a comunidade pediu",
        ],
        "neg": [
            "o conteúdo pós-lançamento é só microtransação atrás de microtransação",
            "o season pass cobra caro por migalhas de conteúdo",
            "prometeram um roadmap e abandonaram o jogo",
            "as atualizações só trazem skins pagas, nada de novo",
            "a dlc divide a base de jogadores e cobra por nada",
            "faz meses sem um único patch de conteúdo",
        ],
    },
    "suporte técnico": {
        "pos": [
            "o suporte respondeu meu ticket em poucas horas",
            "os bugs que reportei foram corrigidos no patch seguinte",
            "a equipe é atenciosa e resolveu meu reembolso rápido",
            "os desenvolvedores conversam de verdade com a comunidade",
            "o atendimento foi educado e resolveu meu problema",
        ],
        "neg": [
            "abri um ticket faz semanas e ninguém respondeu",
            "o suporte só manda resposta automática que não ajuda",
            "reportei o bug no lançamento e até hoje não corrigiram",
            "pedir reembolso aqui é uma novela sem fim",
            "os devs ignoram completamente os relatos da comunidade",
            "o atendimento é terceirizado e não resolve nada",
        ],
    },
}


def _finish(rng: random.Random, opener: str, body: str, closer: str) -> str:
    """Assemble opener, clause body and closer into a finished comment.

    Capitalizes the sentence start, joins the parts, randomly emphasizes some
    comments with ``!``, and guarantees terminal punctuation.

    Args:
        rng: Seeded random generator.
        opener: Capitalized forum opener, or ``""`` for none.
        body: Lowercase clause body (no trailing period).
        closer: A full closer sentence, or ``""`` for none.

    Returns:
        The finished comment text.
    """
    if opener:
        sentence = f"{opener} {body}"
    else:
        sentence = body[0].upper() + body[1:]
    terminator = "!" if rng.random() < 0.1 else "."
    text = sentence + terminator
    if closer:
        text = f"{text} {closer}"
    return text


def _make_text(rng: random.Random, bank: dict[str, list[str]]) -> str:
    """Build one topic-coherent forum comment from a topic's clause bank.

    Picks a sentiment profile (negative/positive/mixed), assembles one or two
    clauses with a connector, and adds an optional opener and a sentiment-matched
    closer.

    Args:
        rng: Seeded random generator.
        bank: ``{"pos": [...], "neg": [...]}`` clauses for one topic.

    Returns:
        The finished comment text.
    """
    profile = rng.choices(["neg", "pos", "mixed"], weights=[40, 35, 25])[0]
    if profile == "mixed":
        pos, neg = rng.choice(bank["pos"]), rng.choice(bank["neg"])
        first, second = (pos, neg) if rng.random() < 0.5 else (neg, pos)
        body = first + rng.choice(_MIXED_CONNECTORS) + second
        closer_pool = _NEUTRAL_CLOSERS
    else:
        clauses = bank["pos"] if profile == "pos" else bank["neg"]
        if rng.random() < 0.55:
            body = rng.choice(clauses)
        else:
            first, second = rng.sample(clauses, 2)
            body = first + rng.choice(_SAME_CONNECTORS) + second
        closer_pool = _POS_CLOSERS if profile == "pos" else _NEG_CLOSERS

    opener = rng.choice(_OPENERS)
    closer = rng.choice(closer_pool) if rng.random() < 0.5 else ""
    return _finish(rng, opener, body, closer)


def generate(count: int, seed: int) -> list[dict]:
    """Generate ``count`` comments balanced across the ten topics.

    Each topic gets an equal share of unique texts (the remainder is spread over
    the first topics). The full list is shuffled so topics interleave like a real
    forum feed, then ids are assigned sequentially.

    Args:
        count: Total number of comments to generate.
        seed: Random seed for reproducibility.

    Returns:
        List of ``{"id", "topic", "text"}`` dicts, ids running 1..count.
    """
    rng = random.Random(seed)
    topics = list(_TOPICS)
    base, extra = divmod(count, len(topics))

    comments: list[dict] = []
    for position, topic in enumerate(topics):
        target = base + (1 if position < extra else 0)
        seen: set[str] = set()
        while len(seen) < target:
            text = _make_text(rng, _TOPICS[topic])
            if text in seen:
                continue
            seen.add(text)
            comments.append({"topic": topic, "text": text})

    rng.shuffle(comments)
    return [{"id": i, "topic": c["topic"], "text": c["text"]} for i, c in enumerate(comments, start=1)]


def _dump(comments: list[dict], out: Path) -> None:
    """Write the dataset one object per line, matching the repo's JSON style.

    Args:
        comments: The generated comments.
        out: Destination path.
    """
    lines = ",\n".join("  " + json.dumps(c, ensure_ascii=False) for c in comments)
    out.write_text(f"[\n{lines}\n]\n", encoding="utf-8")


def main() -> None:
    """Parse CLI flags, generate the dataset, and write it to disk."""
    parser = argparse.ArgumentParser(prog="python -m scripts.generate_comments")
    parser.add_argument("--count", type=int, default=2000, help="Number of comments (default: 2000).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42).")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/comments_2000.json"),
        help="Output path (default: data/comments_2000.json).",
    )
    args = parser.parse_args()

    comments = generate(args.count, args.seed)
    _dump(comments, args.out)
    print(f"[generate_comments] Wrote {len(comments)} comments -> {args.out}")


if __name__ == "__main__":
    main()
