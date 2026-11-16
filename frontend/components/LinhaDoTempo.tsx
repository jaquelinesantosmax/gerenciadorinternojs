import type { Evento } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { descreverEvento, eventoDeAlerta } from "@/lib/textos";

/** Linha do tempo no estilo da prévia v3, do mais recente para o mais antigo. */
export function LinhaDoTempo({ eventos, mostrarIp = false }: { eventos: Evento[]; mostrarIp?: boolean }) {
  if (eventos.length === 0) {
    return <p className="legenda">Nenhum evento registrado.</p>;
  }
  return (
    <ol className="trilho" style={{ listStyle: "none", margin: 0 }}>
      {eventos.map((e) => {
        const classe = eventoDeAlerta(e.tipo) ? " destaque" : e.tipo.startsWith("papel_") ? " papel" : "";
        return (
          <li key={e.id} className={`evento${classe}`}>
            <span className="ponto" aria-hidden="true" />
            <span className="legenda" style={{ fontVariantNumeric: "tabular-nums" }}>
              {formatarDataHora(e.ocorrido_em)}
            </span>{" "}
            <span style={{ fontSize: 13, color: eventoDeAlerta(e.tipo) ? "var(--alerta-texto)" : "var(--texto)" }}>
              {descreverEvento(e)}
            </span>
            {mostrarIp && e.ip && <span className="legenda"> · IP {e.ip}</span>}
          </li>
        );
      })}
    </ol>
  );
}
