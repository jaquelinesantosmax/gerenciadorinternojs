"use client";

import {
  IconBlockquote,
  IconBold,
  IconCode,
  IconH2,
  IconH3,
  IconItalic,
  IconLink,
  IconList,
  IconListNumbers,
  IconPhoto,
  IconSourceCode,
  IconStrikethrough,
  IconTable,
} from "@tabler/icons-react";
import Image from "@tiptap/extension-image";
import Mention from "@tiptap/extension-mention";
import { Table, TableCell, TableHeader, TableRow } from "@tiptap/extension-table";
import { EditorContent, useEditor, type Editor as EditorTiptap } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useRef, useState } from "react";
import type { DocTexto, Pessoa } from "@/lib/api";

// Editor de texto formatado da descrição e dos comentários (docs/decisoes-de-desenho.md, Detalhe do item):
// negrito, itálico, títulos, listas, tabelas, links, blocos de código, imagens coladas e menções.

/** Imagem guardada pelo id do anexo; o endereço (link temporário) só existe na tela. */
const ImagemAnexo = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      anexoId: { default: null, parseHTML: (el) => el.getAttribute("data-anexo"), renderHTML: (a) => ({ "data-anexo": a.anexoId }) },
    };
  },
});

/** Prepara o documento para salvar: tira o endereço temporário das imagens. */
export function paraSalvar(doc: DocTexto): DocTexto {
  const limpar = (no: Record<string, unknown>): Record<string, unknown> => {
    const copia: Record<string, unknown> = { ...no };
    if (no.type === "image") {
      const attrs = (no.attrs ?? {}) as Record<string, unknown>;
      copia.attrs = { anexoId: attrs.anexoId, alt: attrs.alt ?? "" };
    }
    if (Array.isArray(no.content)) copia.content = (no.content as Record<string, unknown>[]).map(limpar);
    return copia;
  };
  return limpar(doc as unknown as Record<string, unknown>) as DocTexto;
}

/** Prepara o documento para editar: põe o link temporário em cada imagem. */
export function paraEditar(doc: DocTexto | null | undefined, imagens: Record<string, string>): DocTexto | undefined {
  if (!doc) return undefined;
  const preencher = (no: Record<string, unknown>): Record<string, unknown> => {
    const copia: Record<string, unknown> = { ...no };
    if (no.type === "image") {
      const attrs = (no.attrs ?? {}) as Record<string, unknown>;
      copia.attrs = { ...attrs, src: imagens[String(attrs.anexoId)] ?? "" };
    }
    if (Array.isArray(no.content)) copia.content = (no.content as Record<string, unknown>[]).map(preencher);
    return copia;
  };
  return preencher(doc as unknown as Record<string, unknown>) as DocTexto;
}

/** Lista de sugestões das menções (@pessoa), montada sem bibliotecas extras. */
function sugestaoDeMencoes(pessoas: () => Pessoa[]) {
  return {
    items: ({ query }: { query: string }) =>
      pessoas()
        .filter((p) => `${p.nome} ${p.email}`.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 6),
    render: () => {
      let caixa: HTMLDivElement | null = null;
      let selecionado = 0;
      let atuais: Pessoa[] = [];
      let escolher: (p: Pessoa) => void = () => undefined;
      const desenhar = () => {
        if (!caixa) return;
        caixa.replaceChildren(
          ...atuais.map((p, i) => {
            const botao = document.createElement("button");
            botao.type = "button";
            botao.textContent = p.nome;
            botao.className = i === selecionado ? "ativo" : "";
            botao.onmousedown = (e) => {
              e.preventDefault();
              escolher(p);
            };
            return botao;
          }),
        );
        caixa.style.display = atuais.length ? "block" : "none";
      };
      const posicionar = (rect: DOMRect | null | undefined) => {
        if (caixa && rect) {
          caixa.style.left = `${rect.left + window.scrollX}px`;
          caixa.style.top = `${rect.bottom + window.scrollY + 4}px`;
        }
      };
      return {
        onStart: (props: { items: Pessoa[]; command: (a: { id: string; label: string }) => void; clientRect?: (() => DOMRect | null) | null }) => {
          caixa = document.createElement("div");
          caixa.className = "sugestoes-mencao";
          document.body.appendChild(caixa);
          atuais = props.items;
          selecionado = 0;
          escolher = (p) => props.command({ id: p.id, label: p.nome });
          posicionar(props.clientRect?.());
          desenhar();
        },
        onUpdate: (props: { items: Pessoa[]; command: (a: { id: string; label: string }) => void; clientRect?: (() => DOMRect | null) | null }) => {
          atuais = props.items;
          selecionado = 0;
          escolher = (p) => props.command({ id: p.id, label: p.nome });
          posicionar(props.clientRect?.());
          desenhar();
        },
        onKeyDown: ({ event }: { event: KeyboardEvent }) => {
          if (!atuais.length) return false;
          if (event.key === "ArrowDown") selecionado = (selecionado + 1) % atuais.length;
          else if (event.key === "ArrowUp") selecionado = (selecionado - 1 + atuais.length) % atuais.length;
          else if (event.key === "Enter") {
            escolher(atuais[selecionado]);
            return true;
          } else return false;
          desenhar();
          return true;
        },
        onExit: () => {
          caixa?.remove();
          caixa = null;
        },
      };
    },
  };
}

function Botao({ ativo, titulo, aoClicar, children }: { ativo?: boolean; titulo: string; aoClicar: () => void; children: React.ReactNode }) {
  return (
    <button type="button" className={`ferramenta${ativo ? " ativa" : ""}`} title={titulo} aria-label={titulo} aria-pressed={ativo} onMouseDown={(e) => e.preventDefault()} onClick={aoClicar}>
      {children}
    </button>
  );
}

function Ferramentas({ editor, aoEscolherImagem }: { editor: EditorTiptap; aoEscolherImagem?: () => void }) {
  const icone = { size: 16, stroke: 1.5 };
  const link = () => {
    const atual = editor.getAttributes("link").href as string | undefined;
    const href = window.prompt("Endereço do link (https://...)", atual ?? "https://");
    if (href === null) return;
    if (!href.trim()) editor.chain().focus().unsetLink().run();
    else if (/^(https?:\/\/|mailto:)/i.test(href.trim())) editor.chain().focus().setLink({ href: href.trim() }).run();
    else window.alert("O link precisa começar com http://, https:// ou mailto:.");
  };
  return (
    <div className="ferramentas" role="toolbar" aria-label="Formatação">
      <Botao titulo="Negrito" ativo={editor.isActive("bold")} aoClicar={() => editor.chain().focus().toggleBold().run()}><IconBold {...icone} /></Botao>
      <Botao titulo="Itálico" ativo={editor.isActive("italic")} aoClicar={() => editor.chain().focus().toggleItalic().run()}><IconItalic {...icone} /></Botao>
      <Botao titulo="Riscado" ativo={editor.isActive("strike")} aoClicar={() => editor.chain().focus().toggleStrike().run()}><IconStrikethrough {...icone} /></Botao>
      <Botao titulo="Código" ativo={editor.isActive("code")} aoClicar={() => editor.chain().focus().toggleCode().run()}><IconCode {...icone} /></Botao>
      <span className="separador" />
      <Botao titulo="Título" ativo={editor.isActive("heading", { level: 2 })} aoClicar={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}><IconH2 {...icone} /></Botao>
      <Botao titulo="Subtítulo" ativo={editor.isActive("heading", { level: 3 })} aoClicar={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}><IconH3 {...icone} /></Botao>
      <Botao titulo="Lista" ativo={editor.isActive("bulletList")} aoClicar={() => editor.chain().focus().toggleBulletList().run()}><IconList {...icone} /></Botao>
      <Botao titulo="Lista numerada" ativo={editor.isActive("orderedList")} aoClicar={() => editor.chain().focus().toggleOrderedList().run()}><IconListNumbers {...icone} /></Botao>
      <Botao titulo="Citação" ativo={editor.isActive("blockquote")} aoClicar={() => editor.chain().focus().toggleBlockquote().run()}><IconBlockquote {...icone} /></Botao>
      <Botao titulo="Bloco de código" ativo={editor.isActive("codeBlock")} aoClicar={() => editor.chain().focus().toggleCodeBlock().run()}><IconSourceCode {...icone} /></Botao>
      <span className="separador" />
      <Botao titulo="Tabela" aoClicar={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><IconTable {...icone} /></Botao>
      <Botao titulo="Link" ativo={editor.isActive("link")} aoClicar={link}><IconLink {...icone} /></Botao>
      {aoEscolherImagem && <Botao titulo="Imagem" aoClicar={aoEscolherImagem}><IconPhoto {...icone} /></Botao>}
    </div>
  );
}

export function Editor({
  valor,
  aoMudar,
  pessoas = [],
  aoEnviarImagem,
  placeholder,
  autoFoco = false,
  rotulo,
}: {
  valor?: DocTexto | null;
  aoMudar: (doc: DocTexto) => void;
  /** Quem pode ser mencionado com @. */
  pessoas?: Pessoa[];
  /** Envia a imagem como anexo do item e devolve o id e o link. Sem isso, imagens não podem ser coladas. */
  aoEnviarImagem?: (arquivo: File) => Promise<{ id: string; link: string } | null>;
  placeholder?: string;
  autoFoco?: boolean;
  rotulo: string;
}) {
  const pessoasRef = useRef(pessoas);
  pessoasRef.current = pessoas;
  const envioRef = useRef(aoEnviarImagem);
  envioRef.current = aoEnviarImagem;
  const entradaArquivo = useRef<HTMLInputElement>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  async function inserirImagens(editor: EditorTiptap, arquivos: File[]) {
    const imagens = arquivos.filter((a) => a.type.startsWith("image/"));
    if (!imagens.length) return false;
    if (!envioRef.current) {
      setAviso("Salve o item antes de colar imagens.");
      return true;
    }
    setAviso("Enviando imagem…");
    for (const arquivo of imagens) {
      const enviado = await envioRef.current(arquivo);
      if (enviado) editor.chain().focus().setImage({ src: enviado.link, alt: arquivo.name, ...({ anexoId: enviado.id } as object) }).run();
    }
    setAviso(null);
    return true;
  }

  const editor = useEditor({
    immediatelyRender: false,
    autofocus: autoFoco ? "end" : false,
    extensions: [
      StarterKit.configure({
        underline: false,
        heading: { levels: [1, 2, 3] },
        link: { openOnClick: false, autolink: true, protocols: ["mailto"], HTMLAttributes: { rel: "noopener noreferrer nofollow", target: "_blank" } },
      }),
      ImagemAnexo.configure({ inline: false }),
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
      Mention.configure({
        HTMLAttributes: { class: "mencao" },
        renderText: ({ node }) => `@${node.attrs.label}`,
        suggestion: sugestaoDeMencoes(() => pessoasRef.current),
      }),
    ],
    content: (valor ?? undefined) as Parameters<typeof useEditor>[0]["content"],
    editorProps: {
      attributes: { class: "area-editor", "aria-label": rotulo, ...(placeholder ? { "data-placeholder": placeholder } : {}) },
      handlePaste: (_vista, evento) => {
        const arquivos = Array.from(evento.clipboardData?.files ?? []);
        if (!arquivos.length || !editorAtual.current) return false;
        void inserirImagens(editorAtual.current, arquivos);
        return arquivos.some((a) => a.type.startsWith("image/"));
      },
      handleDrop: (_vista, evento) => {
        const arquivos = Array.from((evento as DragEvent).dataTransfer?.files ?? []);
        if (!arquivos.length || !editorAtual.current) return false;
        void inserirImagens(editorAtual.current, arquivos);
        return arquivos.some((a) => a.type.startsWith("image/"));
      },
    },
    onUpdate: ({ editor: e }) => aoMudar(paraSalvar(e.getJSON() as DocTexto)),
  });
  const editorAtual = useRef<EditorTiptap | null>(null);
  editorAtual.current = editor;

  if (!editor) return <div className="caixa-editor legenda" style={{ padding: 10 }}>Carregando editor…</div>;

  return (
    <div className="caixa-editor">
      <Ferramentas editor={editor} aoEscolherImagem={aoEnviarImagem ? () => entradaArquivo.current?.click() : undefined} />
      <EditorContent editor={editor} />
      {aviso && <div className="legenda" style={{ padding: "4px 10px" }}>{aviso}</div>}
      <input
        ref={entradaArquivo}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          const arquivos = Array.from(e.target.files ?? []);
          e.target.value = "";
          void inserirImagens(editor, arquivos);
        }}
      />
    </div>
  );
}
