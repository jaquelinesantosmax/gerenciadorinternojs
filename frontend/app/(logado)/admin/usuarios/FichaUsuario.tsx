"use client";

import { IconX } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { Dialogo } from "@/components/Dialogo";
import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { useEu } from "@/components/Moldura";
import { api, ErroApi, type Evento, type Papel, type Permissao, type UsuarioAdmin } from "@/lib/api";
import { formatarData, formatarDataHora } from "@/lib/formato";
import { DESCRICAO_PAPEL, NOME_PAPEL, ORDEM_PAPEIS } from "@/lib/textos";

const PERMISSAO_DO_PAPEL: Record<Papel, Permissao> = {
  adm_plataforma: "dar_tirar_adm_plataforma",
  gestor: "dar_tirar_gestor",
  criar_espacos: "dar_tirar_criar_espacos",
};

type Acao =
  | { tipo: "conceder" | "retirar"; papel: Papel }
  | { tipo: "desativar" }
  | { tipo: "reativar" };

/** Ficha do usuário no estilo da prévia v3: faixa lateral escura, papéis e linha do tempo. */
export function FichaUsuario({
  usuario,
  aoFechar,
  aoMudar,
}: {
  usuario: UsuarioAdmin;
  aoFechar: () => void;
  aoMudar: () => Promise<void>;
}) {
  const { eu, recarregar } = useEu();
  const [eventos, setEventos] = useState<Evento[] | null>(null);
  const [acao, setAcao] = useState<Acao | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregarEventos = useCallback(async () => {
    if (!eu.permissoes.ver_auditoria) return;
    const pagina = await api.auditoria({ usuarioId: usuario.id, limite: 30 }).catch(() => null);
    setEventos(pagina?.eventos ?? []);
  }, [eu.permissoes.ver_auditoria, usuario.id]);

  useEffect(() => {
    void carregarEventos();
  }, [carregarEventos]);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && !acao && aoFechar();
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [acao, aoFechar]);

  const souEu = usuario.id === eu.id;

  async function confirmar() {
    if (!acao) return;
    setOcupado(true);
    setErro(null);
    try {
      if (acao.tipo === "conceder") await api.concederPapel(usuario.id, acao.papel);
      if (acao.tipo === "retirar") await api.revogarPapel(usuario.id, acao.papel);
      if (acao.tipo === "desativar") await api.desativar(usuario.id);
      if (acao.tipo === "reativar") await api.reativar(usuario.id);
      setAcao(null);
      await aoMudar();
      await carregarEventos();
      if (souEu) await recarregar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível concluir.");
    } finally {
      setOcupado(false);
    }
  }

  const textoDialogo = (() => {
    if (!acao) return { titulo: "", corpo: "", botao: "", perigo: false };
    if (acao.tipo === "conceder")
      return {
        titulo: `Dar o papel ${NOME_PAPEL[acao.papel]}?`,
        corpo: `${usuario.nome} passa a ter o papel ${NOME_PAPEL[acao.papel]}. ${DESCRICAO_PAPEL[acao.papel]} A mudança fica registrada na auditoria.`,
        botao: "Dar papel",
        perigo: false,
      };
    if (acao.tipo === "retirar")
      return {
        titulo: `Tirar o papel ${NOME_PAPEL[acao.papel]}?`,
        corpo: `${usuario.nome} perde o papel ${NOME_PAPEL[acao.papel]} na hora. A mudança fica registrada na auditoria.`,
        botao: "Tirar papel",
        perigo: true,
      };
    if (acao.tipo === "desativar")
      return {
        titulo: `Desativar ${usuario.nome}?`,
        corpo: "A pessoa sai do sistema na hora, em todos os aparelhos, e não consegue entrar de novo. Papéis e acessos ficam guardados para uma eventual reativação.",
        botao: "Desativar",
        perigo: true,
      };
    return {
      titulo: `Reativar ${usuario.nome}?`,
      corpo: "A pessoa volta a entrar no sistema, com os mesmos papéis e acessos que tinha.",
      botao: "Reativar",
      perigo: false,
    };
  })();

  return (
    <div className="fundo-ficha" onMouseDown={(e) => e.target === e.currentTarget && !acao && aoFechar()}>
      <div className="ficha" role="dialog" aria-modal="true" aria-label={`Ficha de ${usuario.nome}`}>
        <aside className="ficha-faixa">
          <Avatar nome={usuario.nome} fotoUrl={usuario.foto_url} claro tamanho={44} />
          <div style={{ fontSize: 18, fontWeight: 600, marginTop: 10, lineHeight: 1.25 }}>{usuario.nome}</div>
          <div style={{ fontSize: 12, fontWeight: 300, color: "var(--verde-claro)", wordBreak: "break-all" }}>{usuario.email}</div>
          <div className="rotulo-faixa">Situação</div>
          <div style={{ marginTop: 4 }}>
            <span
              className="etiqueta"
              style={usuario.ativo ? { background: "#fff", color: "var(--verde-escuro)" } : { background: "var(--alerta-fundo)", color: "var(--alerta-texto)" }}
            >
              {usuario.ativo ? "Ativo" : "Desativado"}
            </span>
          </div>
          {!usuario.ativo && usuario.desativado_em && (
            <>
              <div className="rotulo-faixa">Desativado em</div>
              <div className="valor-faixa">{formatarDataHora(usuario.desativado_em)}</div>
            </>
          )}
          <div className="rotulo-faixa">Cadastrado em</div>
          <div className="valor-faixa">{formatarData(usuario.criado_em)}</div>
          <div className="rotulo-faixa">Último acesso</div>
          <div className="valor-faixa">{formatarDataHora(usuario.ultimo_acesso_em)}</div>
          {eu.permissoes.desativar_usuarios && !souEu && (
            <button
              className="botao-faixa"
              onClick={() => {
                setErro(null);
                setAcao({ tipo: usuario.ativo ? "desativar" : "reativar" });
              }}
            >
              {usuario.ativo ? "Desativar usuário" : "Reativar usuário"}
            </button>
          )}
        </aside>
        <section className="ficha-folha">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 className="h2">Papéis na plataforma</h2>
            <button className="botao botao-discreto" onClick={aoFechar} aria-label="Fechar">
              <IconX size={18} stroke={1.5} />
            </button>
          </div>
          <ul style={{ listStyle: "none", padding: 0, margin: "10px 0 0" }}>
            {ORDEM_PAPEIS.map((papel) => {
              const tem = usuario.papeis.includes(papel);
              const pode = eu.permissoes[PERMISSAO_DO_PAPEL[papel]] && usuario.ativo;
              return (
                <li key={papel} className="linha-papel">
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{ fontWeight: 500 }}>{NOME_PAPEL[papel]}</span>
                      {tem && <span className="etiqueta">Tem</span>}
                    </div>
                    <div className="legenda" style={{ marginTop: 2 }}>
                      {DESCRICAO_PAPEL[papel]}
                    </div>
                  </div>
                  {pode && (
                    <button
                      className={`botao${tem ? " botao-perigo" : ""}`}
                      onClick={() => {
                        setErro(null);
                        setAcao({ tipo: tem ? "retirar" : "conceder", papel });
                      }}
                    >
                      {tem ? "Tirar" : "Dar papel"}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {!usuario.ativo && (
            <p className="legenda" style={{ marginTop: 8 }}>
              Usuário desativado: reative antes de mudar papéis.
            </p>
          )}
          {eu.permissoes.ver_auditoria && (
            <>
              <h3 className="h3" style={{ marginTop: 22, marginBottom: 6 }}>
                Atividade
              </h3>
              {eventos === null ? <p className="legenda">Carregando…</p> : <LinhaDoTempo eventos={eventos} />}
            </>
          )}
        </section>
      </div>
      <Dialogo
        aberto={acao !== null}
        titulo={textoDialogo.titulo}
        textoConfirmar={textoDialogo.botao}
        perigo={textoDialogo.perigo}
        ocupado={ocupado}
        erro={erro}
        aoConfirmar={confirmar}
        aoCancelar={() => setAcao(null)}
      >
        {textoDialogo.corpo}
      </Dialogo>
      <style>{`
        .fundo-ficha{position:fixed;inset:0;background:rgba(16,23,41,.45);display:flex;align-items:center;justify-content:center;padding:16px;z-index:40}
        .ficha{display:grid;grid-template-columns:230px minmax(0,1fr);width:100%;max-width:880px;max-height:88vh;background:#fff;border-radius:12px;overflow:hidden;border:0.5px solid var(--borda)}
        .ficha-faixa{background:var(--verde-escuro);color:#fff;padding:20px 18px;overflow-y:auto}
        .ficha-folha{padding:18px 22px;overflow-y:auto}
        .rotulo-faixa{font-size:12px;font-weight:300;color:var(--verde-claro);margin-top:14px}
        .valor-faixa{font-size:14px;margin-top:2px}
        .botao-faixa{margin-top:20px;width:100%;background:none;border:0.5px solid var(--verde-claro);color:#fff;border-radius:8px;padding:7px;font-size:13px;cursor:pointer}
        .botao-faixa:hover{background:var(--verde-faixa)}
        .linha-papel{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-bottom:0.5px solid var(--borda)}
        .linha-papel:last-child{border-bottom:none}
        @media (max-width:700px){.ficha{grid-template-columns:1fr;max-height:92vh;overflow-y:auto}.ficha-faixa,.ficha-folha{overflow:visible}}
      `}</style>
    </div>
  );
}
