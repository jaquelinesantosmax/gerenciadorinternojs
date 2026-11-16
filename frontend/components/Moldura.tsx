"use client";

import {
  IconCompass,
  IconFolder,
  IconShare,
  IconUsersGroup,
  IconHistory,
  IconHome,
  IconLogout,
  IconPlus,
  IconSettings,
  IconUser,
  IconUsers,
  IconUserStar,
  IconWorldWww,
} from "@tabler/icons-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, type EspacoResumo, type Eu, type Permissao } from "@/lib/api";
import { Avatar } from "./Avatar";

const ContextoEu = createContext<{ eu: Eu; recarregar: () => Promise<void> } | null>(null);

export function useEu() {
  const valor = useContext(ContextoEu);
  if (!valor) throw new Error("useEu fora da Moldura");
  return valor;
}

interface ItemMenu {
  href: string;
  texto: string;
  icone: React.ReactNode;
  permissao?: Permissao;
}

const ITENS_ADMIN: ItemMenu[] = [
  { href: "/admin/usuarios", texto: "Usuários", icone: <IconUsers size={16} stroke={1.5} />, permissao: "ver_usuarios" },
  { href: "/admin/gestores", texto: "Gestores", icone: <IconUserStar size={16} stroke={1.5} />, permissao: "ver_usuarios" },
  { href: "/admin/auditoria", texto: "Auditoria", icone: <IconHistory size={16} stroke={1.5} />, permissao: "ver_auditoria" },
  { href: "/admin/dominios", texto: "Domínios", icone: <IconWorldWww size={16} stroke={1.5} />, permissao: "configurar_dominios" },
  { href: "/admin/plataforma", texto: "Plataforma", icone: <IconSettings size={16} stroke={1.5} />, permissao: "definir_limite_anexos" },
];

/** Estrutura das telas logadas: faixa lateral escura com menu e área de conteúdo. */
export function Moldura({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const caminho = usePathname();
  const [eu, setEu] = useState<Eu | null>(null);

  const recarregar = useCallback(async () => {
    try {
      setEu(await api.eu());
    } catch {
      router.replace("/entrar");
    }
  }, [router]);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  const [espacos, setEspacos] = useState<EspacoResumo[]>([]);
  useEffect(() => {
    if (!eu) return;
    const carregar = () => api.espacos().then(setEspacos).catch(() => undefined);
    void carregar();
    window.addEventListener("espacos-mudaram", carregar);
    return () => window.removeEventListener("espacos-mudaram", carregar);
  }, [eu]);

  async function sair() {
    await api.sair().catch(() => undefined);
    router.replace("/entrar");
  }

  if (!eu) {
    return <div style={{ padding: 32 }} className="legenda">Carregando…</div>;
  }

  const admin = ITENS_ADMIN.filter((i) => !i.permissao || eu.permissoes[i.permissao]);
  const ativo = (href: string) => (href === "/" ? caminho === "/" : caminho.startsWith(href));

  return (
    <ContextoEu.Provider value={{ eu, recarregar }}>
      <div className="moldura">
        <nav className="faixa" aria-label="Menu principal">
          <div style={{ fontWeight: 600, fontSize: 16, padding: "0 8px 10px" }}>Gerenciador</div>
          <Link href="/" className={`item${ativo("/") ? " ativo" : ""}`}>
            <IconHome size={16} stroke={1.5} /> Início
          </Link>
          {[
            ["Espaços", espacos.filter((e) => e.tipo === "projeto"), <IconFolder key="f" size={16} stroke={1.5} />],
            ["Pessoal", espacos.filter((e) => e.tipo === "pessoal" && e.meu_papel !== "compartilhado"), <IconUser key="u" size={16} stroke={1.5} />],
            ["Compartilhados comigo", espacos.filter((e) => e.meu_papel === "compartilhado"), <IconShare key="c" size={16} stroke={1.5} />],
          ].map(([titulo, lista, icone]) =>
            (lista as EspacoResumo[]).length > 0 ? (
              <div key={titulo as string}>
                <div className="secao">{titulo as string}</div>
                {(lista as EspacoResumo[]).map((e) => {
                  const base = `/espacos/${e.sigla}`;
                  const noPainel = caminho.startsWith(`${base}/paineis/`);
                  return (
                    <div key={e.id}>
                      <Link href={base} className={`item${caminho.startsWith(base) && !noPainel ? " ativo" : ""}`} title={e.nome}>
                        {icone as React.ReactNode} <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.nome}</span>
                      </Link>
                      {/* Painéis em cascata abaixo do nome do espaço (decisão de 16/11). */}
                      {e.paineis.map((p) => (
                        <Link key={p.id} href={`${base}/paineis/${p.id}`} className={`item item-painel${caminho === `${base}/paineis/${p.id}` ? " ativo" : ""}`} title={p.nome}>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.nome}</span>
                        </Link>
                      ))}
                    </div>
                  );
                })}
              </div>
            ) : null,
          )}
          <Link href="/espacos/novo" className={`item item-discreto${ativo("/espacos/novo") ? " ativo" : ""}`}>
            <IconPlus size={16} stroke={1.5} /> Criar espaço
          </Link>
          <Link href="/explorar" className={`item item-discreto${ativo("/explorar") ? " ativo" : ""}`}>
            <IconCompass size={16} stroke={1.5} /> Explorar espaços
          </Link>
          <Link href="/times" className={`item item-discreto${ativo("/times") ? " ativo" : ""}`}>
            <IconUsersGroup size={16} stroke={1.5} /> Times
          </Link>
          {admin.length > 0 && (
            <>
              <div className="secao">Administração</div>
              {admin.map((i) => (
                <Link key={i.href} href={i.href} className={`item${ativo(i.href) ? " ativo" : ""}`}>
                  {i.icone} {i.texto}
                </Link>
              ))}
            </>
          )}
          <div className="rodape">
            <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "0 8px" }}>
              <Avatar nome={eu.nome} fotoUrl={eu.foto_url} claro tamanho={28} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{eu.nome}</div>
                <div style={{ fontSize: 11, color: "var(--verde-claro)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {eu.email}
                </div>
              </div>
            </div>
            <button className="item" onClick={sair} style={{ marginTop: 8 }}>
              <IconLogout size={16} stroke={1.5} /> Sair
            </button>
          </div>
        </nav>
        <main className="conteudo">{children}</main>
      </div>
      <style>{`
        .moldura{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:100vh}
        .faixa{background:var(--verde-escuro);color:#fff;padding:18px 10px;display:flex;flex-direction:column;position:sticky;top:0;height:100vh}
        .faixa .secao{font-size:11px;color:var(--verde-claro);margin:18px 8px 4px;text-transform:uppercase;letter-spacing:.06em}
        .faixa .item{display:flex;gap:8px;align-items:center;padding:7px 8px;border-radius:8px;color:#fff;font-size:13px;text-decoration:none;background:none;border:none;cursor:pointer;width:100%;text-align:left}
        .faixa .item:hover{background:var(--verde-faixa)}
        .faixa .item.ativo{background:var(--verde)}
        .faixa .item-discreto{color:var(--verde-claro);margin-top:6px}
        .faixa .item-painel{position:relative;padding-left:32px;font-size:12.5px;color:var(--verde-claro)}
        .faixa .item-painel::before{content:"";position:absolute;left:15px;top:0;bottom:50%;width:9px;border-left:0.5px solid var(--verde-claro);border-bottom:0.5px solid var(--verde-claro);border-bottom-left-radius:4px;opacity:.6}
        .faixa .item-painel.ativo{color:#fff}
        .faixa{overflow-y:auto}
        .faixa .rodape{margin-top:auto;border-top:0.5px solid var(--verde-faixa);padding-top:12px}
        .conteudo{padding:24px 28px;min-width:0;max-width:1180px}
        @media (max-width:760px){.moldura{grid-template-columns:1fr}.faixa{position:static;height:auto}.conteudo{padding:16px}}
      `}</style>
    </ContextoEu.Provider>
  );
}
