"use client";

import { IconKey, IconLock, IconPlus, IconX } from "@tabler/icons-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { DialogoSolicitar } from "@/components/AcessoEspaco";
import { Dialogo } from "@/components/Dialogo";
import { EtiquetaStatus } from "@/components/EtiquetaStatus";
import { api, ErroApi, type ItemCurto, type Vinculo } from "@/lib/api";

/** Itens relacionados: sete tipos fixos, nos dois sentidos, entre espaços diferentes. */
export function Vinculos({
  chave,
  vinculos,
  tipos,
  podeVincular,
  aoMudar,
}: {
  chave: string;
  vinculos: Vinculo[];
  tipos: Record<string, [string, string]>;
  podeVincular: boolean;
  aoMudar: () => Promise<void>;
}) {
  // Cada opção é um tipo + sentido: "bloqueia" (saída) ou "é bloqueado por" (entrada).
  const opcoes = Object.entries(tipos).flatMap(([tipo, [ida, volta]]) =>
    ida === volta ? [{ valor: `${tipo}|saida`, nome: ida }] : [{ valor: `${tipo}|saida`, nome: ida }, { valor: `${tipo}|entrada`, nome: volta }],
  );
  const [adicionando, setAdicionando] = useState(false);
  const [escolha, setEscolha] = useState(opcoes[0]?.valor ?? "");
  const [busca, setBusca] = useState("");
  const [sugestoes, setSugestoes] = useState<ItemCurto[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [pendente, setPendente] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [pedindo, setPedindo] = useState<string | null>(null);

  useEffect(() => {
    if (busca.trim().length < 2) {
      setSugestoes([]);
      return;
    }
    const espera = setTimeout(() => api.buscarItens(busca.trim()).then((l) => setSugestoes(l.filter((i) => i.chave !== chave))).catch(() => setSugestoes([])), 250);
    return () => clearTimeout(espera);
  }, [busca, chave]);

  async function vincular(outra: string, confirmar_ciclo = false) {
    const [tipo, sentido] = escolha.split("|");
    setErro(null);
    setOcupado(true);
    try {
      await api.vincular(chave, { tipo, sentido, chave: outra, confirmar_ciclo });
      setBusca("");
      setAviso(null);
      setAdicionando(false);
      await aoMudar();
    } catch (falha) {
      if (falha instanceof ErroApi && falha.codigo === "bloqueio_circular") {
        setPendente(outra);
        setAviso(falha.message);
      } else setErro(falha instanceof ErroApi ? falha.message : "Não foi possível vincular.");
    } finally {
      setOcupado(false);
    }
  }

  async function desvincular(id: string) {
    try {
      await api.desvincular(chave, id);
      await aoMudar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível desvincular.");
    }
  }

  return (
    <section aria-labelledby="titulo-vinculos" style={{ marginTop: 22 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 id="titulo-vinculos" className="h3">
          Itens relacionados
        </h2>
        {podeVincular && !adicionando && (
          <button className="botao botao-discreto" onClick={() => setAdicionando(true)}>
            <IconPlus size={16} stroke={1.5} /> Vincular
          </button>
        )}
      </div>
      {vinculos.length === 0 && !adicionando && <p className="legenda" style={{ margin: "6px 0 0" }}>Nenhum vínculo.</p>}
      <ul style={{ listStyle: "none", padding: 0, margin: "6px 0 0" }}>
        {vinculos.map((v) => (
          <li key={v.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", flexWrap: "wrap", borderBottom: "0.5px solid var(--borda)" }}>
            <span className="legenda" style={{ minWidth: 120 }}>
              {v.rotulo}
            </span>
            {v.acesso_restrito ? (
              <>
                <b style={{ fontWeight: 500 }}>{v.chave}</b>
                <span className="etiqueta etiqueta-neutra">
                  <IconLock size={12} stroke={1.5} /> acesso restrito
                </span>
                {v.pedido_pendente ? (
                  <span className="legenda">Acesso solicitado</span>
                ) : (
                  <button className="botao botao-discreto" onClick={() => setPedindo(v.chave)}>
                    <IconKey size={14} stroke={1.5} /> Solicitar acesso
                  </button>
                )}
              </>
            ) : (
              <>
                <Link href={`/itens/${v.chave}`} style={{ fontWeight: 500 }}>
                  {v.chave}
                </Link>
                <span style={{ flex: 1, minWidth: 120 }}>{v.resumo}</span>
                {v.status && <EtiquetaStatus nome={v.status} categoria={v.status_categoria ?? "a_fazer"} />}
              </>
            )}
            {v.bloqueio_aberto && <span className="etiqueta etiqueta-alerta">Aberto</span>}
            {podeVincular && (
              <button className="botao botao-discreto" aria-label={`Desvincular ${v.chave}`} title="Desvincular" onClick={() => void desvincular(v.id)} style={{ marginLeft: "auto" }}>
                <IconX size={14} stroke={1.5} />
              </button>
            )}
          </li>
        ))}
      </ul>
      {adicionando && (
        <div className="painel" style={{ marginTop: 8, padding: 12 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div>
              <label className="rotulo" htmlFor="tipo-vinculo">
                Este item
              </label>
              <select id="tipo-vinculo" className="campo" value={escolha} onChange={(e) => setEscolha(e.target.value)}>
                {opcoes.map((o) => (
                  <option key={o.valor} value={o.valor}>
                    {o.nome}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1, minWidth: 200, position: "relative" }}>
              <label className="rotulo" htmlFor="busca-vinculo">
                Item
              </label>
              <input
                id="busca-vinculo"
                className="campo"
                placeholder="Chave (ex.: SUP-41) ou parte do resumo"
                value={busca}
                autoFocus
                onChange={(e) => setBusca(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (busca.trim()) void vincular(sugestoes[0]?.chave ?? busca.trim());
                  }
                }}
              />
              {sugestoes.length > 0 && (
                <ul className="sugestoes-itens">
                  {sugestoes.map((s) => (
                    <li key={s.chave}>
                      <button type="button" onClick={() => void vincular(s.chave)} disabled={ocupado}>
                        <b style={{ fontWeight: 500 }}>{s.chave}</b> {s.resumo}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <button className="botao" onClick={() => setAdicionando(false)}>
              Cancelar
            </button>
          </div>
          <p className="legenda" style={{ margin: "6px 0 0" }}>
            Pode ser um item de outro espaço. Links externos não entram aqui.
          </p>
        </div>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <Dialogo
        aberto={aviso !== null}
        titulo="Bloqueio circular"
        textoConfirmar="Vincular mesmo assim"
        ocupado={ocupado}
        aoConfirmar={() => void vincular(pendente, true)}
        aoCancelar={() => setAviso(null)}
      >
        {aviso}
      </Dialogo>
      <style>{`
        .sugestoes-itens{position:absolute;left:0;right:0;top:100%;margin:4px 0 0;padding:4px;list-style:none;background:#fff;border:0.5px solid var(--borda);border-radius:8px;z-index:10}
        .sugestoes-itens button{width:100%;text-align:left;border:none;background:none;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px}
        .sugestoes-itens button:hover{background:var(--verde-fundo)}
      `}</style>
      <DialogoSolicitar
        aberto={pedindo !== null}
        titulo={`Pedir acesso a ${pedindo ?? ""}?`}
        texto="O ADM do espaço onde o item está recebe o pedido e escolhe o seu papel ao aprovar."
        enviar={(m) => api.solicitarAcessoItem(pedindo ?? "", m)}
        aoFechar={() => setPedindo(null)}
        aoEnviar={() => {
          setPedindo(null);
          void aoMudar();
        }}
      />
    </section>
  );
}
