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
  | "acessar_espaco_gestao"
  | "gerenciar_times_provisorios"
  | "definir_limite_anexos";

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

// --- Etapa 2 ---

export type DocTexto = { type: "doc"; content?: unknown[] };
export type PermissaoEspaco =
  | "ver"
  | "criar_itens"
  | "editar_itens"
  | "comentar"
  | "anexar"
  | "vincular"
  | "excluir_qualquer_item"
  | "excluir_proprios_itens"
  | "excluir_qualquer_anexo"
  | "editar_qualquer_comentario"
  | "configurar"
  | "gerenciar_membros"
  | "criar_paineis";

export interface Ref {
  id: string;
  nome: string;
}
export interface TimeItem extends Ref {
  ativo: boolean;
}
export interface TipoRef extends Ref {
  nivel: "epico" | "padrao" | "subtarefa";
  padrao: boolean;
}
export interface StatusRef extends Ref {
  categoria: "a_fazer" | "em_andamento" | "concluido";
}
export interface EspacoResumo {
  id: string;
  sigla: string;
  nome: string;
  tipo: "projeto" | "pessoal";
  modelo: string | null;
  meu_papel: string;
  paineis: Ref[];
}
export interface EspacoDetalhe extends EspacoResumo {
  descricao: string | null;
  criado_em: string;
  permissoes: Record<PermissaoEspaco, boolean>;
  paineis: Ref[];
  tipos: TipoRef[];
  status: StatusRef[];
  origens: Ref[];
}
export interface Membro {
  usuario: Pessoa;
  papel: "adm" | "membro" | "leitor";
  adicionado_em: string;
}
export type TipoCampo =
  | "texto_curto"
  | "texto_longo"
  | "numero"
  | "moeda"
  | "data"
  | "data_hora"
  | "url"
  | "lista_unica"
  | "lista_multipla"
  | "lista_cascata"
  | "pessoa"
  | "sim_nao";
export interface OpcaoCampo {
  id?: string;
  nome: string;
  ativo?: boolean;
  filhos?: OpcaoCampo[];
}
export interface Campo {
  id: string;
  nome: string;
  tipo: TipoCampo;
  obrigatorio: boolean;
  tipos_item: string[];
  config: { opcoes?: OpcaoCampo[]; moeda?: string; varias?: boolean; texto?: string };
  ativo: boolean;
}
export interface ItemLinha {
  id: string;
  chave: string;
  resumo: string;
  tipo: Ref;
  nivel: string;
  status: StatusRef;
  prioridade: string;
  responsavel: Pessoa | null;
  data_entrega: string;
  painel: Ref | null;
}
export interface ItemCurto {
  chave: string;
  resumo: string;
  tipo: string;
  status: string;
  status_categoria: string;
}
export interface Anexo {
  id: string;
  nome_arquivo: string;
  tipo_mime: string;
  tamanho: number;
  enviado_por: Pessoa | null;
  enviado_em: string;
  link: string;
  pre_visualizacao: boolean;
  pode_excluir: boolean;
}
export interface Vinculo {
  id: string;
  tipo: string;
  rotulo: string;
  chave: string;
  acesso_restrito: boolean;
  resumo: string | null;
  status: string | null;
  status_categoria: string | null;
  bloqueio_aberto: boolean;
}
export interface ItemDetalhe {
  id: string;
  chave: string;
  espaco: Ref;
  espaco_sigla: string;
  tipo: Ref;
  nivel: string;
  resumo: string;
  descricao: DocTexto | null;
  status: StatusRef;
  prioridade: string;
  responsavel: Pessoa | null;
  relator: Pessoa | null;
  co_responsaveis: Pessoa[];
  time: Ref;
  data_inicio: string;
  data_entrega: string;
  data_real_entrega: string | null;
  justificativa_atraso: string | null;
  estimativa: string | null;
  pai: ItemCurto | null;
  filhos: ItemCurto[];
  painel: Ref | null;
  origem: Ref | null;
  categorias: string[];
  valores: Record<string, unknown>;
  criado_em: string;
  atualizado_em: string;
  anexos: Anexo[];
  vinculos: Vinculo[];
  permissoes: Record<PermissaoEspaco, boolean>;
  pode_excluir: boolean;
}
export type DadosItem = Record<string, unknown>;
export interface OpcoesItem {
  responsaveis: Pessoa[];
  membros: Pessoa[];
  times: Ref[];
  campos: Campo[];
  categorias: string[];
  prioridades: Record<string, string>;
  tipos_campo: Record<TipoCampo, string>;
  tipos_vinculo: Record<string, [string, string]>;
  moedas: Record<string, string>;
}
export interface EventoAtividade {
  tipo: "comentario" | "historico";
  id: string;
  quando: string;
  autor: Pessoa | null;
  corpo?: DocTexto | null;
  editado_em?: string | null;
  excluido_em?: string | null;
  excluido_por?: Pessoa | null;
  pode_editar?: boolean;
  campo?: string | null;
  valor_anterior?: string | null;
  valor_novo?: string | null;
}

export class ErroApi extends Error {
  constructor(
    public status: number,
    mensagem: string,
    /** Avisos que pedem confirmação: "concluir_bloqueado", "bloqueio_circular". */
    public codigo?: string,
    public dados?: Record<string, unknown>,
  ) {
    super(mensagem);
  }
}

const MENSAGEM_PADRAO = "Não foi possível concluir. Tente de novo em instantes.";

async function pedir<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  const ehFormulario = typeof FormData !== "undefined" && opcoes.body instanceof FormData;
  try {
    resposta = await fetch(caminho, {
      ...opcoes,
      credentials: "same-origin",
      headers: {
        "X-Gerenciador": "1",
        ...(opcoes.body && !ehFormulario ? { "Content-Type": "application/json" } : {}),
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
    if (typeof detalhe === "string") throw new ErroApi(resposta.status, detalhe);
    if (detalhe && typeof detalhe === "object" && typeof detalhe.mensagem === "string") {
      throw new ErroApi(resposta.status, detalhe.mensagem, detalhe.codigo, detalhe);
    }
    if (resposta.status === 422) throw new ErroApi(422, "Algum campo está com valor inválido.");
    throw new ErroApi(resposta.status, MENSAGEM_PADRAO);
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

  // --- Etapa 2 ---
  times: (todos = false) => pedir<TimeItem[]>(`/api/times${todos ? "?todos=true" : ""}`),
  criarTime: (nome: string) => pedir<TimeItem>("/api/admin/times", { method: "POST", body: json({ nome }) }),
  alterarTime: (id: string, dados: { nome?: string; ativo?: boolean }) =>
    pedir<void>(`/api/admin/times/${id}`, { method: "PATCH", body: json(dados) }),
  limiteAnexos: () => pedir<{ limite_mb: number }>("/api/admin/limite-anexos"),
  definirLimiteAnexos: (limite_mb: number) =>
    pedir<void>("/api/admin/limite-anexos", { method: "PUT", body: json({ limite_mb }) }),

  espacos: () => pedir<EspacoResumo[]>("/api/espacos"),
  criarEspaco: (dados: { tipo: string; nome: string; sigla: string; modelo?: string | null }) =>
    pedir<EspacoDetalhe>("/api/espacos", { method: "POST", body: json(dados) }),
  espaco: (sigla: string) => pedir<EspacoDetalhe>(`/api/espacos/${sigla}`),
  editarEspaco: (sigla: string, dados: { nome?: string; descricao?: string }) =>
    pedir<EspacoDetalhe>(`/api/espacos/${sigla}`, { method: "PATCH", body: json(dados) }),
  membros: (sigla: string) => pedir<Membro[]>(`/api/espacos/${sigla}/membros`),
  adicionarMembro: (sigla: string, usuario_id: string, papel: string) =>
    pedir<void>(`/api/espacos/${sigla}/membros`, { method: "POST", body: json({ usuario_id, papel }) }),
  mudarPapelMembro: (sigla: string, usuarioId: string, papel: string) =>
    pedir<void>(`/api/espacos/${sigla}/membros/${usuarioId}`, { method: "PATCH", body: json({ papel }) }),
  removerMembro: (sigla: string, usuarioId: string) =>
    pedir<void>(`/api/espacos/${sigla}/membros/${usuarioId}`, { method: "DELETE" }),
  pessoas: (busca: string) => pedir<Pessoa[]>(`/api/pessoas?busca=${encodeURIComponent(busca)}`),

  criarOpcaoEspaco: (sigla: string, lista: "paineis" | "tipos" | "origens", nome: string) =>
    pedir<{ id: string; nome: string }>(`/api/espacos/${sigla}/${lista}`, { method: "POST", body: json({ nome }) }),
  renomearOpcaoEspaco: (sigla: string, lista: "paineis" | "tipos", id: string, nome: string) =>
    pedir<void>(`/api/espacos/${sigla}/${lista}/${id}`, { method: "PATCH", body: json({ nome }) }),
  excluirOpcaoEspaco: (sigla: string, lista: "paineis" | "tipos" | "origens", id: string) =>
    pedir<void>(`/api/espacos/${sigla}/${lista}/${id}`, { method: "DELETE" }),

  campos: (sigla: string, todos = false) => pedir<Campo[]>(`/api/espacos/${sigla}/campos${todos ? "?todos=true" : ""}`),
  criarCampo: (sigla: string, dados: Omit<Campo, "id" | "ativo">) =>
    pedir<Campo>(`/api/espacos/${sigla}/campos`, { method: "POST", body: json(dados) }),
  editarCampo: (sigla: string, id: string, dados: Partial<Omit<Campo, "id" | "tipo">>) =>
    pedir<Campo>(`/api/espacos/${sigla}/campos/${id}`, { method: "PATCH", body: json(dados) }),

  itens: (sigla: string, filtros: Record<string, string | undefined> = {}) => {
    const p = new URLSearchParams();
    Object.entries(filtros).forEach(([k, v]) => v && p.set(k, v));
    const qs = p.toString();
    return pedir<ItemLinha[]>(`/api/espacos/${sigla}/itens${qs ? `?${qs}` : ""}`);
  },
  opcoesItem: (sigla: string) => pedir<OpcoesItem>(`/api/espacos/${sigla}/opcoes-item`),
  criarItem: (sigla: string, dados: DadosItem) =>
    pedir<ItemDetalhe>(`/api/espacos/${sigla}/itens`, { method: "POST", body: json({ dados }) }),
  item: (chave: string) => pedir<ItemDetalhe>(`/api/itens/${chave}`),
  editarItem: (chave: string, dados: DadosItem, confirmar_bloqueio = false) =>
    pedir<ItemDetalhe>(`/api/itens/${chave}`, { method: "PATCH", body: json({ dados, confirmar_bloqueio }) }),
  excluirItem: (chave: string) => pedir<void>(`/api/itens/${chave}`, { method: "DELETE" }),
  clonarItem: (chave: string, opcoes: { copiar_comentarios: boolean; copiar_anexos: boolean }) =>
    pedir<ItemDetalhe>(`/api/itens/${chave}/clonar`, { method: "POST", body: json(opcoes) }),
  buscarItens: (q: string) => pedir<ItemCurto[]>(`/api/itens/busca?q=${encodeURIComponent(q)}`),

  atividade: (chave: string, filtro: "tudo" | "comentarios" | "historico") =>
    pedir<EventoAtividade[]>(`/api/itens/${chave}/atividade?filtro=${filtro}`),
  comentar: (chave: string, corpo: DocTexto) =>
    pedir<EventoAtividade>(`/api/itens/${chave}/comentarios`, { method: "POST", body: json({ corpo }) }),
  editarComentario: (chave: string, id: string, corpo: DocTexto) =>
    pedir<void>(`/api/itens/${chave}/comentarios/${id}`, { method: "PATCH", body: json({ corpo }) }),
  excluirComentario: (chave: string, id: string) =>
    pedir<void>(`/api/itens/${chave}/comentarios/${id}`, { method: "DELETE" }),

  enviarAnexos: (chave: string, arquivos: File[]) => {
    const formulario = new FormData();
    arquivos.forEach((a) => formulario.append("arquivos", a, a.name));
    return pedir<Anexo[]>(`/api/itens/${chave}/anexos`, { method: "POST", body: formulario });
  },
  excluirAnexo: (chave: string, id: string) => pedir<void>(`/api/itens/${chave}/anexos/${id}`, { method: "DELETE" }),

  vincular: (chave: string, dados: { tipo: string; sentido: string; chave: string; confirmar_ciclo?: boolean }) =>
    pedir<Vinculo[]>(`/api/itens/${chave}/vinculos`, { method: "POST", body: json(dados) }),
  desvincular: (chave: string, id: string) => pedir<void>(`/api/itens/${chave}/vinculos/${id}`, { method: "DELETE" }),

  dominios: () => pedir<Dominio[]>("/api/admin/dominios"),
  adicionarDominio: (dominio: string) =>
    pedir<void>("/api/admin/dominios", { method: "POST", body: json({ dominio }) }),
  removerDominio: (dominio: string) =>
    pedir<void>(`/api/admin/dominios/${encodeURIComponent(dominio)}`, { method: "DELETE" }),
};
