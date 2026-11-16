// Acesso à API do servidor. Todo pedido que muda dados leva o cabeçalho X-Gerenciador,
// exigido pelo servidor como proteção contra pedidos forjados por outros sites (CSRF).

export type Papel = "adm_plataforma" | "gestor" | "criar_espacos";

export type Permissao =
  | "configurar_dominios"
  | "dar_tirar_adm_plataforma"
  | "dar_tirar_gestor"
  | "dar_tirar_criar_espacos"
  | "desativar_usuarios"
  | "ver_auditoria"
  | "ver_usuarios"
  | "criar_espaco_equipe"
  | "acessar_espaco_gestao";

export interface Pessoa {
  id: string;
  nome: string;
  email: string;
  foto_url: string | null;
}

export interface Eu extends Pessoa {
  papeis: Papel[];
  permissoes: Record<Permissao, boolean>;
}

export interface UsuarioAdmin extends Pessoa {
  ativo: boolean;
  papeis: Papel[];
  criado_em: string;
  ultimo_acesso_em: string | null;
  desativado_em: string | null;
}

export interface Gestor {
  usuario: Pessoa;
  concedido_por: Pessoa | null;
  concedido_em: string;
}

export interface Evento {
  id: number;
  ocorrido_em: string;
  tipo: string;
  ator: Pessoa | null;
  alvo: Pessoa | null;
  detalhes: Record<string, unknown>;
  ip: string | null;
}

export interface PaginaEventos {
  eventos: Evento[];
  proximo: number | null;
}

export interface Dominio {
  dominio: string;
  adicionado_por: Pessoa | null;
  adicionado_em: string;
}

export interface Provedores {
  teste: boolean;
  google: boolean;
}

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

const MENSAGEM_PADRAO = "Não foi possível concluir. Tente de novo em instantes.";

async function pedir<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(caminho, {
      ...opcoes,
      credentials: "same-origin",
      headers: {
        "X-Gerenciador": "1",
        ...(opcoes.body ? { "Content-Type": "application/json" } : {}),
        ...opcoes.headers,
      },
    });
  } catch {
    throw new ErroApi(0, "Sem conexão com o servidor. Confira se o sistema está ligado.");
  }
  if (resposta.status === 204) return undefined as T;
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const detalhe = corpo?.detail;
    throw new ErroApi(resposta.status, typeof detalhe === "string" ? detalhe : MENSAGEM_PADRAO);
  }
  return corpo as T;
}

const json = (dados: unknown) => JSON.stringify(dados);

export const api = {
  provedores: () => pedir<Provedores>("/api/auth/provedores"),
  entrarTeste: (email: string, nome: string) =>
    pedir<Eu>("/api/auth/teste/entrar", { method: "POST", body: json({ email, nome }) }),
  sair: () => pedir<void>("/api/auth/sair", { method: "POST" }),
  eu: () => pedir<Eu>("/api/eu"),

  usuarios: (busca?: string) =>
    pedir<UsuarioAdmin[]>(`/api/admin/usuarios${busca ? `?busca=${encodeURIComponent(busca)}` : ""}`),
  concederPapel: (id: string, papel: Papel) =>
    pedir<void>(`/api/admin/usuarios/${id}/papeis`, { method: "POST", body: json({ papel }) }),
  revogarPapel: (id: string, papel: Papel) =>
    pedir<void>(`/api/admin/usuarios/${id}/papeis/${papel}`, { method: "DELETE" }),
  desativar: (id: string) => pedir<void>(`/api/admin/usuarios/${id}/desativar`, { method: "POST" }),
  reativar: (id: string) => pedir<void>(`/api/admin/usuarios/${id}/reativar`, { method: "POST" }),

  gestores: () => pedir<Gestor[]>("/api/admin/gestores"),

  auditoria: (filtros: { tipo?: string; usuarioId?: string; antesDe?: number; limite?: number } = {}) => {
    const p = new URLSearchParams();
    if (filtros.tipo) p.set("tipo", filtros.tipo);
    if (filtros.usuarioId) p.set("usuario_id", filtros.usuarioId);
    if (filtros.antesDe) p.set("antes_de", String(filtros.antesDe));
    if (filtros.limite) p.set("limite", String(filtros.limite));
    const qs = p.toString();
    return pedir<PaginaEventos>(`/api/admin/auditoria${qs ? `?${qs}` : ""}`);
  },

  dominios: () => pedir<Dominio[]>("/api/admin/dominios"),
  adicionarDominio: (dominio: string) =>
    pedir<void>("/api/admin/dominios", { method: "POST", body: json({ dominio }) }),
  removerDominio: (dominio: string) =>
    pedir<void>(`/api/admin/dominios/${encodeURIComponent(dominio)}`, { method: "DELETE" }),
};
