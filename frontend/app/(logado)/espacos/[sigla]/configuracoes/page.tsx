"use client";

import { IconPencil, IconPlus, IconTrash } from "@tabler/icons-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { Dialogo } from "@/components/Dialogo";
import { useEu } from "@/components/Moldura";
import { api, ErroApi, type Campo, type EspacoDetalhe, type Membro, type OpcoesItem, type Pessoa } from "@/lib/api";
import { DESCRICAO_PAPEL_ESPACO, NOME_PAPEL_ESPACO } from "@/lib/textos";
import { Compartilhar, EspacoAberto, GestoresQueAcompanham, PedidosDeAcesso, TimesComAcesso } from "./ConfigAcesso";
import { ConfigQuadros } from "./ConfigQuadros";
import { ConfigWorkflow } from "./ConfigWorkflow";
import { EditorCampo, NOMES_TIPO } from "./EditorCampo";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

function Secao({ titulo, descricao, children }: { titulo: string; descricao?: string; children: React.ReactNode }) {
  return (
    <section className="painel" style={{ marginTop: 16 }}>
      <h2 className="h2">{titulo}</h2>
      {descricao && (
        <p className="legenda" style={{ margin: "4px 0 10px" }}>
          {descricao}
        </p>
      )}
      {children}
    </section>
  );
}

/** Lista simples com adicionar, renomear e excluir (painéis, tipos próprios e origens). */
function ListaNomes({
  itens,
  aoAdicionar,
  aoRenomear,
  aoExcluir,
  rotuloNovo,
  textoExcluir,
}: {
  itens: { id: string; nome: string; fixo?: boolean }[];
  aoAdicionar: (nome: string) => Promise<void>;
  aoRenomear?: (id: string, nome: string) => Promise<void>;
  aoExcluir: (id: string) => Promise<void>;
  rotuloNovo: string;
  textoExcluir: string;
}) {
  const [novo, setNovo] = useState("");
  const [renomeando, setRenomeando] = useState<{ id: string; nome: string } | null>(null);
  const [excluir, setExcluir] = useState<{ id: string; nome: string } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const executar = async (acao: () => Promise<void>) => {
    setErro(null);
    try {
      await acao();
      return true;
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
      return false;
    }
  };
  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {itens.map((i) => (
          <li key={i.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--borda)" }}>
            {renomeando?.id === i.id ? (
              <>
                <input className="campo" aria-label="Novo nome" value={renomeando.nome} onChange={(e) => setRenomeando({ ...renomeando, nome: e.target.value })} autoFocus />
                <button className="botao botao-acao" onClick={async () => (await executar(() => aoRenomear!(i.id, renomeando.nome))) && setRenomeando(null)}>
                  Salvar
                </button>
                <button className="botao" onClick={() => setRenomeando(null)}>
                  Cancelar
                </button>
              </>
            ) : (
              <>
                <span style={{ flex: 1 }}>{i.nome}</span>
                {i.fixo ? (
                  <span className="legenda">Padrão da plataforma</span>
                ) : (
                  <>
                    {aoRenomear && (
                      <button className="botao botao-discreto" aria-label={`Renomear ${i.nome}`} onClick={() => setRenomeando({ id: i.id, nome: i.nome })}>
                        <IconPencil size={14} stroke={1.5} />
                      </button>
                    )}
                    <button className="botao botao-discreto" aria-label={`Excluir ${i.nome}`} onClick={() => setExcluir(i)}>
                      <IconTrash size={14} stroke={1.5} />
                    </button>
                  </>
                )}
              </>
            )}
          </li>
        ))}
        {itens.length === 0 && <li className="legenda">Nenhum ainda.</li>}
      </ul>
      <form
        style={{ display: "flex", gap: 8, marginTop: 10 }}
        onSubmit={async (e) => {
          e.preventDefault();
          if (novo.trim() && (await executar(() => aoAdicionar(novo)))) setNovo("");
        }}
      >
        <input className="campo" aria-label={rotuloNovo} placeholder={rotuloNovo} value={novo} onChange={(e) => setNovo(e.target.value)} />
        <button className="botao botao-acao" type="submit" disabled={!novo.trim()}>
          <IconPlus size={14} stroke={1.5} /> Adicionar
        </button>
      </form>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <Dialogo
        aberto={excluir !== null}
        titulo={`Excluir ${excluir?.nome ?? ""}?`}
        textoConfirmar="Excluir"
        perigo
        aoConfirmar={async () => {
          if (excluir) await executar(() => aoExcluir(excluir.id));
          setExcluir(null);
        }}
        aoCancelar={() => setExcluir(null)}
      >
        {textoExcluir}
      </Dialogo>
    </div>
  );
}

function Membros({ sigla, membros, aoMudar }: { sigla: string; membros: Membro[]; aoMudar: () => Promise<void> }) {
  const { eu } = useEu();
  const [busca, setBusca] = useState("");
  const [achadas, setAchadas] = useState<Pessoa[]>([]);
  const [papel, setPapel] = useState("membro");
  const [remover, setRemover] = useState<Membro | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (busca.trim().length < 2) {
      setAchadas([]);
      return;
    }
    const espera = setTimeout(() => api.pessoas(busca.trim()).then(setAchadas).catch(() => setAchadas([])), 250);
    return () => clearTimeout(espera);
  }, [busca]);

  const executar = async (acao: () => Promise<void>) => {
    setErro(null);
    try {
      await acao();
      await aoMudar();
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
    }
  };

  const jaMembros = new Set(membros.map((m) => m.usuario.id));
  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {membros.map((m) => (
          <li key={m.usuario.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--borda)" }}>
            <Avatar nome={m.usuario.nome} fotoUrl={m.usuario.foto_url} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 500 }}>
                {m.usuario.nome}
                {m.usuario.id === eu.id && <span className="legenda"> (você)</span>}
              </div>
              <div className="legenda">{m.usuario.email}</div>
            </div>
            <select className="campo" style={{ width: 160 }} aria-label={`Papel de ${m.usuario.nome}`} value={m.papel} onChange={(e) => void executar(() => api.mudarPapelMembro(sigla, m.usuario.id, e.target.value))}>
              {["adm", "membro", "leitor"].map((p) => (
                <option key={p} value={p}>
                  {NOME_PAPEL_ESPACO[p]}
                </option>
              ))}
            </select>
            <button className="botao botao-discreto" aria-label={`Tirar ${m.usuario.nome} do espaço`} onClick={() => setRemover(m)}>
              <IconTrash size={14} stroke={1.5} />
            </button>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 220, position: "relative" }}>
          <label className="rotulo" htmlFor="busca-pessoa">
            Adicionar pessoa
          </label>
          <input id="busca-pessoa" className="campo" placeholder="Nome ou e-mail (a pessoa precisa ter entrado uma vez)" value={busca} onChange={(e) => setBusca(e.target.value)} />
          {achadas.length > 0 && (
            <ul className="sugestoes-pessoas">
              {achadas.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    disabled={jaMembros.has(p.id)}
                    onClick={() =>
                      void executar(async () => {
                        await api.adicionarMembro(sigla, p.id, papel);
                        setBusca("");
                      })
                    }
                  >
                    {p.nome} <span className="legenda">{p.email}</span>
                    {jaMembros.has(p.id) && <span className="legenda"> · já é membro</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <label className="rotulo" htmlFor="papel-novo">
            Como
          </label>
          <select id="papel-novo" className="campo" value={papel} onChange={(e) => setPapel(e.target.value)}>
            {["adm", "membro", "leitor"].map((p) => (
              <option key={p} value={p}>
                {NOME_PAPEL_ESPACO[p]}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="legenda" style={{ margin: "6px 0 0" }}>
        {DESCRICAO_PAPEL_ESPACO[papel]}
      </p>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <Dialogo
        aberto={remover !== null}
        titulo={`Tirar ${remover?.usuario.nome ?? ""} do espaço?`}
        textoConfirmar="Tirar do espaço"
        perigo
        aoConfirmar={async () => {
          if (remover) await executar(() => api.removerMembro(sigla, remover.usuario.id));
          setRemover(null);
        }}
        aoCancelar={() => setRemover(null)}
      >
        A pessoa perde o acesso ao espaço na hora. A mudança fica registrada na auditoria.
      </Dialogo>
      <style>{`
        .sugestoes-pessoas{position:absolute;left:0;right:0;top:100%;margin:4px 0 0;padding:4px;list-style:none;background:#fff;border:0.5px solid var(--borda);border-radius:8px;z-index:10}
        .sugestoes-pessoas button{width:100%;text-align:left;border:none;background:none;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px}
        .sugestoes-pessoas button:hover:not(:disabled){background:var(--verde-fundo)}
        .sugestoes-pessoas button:disabled{opacity:.6;cursor:default}
      `}</style>
    </div>
  );
}

export default function ConfiguracoesEspaco() {
  const { sigla } = useParams<{ sigla: string }>();
  const [espaco, setEspaco] = useState<EspacoDetalhe | null>(null);
  const [membros, setMembros] = useState<Membro[]>([]);
  const [campos, setCampos] = useState<Campo[]>([]);
  const [opcoes, setOpcoes] = useState<OpcoesItem | null>(null);
  const [geral, setGeral] = useState({ nome: "", descricao: "" });
  const [campoAberto, setCampoAberto] = useState<Campo | "novo" | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [versaoWorkflow, setVersaoWorkflow] = useState(0);

  const carregar = useCallback(async () => {
    try {
      const e = await api.espaco(sigla);
      setEspaco(e);
      setGeral({ nome: e.nome, descricao: e.descricao ?? "" });
      if (e.tipo === "projeto") setMembros(await api.membros(sigla));
      setCampos(await api.campos(sigla, true));
      setOpcoes(await api.opcoesItem(sigla));
    } catch (f) {
      setErro(msg(f, "Não foi possível carregar."));
    }
  }, [sigla]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (erro) return <p className="mensagem-erro">{erro}</p>;
  if (!espaco) return <p className="legenda">Carregando…</p>;
  if (!espaco.permissoes.configurar && !espaco.permissoes.gerenciar_membros)
    return <p className="painel">Só o ADM do espaço mexe nas configurações.</p>;

  const recarregarEspaco = async () => {
    setEspaco(await api.espaco(sigla));
    window.dispatchEvent(new Event("espacos-mudaram"));
  };

  return (
    <div style={{ maxWidth: 860 }}>
      <nav className="legenda">
        <Link href={`/espacos/${sigla}`}>{espaco.nome}</Link> › Configurações
      </nav>
      <h1 className="h1" style={{ marginTop: 6 }}>
        Configurações de {espaco.nome}
      </h1>

      <Secao titulo="Geral">
        <form
          className="grade-campos"
          onSubmit={async (e) => {
            e.preventDefault();
            setAviso(null);
            try {
              await api.editarEspaco(sigla, geral);
              await recarregarEspaco();
              setAviso("Salvo.");
            } catch (f) {
              setAviso(msg(f, "Não foi possível salvar."));
            }
          }}
        >
          <div>
            <label className="rotulo obrigatorio" htmlFor="geral-nome">
              Nome
            </label>
            <input id="geral-nome" className="campo" value={geral.nome} onChange={(e) => setGeral({ ...geral, nome: e.target.value })} />
          </div>
          <div>
            <span className="rotulo">Sigla</span>
            <div style={{ height: 36, display: "flex", alignItems: "center" }}>
              {espaco.sigla} <span className="legenda" style={{ marginLeft: 6 }}>(não muda)</span>
            </div>
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <label className="rotulo" htmlFor="geral-descricao">
              Descrição do espaço
            </label>
            <textarea id="geral-descricao" className="campo" value={geral.descricao} onChange={(e) => setGeral({ ...geral, descricao: e.target.value })} />
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button className="botao botao-acao" type="submit">
              Salvar
            </button>
            {aviso && <span className="legenda">{aviso}</span>}
          </div>
        </form>
      </Secao>

      {espaco.tipo === "projeto" && espaco.permissoes.gerenciar_membros && (
        <>
          <Secao titulo="Membros" descricao="Papéis fixos por espaço: a mesma pessoa pode ter papéis diferentes em espaços diferentes.">
            <Membros sigla={sigla} membros={membros} aoMudar={async () => setMembros(await api.membros(sigla))} />
          </Secao>
          <Secao titulo="Times com acesso" descricao="Todo mundo do time ganha o papel escolhido. Quem sai do time perde o acesso que vinha dele.">
            <TimesComAcesso sigla={sigla} />
          </Secao>
        </>
      )}

      {espaco.tipo === "projeto" && espaco.permissoes.aprovar_acesso && (
        <Secao titulo="Pedidos de acesso" descricao="Pedidos feitos pelo botão Solicitar acesso. Ao aprovar, escolha o papel da pessoa.">
          <PedidosDeAcesso sigla={sigla} aoMudar={async () => setMembros(await api.membros(sigla))} />
        </Secao>
      )}

      {espaco.tipo === "projeto" && (espaco.permissoes.marcar_aberto || espaco.permissoes.ver_gestores) && (
        <Secao titulo="Visibilidade">
          {espaco.permissoes.marcar_aberto && <EspacoAberto sigla={sigla} aberto={espaco.aberto} aoMudar={recarregarEspaco} />}
          {espaco.permissoes.ver_gestores && (
            <>
              <h3 className="h3" style={{ margin: "14px 0 6px" }}>
                Gestores que acompanham
              </h3>
              <GestoresQueAcompanham sigla={sigla} />
            </>
          )}
        </Secao>
      )}

      {espaco.tipo === "pessoal" && espaco.permissoes.compartilhar && (
        <Secao titulo="Compartilhar" descricao="As pessoas escolhidas veem os itens deste espaço, sem comentar nem editar. Gestor e ADM da plataforma não veem espaços pessoais.">
          <Compartilhar sigla={sigla} />
        </Secao>
      )}

      {espaco.tipo === "projeto" && espaco.permissoes.criar_paineis && (
        <Secao titulo="Painéis" descricao="Frentes dentro do espaço, como Suporte B2B ou Legal Ops. Quando existe painel, todo item precisa indicar o seu.">
          <ListaNomes
            itens={espaco.paineis}
            rotuloNovo="Nome do painel"
            textoExcluir="O painel só pode ser excluído se não tiver itens."
            aoAdicionar={async (nome) => {
              await api.criarOpcaoEspaco(sigla, "paineis", nome);
              await recarregarEspaco();
            }}
            aoRenomear={async (id, nome) => {
              await api.renomearOpcaoEspaco(sigla, "paineis", id, nome);
              await recarregarEspaco();
            }}
            aoExcluir={async (id) => {
              await api.excluirOpcaoEspaco(sigla, "paineis", id);
              await recarregarEspaco();
            }}
          />
        </Secao>
      )}

      {espaco.permissoes.configurar && (
        <>
          <Secao titulo="Status e fluxo" descricao="Quais status valem neste espaço e por onde os itens podem passar. Todo espaço nasce com os 8 status padrão e o fluxo padrão.">
            <ConfigWorkflow
              sigla={sigla}
              aoMudar={() => {
                setVersaoWorkflow((v) => v + 1);
                void recarregarEspaco();
              }}
            />
          </Secao>

          <Secao titulo="Quadros" descricao="Colunas de cada quadro. Uma coluna pode juntar vários status. O limite de itens gera alerta quando passa, sem impedir.">
            <ConfigQuadros sigla={sigla} versao={versaoWorkflow} />
          </Secao>

          <Secao titulo="Tipos de item" descricao="Épico, História, Tarefa, Bug e Subtarefa são da plataforma. Tipos próprios ficam no nível de História e Tarefa.">
            <ListaNomes
              itens={espaco.tipos.map((t) => ({ id: t.id, nome: t.nome, fixo: t.padrao }))}
              rotuloNovo="Nome do tipo (ex.: Processo)"
              textoExcluir="O tipo só pode ser excluído se nenhum item usar."
              aoAdicionar={async (nome) => {
                await api.criarOpcaoEspaco(sigla, "tipos", nome);
                await recarregarEspaco();
              }}
              aoRenomear={async (id, nome) => {
                await api.renomearOpcaoEspaco(sigla, "tipos", id, nome);
                await recarregarEspaco();
              }}
              aoExcluir={async (id) => {
                await api.excluirOpcaoEspaco(sigla, "tipos", id);
                await recarregarEspaco();
              }}
            />
          </Secao>

          <Secao titulo="Origens da solicitação" descricao="Opções do campo Origem da solicitação neste espaço.">
            <ListaNomes
              itens={espaco.origens}
              rotuloNovo="Nova origem (ex.: Slack)"
              textoExcluir="A origem sai da lista de escolha, mas continua nos itens que já a usam."
              aoAdicionar={async (nome) => {
                await api.criarOpcaoEspaco(sigla, "origens", nome);
                await recarregarEspaco();
              }}
              aoExcluir={async (id) => {
                await api.excluirOpcaoEspaco(sigla, "origens", id);
                await recarregarEspaco();
              }}
            />
          </Secao>

          <Secao titulo="Campos personalizados" descricao="Campos além dos padronizados. Cada campo aparece só nos tipos escolhidos.">
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {campos.map((c) => (
                <li key={c.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "0.5px solid var(--borda)", opacity: c.ativo ? 1 : 0.55 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>
                      {c.nome} {c.obrigatorio && <span className="etiqueta etiqueta-neutra">Obrigatório</span>} {!c.ativo && <span className="etiqueta etiqueta-neutra">Desativado</span>}
                    </div>
                    <div className="legenda">
                      {NOMES_TIPO[c.tipo]} · {espaco.tipos.filter((t) => c.tipos_item.includes(t.id)).map((t) => t.nome).join(", ")}
                    </div>
                  </div>
                  {c.ativo && (
                    <button className="botao botao-discreto" onClick={() => setCampoAberto(c)}>
                      <IconPencil size={14} stroke={1.5} /> Editar
                    </button>
                  )}
                  <button
                    className="botao botao-discreto"
                    onClick={async () => {
                      await api.editarCampo(sigla, c.id, { ativo: !c.ativo });
                      setCampos(await api.campos(sigla, true));
                    }}
                  >
                    {c.ativo ? "Desativar" : "Reativar"}
                  </button>
                </li>
              ))}
              {campos.length === 0 && <li className="legenda">Nenhum campo personalizado ainda.</li>}
            </ul>
            <button className="botao botao-acao" style={{ marginTop: 12 }} onClick={() => setCampoAberto("novo")}>
              <IconPlus size={14} stroke={1.5} /> Criar campo
            </button>
            <p className="legenda" style={{ margin: "6px 0 0" }}>
              Campo desativado some dos formulários, mas os valores já preenchidos ficam guardados.
            </p>
          </Secao>
        </>
      )}

      {campoAberto && opcoes && (
        <div className="fundo-janela" onMouseDown={(e) => e.target === e.currentTarget && setCampoAberto(null)}>
          <div className="janela" role="dialog" aria-modal="true" aria-labelledby="titulo-campo">
            <h2 id="titulo-campo" className="h2" style={{ marginBottom: 14 }}>
              {campoAberto === "novo" ? "Criar campo" : `Editar ${campoAberto.nome}`}
            </h2>
            <EditorCampo
              sigla={sigla}
              tipos={espaco.tipos}
              moedas={opcoes.moedas}
              campo={campoAberto === "novo" ? null : campoAberto}
              aoCancelar={() => setCampoAberto(null)}
              aoSalvar={async () => {
                setCampos(await api.campos(sigla, true));
                setCampoAberto(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
