"use client";

import { IconEye, IconEyeOff, IconKey, IconLifebuoy } from "@tabler/icons-react";
import { useState } from "react";
import { api, ErroApi, type EspacoDetalhe } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { Dialogo } from "./Dialogo";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Janela para o ADM da plataforma entrar num espaço para suporte: pede o motivo, vale por 4 horas. */
export function DialogoSuporte({
  sigla,
  nome,
  aberto,
  aoFechar,
  aoEntrar,
}: {
  sigla: string;
  nome: string;
  aberto: boolean;
  aoFechar: () => void;
  aoEntrar: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  return (
    <Dialogo
      aberto={aberto}
      titulo={`Entrar para suporte em ${nome}?`}
      textoConfirmar="Entrar para suporte"
      ocupado={ocupado}
      erro={erro}
      aoCancelar={() => {
        setErro(null);
        aoFechar();
      }}
      aoConfirmar={async () => {
        setErro(null);
        if (!motivo.trim()) {
          setErro("Informe o motivo do suporte.");
          return;
        }
        setOcupado(true);
        try {
          await api.entrarSuporte(sigla, motivo.trim());
          setMotivo("");
          aoEntrar();
        } catch (f) {
          setErro(msg(f, "Não foi possível entrar."));
        } finally {
          setOcupado(false);
        }
      }}
    >
      <p style={{ margin: 0 }}>
        Você terá os poderes de ADM deste espaço por 4 horas. A entrada, o motivo e tudo o que você mudar ficam registrados na auditoria.
      </p>
      <label className="rotulo obrigatorio" htmlFor="motivo-suporte" style={{ marginTop: 12, display: "block" }}>
        Motivo
      </label>
      <textarea id="motivo-suporte" className="campo" placeholder="Ex.: chamado 123, ajuste do fluxo pedido pela equipe" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
    </Dialogo>
  );
}

/** Janela de Solicitar acesso (pelo espaço ou por um item restrito). */
export function DialogoSolicitar({
  aberto,
  titulo,
  texto,
  enviar,
  aoFechar,
  aoEnviar,
}: {
  aberto: boolean;
  titulo: string;
  texto: string;
  enviar: (mensagem: string) => Promise<void>;
  aoFechar: () => void;
  aoEnviar: () => void;
}) {
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  return (
    <Dialogo
      aberto={aberto}
      titulo={titulo}
      textoConfirmar="Enviar pedido"
      ocupado={ocupado}
      erro={erro}
      aoCancelar={() => {
        setErro(null);
        aoFechar();
      }}
      aoConfirmar={async () => {
        setErro(null);
        setOcupado(true);
        try {
          await enviar(mensagem.trim());
          setMensagem("");
          aoEnviar();
        } catch (f) {
          setErro(msg(f, "Não foi possível enviar o pedido."));
        } finally {
          setOcupado(false);
        }
      }}
    >
      <p style={{ margin: 0 }}>{texto}</p>
      <label className="rotulo" htmlFor="mensagem-pedido" style={{ marginTop: 12, display: "block" }}>
        Mensagem (opcional)
      </label>
      <textarea id="mensagem-pedido" className="campo" placeholder="Conte por que você precisa do acesso" value={mensagem} onChange={(e) => setMensagem(e.target.value)} />
    </Dialogo>
  );
}

/** Faixa e botões de acesso no topo do espaço: suporte ativo, Acompanhar (Gestor) e Solicitar acesso. */
export function AcessoNoTopo({ espaco, parte, aoMudar }: { espaco: EspacoDetalhe; parte: "faixas" | "botoes"; aoMudar: () => void }) {
  const [pedindo, setPedindo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const executar = async (acao: () => Promise<void>) => {
    setErro(null);
    try {
      await acao();
      window.dispatchEvent(new Event("espacos-mudaram"));
      aoMudar();
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
    }
  };
  // Leitor e quem vê por espaço aberto podem pedir para virar Membro.
  const podePedir = espaco.tipo === "projeto" && (espaco.meu_papel === "leitor" || espaco.meu_papel === "aberto");

  if (parte === "faixas")
    return (
      <>
      {espaco.meu_papel === "suporte" && espaco.suporte_ate && (
        <div className="faixa-aviso" role="status">
          <IconLifebuoy size={16} stroke={1.5} />
          <span style={{ flex: 1 }}>
            Você está em suporte neste espaço até {formatarDataHora(espaco.suporte_ate)}. Tudo o que você mudar fica registrado na auditoria.
          </span>
          <button className="botao" onClick={() => void executar(() => api.sairSuporte(espaco.sigla))}>
            Sair do suporte
          </button>
        </div>
      )}
      {espaco.meu_papel === "aberto" && (
        <div className="faixa-aviso" role="status" style={{ background: "var(--verde-fundo)", borderColor: "var(--verde)" }}>
          <span style={{ flex: 1 }}>Este espaço está aberto para a empresa: você pode ver, comentar e anexar arquivos.</span>
        </div>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      </>
    );

  return (
    <>
        {espaco.pode_acompanhar && (
          <button className="botao" onClick={() => void executar(() => api.acompanhar(espaco.sigla, !espaco.acompanha))}>
            {espaco.acompanha ? <IconEyeOff size={14} stroke={1.5} /> : <IconEye size={14} stroke={1.5} />}
            {espaco.acompanha ? "Deixar de acompanhar" : "Acompanhar"}
          </button>
        )}
        {podePedir &&
          (espaco.pedido_pendente ? (
            <span className="etiqueta etiqueta-neutra">Acesso solicitado</span>
          ) : (
            <button className="botao" onClick={() => setPedindo(true)}>
              <IconKey size={14} stroke={1.5} /> Solicitar acesso
            </button>
          ))}
      {erro && (
        <span className="mensagem-erro" role="alert">
          {erro}
        </span>
      )}
      <DialogoSolicitar
        aberto={pedindo}
        titulo={`Pedir para ser Membro de ${espaco.nome}?`}
        texto="O ADM do espaço recebe o pedido e escolhe o papel ao aprovar."
        enviar={(m) => api.solicitarAcessoEspaco(espaco.sigla, m)}
        aoFechar={() => setPedindo(false)}
        aoEnviar={() => {
          setPedindo(false);
          aoMudar();
        }}
      />
    </>
  );
}
