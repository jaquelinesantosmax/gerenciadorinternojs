"use client";

import { useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type Gestor } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";

export default function PaginaGestores() {
  const { eu } = useEu();
  const [gestores, setGestores] = useState<Gestor[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!eu.permissoes.ver_usuarios) return;
    api
      .gestores()
      .then(setGestores)
      .catch((f) => setErro(f instanceof ErroApi ? f.message : "Não foi possível carregar."));
  }, [eu.permissoes.ver_usuarios]);

  if (!eu.permissoes.ver_usuarios) return <SemPermissao />;

  return (
    <>
      <h1 className="h1">Gestores</h1>
      <p className="legenda" style={{ marginTop: 4 }}>
        Quem tem o papel de Gestor, quem concedeu e quando. Para dar ou tirar o papel, abra a pessoa em Usuários.
      </p>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div className="painel" style={{ marginTop: 16, padding: "4px 8px", overflowX: "auto" }}>
        {gestores === null ? (
          <p className="legenda" style={{ padding: 10 }}>
            Carregando…
          </p>
        ) : gestores.length === 0 ? (
          <p className="legenda" style={{ padding: 10 }}>
            Ainda não há Gestores.
          </p>
        ) : (
          <table className="tabela">
            <thead>
              <tr>
                <th>Gestor</th>
                <th>Concedido por</th>
                <th style={{ width: 160 }}>Quando</th>
              </tr>
            </thead>
            <tbody>
              {gestores.map((g) => (
                <tr key={g.usuario.id}>
                  <td>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <Avatar nome={g.usuario.nome} fotoUrl={g.usuario.foto_url} />
                      <div>
                        <div style={{ fontWeight: 500 }}>{g.usuario.nome}</div>
                        <div className="legenda">{g.usuario.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>{g.concedido_por ? g.concedido_por.nome : <span className="legenda">Instalação</span>}</td>
                  <td className="legenda" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatarDataHora(g.concedido_em)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
