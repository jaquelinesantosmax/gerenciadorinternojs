"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api, ErroApi, type BarraGantt } from "@/lib/api";
import { formatarData } from "@/lib/formato";

const DIA = 86_400_000;
const ALTURA = 34;
const LARGURA_NOMES = 280;

const dia = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const hojeBrasilia = () => {
  const agora = new Date(Date.now() - 3 * 3600 * 1000);
  return Date.UTC(agora.getUTCFullYear(), agora.getUTCMonth(), agora.getUTCDate());
};

/** Ordena com cada filho logo abaixo do pai (Épico > item > subtarefa). */
export function ordenarHierarquia(barras: BarraGantt[]): (BarraGantt & { nivelVisual: number })[] {
  const chaves = new Set(barras.map((b) => b.chave));
  const filhos = new Map<string, BarraGantt[]>();
  barras.forEach((b) => {
    const pai = b.pai && chaves.has(b.pai) ? b.pai : "";
    filhos.set(pai, [...(filhos.get(pai) ?? []), b]);
  });
  const resultado: (BarraGantt & { nivelVisual: number })[] = [];
  const visitar = (pai: string, nivel: number) => {
    for (const b of filhos.get(pai) ?? []) {
      resultado.push({ ...b, nivelVisual: nivel });
      visitar(b.chave, nivel + 1);
    }
  };
  visitar("", 0);
  return resultado;
}

const COR: Record<string, string> = { a_fazer: "#9aa8b5", em_andamento: "#007a5f", concluido: "#bfe0d5" };

/** Gantt do espaço ou painel, com setas de dependência para os vínculos "bloqueia". */
export function Gantt({ sigla, painelId }: { sigla: string; painelId?: string }) {
  const router = useRouter();
  const [dados, setDados] = useState<{ barras: BarraGantt[]; bloqueios: [string, string][] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [escala, setEscala] = useState<"semana" | "mes">("semana");
  const pxDia = escala === "semana" ? 28 : 9;

  useEffect(() => {
    api
      .gantt(sigla, painelId)
      .then(setDados)
      .catch((f) => setErro(f instanceof ErroApi ? f.message : "Não foi possível carregar o Gantt."));
  }, [sigla, painelId]);

  const linhas = useMemo(() => ordenarHierarquia(dados?.barras ?? []), [dados]);
  if (erro) return <p className="mensagem-erro">{erro}</p>;
  if (!dados) return <p className="legenda">Carregando Gantt…</p>;
  if (linhas.length === 0) return <p className="legenda">Nenhum item para mostrar.</p>;

  const hoje = hojeBrasilia();
  const fins = linhas.map((b) => Math.max(dia(b.entrega), b.entrega_real ? dia(b.entrega_real) : 0));
  const inicio = Math.min(...linhas.map((b) => dia(b.inicio)), hoje) - 3 * DIA;
  const fim = Math.max(...fins, hoje) + 7 * DIA;
  const dias = Math.round((fim - inicio) / DIA) + 1;
  const x = (t: number) => ((t - inicio) / DIA) * pxDia;
  const largura = dias * pxDia;
  const posicao = new Map(linhas.map((b, i) => [b.chave, i]));

  // Marcas da régua: segundas-feiras (semana) ou dia 1 de cada mês (mês).
  const marcas: { t: number; rotulo: string }[] = [];
  for (let t = inicio; t <= fim; t += DIA) {
    const d = new Date(t);
    if (escala === "semana" ? d.getUTCDay() === 1 : d.getUTCDate() === 1) {
      marcas.push({
        t,
        rotulo: escala === "semana" ? `${String(d.getUTCDate()).padStart(2, "0")}/${String(d.getUTCMonth() + 1).padStart(2, "0")}` : d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit", timeZone: "UTC" }),
      });
    }
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 8 }}>
        <span className="legenda">Escala:</span>
        {(["semana", "mes"] as const).map((e) => (
          <button key={e} className={`aba-pequena${escala === e ? " ativa" : ""}`} onClick={() => setEscala(e)} aria-pressed={escala === e}>
            {e === "semana" ? "Semanas" : "Meses"}
          </button>
        ))}
        <span className="legenda" style={{ marginLeft: "auto" }}>
          Setas: vínculos &quot;bloqueia&quot;. Linha verde: hoje.
        </span>
      </div>
      <div className="gantt">
        <div className="gantt-nomes" style={{ width: LARGURA_NOMES }}>
          <div className="gantt-cabecalho" />
          {linhas.map((b) => (
            <button key={b.chave} className="gantt-nome" style={{ paddingLeft: 8 + b.nivelVisual * 16, height: ALTURA }} onClick={() => router.push(`/itens/${b.chave}`)} title={`${b.chave} ${b.resumo}`}>
              <span className="legenda">{b.chave}</span> <span style={{ fontWeight: b.nivel === "epico" ? 600 : 400 }}>{b.resumo}</span>
            </button>
          ))}
        </div>
        <div className="gantt-linha-tempo">
          <div style={{ width: largura, position: "relative" }}>
            <div className="gantt-cabecalho" style={{ position: "relative" }}>
              {marcas.map((m) => (
                <span key={m.t} className="gantt-marca" style={{ left: x(m.t) }}>
                  {m.rotulo}
                </span>
              ))}
            </div>
            <svg width={largura} height={linhas.length * ALTURA} style={{ display: "block" }} role="img" aria-label="Linha do tempo dos itens">
              {marcas.map((m) => (
                <line key={m.t} x1={x(m.t)} x2={x(m.t)} y1={0} y2={linhas.length * ALTURA} stroke="#e4eaf0" />
              ))}
              {linhas.map((_, i) => (
                <line key={i} x1={0} x2={largura} y1={(i + 1) * ALTURA} y2={(i + 1) * ALTURA} stroke="#f1f4f8" />
              ))}
              <line x1={x(hoje) + pxDia / 2} x2={x(hoje) + pxDia / 2} y1={0} y2={linhas.length * ALTURA} stroke="#63b424" strokeWidth={1.5} />
              <defs>
                <marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#a32d2d" />
                </marker>
              </defs>
              {dados.bloqueios.map(([de, para]) => {
                const i = posicao.get(de);
                const j = posicao.get(para);
                if (i === undefined || j === undefined) return null;
                const a = linhas[i];
                const b = linhas[j];
                const x1 = x(dia(a.entrega)) + pxDia;
                const y1 = i * ALTURA + ALTURA / 2;
                const x2 = x(dia(b.inicio));
                const y2 = j * ALTURA + ALTURA / 2;
                // Se o bloqueado começa depois do fim de quem bloqueia, a seta desce no meio do caminho;
                // se começa antes, ela contorna por cima da barra do bloqueado.
                const caminho =
                  x2 - x1 > 20
                    ? `M ${x1} ${y1} H ${(x1 + x2) / 2} V ${y2} H ${x2}`
                    : `M ${x1} ${y1} h 10 V ${y2 + (y2 > y1 ? -ALTURA / 2 : ALTURA / 2)} H ${x2 - 10} V ${y2} H ${x2}`;
                return <path key={`${de}-${para}`} d={caminho} fill="none" stroke="#a32d2d" strokeWidth={1.2} markerEnd="url(#seta)" />;
              })}
              {linhas.map((b, i) => {
                const x0 = x(dia(b.inicio));
                const w = Math.max(x(dia(b.entrega)) + pxDia - x0, 4);
                const y = i * ALTURA + (b.nivel === "epico" ? 12 : 8);
                const h = b.nivel === "epico" ? 10 : 18;
                const atrasado = b.status_categoria !== "concluido" && dia(b.entrega) < hoje;
                return (
                  <g key={b.chave} style={{ cursor: "pointer" }} onClick={() => router.push(`/itens/${b.chave}`)}>
                    <title>{`${b.chave} ${b.resumo}\n${b.status} · ${formatarData(`${b.inicio}T12:00:00Z`)} a ${formatarData(`${b.entrega}T12:00:00Z`)}${b.responsavel ? ` · ${b.responsavel}` : ""}`}</title>
                    <rect x={x0} y={y} width={w} height={h} rx={b.nivel === "epico" ? 3 : 5} fill={b.nivel === "epico" ? "#004d3b" : COR[b.status_categoria] ?? "#9aa8b5"} stroke={atrasado ? "#a32d2d" : "none"} strokeWidth={1.5} />
                    {b.entrega_real && <circle cx={x(dia(b.entrega_real)) + pxDia / 2} cy={y + h / 2} r={3.5} fill="#fff" stroke="#101729" />}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>
      <p className="legenda" style={{ marginTop: 6 }}>
        Barras: início até a data de entrega. Contorno vermelho: atrasado. Bolinha: data real da entrega. Cinza: a fazer · verde: em andamento · verde-claro: concluído.
      </p>
      <style>{`
        .gantt{display:flex;border:0.5px solid var(--borda);border-radius:12px;background:#fff;overflow:hidden}
        .gantt-nomes{flex-shrink:0;border-right:0.5px solid var(--borda)}
        .gantt-cabecalho{height:28px;border-bottom:0.5px solid var(--borda);background:var(--fundo)}
        .gantt-nome{display:flex;gap:6px;align-items:center;width:100%;border:none;background:none;text-align:left;font-size:13px;cursor:pointer;border-bottom:0.5px solid #f1f4f8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .gantt-nome:hover{background:var(--verde-fundo)}
        .gantt-nome span:last-child{overflow:hidden;text-overflow:ellipsis}
        .gantt-linha-tempo{overflow-x:auto;flex:1}
        .gantt-marca{position:absolute;top:7px;font-size:11px;color:var(--texto-2);padding-left:3px;white-space:nowrap}
        .aba-pequena{border:0.5px solid var(--borda);background:#fff;border-radius:20px;padding:3px 10px;font-size:12px;cursor:pointer}
        .aba-pequena.ativa{background:var(--verde-fundo);border-color:var(--verde);color:var(--verde-escuro)}
      `}</style>
    </div>
  );
}
