"use client";

import { IconCopy, IconPencil, IconTrash } from "@tabler/icons-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { textoDoCampo } from "@/components/CampoPersonalizado";
import { Dialogo } from "@/components/Dialogo";
import { Editor, paraEditar } from "@/components/Editor";
import { EtiquetaPrioridade, EtiquetaStatus } from "@/components/EtiquetaStatus";
import { FormularioItem } from "@/components/FormularioItem";
import { TextoRico } from "@/components/TextoRico";
import { api, ErroApi, type DocTexto, type EspacoDetalhe, type ItemDetalhe, type OpcoesItem } from "@/lib/api";
import { formatarData, formatarDataHora } from "@/lib/formato";
import { Anexos } from "./Anexos";
import { Atividade } from "./Atividade";
import { Vinculos } from "./Vinculos";

const data = (d: string | null) => (d ? formatarData(`${d}T12:00:00Z`) : "—");

/** Ficha do item no estilo da prévia v3: faixa lateral escura com o essencial e a folha com o restante. */
export default function PaginaItem() {
  const { chave } = useParams<{ chave: string }>();
  const router = useRouter();
  const [item, setItem] = useState<ItemDetalhe | null>(null);
  const [espaco, setEspaco] = useState<EspacoDetalhe | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesItem | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [editandoCampos, setEditandoCampos] = useState(false);
  const [editandoDescricao, setEditandoDescricao] = useState(false);
  const [descricao, setDescricao] = useState<DocTexto | null>(null);
  const [confirmacao, setConfirmacao] = useState<{ mensagem: string; dados: Record<string, unknown> } | null>(null);
  const [excluindo, setExcluindo] = useState(false);
  const [clonando, setClonando] = useState<{ copiar_comentarios: boolean; copiar_anexos: boolean } | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    try {
      const atual = await api.item(chave);
      setItem(atual);
      if (atual.chave !== chave.toUpperCase()) router.replace(`/itens/${atual.chave}`);
      return atual;
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível carregar.");
      return null;
    }
  }, [chave, router]);

  useEffect(() => {
    setItem(null);
    setErro(null);
    void recarregar().then((atual) => {
      if (!atual) return;
      api.espaco(atual.espaco_sigla).then(setEspaco).catch(() => undefined);
      api.opcoesItem(atual.espaco_sigla).then(setOpcoes).catch(() => undefined);
    });
  }, [recarregar]);

  const imagens = useMemo(() => Object.fromEntries((item?.anexos ?? []).map((a) => [a.id, a.link])), [item?.anexos]);

  const enviarImagem = useCallback(
    async (arquivo: File) => {
      try {
        const [anexo] = await api.enviarAnexos(chave, [arquivo]);
        void recarregar();
        return anexo ? { id: anexo.id, link: anexo.link } : null;
      } catch (falha) {
        setMensagem(falha instanceof ErroApi ? falha.message : "Não foi possível enviar a imagem.");
        return null;
      }
    },
    [chave, recarregar],
  );

  async function salvar(dados: Record<string, unknown>, confirmar = false) {
    try {
      setItem(await api.editarItem(chave, dados, confirmar));
      setConfirmacao(null);
      setMensagem(null);
      return true;
    } catch (falha) {
      if (falha instanceof ErroApi && falha.codigo === "concluir_bloqueado") {
        setConfirmacao({ mensagem: falha.message, dados });
        return false;
      }
      throw falha;
    }
  }

  if (erro) return <p className="mensagem-erro">{erro}</p>;
  if (!item) return <p className="legenda">Carregando…</p>;

  const p = item.permissoes;
  const campos = (opcoes?.campos ?? []).filter((c) => c.tipos_item.includes(item.tipo.id));
  const pessoas = opcoes?.membros ?? [];
  const faixa: [string, React.ReactNode][] = [
    ["Responsável", item.responsavel?.nome ?? "—"],
    ["Prioridade", <EtiquetaPrioridade key="p" prioridade={item.prioridade} />],
    ["Time", item.time.nome],
    ["Início", data(item.data_inicio)],
    ["Entrega", data(item.data_entrega)],
    ...(item.painel ? ([["Painel", item.painel.nome]] as [string, React.ReactNode][]) : []),
    ["Relator", item.relator?.nome ?? "—"],
  ];
  const detalhes: [string, React.ReactNode][] = [
    ["Tipo", item.tipo.nome],
    ["Co-responsáveis", item.co_responsaveis.map((c) => c.nome).join(", ") || "—"],
    ["Categorias", item.categorias.length ? item.categorias.map((c) => <span key={c} className="etiqueta etiqueta-neutra" style={{ marginRight: 4 }}>{c}</span>) : "—"],
    ["Origem da solicitação", item.origem?.nome ?? "—"],
    ["Estimativa", item.estimativa ? `${Number(item.estimativa).toLocaleString("pt-BR")} pontos` : "—"],
    ["Data real da entrega", data(item.data_real_entrega)],
    ...(item.justificativa_atraso ? ([["Justificativa do atraso", item.justificativa_atraso]] as [string, React.ReactNode][]) : []),
    ...campos.map((c) => [c.nome, textoDoCampo(c, item.valores[c.id], pessoas) ?? "—"] as [string, React.ReactNode]),
  ];

  return (
    <>
      <nav className="legenda" aria-label="Caminho" style={{ marginBottom: 10 }}>
        <Link href={`/espacos/${item.espaco_sigla}`}>{item.espaco.nome}</Link>
        {item.pai && (
          <>
            {" › "}
            <Link href={`/itens/${item.pai.chave}`}>
              {item.pai.chave} {item.pai.resumo}
            </Link>
          </>
        )}
      </nav>
      <article className="ficha-item">
        <aside className="faixa-item">
          <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.5px" }}>{item.chave}</div>
          <div style={{ fontSize: 12, fontWeight: 300, color: "var(--verde-claro)" }}>{item.espaco.nome}</div>
          <label className="rotulo-faixa" htmlFor="status-item">
            Status
          </label>
          {p.editar_itens && espaco ? (
            <select
              id="status-item"
              className="seletor-status"
              value={item.status.id}
              onChange={(e) => void salvar({ status_id: e.target.value }).catch((f) => setMensagem(f instanceof ErroApi ? f.message : "Não foi possível mudar o status."))}
            >
              {espaco.status.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
          ) : (
            <div style={{ marginTop: 4 }}>
              <span className="etiqueta" style={{ background: "#fff", color: "var(--verde-escuro)" }}>
                {item.status.nome}
              </span>
            </div>
          )}
          {faixa.map(([rotulo, valor]) => (
            <div key={rotulo}>
              <div className="rotulo-faixa">{rotulo}</div>
              <div className="valor-faixa">{valor}</div>
            </div>
          ))}
          <div className="acoes-faixa">
            {p.editar_itens && (
              <button className="botao-faixa" onClick={() => setEditandoCampos(true)} disabled={!espaco || !opcoes}>
                <IconPencil size={14} stroke={1.5} /> Editar campos
              </button>
            )}
            {p.criar_itens && (
              <button className="botao-faixa" onClick={() => setClonando({ copiar_comentarios: false, copiar_anexos: false })}>
                <IconCopy size={14} stroke={1.5} /> Clonar
              </button>
            )}
            {item.pode_excluir && (
              <button className="botao-faixa" onClick={() => setExcluindo(true)}>
                <IconTrash size={14} stroke={1.5} /> Excluir
              </button>
            )}
          </div>
        </aside>

        <div className="folha-item">
          <h1 className="h1" style={{ lineHeight: 1.25 }}>
            {item.resumo}
          </h1>
          <div className="legenda" style={{ marginTop: 4 }}>
            {item.tipo.nome} criado por {item.relator?.nome ?? "—"} em {formatarDataHora(item.criado_em)}
            {item.atualizado_em !== item.criado_em && ` · atualizado em ${formatarDataHora(item.atualizado_em)}`}
          </div>
          {mensagem && (
            <p className="mensagem-erro" role="alert">
              {mensagem}
            </p>
          )}

          <section aria-labelledby="titulo-descricao" style={{ marginTop: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 id="titulo-descricao" className="h3">
                Descrição
              </h2>
              {p.editar_itens && !editandoDescricao && (
                <button
                  className="botao botao-discreto"
                  onClick={() => {
                    setDescricao(item.descricao);
                    setEditandoDescricao(true);
                  }}
                >
                  <IconPencil size={14} stroke={1.5} /> Editar
                </button>
              )}
            </div>
            {editandoDescricao ? (
              <div style={{ marginTop: 6 }}>
                <Editor rotulo="Descrição" valor={paraEditar(item.descricao, imagens)} aoMudar={setDescricao} pessoas={pessoas} aoEnviarImagem={enviarImagem} autoFoco />
                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 6 }}>
                  <button className="botao" onClick={() => setEditandoDescricao(false)}>
                    Cancelar
                  </button>
                  <button
                    className="botao botao-acao"
                    disabled={ocupado}
                    onClick={async () => {
                      setOcupado(true);
                      try {
                        await salvar({ descricao });
                        setEditandoDescricao(false);
                      } catch (f) {
                        setMensagem(f instanceof ErroApi ? f.message : "Não foi possível salvar.");
                      } finally {
                        setOcupado(false);
                      }
                    }}
                  >
                    Salvar
                  </button>
                </div>
              </div>
            ) : item.descricao ? (
              <div style={{ marginTop: 6, maxWidth: "72ch" }}>
                <TextoRico doc={item.descricao} imagens={imagens} />
              </div>
            ) : (
              <p className="legenda" style={{ margin: "6px 0 0" }}>
                Sem descrição.
              </p>
            )}
          </section>

          <section aria-labelledby="titulo-detalhes" style={{ marginTop: 22 }}>
            <h2 id="titulo-detalhes" className="h3" style={{ marginBottom: 8 }}>
              Detalhes
            </h2>
            <dl className="grade-detalhes">
              {detalhes.map(([rotulo, valor]) => (
                <div key={rotulo}>
                  <dt className="legenda">{rotulo}</dt>
                  <dd>{valor}</dd>
                </div>
              ))}
            </dl>
          </section>

          {item.filhos.length > 0 && (
            <section aria-labelledby="titulo-filhos" style={{ marginTop: 22 }}>
              <h2 id="titulo-filhos" className="h3" style={{ marginBottom: 6 }}>
                {item.nivel === "epico" ? "Itens do épico" : "Subtarefas"}
              </h2>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {item.filhos.map((f) => (
                  <li key={f.chave} style={{ display: "flex", gap: 8, alignItems: "center", padding: "5px 0", borderBottom: "0.5px solid var(--borda)" }}>
                    <Link href={`/itens/${f.chave}`} style={{ fontWeight: 500 }}>
                      {f.chave}
                    </Link>
                    <span style={{ flex: 1 }}>{f.resumo}</span>
                    <span className="legenda">{f.tipo}</span>
                    <EtiquetaStatus nome={f.status} categoria={f.status_categoria} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          <Vinculos chave={item.chave} vinculos={item.vinculos} tipos={opcoes?.tipos_vinculo ?? {}} podeVincular={p.vincular && Boolean(opcoes)} aoMudar={async () => void (await recarregar())} />
          <Anexos chave={item.chave} anexos={item.anexos} podeAnexar={p.anexar} aoMudar={async () => void (await recarregar())} />
          <Atividade chave={item.chave} podeComentar={p.comentar} pessoas={pessoas} imagens={imagens} aoEnviarImagem={enviarImagem} versao={item.atualizado_em + item.anexos.length + item.vinculos.length} />
        </div>
      </article>

      {editandoCampos && espaco && opcoes && (
        <div className="fundo-janela" onMouseDown={(e) => e.target === e.currentTarget && setEditandoCampos(false)}>
          <div className="janela" role="dialog" aria-modal="true" aria-labelledby="titulo-editar">
            <h2 id="titulo-editar" className="h2" style={{ marginBottom: 14 }}>
              Editar {item.chave}
            </h2>
            <FormularioItem
              espaco={espaco}
              opcoes={opcoes}
              inicial={item}
              aoCancelar={() => setEditandoCampos(false)}
              aoSalvar={async (dados) => {
                if (await salvar(dados)) setEditandoCampos(false);
              }}
            />
          </div>
        </div>
      )}

      <Dialogo
        aberto={confirmacao !== null}
        titulo="Concluir item bloqueado?"
        textoConfirmar="Concluir mesmo assim"
        perigo
        ocupado={ocupado}
        aoConfirmar={async () => {
          if (!confirmacao) return;
          setOcupado(true);
          try {
            await salvar(confirmacao.dados, true);
            setEditandoCampos(false);
          } finally {
            setOcupado(false);
          }
        }}
        aoCancelar={() => setConfirmacao(null)}
      >
        {confirmacao?.mensagem} A confirmação fica registrada no histórico.
      </Dialogo>

      <Dialogo
        aberto={clonando !== null}
        titulo={`Clonar ${item.chave}?`}
        textoConfirmar="Clonar"
        ocupado={ocupado}
        aoConfirmar={async () => {
          if (!clonando) return;
          setOcupado(true);
          try {
            const copia = await api.clonarItem(item.chave, clonando);
            setClonando(null);
            router.push(`/itens/${copia.chave}`);
          } catch (f) {
            setMensagem(f instanceof ErroApi ? f.message : "Não foi possível clonar.");
            setClonando(null);
          } finally {
            setOcupado(false);
          }
        }}
        aoCancelar={() => setClonando(null)}
      >
        <p style={{ margin: "0 0 10px" }}>A cópia leva todos os campos e fica vinculada ao original como &quot;clona&quot;. Quer copiar também:</p>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input type="checkbox" checked={clonando?.copiar_comentarios ?? false} onChange={(e) => clonando && setClonando({ ...clonando, copiar_comentarios: e.target.checked })} />
          Os comentários
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 6 }}>
          <input type="checkbox" checked={clonando?.copiar_anexos ?? false} onChange={(e) => clonando && setClonando({ ...clonando, copiar_anexos: e.target.checked })} />
          Os anexos{item.anexos.length ? ` (${item.anexos.length})` : ""} e as imagens da descrição
        </label>
      </Dialogo>

      <Dialogo
        aberto={excluindo}
        titulo={`Excluir ${item.chave}?`}
        textoConfirmar="Excluir item"
        perigo
        ocupado={ocupado}
        aoConfirmar={async () => {
          setOcupado(true);
          try {
            await api.excluirItem(item.chave);
            router.push(`/espacos/${item.espaco_sigla}`);
          } catch (f) {
            setMensagem(f instanceof ErroApi ? f.message : "Não foi possível excluir.");
            setExcluindo(false);
          } finally {
            setOcupado(false);
          }
        }}
        aoCancelar={() => setExcluindo(false)}
      >
        O item sai das listas. A exclusão fica registrada na auditoria.
      </Dialogo>

      <style>{`
        .ficha-item{display:grid;grid-template-columns:250px minmax(0,1fr);border-radius:12px;overflow:hidden;background:#fff;border:0.5px solid var(--borda)}
        .faixa-item{background:var(--verde-escuro);color:#fff;padding:20px 18px}
        .folha-item{padding:20px 24px;min-width:0}
        .rotulo-faixa{display:block;font-size:12px;font-weight:300;color:var(--verde-claro);margin-top:14px}
        .valor-faixa{font-size:14px;margin-top:2px}
        .seletor-status{margin-top:4px;width:100%;height:32px;border-radius:20px;border:none;padding:0 10px;font-size:13px;font-weight:500;color:var(--verde-escuro);background:#fff;cursor:pointer}
        .acoes-faixa{display:grid;gap:6px;margin-top:20px}
        .botao-faixa{display:flex;gap:6px;align-items:center;justify-content:center;width:100%;background:none;border:0.5px solid var(--verde-claro);color:#fff;border-radius:8px;padding:7px;font-size:13px;cursor:pointer}
        .botao-faixa:hover{background:var(--verde-faixa)}
        .botao-faixa:disabled{opacity:.5}
        .grade-detalhes{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px 16px;margin:0}
        .grade-detalhes dd{margin:2px 0 0}
        @media (max-width:760px){.ficha-item{grid-template-columns:1fr}}
      `}</style>
    </>
  );
}
