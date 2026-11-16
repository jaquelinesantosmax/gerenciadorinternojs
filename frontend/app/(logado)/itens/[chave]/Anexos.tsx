"use client";

import { IconDownload, IconFile, IconPaperclip, IconTrash } from "@tabler/icons-react";
import { useRef, useState } from "react";
import { Dialogo } from "@/components/Dialogo";
import { api, ErroApi, type Anexo } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";

export function tamanhoLegivel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2).replace(".", ",")} GB`;
}

/** Anexos: vários de uma vez, arrastar e soltar e colar print (docs/decisoes-de-desenho.md). */
export function Anexos({
  chave,
  anexos,
  podeAnexar,
  aoMudar,
}: {
  chave: string;
  anexos: Anexo[];
  podeAnexar: boolean;
  aoMudar: () => Promise<void>;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [arrastando, setArrastando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [excluir, setExcluir] = useState<Anexo | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function enviar(arquivos: File[]) {
    if (!arquivos.length) return;
    setErro(null);
    setEnviando(true);
    try {
      await api.enviarAnexos(chave, arquivos);
      await aoMudar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível enviar.");
    } finally {
      setEnviando(false);
    }
  }

  async function confirmarExclusao() {
    if (!excluir) return;
    setOcupado(true);
    try {
      await api.excluirAnexo(chave, excluir.id);
      setExcluir(null);
      await aoMudar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível excluir.");
      setExcluir(null);
    } finally {
      setOcupado(false);
    }
  }

  return (
    <section aria-labelledby="titulo-anexos" style={{ marginTop: 22 }}>
      <h2 id="titulo-anexos" className="h3" style={{ marginBottom: 8 }}>
        Anexos {anexos.length > 0 && <span className="legenda">({anexos.length})</span>}
      </h2>
      {podeAnexar && (
        <div
          className={`zona-soltar${arrastando ? " ativa" : ""}`}
          tabIndex={0}
          role="button"
          aria-label="Anexar arquivos: clique, arraste ou cole um print"
          onClick={() => entrada.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && entrada.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setArrastando(true);
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastando(false);
            void enviar(Array.from(e.dataTransfer.files));
          }}
          onPaste={(e) => void enviar(Array.from(e.clipboardData.files))}
        >
          <IconPaperclip size={16} stroke={1.5} />
          {enviando ? "Enviando…" : "Arraste arquivos, cole um print (Ctrl+V) ou clique para escolher"}
          <input
            ref={entrada}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              const arquivos = Array.from(e.target.files ?? []);
              e.target.value = "";
              void enviar(arquivos);
            }}
          />
        </div>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      {anexos.length > 0 && (
        <ul className="lista-anexos">
          {anexos.map((a) => (
            <li key={a.id}>
              {a.pre_visualizacao && a.tipo_mime.startsWith("image/") ? (
                <a href={a.link} target="_blank" rel="noopener noreferrer" className="miniatura">
                  <img src={a.link} alt="" />
                </a>
              ) : (
                <span className="miniatura icone">
                  <IconFile size={20} stroke={1.5} />
                </span>
              )}
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.pre_visualizacao ? (
                    <a href={a.link} target="_blank" rel="noopener noreferrer">
                      {a.nome_arquivo}
                    </a>
                  ) : (
                    a.nome_arquivo
                  )}
                </div>
                <div className="legenda">
                  {tamanhoLegivel(a.tamanho)} · {a.enviado_por?.nome ?? "—"} · {formatarDataHora(a.enviado_em)}
                </div>
              </div>
              <a className="botao botao-discreto" href={`${a.link}&baixar=true`} aria-label={`Baixar ${a.nome_arquivo}`} title="Baixar">
                <IconDownload size={16} stroke={1.5} />
              </a>
              {a.pode_excluir && (
                <button className="botao botao-discreto" aria-label={`Excluir ${a.nome_arquivo}`} title="Excluir" onClick={() => setExcluir(a)}>
                  <IconTrash size={16} stroke={1.5} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {!podeAnexar && anexos.length === 0 && <p className="legenda">Nenhum anexo.</p>}
      <Dialogo
        aberto={excluir !== null}
        titulo={`Excluir ${excluir?.nome_arquivo ?? ""}?`}
        textoConfirmar="Excluir anexo"
        perigo
        ocupado={ocupado}
        aoConfirmar={confirmarExclusao}
        aoCancelar={() => setExcluir(null)}
      >
        O arquivo é apagado e a exclusão fica registrada no histórico do item.
      </Dialogo>
      <style>{`
        .zona-soltar{display:flex;gap:8px;align-items:center;justify-content:center;border:1px dashed var(--borda);border-radius:8px;padding:12px;color:var(--texto-2);font-size:13px;cursor:pointer;background:var(--fundo)}
        .zona-soltar:hover,.zona-soltar.ativa{border-color:var(--verde);color:var(--verde-escuro);background:var(--verde-fundo)}
        .lista-anexos{list-style:none;padding:0;margin:10px 0 0;display:grid;gap:6px}
        .lista-anexos li{display:flex;gap:10px;align-items:center;border:0.5px solid var(--borda);border-radius:8px;padding:6px 8px}
        .miniatura{width:40px;height:40px;border-radius:6px;overflow:hidden;flex-shrink:0;background:var(--fundo);display:flex;align-items:center;justify-content:center;color:var(--texto-2)}
        .miniatura img{width:100%;height:100%;object-fit:cover}
      `}</style>
    </section>
  );
}
