"use client";

import { IconAlertTriangle, IconChevronLeft, IconChevronRight, IconLock } from "@tabler/icons-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, ErroApi, type Card, type Coluna, type QuadroDetalhe, type StatusWorkflow } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { Avatar } from "./Avatar";
import { Dialogo } from "./Dialogo";
import { EtiquetaPrioridade } from "./EtiquetaStatus";

/** Status para onde o card pode ir ao cair numa coluna: os da coluna que o fluxo permite. */
export function statusPossiveis(card: Card, coluna: Pick<Coluna, "status">, destinos: Record<string, string[]>): StatusWorkflow[] {
  const permitidos = new Set(destinos[card.status_id] ?? []);
  return coluna.status.filter((s) => s.id !== card.status_id && permitidos.has(s.id));
}

function CartaoItem({ card, aoArrastar, mostrarStatus = false }: { card: Card; aoArrastar?: (c: Card) => void; mostrarStatus?: boolean }) {
  const router = useRouter();
  return (
    <div
      className="cartao"
      role="link"
      tabIndex={0}
      draggable={Boolean(aoArrastar)}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", card.chave);
        e.dataTransfer.effectAllowed = "move";
        aoArrastar?.(card);
      }}
      onClick={() => router.push(`/itens/${card.chave}`)}
      onKeyDown={(e) => e.key === "Enter" && router.push(`/itens/${card.chave}`)}
      aria-label={`${card.chave} ${card.resumo}`}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6 }}>
        <span className="legenda">{card.chave}</span>
        {card.bloqueado && <IconLock size={14} stroke={1.5} color="var(--alerta)" aria-label="Bloqueado por outro item" />}
      </div>
      <div style={{ margin: "4px 0 6px", lineHeight: 1.35 }}>{card.resumo}</div>
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
        <span className="etiqueta etiqueta-neutra">{card.tipo}</span>
        <EtiquetaPrioridade prioridade={card.prioridade} />
        {card.painel && <span className="etiqueta etiqueta-neutra">{card.painel}</span>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
        <span className="legenda" style={{ color: card.atrasado ? "var(--alerta)" : undefined, fontVariantNumeric: "tabular-nums" }}>
          {card.atrasado ? "Atrasado · " : ""}
          {formatarData(`${card.data_entrega}T12:00:00Z`)}
        </span>
        {card.responsavel && <Avatar nome={card.responsavel.nome} fotoUrl={card.responsavel.foto_url} tamanho={22} />}
      </div>
      {mostrarStatus && <div className="legenda" style={{ marginTop: 4 }}>{card.status}</div>}
    </div>
  );
}

interface Movimento {
  card: Card;
  coluna: Coluna;
  opcoes: StatusWorkflow[];
  escolhido: string;
}

/** Quadro Kanban ou simples: colunas por status, backlog separado e limite de itens com alerta. */
export function QuadroKanban({ quadroId, podeMover, sprintId }: { quadroId: string; podeMover: boolean; sprintId?: string }) {
  const [quadro, setQuadro] = useState<QuadroDetalhe | null>(null);
  const [arrastando, setArrastando] = useState<Card | null>(null);
  const [sobre, setSobre] = useState<string | null>(null);
  const [movimento, setMovimento] = useState<Movimento | null>(null);
  const [bloqueio, setBloqueio] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [backlogAberto, setBacklogAberto] = useState(true);

  const carregar = useCallback(async () => {
    try {
      setQuadro(await api.quadro(quadroId, sprintId));
    } catch (f) {
      setAviso(f instanceof ErroApi ? f.message : "Não foi possível carregar o quadro.");
    }
  }, [quadroId, sprintId]);

  useEffect(() => {
    setQuadro(null);
    void carregar();
  }, [carregar]);

  function soltar(coluna: Coluna) {
    setSobre(null);
    const card = arrastando;
    setArrastando(null);
    if (!card || !quadro || coluna.status.some((s) => s.id === card.status_id)) return;
    const opcoes = statusPossiveis(card, coluna, quadro.destinos);
    if (opcoes.length === 0) {
      setAviso(`O fluxo não permite levar ${card.chave} de ${card.status} para ${coluna.nome}.`);
      return;
    }
    // Decisão de 16/11: ao arrastar, o sistema pergunta se a pessoa quer mudar o status.
    setAviso(null);
    setMovimento({ card, coluna, opcoes, escolhido: opcoes[0].id });
  }

  async function confirmar(confirmarBloqueio = false) {
    if (!movimento) return;
    setOcupado(true);
    try {
      await api.editarItem(movimento.card.chave, { status_id: movimento.escolhido }, confirmarBloqueio);
      setMovimento(null);
      setBloqueio(null);
      await carregar();
    } catch (f) {
      if (f instanceof ErroApi && f.codigo === "concluir_bloqueado") setBloqueio(f.message);
      else {
        setAviso(f instanceof ErroApi ? f.message : "Não foi possível mover.");
        setMovimento(null);
      }
    } finally {
      setOcupado(false);
    }
  }

  if (!quadro) return <p className="legenda">{aviso ?? "Carregando quadro…"}</p>;
  const nomeEscolhido = movimento?.opcoes.find((o) => o.id === movimento.escolhido)?.nome ?? "";

  return (
    <div>
      {aviso && (
        <p className="caixa-alerta" role="alert" style={{ marginBottom: 10 }}>
          {aviso}
        </p>
      )}
      {quadro.sem_coluna.length > 0 && (
        <p className="legenda" style={{ marginTop: 0 }}>
          <IconAlertTriangle size={13} stroke={1.5} /> {quadro.sem_coluna.length} item(ns) em status sem coluna neste quadro:{" "}
          {quadro.sem_coluna.map((c) => c.chave).join(", ")}. O ADM do espaço pode incluir esses status nas colunas.
        </p>
      )}
      <div className="quadro">
        {quadro.usa_backlog && (
          <section className={`coluna backlog${backlogAberto ? "" : " fechada"}`} aria-label="Backlog">
            <header>
              <button className="botao botao-discreto" onClick={() => setBacklogAberto(!backlogAberto)} aria-label={backlogAberto ? "Recolher backlog" : "Abrir backlog"} style={{ padding: 2 }}>
                {backlogAberto ? <IconChevronLeft size={16} stroke={1.5} /> : <IconChevronRight size={16} stroke={1.5} />}
              </button>
              <span>Backlog</span>
              <span className="contador">{quadro.backlog.length}</span>
            </header>
            {backlogAberto && (
              <div className="cartoes">
                {quadro.backlog.map((c) => (
                  <CartaoItem key={c.chave} card={c} aoArrastar={podeMover ? setArrastando : undefined} />
                ))}
                {quadro.backlog.length === 0 && <p className="legenda">Vazio.</p>}
              </div>
            )}
          </section>
        )}
        {quadro.colunas.map((col) => {
          const pode = arrastando ? statusPossiveis(arrastando, col, quadro.destinos).length > 0 : false;
          return (
            <section
              key={col.id}
              className={`coluna${col.acima_do_limite ? " estourada" : ""}${sobre === col.id ? (pode ? " alvo" : " proibida") : ""}`}
              aria-label={col.nome}
              onDragOver={(e) => {
                if (!arrastando) return;
                e.preventDefault();
                setSobre(col.id);
              }}
              onDragLeave={() => setSobre((atual) => (atual === col.id ? null : atual))}
              onDrop={(e) => {
                e.preventDefault();
                soltar(col);
              }}
            >
              <header title={col.status.map((s) => s.nome).join(", ")}>
                <span>{col.nome}</span>
                <span className="contador" title={col.limite ? `Limite: ${col.limite}` : undefined}>
                  {col.cards.length}
                  {col.limite ? `/${col.limite}` : ""}
                </span>
              </header>
              {col.acima_do_limite && (
                <div className="alerta-limite" role="status">
                  <IconAlertTriangle size={13} stroke={1.5} /> Acima do limite de {col.limite}
                </div>
              )}
              <div className="cartoes">
                {col.cards.map((c) => (
                  <CartaoItem key={c.chave} card={c} mostrarStatus={col.status.length > 1} aoArrastar={podeMover ? setArrastando : undefined} />
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <Dialogo
        aberto={movimento !== null && bloqueio === null}
        titulo={`Mudar o status de ${movimento?.card.chave ?? ""}?`}
        textoConfirmar={`Mudar para ${nomeEscolhido}`}
        ocupado={ocupado}
        aoConfirmar={() => void confirmar()}
        aoCancelar={() => setMovimento(null)}
      >
        {movimento && (
          <>
            <p style={{ margin: "0 0 8px" }}>
              {movimento.card.resumo}: de <b style={{ fontWeight: 500 }}>{movimento.card.status}</b> para
              {movimento.opcoes.length === 1 ? (
                <b style={{ fontWeight: 500 }}> {movimento.opcoes[0].nome}</b>
              ) : (
                " qual status?"
              )}
            </p>
            {movimento.opcoes.length > 1 &&
              movimento.opcoes.map((o) => (
                <label key={o.id} style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                  <input type="radio" name="status-destino" checked={movimento.escolhido === o.id} onChange={() => setMovimento({ ...movimento, escolhido: o.id })} />
                  {o.nome}
                </label>
              ))}
          </>
        )}
      </Dialogo>
      <Dialogo
        aberto={bloqueio !== null}
        titulo="Concluir item bloqueado?"
        textoConfirmar="Concluir mesmo assim"
        perigo
        ocupado={ocupado}
        aoConfirmar={() => void confirmar(true)}
        aoCancelar={() => {
          setBloqueio(null);
          setMovimento(null);
        }}
      >
        {bloqueio} A confirmação fica registrada no histórico.
      </Dialogo>

      <style>{`
        .quadro{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;align-items:flex-start}
        .coluna{background:#e4eaf0;border-radius:12px;padding:8px;min-width:240px;width:240px;flex-shrink:0;border:1px solid transparent}
        .coluna header{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:500;color:var(--texto-2);padding:2px 4px 6px}
        .coluna header span:first-of-type{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .coluna .contador{background:#fff;border-radius:20px;padding:0 7px;font-size:11px;font-variant-numeric:tabular-nums}
        .coluna.estourada{border-color:var(--alerta);background:var(--alerta-fundo)}
        .coluna.estourada .contador{color:var(--alerta);font-weight:600}
        .coluna.alvo{border-color:var(--verde);background:var(--verde-fundo)}
        .coluna.proibida{border-color:var(--borda);opacity:.6}
        .coluna.backlog{background:#f1f4f8;border:1px dashed var(--borda)}
        .coluna.backlog.fechada{min-width:44px;width:44px}
        .coluna.backlog.fechada header span{writing-mode:vertical-rl}
        .alerta-limite{font-size:11px;color:var(--alerta-texto);padding:0 4px 6px;display:flex;gap:4px;align-items:center}
        .cartoes{display:grid;gap:8px;min-height:40px}
        .cartao{background:#fff;border:0.5px solid var(--borda);border-radius:8px;padding:8px 9px;cursor:pointer;font-size:13px}
        .cartao:hover{border-color:var(--verde)}
        .cartao[draggable=true]{cursor:grab}
      `}</style>
    </div>
  );
}
