"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, ErroApi, type DiaFluxo, type PontoBurndown, type QuadroResumo, type RelatorioSprint, type Sprint, type TempoDeCiclo } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { formatarValor } from "./PlanejamentoScrum";

// Gráficos dos relatórios. Cores validadas (daltonismo e contraste) com o validador de paleta:
// azul #2a78d6, laranja #eb6834 e o verde da marca #007a5f. Linhas de referência em cinza tracejado.
const COR = { azul: "#2a78d6", laranja: "#eb6834", verde: "#007a5f", referencia: "#8a96a3", grade: "#e8edf2", texto: "#383f49" };
const L = 640;
const A = 240;
const M = { topo: 16, dir: 16, base: 30, esq: 44 };
const diaCurto = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const num = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });

/** Escala do eixo vertical. Com inteiro=true (contagem de itens), as marcas são sempre números inteiros. */
export function escalaY(maximo: number, inteiro = false) {
  const topo = maximo <= 0 ? 1 : maximo;
  const passo = Math.pow(10, Math.floor(Math.log10(topo)));
  const teto = inteiro ? Math.max(4, Math.ceil(topo / 4) * 4) : Math.ceil(topo / passo) * passo;
  const marcas = [0, 0.25, 0.5, 0.75, 1].map((f) => +(teto * f).toFixed(2));
  return { teto, marcas, y: (v: number) => M.topo + (A - M.topo - M.base) * (1 - v / teto) };
}

function Eixos({ marcas, y, rotulosX }: { marcas: number[]; y: (v: number) => number; rotulosX: { x: number; texto: string }[] }) {
  return (
    <g fontSize={11} fill={COR.texto}>
      {marcas.map((m) => (
        <g key={m}>
          <line x1={M.esq} x2={L - M.dir} y1={y(m)} y2={y(m)} stroke={COR.grade} />
          <text x={M.esq - 6} y={y(m) + 4} textAnchor="end">
            {num(m)}
          </text>
        </g>
      ))}
      {rotulosX.map((r, i) => (
        <text key={i} x={r.x} y={A - 10} textAnchor="middle">
          {r.texto}
        </text>
      ))}
    </g>
  );
}

function Legenda({ itens }: { itens: { cor: string; nome: string; tracejado?: boolean }[] }) {
  return (
    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: "var(--texto-2)", margin: "4px 0 6px" }}>
      {itens.map((i) => (
        <span key={i.nome} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
          <svg width={18} height={10} aria-hidden="true">
            <line x1={0} x2={18} y1={5} y2={5} stroke={i.cor} strokeWidth={i.tracejado ? 2 : 3} strokeDasharray={i.tracejado ? "4 3" : undefined} strokeLinecap="round" />
          </svg>
          {i.nome}
        </span>
      ))}
    </div>
  );
}

function Dica({ x, y, linhas }: { x: number; y: number; linhas: string[] }) {
  return (
    <div className="dica-grafico" style={{ left: `${(x / L) * 100}%`, top: y }} role="status">
      {linhas.map((l, i) => (
        <div key={i} style={{ fontWeight: i === 0 ? 500 : 400 }}>
          {l}
        </div>
      ))}
    </div>
  );
}

function Tabela({ cabecalho, linhas }: { cabecalho: string[]; linhas: (string | number)[][] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="tabela" style={{ marginTop: 6 }}>
        <thead>
          <tr>
            {cabecalho.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {linhas.map((l, i) => (
            <tr key={i}>
              {l.map((v, j) => (
                <td key={j} style={{ fontVariantNumeric: "tabular-nums" }}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cartao({ titulo, descricao, children, tabela }: { titulo: string; descricao: string; children: React.ReactNode; tabela?: React.ReactNode }) {
  const [verTabela, setVerTabela] = useState(false);
  return (
    <section className="painel" style={{ marginTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        <h3 className="h3" style={{ margin: 0 }}>
          {titulo}
        </h3>
        {tabela && (
          <button className="botao botao-discreto" onClick={() => setVerTabela(!verTabela)}>
            {verTabela ? "Ver gráfico" : "Ver tabela"}
          </button>
        )}
      </div>
      <p className="legenda" style={{ margin: "2px 0 6px" }}>
        {descricao}
      </p>
      {verTabela ? tabela : children}
    </section>
  );
}

/** Burndown: quanto falta, dia a dia, contra a linha ideal. */
export function Burndown({ pontos, unidade }: { pontos: PontoBurndown[]; unidade: string }) {
  const [foco, setFoco] = useState<number | null>(null);
  if (pontos.length === 0) return <p className="legenda">O burndown aparece quando a sprint começa.</p>;
  const valores = pontos.flatMap((p) => [Number(p.ideal), Number(p.restante ?? 0), Number(p.escopo ?? 0)]);
  const { marcas, y } = escalaY(Math.max(...valores), unidade === "itens");
  const x = (i: number) => M.esq + ((L - M.esq - M.dir) * i) / Math.max(pontos.length - 1, 1);
  const reais = pontos.map((p, i) => ({ i, v: p.restante === null ? null : Number(p.restante) })).filter((p) => p.v !== null) as { i: number; v: number }[];
  const passo = Math.ceil(pontos.length / 8);
  const ultimo = reais[reais.length - 1];
  return (
    <div style={{ position: "relative" }} onMouseLeave={() => setFoco(null)}>
      <Legenda itens={[{ cor: COR.verde, nome: "Restante" }, { cor: COR.referencia, nome: "Ideal", tracejado: true }]} />
      <svg viewBox={`0 0 ${L} ${A}`} width="100%" role="img" aria-label="Burndown da sprint">
        <Eixos marcas={marcas} y={y} rotulosX={pontos.map((p, i) => ({ x: x(i), texto: i % passo === 0 ? diaCurto(p.dia) : "" }))} />
        <polyline points={pontos.map((p, i) => `${x(i)},${y(Number(p.ideal))}`).join(" ")} fill="none" stroke={COR.referencia} strokeWidth={2} strokeDasharray="5 4" />
        <polyline points={reais.map((p) => `${x(p.i)},${y(p.v)}`).join(" ")} fill="none" stroke={COR.verde} strokeWidth={2} strokeLinejoin="round" />
        {reais.map((p) => (
          <circle key={p.i} cx={x(p.i)} cy={y(p.v)} r={4} fill={COR.verde} stroke="#fff" strokeWidth={2} />
        ))}
        {ultimo && (
          <text x={x(ultimo.i) + 8} y={y(ultimo.v) - 8} fontSize={11} fill={COR.texto}>
            {formatarValor(ultimo.v, unidade)}
          </text>
        )}
        {foco !== null && <line x1={x(foco)} x2={x(foco)} y1={M.topo} y2={A - M.base} stroke={COR.texto} strokeOpacity={0.3} />}
        {pontos.map((_, i) => (
          <rect key={i} x={x(i) - (L - M.esq - M.dir) / pontos.length / 2} y={M.topo} width={(L - M.esq - M.dir) / pontos.length} height={A - M.topo - M.base} fill="transparent" onMouseEnter={() => setFoco(i)} />
        ))}
      </svg>
      {foco !== null && (
        <Dica
          x={x(foco)}
          y={30}
          linhas={[
            formatarData(`${pontos[foco].dia}T12:00:00Z`),
            `Restante: ${pontos[foco].restante === null ? "—" : formatarValor(pontos[foco].restante, unidade)}`,
            `Ideal: ${formatarValor(pontos[foco].ideal, unidade)}`,
            `Escopo: ${pontos[foco].escopo === null ? "—" : formatarValor(pontos[foco].escopo, unidade)}`,
          ]}
        />
      )}
    </div>
  );
}

/** Velocidade: compromisso no início contra o entregue, por sprint encerrada. */
export function Velocidade({ linhas, unidade }: { linhas: { sprint: string; compromisso: string; entregue: string }[]; unidade: string }) {
  const [foco, setFoco] = useState<number | null>(null);
  if (linhas.length === 0) return <p className="legenda">A velocidade aparece depois da primeira sprint encerrada.</p>;
  const { marcas, y } = escalaY(Math.max(...linhas.flatMap((l) => [Number(l.compromisso), Number(l.entregue)])));
  const grupo = (L - M.esq - M.dir) / linhas.length;
  const barra = Math.min(28, grupo / 3);
  const base = y(0);
  const coluna = (x0: number, v: number, cor: string) => {
    const topo = y(v);
    const h = Math.max(base - topo, 0);
    const r = Math.min(4, h);
    return <path d={`M ${x0} ${base} V ${topo + r} Q ${x0} ${topo} ${x0 + r} ${topo} H ${x0 + barra - r} Q ${x0 + barra} ${topo} ${x0 + barra} ${topo + r} V ${base} Z`} fill={cor} />;
  };
  return (
    <div style={{ position: "relative" }} onMouseLeave={() => setFoco(null)}>
      <Legenda itens={[{ cor: COR.azul, nome: "Compromisso no início" }, { cor: COR.verde, nome: "Entregue" }]} />
      <svg viewBox={`0 0 ${L} ${A}`} width="100%" role="img" aria-label="Velocidade por sprint">
        <Eixos marcas={marcas} y={y} rotulosX={linhas.map((l, i) => ({ x: M.esq + grupo * i + grupo / 2, texto: l.sprint }))} />
        {linhas.map((l, i) => {
          const centro = M.esq + grupo * i + grupo / 2;
          return (
            <g key={l.sprint} onMouseEnter={() => setFoco(i)}>
              <rect x={centro - grupo / 2} y={M.topo} width={grupo} height={A - M.topo - M.base} fill={foco === i ? "#f1f4f8" : "transparent"} />
              {coluna(centro - barra - 1, Number(l.compromisso), COR.azul)}
              {coluna(centro + 1, Number(l.entregue), COR.verde)}
            </g>
          );
        })}
      </svg>
      {foco !== null && (
        <Dica
          x={M.esq + grupo * foco + grupo / 2}
          y={30}
          linhas={[linhas[foco].sprint, `Compromisso: ${formatarValor(linhas[foco].compromisso, unidade)}`, `Entregue: ${formatarValor(linhas[foco].entregue, unidade)}`]}
        />
      )}
    </div>
  );
}

/** Fluxo acumulado: quantos itens em cada categoria, dia a dia (camadas empilhadas). */
export function FluxoAcumulado({ dias }: { dias: DiaFluxo[] }) {
  const [foco, setFoco] = useState<number | null>(null);
  if (dias.length === 0) return null;
  const { marcas, y } = escalaY(Math.max(...dias.map((d) => d.a_fazer + d.em_andamento + d.concluido)), true);
  const x = (i: number) => M.esq + ((L - M.esq - M.dir) * i) / Math.max(dias.length - 1, 1);
  const camadas = [
    { chave: "concluido" as const, nome: "Concluído", cor: COR.verde },
    { chave: "em_andamento" as const, nome: "Em andamento", cor: COR.laranja },
    { chave: "a_fazer" as const, nome: "A fazer", cor: COR.azul },
  ];
  const acumulado = dias.map((d) => {
    let soma = 0;
    return camadas.map((c) => {
      const de = soma;
      soma += d[c.chave];
      return [de, soma];
    });
  });
  const passo = Math.ceil(dias.length / 8);
  return (
    <div style={{ position: "relative" }} onMouseLeave={() => setFoco(null)}>
      <Legenda itens={[...camadas].reverse().map((c) => ({ cor: c.cor, nome: c.nome }))} />
      <svg viewBox={`0 0 ${L} ${A}`} width="100%" role="img" aria-label="Fluxo acumulado">
        <Eixos marcas={marcas} y={y} rotulosX={dias.map((d, i) => ({ x: x(i), texto: i % passo === 0 ? diaCurto(d.dia) : "" }))} />
        {camadas.map((c, k) => {
          const cima = acumulado.map((a, i) => `${x(i)},${y(a[k][1])}`);
          const baixo = acumulado.map((a, i) => `${x(i)},${y(a[k][0])}`).reverse();
          // Uma faixa clara de 2px entre as camadas, para separar as cores.
          return <polygon key={c.chave} points={[...cima, ...baixo].join(" ")} fill={c.cor} fillOpacity={0.85} stroke="#fff" strokeWidth={2} strokeLinejoin="round" />;
        })}
        {foco !== null && <line x1={x(foco)} x2={x(foco)} y1={M.topo} y2={A - M.base} stroke={COR.texto} strokeOpacity={0.4} />}
        {dias.map((_, i) => (
          <rect key={i} x={x(i) - (L - M.esq - M.dir) / dias.length / 2} y={M.topo} width={(L - M.esq - M.dir) / dias.length} height={A - M.topo - M.base} fill="transparent" onMouseEnter={() => setFoco(i)} />
        ))}
      </svg>
      {foco !== null && (
        <Dica
          x={x(foco)}
          y={30}
          linhas={[formatarData(`${dias[foco].dia}T12:00:00Z`), `A fazer: ${dias[foco].a_fazer}`, `Em andamento: ${dias[foco].em_andamento}`, `Concluído: ${dias[foco].concluido}`]}
        />
      )}
    </div>
  );
}

/** Tempo de ciclo: do primeiro "Em andamento" até a conclusão, cada item como um ponto. */
export function TempoCiclo({ dados }: { dados: TempoDeCiclo }) {
  const [foco, setFoco] = useState<number | null>(null);
  if (dados.itens.length === 0) return <p className="legenda">Nenhum item concluído no período (que tenha passado por Em andamento).</p>;
  const { marcas, y } = escalaY(Math.max(...dados.itens.map((i) => i.dias), dados.p85 ?? 0));
  const tempos = dados.itens.map((i) => new Date(i.fim).getTime());
  const t0 = Math.min(...tempos);
  const t1 = Math.max(...tempos);
  const x = (t: number) => M.esq + 10 + ((L - M.esq - M.dir - 20) * (t - t0)) / Math.max(t1 - t0, 1);
  return (
    <div style={{ position: "relative" }} onMouseLeave={() => setFoco(null)}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "4px 0 8px" }}>
        {(
          [
            ["Média", dados.media],
            ["Mediana", dados.mediana],
            ["85% dos itens em até", dados.p85],
          ] as const
        ).map(([rotulo, v]) => (
          <div key={rotulo} className="bloco-numero">
            <div className="legenda">{rotulo}</div>
            <div style={{ fontSize: 22, fontWeight: 600, color: "var(--texto)", fontVariantNumeric: "tabular-nums" }}>{v === null ? "—" : `${num(v)} dias`}</div>
          </div>
        ))}
      </div>
      <svg viewBox={`0 0 ${L} ${A}`} width="100%" role="img" aria-label="Tempo de ciclo por item concluído">
        <Eixos marcas={marcas} y={y} rotulosX={[{ x: x(t0), texto: formatarData(dados.itens[0].fim) }, { x: x(t1), texto: t1 !== t0 ? formatarData(dados.itens[dados.itens.length - 1].fim) : "" }]} />
        {dados.p85 !== null && (
          <g>
            <line x1={M.esq} x2={L - M.dir} y1={y(dados.p85)} y2={y(dados.p85)} stroke={COR.referencia} strokeWidth={1.5} strokeDasharray="5 4" />
            <text x={L - M.dir} y={y(dados.p85) - 5} textAnchor="end" fontSize={11} fill={COR.texto}>
              85%: {num(dados.p85)} dias
            </text>
          </g>
        )}
        {dados.itens.map((it, i) => (
          <circle key={it.chave} cx={x(new Date(it.fim).getTime())} cy={y(it.dias)} r={foco === i ? 7 : 5} fill={COR.verde} stroke="#fff" strokeWidth={2} onMouseEnter={() => setFoco(i)} style={{ cursor: "pointer" }} />
        ))}
      </svg>
      {foco !== null && <Dica x={x(new Date(dados.itens[foco].fim).getTime())} y={60} linhas={[`${dados.itens[foco].chave} ${dados.itens[foco].resumo}`, `${num(dados.itens[foco].dias)} dias`, `Concluído em ${formatarData(dados.itens[foco].fim)}`]} />}
    </div>
  );
}

function ListaRelatorio({ titulo, itens, unidade }: { titulo: string; itens: RelatorioSprint["concluidos"]; unidade: string }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontWeight: 500 }}>
        {titulo} <span className="legenda">· {itens.length} · {formatarValor(itens.reduce((s, i) => s + Number(i.valor), 0), unidade)}</span>
      </div>
      {itens.length === 0 ? (
        <div className="legenda">Nenhum.</div>
      ) : (
        <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
          {itens.map((i) => (
            <li key={i.chave}>
              <Link href={`/itens/${i.chave}`}>{i.chave}</Link> {i.resumo}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Aba Relatórios: Scrum mostra burndown, velocidade e relatório; Kanban e simples mostram fluxo acumulado e tempo de ciclo. */
export function Relatorios({ quadro }: { quadro: QuadroResumo }) {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [sprintId, setSprintId] = useState<string>("");
  const [burndown, setBurndown] = useState<PontoBurndown[]>([]);
  const [relatorio, setRelatorio] = useState<RelatorioSprint | null>(null);
  const [velocidade, setVelocidade] = useState<{ sprint: string; compromisso: string; entregue: string }[]>([]);
  const [periodo, setPeriodo] = useState(30);
  const [fluxo, setFluxo] = useState<DiaFluxo[]>([]);
  const [ciclo, setCiclo] = useState<TempoDeCiclo | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const scrum = quadro.tipo === "scrum";
  const unidade = quadro.unidade_estimativa;

  useEffect(() => {
    const falhou = (f: unknown) => setErro(f instanceof ErroApi ? f.message : "Não foi possível carregar.");
    if (scrum) {
      api
        .sprints(quadro.id)
        .then((lista) => {
          const comDados = lista.filter((s) => s.estado !== "planejada");
          setSprints(comDados);
          setSprintId((atual) => atual || comDados[0]?.id || "");
        })
        .catch(falhou);
      api.velocidade(quadro.id).then(setVelocidade).catch(falhou);
    }
    api.fluxoAcumulado(quadro.id, periodo).then(setFluxo).catch(falhou);
    api.tempoDeCiclo(quadro.id, periodo * 3).then(setCiclo).catch(falhou);
  }, [quadro.id, scrum, periodo]);

  useEffect(() => {
    if (!sprintId) return;
    api.burndown(sprintId).then(setBurndown).catch(() => setBurndown([]));
    api.relatorioSprint(sprintId).then(setRelatorio).catch(() => setRelatorio(null));
  }, [sprintId]);

  const sprintAtual = useMemo(() => sprints.find((s) => s.id === sprintId), [sprints, sprintId]);
  if (erro) return <p className="mensagem-erro">{erro}</p>;

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
        {scrum && (
          <div>
            <label className="rotulo" htmlFor="rel-sprint">
              Sprint
            </label>
            <select id="rel-sprint" className="campo" style={{ width: 220 }} value={sprintId} onChange={(e) => setSprintId(e.target.value)}>
              {sprints.length === 0 && <option value="">Nenhuma sprint iniciada</option>}
              {sprints.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome} ({s.estado === "ativa" ? "ativa" : "encerrada"})
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="rotulo" htmlFor="rel-periodo">
            Período do fluxo
          </label>
          <select id="rel-periodo" className="campo" style={{ width: 160 }} value={periodo} onChange={(e) => setPeriodo(Number(e.target.value))}>
            <option value={14}>Últimos 14 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
          </select>
        </div>
      </div>

      {scrum && (
        <>
          <Cartao
            titulo={`Burndown${sprintAtual ? ` · ${sprintAtual.nome}` : ""}`}
            descricao="Quanto ainda falta, dia a dia. Quando a linha sobe, entrou escopo depois do início."
            tabela={<Tabela cabecalho={["Dia", "Restante", "Ideal", "Escopo"]} linhas={burndown.map((p) => [formatarData(`${p.dia}T12:00:00Z`), p.restante === null ? "—" : num(Number(p.restante)), num(Number(p.ideal)), p.escopo === null ? "—" : num(Number(p.escopo))])} />}
          >
            <Burndown pontos={burndown} unidade={unidade} />
          </Cartao>
          <Cartao
            titulo="Velocidade"
            descricao="O que foi assumido no início de cada sprint e o que foi entregue, nas últimas sprints encerradas."
            tabela={<Tabela cabecalho={["Sprint", "Compromisso", "Entregue"]} linhas={velocidade.map((v) => [v.sprint, num(Number(v.compromisso)), num(Number(v.entregue))])} />}
          >
            <Velocidade linhas={velocidade} unidade={unidade} />
          </Cartao>
          {relatorio && (
            <Cartao titulo={`Relatório da ${relatorio.sprint.nome}`} descricao="Itens concluídos, não concluídos, que entraram depois do início e que saíram da sprint.">
              <ListaRelatorio titulo="Concluídos" itens={relatorio.concluidos} unidade={unidade} />
              <ListaRelatorio titulo="Não concluídos" itens={relatorio.nao_concluidos} unidade={unidade} />
              <ListaRelatorio titulo="Entraram depois do início" itens={relatorio.adicionados_depois} unidade={unidade} />
              <ListaRelatorio titulo="Saíram da sprint" itens={relatorio.removidos} unidade={unidade} />
            </Cartao>
          )}
        </>
      )}

      <Cartao
        titulo="Fluxo acumulado"
        descricao="Quantos itens estavam em cada categoria, dia a dia. Faixa do meio engordando é sinal de trabalho parado."
        tabela={<Tabela cabecalho={["Dia", "A fazer", "Em andamento", "Concluído"]} linhas={fluxo.map((d) => [formatarData(`${d.dia}T12:00:00Z`), d.a_fazer, d.em_andamento, d.concluido])} />}
      >
        <FluxoAcumulado dias={fluxo} />
      </Cartao>
      {ciclo && (
        <Cartao
          titulo="Tempo de ciclo"
          descricao={`Dias entre o primeiro "Em andamento" e a conclusão, para itens concluídos nos últimos ${periodo * 3} dias.`}
          tabela={<Tabela cabecalho={["Item", "Resumo", "Dias", "Concluído em"]} linhas={ciclo.itens.map((i) => [i.chave, i.resumo, num(i.dias), formatarData(i.fim)])} />}
        >
          <TempoCiclo dados={ciclo} />
        </Cartao>
      )}
      <style>{`
        .dica-grafico{position:absolute;transform:translateX(-50%);background:#fff;border:0.5px solid var(--borda);border-radius:8px;padding:6px 9px;font-size:12px;pointer-events:none;white-space:nowrap;color:var(--texto)}
        .bloco-numero{border:0.5px solid var(--borda);border-radius:8px;padding:8px 12px;min-width:150px}
      `}</style>
    </div>
  );
}
