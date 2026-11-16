"use client";

import { IconEye, IconEyeOff, IconLifebuoy } from "@tabler/icons-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { DialogoSuporte } from "@/components/AcessoEspaco";
import { useEu } from "@/components/Moldura";
import { api, ErroApi, type EspacoExplorar } from "@/lib/api";
import { NOME_PAPEL_ESPACO } from "@/lib/textos";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Espaços de equipe que dá para descobrir: os abertos para a empresa e, para o Gestor e o ADM da plataforma, todos. */
export default function PaginaExplorar() {
  const { eu } = useEu();
  const router = useRouter();
  const [lista, setLista] = useState<EspacoExplorar[] | null>(null);
  const [suporte, setSuporte] = useState<EspacoExplorar | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const ehGestor = eu.papeis.includes("gestor");
  const ehAdm = eu.papeis.includes("adm_plataforma");

  const carregar = useCallback(async () => {
    try {
      setLista(await api.explorar());
    } catch (f) {
      setErro(msg(f, "Não foi possível carregar."));
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const executar = async (acao: () => Promise<void>) => {
    setErro(null);
    try {
      await acao();
      window.dispatchEvent(new Event("espacos-mudaram"));
      await carregar();
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
    }
  };

  return (
    <div style={{ maxWidth: 860 }}>
      <h1 className="h1">Explorar espaços</h1>
      <p className="legenda" style={{ margin: "4px 0 0" }}>
        {ehGestor
          ? "Como Gestor, você abre qualquer espaço de equipe. Os que você acompanhar aparecem no seu menu, e o ADM e os Membros do espaço veem que você acompanha."
          : ehAdm
            ? "Como ADM da plataforma, você entra num espaço de que não participa só para suporte, com motivo e por 4 horas."
            : "Espaços que as equipes abriram para toda a empresa. Neles você vê, comenta e anexa arquivos."}{" "}
        Espaços pessoais nunca aparecem aqui.
      </p>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      {!lista ? (
        <p className="legenda">Carregando…</p>
      ) : (
        <ul className="painel" style={{ listStyle: "none", margin: "16px 0 0", padding: "4px 16px" }}>
          {lista.map((e) => {
            const entra = e.meu_papel !== null;
            return (
              <li key={e.sigla} style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 0", borderBottom: "0.5px solid var(--borda)", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  {entra ? (
                    <Link href={`/espacos/${e.sigla}`} style={{ fontWeight: 500 }}>
                      {e.nome}
                    </Link>
                  ) : (
                    <span style={{ fontWeight: 500 }}>{e.nome}</span>
                  )}
                  <span className="legenda"> · {e.sigla}</span>
                  <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
                    {e.aberto && <span className="etiqueta etiqueta-neutra">Aberto para a empresa</span>}
                    {e.meu_papel && <span className="etiqueta etiqueta-neutra">{NOME_PAPEL_ESPACO[e.meu_papel] ?? e.meu_papel}</span>}
                    {e.acompanha && <span className="etiqueta etiqueta-neutra">Você acompanha</span>}
                  </div>
                </div>
                {ehGestor && (
                  <button className="botao" onClick={() => void executar(() => api.acompanhar(e.sigla, !e.acompanha))}>
                    {e.acompanha ? <IconEyeOff size={14} stroke={1.5} /> : <IconEye size={14} stroke={1.5} />}
                    {e.acompanha ? "Deixar de acompanhar" : "Acompanhar"}
                  </button>
                )}
                {ehAdm && !entra && (
                  <button className="botao" onClick={() => setSuporte(e)}>
                    <IconLifebuoy size={14} stroke={1.5} /> Entrar para suporte
                  </button>
                )}
              </li>
            );
          })}
          {lista.length === 0 && (
            <li className="legenda" style={{ padding: "10px 0" }}>
              Nenhum espaço para explorar ainda.
            </li>
          )}
        </ul>
      )}
      {suporte && (
        <DialogoSuporte
          sigla={suporte.sigla}
          nome={suporte.nome}
          aberto
          aoFechar={() => setSuporte(null)}
          aoEntrar={() => {
            const sigla = suporte.sigla;
            setSuporte(null);
            window.dispatchEvent(new Event("espacos-mudaram"));
            router.push(`/espacos/${sigla}`);
          }}
        />
      )}
    </div>
  );
}
