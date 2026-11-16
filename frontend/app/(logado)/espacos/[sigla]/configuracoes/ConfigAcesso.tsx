"use client";

import { IconTrash } from "@tabler/icons-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { BuscaPessoa } from "@/components/BuscaPessoa";
import { Dialogo } from "@/components/Dialogo";
import { api, ErroApi, type AcessoTime, type GestorAcompanha, type PedidoAcesso, type Pessoa, type TimeItem } from "@/lib/api";
import { formatarData, formatarDataHora } from "@/lib/formato";
import { NOME_PAPEL_ESPACO } from "@/lib/textos";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);
const PAPEIS = ["adm", "membro", "leitor"];

function useExecutar(aoMudar: () => Promise<void> | void) {
  const [erro, setErro] = useState<string | null>(null);
  const executar = async (acao: () => Promise<unknown>) => {
    setErro(null);
    try {
      await acao();
      await aoMudar();
      return true;
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
      return false;
    }
  };
  const mensagem = erro ? (
    <p className="mensagem-erro" role="alert">
      {erro}
    </p>
  ) : null;
  return { executar, mensagem };
}

/** Times que têm acesso ao espaço. Quem entra no time ganha o acesso; vale o maior papel da pessoa. */
export function TimesComAcesso({ sigla }: { sigla: string }) {
  const [lista, setLista] = useState<AcessoTime[]>([]);
  const [times, setTimes] = useState<TimeItem[]>([]);
  const [novo, setNovo] = useState({ time_id: "", papel: "" });
  const [tirar, setTirar] = useState<AcessoTime | null>(null);
  const carregar = useCallback(async () => {
    setLista(await api.timesComAcesso(sigla));
    setTimes(await api.times());
  }, [sigla]);
  const { executar, mensagem } = useExecutar(carregar);

  useEffect(() => {
    void carregar().catch(() => undefined);
  }, [carregar]);

  const comAcesso = new Set(lista.map((a) => a.time_id));
  const disponiveis = times.filter((t) => !comAcesso.has(t.id));
  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {lista.map((a) => (
          <li key={a.time_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--borda)" }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500 }}>{a.nome}</div>
              <div className="legenda">{a.membros === 1 ? "1 pessoa" : `${a.membros} pessoas`}</div>
            </div>
            <select className="campo" style={{ width: 160 }} aria-label={`Papel do time ${a.nome}`} value={a.papel} onChange={(e) => void executar(() => api.mudarAcessoTime(sigla, a.time_id, e.target.value))}>
              {PAPEIS.map((p) => (
                <option key={p} value={p}>
                  {NOME_PAPEL_ESPACO[p]}
                </option>
              ))}
            </select>
            <button className="botao botao-discreto" aria-label={`Tirar o acesso do time ${a.nome}`} onClick={() => setTirar(a)}>
              <IconTrash size={14} stroke={1.5} />
            </button>
          </li>
        ))}
        {lista.length === 0 && <li className="legenda">Nenhum time tem acesso a este espaço.</li>}
      </ul>
      <form
        style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "flex-end", flexWrap: "wrap" }}
        onSubmit={async (e) => {
          e.preventDefault();
          if (await executar(() => api.darAcessoTime(sigla, novo.time_id, novo.papel))) setNovo({ time_id: "", papel: "" });
        }}
      >
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="rotulo" htmlFor="time-acesso">
            Dar acesso a um time
          </label>
          <select id="time-acesso" className="campo" value={novo.time_id} onChange={(e) => setNovo({ ...novo, time_id: e.target.value })}>
            <option value="">Escolha o time</option>
            {disponiveis.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="rotulo" htmlFor="papel-time">
            Como
          </label>
          <select id="papel-time" className="campo" value={novo.papel} onChange={(e) => setNovo({ ...novo, papel: e.target.value })}>
            <option value="">Escolha o papel</option>
            {PAPEIS.map((p) => (
              <option key={p} value={p}>
                {NOME_PAPEL_ESPACO[p]}
              </option>
            ))}
          </select>
        </div>
        <button className="botao botao-acao" type="submit" disabled={!novo.time_id || !novo.papel}>
          Dar acesso
        </button>
      </form>
      <p className="legenda" style={{ margin: "6px 0 0" }}>
        Os times são cadastrados na página <Link href="/times">Times</Link>. Se a pessoa também tiver papel individual, vale o maior.
      </p>
      {mensagem}
      <Dialogo
        aberto={tirar !== null}
        titulo={`Tirar o acesso do time ${tirar?.nome ?? ""}?`}
        textoConfirmar="Tirar o acesso"
        perigo
        aoConfirmar={async () => {
          if (tirar) await executar(() => api.tirarAcessoTime(sigla, tirar.time_id));
          setTirar(null);
        }}
        aoCancelar={() => setTirar(null)}
      >
        Quem só tinha acesso por este time perde o acesso na hora. A mudança fica registrada na auditoria.
      </Dialogo>
    </div>
  );
}

/** Pedidos de acesso pendentes. Ao aprovar, o ADM escolhe o papel (nada vem marcado). */
export function PedidosDeAcesso({ sigla, aoMudar }: { sigla: string; aoMudar: () => Promise<void> }) {
  const [lista, setLista] = useState<PedidoAcesso[]>([]);
  const [papeis, setPapeis] = useState<Record<string, string>>({});
  const carregar = useCallback(async () => setLista(await api.pedidosAcesso(sigla)), [sigla]);
  const { executar, mensagem } = useExecutar(async () => {
    await carregar();
    await aoMudar();
  });

  useEffect(() => {
    void carregar().catch(() => undefined);
  }, [carregar]);

  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {lista.map((p) => (
          <li key={p.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--borda)", flexWrap: "wrap" }}>
            <Avatar nome={p.pessoa.nome} fotoUrl={p.pessoa.foto_url} />
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontWeight: 500 }}>{p.pessoa.nome}</div>
              <div className="legenda">
                {p.pessoa.email} · {formatarDataHora(p.criado_em)}
                {p.item_chave && ` · pelo item ${p.item_chave}`}
              </div>
              {p.mensagem && <div style={{ marginTop: 2 }}>“{p.mensagem}”</div>}
            </div>
            <select className="campo" style={{ width: 160 }} aria-label={`Papel para ${p.pessoa.nome}`} value={papeis[p.id] ?? ""} onChange={(e) => setPapeis({ ...papeis, [p.id]: e.target.value })}>
              <option value="">Escolha o papel</option>
              {PAPEIS.map((papel) => (
                <option key={papel} value={papel}>
                  {NOME_PAPEL_ESPACO[papel]}
                </option>
              ))}
            </select>
            <button className="botao botao-acao" disabled={!papeis[p.id]} onClick={() => void executar(() => api.aprovarPedido(sigla, p.id, papeis[p.id]))}>
              Aprovar
            </button>
            <button className="botao" onClick={() => void executar(() => api.recusarPedido(sigla, p.id))}>
              Recusar
            </button>
          </li>
        ))}
        {lista.length === 0 && <li className="legenda">Nenhum pedido esperando resposta.</li>}
      </ul>
      {mensagem}
    </div>
  );
}

/** Espaço aberto: qualquer pessoa da empresa vê, comenta e anexa (sem criar nem editar itens). */
export function EspacoAberto({ sigla, aberto, aoMudar }: { sigla: string; aberto: boolean; aoMudar: () => Promise<void> }) {
  const [confirmar, setConfirmar] = useState(false);
  const { executar, mensagem } = useExecutar(aoMudar);
  return (
    <div>
      <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
        <input type="checkbox" checked={aberto} onChange={() => (aberto ? void executar(() => api.marcarAberto(sigla, false)) : setConfirmar(true))} />
        Aberto para toda a empresa
      </label>
      {mensagem}
      <Dialogo
        aberto={confirmar}
        titulo="Abrir o espaço para toda a empresa?"
        textoConfirmar="Abrir"
        aoConfirmar={async () => {
          await executar(() => api.marcarAberto(sigla, true));
          setConfirmar(false);
        }}
        aoCancelar={() => setConfirmar(false)}
      >
        Qualquer pessoa com acesso ao Gerenciador poderá ver os itens, comentar e anexar arquivos. Só os membros criam e editam itens.
      </Dialogo>
    </div>
  );
}

/** Gestores que acompanham o espaço (visível para o ADM e os Membros). */
export function GestoresQueAcompanham({ sigla }: { sigla: string }) {
  const [lista, setLista] = useState<GestorAcompanha[] | null>(null);
  useEffect(() => {
    api.gestoresDoEspaco(sigla).then(setLista).catch(() => setLista([]));
  }, [sigla]);
  if (!lista) return null;
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {lista.map((g) => (
        <li key={g.pessoa.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}>
          <Avatar nome={g.pessoa.nome} fotoUrl={g.pessoa.foto_url} />
          <span style={{ flex: 1 }}>{g.pessoa.nome}</span>
          <span className="legenda">desde {formatarData(g.desde)}</span>
        </li>
      ))}
      {lista.length === 0 && <li className="legenda">Nenhum Gestor acompanha este espaço.</li>}
    </ul>
  );
}

/** Compartilhamento do espaço pessoal: as pessoas escolhidas só veem (não comentam nem editam). */
export function Compartilhar({ sigla }: { sigla: string }) {
  const [lista, setLista] = useState<Pessoa[]>([]);
  const carregar = useCallback(async () => setLista(await api.compartilhamentos(sigla)), [sigla]);
  const { executar, mensagem } = useExecutar(carregar);
  useEffect(() => {
    void carregar().catch(() => undefined);
  }, [carregar]);
  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {lista.map((p) => (
          <li key={p.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--borda)" }}>
            <Avatar nome={p.nome} fotoUrl={p.foto_url} />
            <div style={{ flex: 1 }}>
              <div>{p.nome}</div>
              <div className="legenda">{p.email}</div>
            </div>
            <button className="botao botao-discreto" aria-label={`Parar de compartilhar com ${p.nome}`} onClick={() => void executar(() => api.descompartilhar(sigla, p.id))}>
              <IconTrash size={14} stroke={1.5} />
            </button>
          </li>
        ))}
        {lista.length === 0 && <li className="legenda">Ninguém além de você vê este espaço.</li>}
      </ul>
      <div style={{ marginTop: 12 }}>
        <BuscaPessoa
          rotulo="Compartilhar com"
          jaEscolhidas={new Set(lista.map((p) => p.id))}
          textoJaEscolhida="já vê"
          aoEscolher={(p) => void executar(() => api.compartilhar(sigla, p.id))}
        />
      </div>
      {mensagem}
    </div>
  );
}
