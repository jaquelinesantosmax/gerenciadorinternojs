"use client";

import { useCallback, useEffect, useState } from "react";
import { Dialogo } from "@/components/Dialogo";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type Dominio } from "@/lib/api";
import { formatarData } from "@/lib/formato";

export default function PaginaDominios() {
  const { eu } = useEu();
  const [dominios, setDominios] = useState<Dominio[] | null>(null);
  const [novo, setNovo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [remover, setRemover] = useState<string | null>(null);
  const [erroRemover, setErroRemover] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDominios(await api.dominios());
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível carregar.");
    }
  }, []);

  useEffect(() => {
    if (eu.permissoes.configurar_dominios) void carregar();
  }, [carregar, eu.permissoes.configurar_dominios]);

  if (!eu.permissoes.configurar_dominios) return <SemPermissao />;

  async function adicionar(e: React.FormEvent) {
    e.preventDefault();
    if (!novo.trim()) return;
    setOcupado(true);
    setErro(null);
    try {
      await api.adicionarDominio(novo);
      setNovo("");
      await carregar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível adicionar.");
    } finally {
      setOcupado(false);
    }
  }

  async function confirmarRemocao() {
    if (!remover) return;
    setOcupado(true);
    setErroRemover(null);
    try {
      await api.removerDominio(remover);
      setRemover(null);
      await carregar();
    } catch (falha) {
      setErroRemover(falha instanceof ErroApi ? falha.message : "Não foi possível remover.");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <h1 className="h1">Domínios autorizados</h1>
      <p className="legenda" style={{ marginTop: 4 }}>
        Só quem tem e-mail de um destes domínios consegue entrar. Na primeira entrada, a pessoa é cadastrada sem acesso a
        nenhum espaço.
      </p>
      <div className="painel" style={{ marginTop: 16, maxWidth: 620 }}>
        {dominios === null ? (
          <p className="legenda">Carregando…</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {dominios.map((d) => (
              <li
                key={d.dominio}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "9px 0", borderBottom: "0.5px solid var(--borda)" }}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>@{d.dominio}</div>
                  <div className="legenda">
                    {d.adicionado_por ? `Adicionado por ${d.adicionado_por.nome}` : "Desde a instalação"} em{" "}
                    {formatarData(d.adicionado_em)}
                  </div>
                </div>
                <button
                  className="botao botao-perigo"
                  onClick={() => {
                    setErroRemover(null);
                    setRemover(d.dominio);
                  }}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={adicionar} style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label className="rotulo" htmlFor="novo-dominio">
              Novo domínio
            </label>
            <input
              id="novo-dominio"
              className="campo"
              placeholder="exemplo.com.br"
              value={novo}
              onChange={(e) => setNovo(e.target.value)}
            />
          </div>
          <button className="botao botao-acao" type="submit" disabled={ocupado || !novo.trim()} style={{ height: 36 }}>
            Adicionar
          </button>
        </form>
        {erro && (
          <p className="mensagem-erro" role="alert" style={{ marginBottom: 0 }}>
            {erro}
          </p>
        )}
      </div>
      <Dialogo
        aberto={remover !== null}
        titulo={`Remover @${remover ?? ""}?`}
        textoConfirmar="Remover domínio"
        perigo
        ocupado={ocupado}
        erro={erroRemover}
        aoConfirmar={confirmarRemocao}
        aoCancelar={() => setRemover(null)}
      >
        Quem tem e-mail deste domínio sai do sistema na hora e não consegue mais entrar. Os cadastros e papéis ficam
        guardados caso o domínio volte a ser autorizado.
      </Dialogo>
    </>
  );
}
