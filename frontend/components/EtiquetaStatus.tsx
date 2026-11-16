import { PRIORIDADES } from "@/lib/textos";

export function EtiquetaStatus({ nome, categoria }: { nome: string; categoria: string }) {
  return <span className={`etiqueta status-${categoria}`}>{nome}</span>;
}

const COR_PRIORIDADE: Record<string, React.CSSProperties> = {
  critica: { background: "var(--alerta-fundo)", color: "var(--alerta-texto)" },
  alta: { background: "var(--aviso-fundo)", color: "#633806" },
  media: { background: "var(--fundo)", color: "var(--texto-2)" },
  baixa: { background: "var(--fundo)", color: "var(--texto-2)" },
};

export function EtiquetaPrioridade({ prioridade }: { prioridade: string }) {
  return (
    <span className="etiqueta" style={COR_PRIORIDADE[prioridade]}>
      {PRIORIDADES[prioridade] ?? prioridade}
    </span>
  );
}
