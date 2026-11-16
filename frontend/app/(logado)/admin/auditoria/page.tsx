"use client";

import { useCallback, useEffect, useState } from "react";
import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type Evento } from "@/lib/api";
import { TIPOS_EVENTO } from "@/lib/textos";

const POR_PAGINA = 50;

export default function PaginaAuditoria() {
  const { eu } = useEu();
  const [tipo, setTipo] = useState("");
  const [eventos, setEventos] = useState<Evento[] | null>(null);
  const [proximo, setProximo] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(
    async (antesDe?: number) => {
      setCarregando(true);
      try {
        const pagina = await api.auditoria({ tipo: tipo || undefined, antesDe, limite: POR_PAGINA });
        setEventos((atuais) => (antesDe && atuais ? [...atuais, ...pagina.eventos] : pagina.eventos));
        setProximo(pagina.proximo);
        setErro(null);
      } catch (falha) {
        setErro(falha instanceof ErroApi ? falha.message : "Não foi possível carregar.");
      } finally {
        setCarregando(false);
      }
    },
    [tipo],
  );

  useEffect(() => {
    if (eu.permissoes.ver_auditoria) void carregar();
  }, [carregar, eu.permissoes.ver_auditoria]);

  if (!eu.permissoes.ver_auditoria) return <SemPermissao />;

  return (
    <>
      <h1 className="h1">Auditoria</h1>
      <p className="legenda" style={{ marginTop: 4 }}>
        Entradas, entradas recusadas, saídas, mudanças de papel, desativações e domínios, do mais recente para o mais
        antigo. Horários de Brasília.
      </p>
      <div style={{ marginTop: 16, maxWidth: 280 }}>
        <label className="rotulo" htmlFor="tipo">
          Tipo de evento
        </label>
        <select id="tipo" className="campo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
          <option value="">Todos</option>
          {Object.entries(TIPOS_EVENTO).map(([valor, nome]) => (
            <option key={valor} value={valor}>
              {nome}
            </option>
          ))}
        </select>
      </div>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div className="painel" style={{ marginTop: 14 }}>
        {eventos === null ? <p className="legenda">Carregando…</p> : <LinhaDoTempo eventos={eventos} mostrarIp />}
        {proximo && (
          <button className="botao" style={{ marginTop: 12 }} disabled={carregando} onClick={() => carregar(proximo)}>
            {carregando ? "Carregando…" : "Carregar mais"}
          </button>
        )}
      </div>
    </>
  );
}
