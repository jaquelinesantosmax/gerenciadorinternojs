"use client";

import { IconSearch } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type UsuarioAdmin } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { NOME_PAPEL } from "@/lib/textos";
import { FichaUsuario } from "./FichaUsuario";

export default function PaginaUsuarios() {
  const { eu } = useEu();
  const [busca, setBusca] = useState("");
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);

  const carregar = useCallback(async (termo: string) => {
    try {
      setUsuarios(await api.usuarios(termo));
      setErro(null);
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível carregar.");
    }
  }, []);

  useEffect(() => {
    if (!eu.permissoes.ver_usuarios) return;
    const espera = setTimeout(() => void carregar(busca), 250);
    return () => clearTimeout(espera);
  }, [busca, carregar, eu.permissoes.ver_usuarios]);

  if (!eu.permissoes.ver_usuarios) return <SemPermissao />;

  const selecionado = usuarios?.find((u) => u.id === aberto) ?? null;

  return (
    <>
      <h1 className="h1">Usuários</h1>
      <p className="legenda" style={{ marginTop: 4 }}>
        Todo mundo que já entrou no sistema. Clique em uma pessoa para ver a ficha, os papéis e a atividade.
      </p>
      <div style={{ position: "relative", maxWidth: 360, marginTop: 16 }}>
        <IconSearch size={16} stroke={1.5} style={{ position: "absolute", left: 10, top: 10, color: "var(--texto-2)" }} />
        <label htmlFor="busca" className="oculto-acessivel">
          Buscar por nome ou e-mail
        </label>
        <input
          id="busca"
          className="campo"
          style={{ paddingLeft: 32 }}
          placeholder="Buscar por nome ou e-mail"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
      </div>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div className="painel" style={{ marginTop: 14, padding: "4px 8px", overflowX: "auto" }}>
        {usuarios === null ? (
          <p className="legenda" style={{ padding: 10 }}>
            Carregando…
          </p>
        ) : usuarios.length === 0 ? (
          <p className="legenda" style={{ padding: 10 }}>
            Ninguém encontrado.
          </p>
        ) : (
          <table className="tabela">
            <thead>
              <tr>
                <th>Pessoa</th>
                <th>Papéis</th>
                <th style={{ width: 110 }}>Situação</th>
                <th style={{ width: 150 }}>Último acesso</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr
                  key={u.id}
                  className="clicavel"
                  tabIndex={0}
                  onClick={() => setAberto(u.id)}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), setAberto(u.id))}
                >
                  <td>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <Avatar nome={u.nome} fotoUrl={u.foto_url} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 500 }}>{u.nome}</div>
                        <div className="legenda">{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {u.papeis.length === 0 ? (
                        <span className="legenda">Usuário</span>
                      ) : (
                        u.papeis.map((p) => (
                          <span key={p} className="etiqueta">
                            {NOME_PAPEL[p]}
                          </span>
                        ))
                      )}
                    </div>
                  </td>
                  <td>
                    {u.ativo ? (
                      <span className="etiqueta etiqueta-neutra">Ativo</span>
                    ) : (
                      <span className="etiqueta etiqueta-alerta">Desativado</span>
                    )}
                  </td>
                  <td className="legenda" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatarDataHora(u.ultimo_acesso_em)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {selecionado && (
        <FichaUsuario usuario={selecionado} aoFechar={() => setAberto(null)} aoMudar={() => carregar(busca)} />
      )}
    </>
  );
}
