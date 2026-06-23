import { useMemo, useState } from "react";
import type { ReportData, ReportMethod } from "../data/schemas";

function formatTopic(topic: string | null): string {
  if (!topic) {
    return "sem comentários";
  }
  return topic.charAt(0).toUpperCase() + topic.slice(1);
}

interface CommentStats {
  /** Comment counts per community, descending, excluding empty communities. */
  distribution: number[];
  /** Number of communities that hold at least one comment. */
  communities: number;
  /** Normalized Shannon entropy of the comment distribution, in [0, 1]. */
  balance: number;
}

/**
 * Measure how evenly a method spreads the comments across its communities.
 *
 * The global modularity Q is dominated by the word/sentence structure and does
 * not tell whether the *comment* grouping is usable: greedy modularity scores
 * the highest Q yet lumps every comment into one community. This balance score
 * — the Shannon entropy of the per-community comment counts, normalized by
 * ln(k) — is 0 when one community absorbs all comments and approaches 1 when the
 * comments are split evenly into k communities, so it directly captures the
 * property the explorer needs.
 */
function commentStats(method: ReportMethod, k: number): CommentStats {
  const distribution = method.communities
    .map((community) => community.comments.length)
    .filter((count) => count > 0)
    .sort((a, b) => b - a);

  const total = distribution.reduce((sum, count) => sum + count, 0);
  let balance = 0;
  if (total > 0 && distribution.length > 1 && k > 1) {
    const entropy = -distribution.reduce((acc, count) => {
      const p = count / total;
      return acc + p * Math.log(p);
    }, 0);
    balance = Math.min(1, entropy / Math.log(k));
  }

  return { distribution, communities: distribution.length, balance };
}

interface ReportViewProps {
  report: ReportData;
  onClose: () => void;
}

export function ReportView({ report, onClose }: ReportViewProps) {
  const rows = useMemo(
    () =>
      report.methods.map((method) => ({
        method,
        stats: commentStats(method, report.k),
      })),
    [report],
  );

  const bestQ = useMemo(
    () => rows.reduce((max, row) => Math.max(max, row.method.modularityQ), Number.NEGATIVE_INFINITY),
    [rows],
  );
  const bestBalance = useMemo(
    () => rows.reduce((max, row) => Math.max(max, row.stats.balance), Number.NEGATIVE_INFINITY),
    [rows],
  );
  const balanceWinner = rows.find((row) => row.stats.balance === bestBalance);
  const qWinner = rows.find((row) => row.method.modularityQ === bestQ);

  const [selectedId, setSelectedId] = useState<number>(report.methods[0]?.id ?? 1);
  const selected = report.methods.find((method) => method.id === selectedId) ?? report.methods[0];
  const maxBar = balanceWinner ? Math.max(...balanceWinner.stats.distribution, 1) : 1;

  return (
    <div className="reportOverlay" role="dialog" aria-label="Relatório final">
      <header className="reportHeader">
        <div className="reportHeadText">
          <div className="reportEyebrow">RELATÓRIO FINAL</div>
          <h1 className="reportTitle">Comparação de métodos de detecção de comunidades</h1>
          <div className="reportSub">
            K-alvo {report.k} · {report.nComments} comentários
            {report.source === "mock" ? " · dados de exemplo" : ""}
          </div>
        </div>
        <button className="reportClose" type="button" onClick={onClose}>
          ✕ Fechar
        </button>
      </header>

      {balanceWinner && qWinner ? (
        <div className="reportCallout">
          <span className="calloutTag">POR QUE O MÉTODO {balanceWinner.method.id}?</span>
          <p>
            O método <strong>{qWinner.method.id}</strong> tem o maior Q ({qWinner.method.modularityQ.toFixed(2)}),
            mas esse Q é dominado pela estrutura de palavras/frases e concentra os comentários em{" "}
            {qWinner.stats.communities} comunidade{qWinner.stats.communities === 1 ? "" : "s"} (equilíbrio{" "}
            {qWinner.stats.balance.toFixed(2)}). Como o explorador navega comunidades de comentários, o que importa é a{" "}
            <strong>distribuição dos comentários</strong>: o método <strong>{balanceWinner.method.id}</strong> tem o
            maior equilíbrio ({balanceWinner.stats.balance.toFixed(2)}), espalhando os comentários por{" "}
            {balanceWinner.stats.communities} comunidades — por isso é o que alimenta o grafo.
          </p>
        </div>
      ) : null}

      <section className="reportMatrix">
        <div className="reportSectionLabel">Matriz comparativa</div>
        <table className="matrixTable">
          <thead>
            <tr>
              <th>Método</th>
              <th>Modularidade Q</th>
              <th>Comunidades c/ comentários</th>
              <th>Equilíbrio</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ method, stats }) => (
              <tr
                key={method.id}
                className="matrixRow"
                data-active={method.id === selectedId}
                onClick={() => setSelectedId(method.id)}
              >
                <td className="methodCell">
                  <span className="methodId">{method.id}</span>
                  <span className="methodLabel">{method.label}</span>
                  {method.id === balanceWinner?.method.id ? (
                    <span className="usedTag">no grafo</span>
                  ) : null}
                </td>
                <td className="qCell" data-best={method.modularityQ === bestQ}>
                  {method.modularityQ.toFixed(4)}
                  {method.modularityQ === bestQ ? <span className="bestTag">maior Q</span> : null}
                </td>
                <td className="numCell">{stats.communities}</td>
                <td className="balanceCell" data-best={stats.balance === bestBalance}>
                  <div className="balanceMeter">
                    <span className="balanceValue">{stats.balance.toFixed(2)}</span>
                    <span className="balanceTrack">
                      <span className="balanceFill" style={{ width: `${Math.round(stats.balance * 100)}%` }} />
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="matrixHint">
          Q é a modularidade global da partição (todos os níveis). O <strong>equilíbrio</strong> é a entropia
          normalizada da distribuição de comentários (0 = todos numa comunidade, 1 = repartidos igualmente entre as K
          comunidades). Clique numa linha para inspecionar as comunidades do método.
        </div>
      </section>

      {selected ? (
        <section className="reportDetail">
          <div className="reportSectionLabel">
            Método {selected.id} · {selected.label}
          </div>
          <div className="communityGrid">
            {selected.communities.map((community) => (
              <article className="communityCard" key={community.id}>
                <div className="cardHead">
                  <span className="cardId">Comunidade {community.id}</span>
                  <span className="cardTopic">{formatTopic(community.topic)}</span>
                </div>
                <div className="cardTerms">
                  {community.centralTerms.length > 0 ? (
                    community.centralTerms.map((term) => (
                      <span className="termChip" key={term}>
                        {term}
                      </span>
                    ))
                  ) : (
                    <span className="termEmpty">sem termos centrais</span>
                  )}
                </div>
                <div className="cardMeta">
                  <span className="cardBar">
                    <span
                      className="cardBarFill"
                      style={{ width: `${Math.round((community.comments.length / maxBar) * 100)}%` }}
                    />
                  </span>
                  {community.comments.length} comentário{community.comments.length === 1 ? "" : "s"}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
