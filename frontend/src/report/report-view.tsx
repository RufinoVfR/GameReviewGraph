import { useMemo, useState } from "react";
import type { ReportData } from "../data/schemas";

function formatTopic(topic: string | null): string {
  if (!topic) {
    return "sem comentários";
  }
  return topic.charAt(0).toUpperCase() + topic.slice(1);
}

interface ReportViewProps {
  report: ReportData;
  onClose: () => void;
}

export function ReportView({ report, onClose }: ReportViewProps) {
  const bestQ = useMemo(
    () => report.comparison.reduce((max, row) => Math.max(max, row.modularityQ), Number.NEGATIVE_INFINITY),
    [report],
  );
  const [selectedId, setSelectedId] = useState<number>(report.methods[0]?.id ?? 1);
  const selected = report.methods.find((method) => method.id === selectedId) ?? report.methods[0];

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

      <section className="reportMatrix">
        <div className="reportSectionLabel">Matriz comparativa</div>
        <table className="matrixTable">
          <thead>
            <tr>
              <th>Método</th>
              <th>Modularidade Q</th>
              <th>Comunidades</th>
              <th>Tamanhos</th>
              <th>Singletons</th>
            </tr>
          </thead>
          <tbody>
            {report.comparison.map((row) => (
              <tr
                key={row.id}
                className="matrixRow"
                data-active={row.id === selectedId}
                data-best={row.modularityQ === bestQ}
                onClick={() => setSelectedId(row.id)}
              >
                <td className="methodCell">
                  <span className="methodId">{row.id}</span>
                  <span className="methodLabel">{row.label}</span>
                </td>
                <td className="qCell">
                  {row.modularityQ.toFixed(4)}
                  {row.modularityQ === bestQ ? <span className="bestTag">maior Q</span> : null}
                </td>
                <td>{row.nCommunities}</td>
                <td>
                  {row.sizeMin}–{row.sizeMax}
                </td>
                <td>{row.singletons}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="matrixHint">
          Q é a modularidade global da partição. Clique numa linha para inspecionar as comunidades do método.
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
