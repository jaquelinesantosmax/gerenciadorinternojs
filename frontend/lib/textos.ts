// Textos das telas que dependem de códigos vindos do servidor.

import type { Evento, Papel } from "./api";

export const NOME_PAPEL: Record<Papel, string> = {
  adm_plataforma: "ADM da plataforma",
  gestor: "Gestor",
  criar_espacos: "Criar espaços",
};

export const DESCRICAO_PAPEL: Record<Papel, string> = {
  adm_plataforma: "Administra a plataforma inteira: domínios, usuários, papéis e auditoria.",
  gestor: "Acompanha qualquer espaço de equipe, com poderes de ADM do espaço. Nunca vê espaços pessoais.",
  criar_espacos: "Pode criar espaços de equipe e vira ADM de cada espaço que criar.",
};

export const ORDEM_PAPEIS: Papel[] = ["adm_plataforma", "gestor", "criar_espacos"];

export const TIPOS_EVENTO: Record<string, string> = {
  login: "Entrada",
  login_falha: "Entrada recusada",
  logout: "Saída",
  cadastro_automatico: "Cadastro no primeiro acesso",
  adm_instalacao: "ADM cadastrado na instalação",
  papel_concedido: "Papel concedido",
  papel_revogado: "Papel retirado",
  usuario_desativado: "Usuário desativado",
  usuario_reativado: "Usuário reativado",
  dominio_adicionado: "Domínio adicionado",
  dominio_removido: "Domínio removido",
  espaco_criado: "Espaço criado",
  membro_adicionado: "Membro adicionado",
  membro_papel_alterado: "Papel no espaço alterado",
  membro_removido: "Membro removido",
  item_excluido: "Item excluído",
  conclusao_com_bloqueio: "Conclusão com bloqueio aberto",
  anexo_excluido: "Anexo excluído",
  comentario_excluido: "Comentário excluído",
  time_criado: "Time criado",
  limite_anexos_alterado: "Limite de anexos alterado",
};

export const PRIORIDADES: Record<string, string> = { critica: "Crítica", alta: "Alta", media: "Média", baixa: "Baixa" };
export const ORDEM_PRIORIDADES = ["critica", "alta", "media", "baixa"];

export const NOME_PAPEL_ESPACO: Record<string, string> = {
  adm: "ADM do espaço",
  membro: "Membro",
  leitor: "Leitor",
  dono: "Dono",
};

export const DESCRICAO_PAPEL_ESPACO: Record<string, string> = {
  adm: "Configura o espaço, gerencia membros e faz tudo nos itens.",
  membro: "Cria, edita e vincula itens; exclui os próprios.",
  leitor: "Vê, comenta e anexa arquivos.",
};

export const MODELOS: Record<string, string> = {
  scrum: "Scrum",
  kanban: "Kanban",
  gestao_tarefas: "Gestão de tarefas",
};

export const DESCRICAO_MODELO: Record<string, string> = {
  scrum: "Backlog, sprints com início e fim, estimativa e burndown.",
  kanban: "Fluxo contínuo, com limite de itens por coluna.",
  gestao_tarefas: "Colunas por status, sem sprint nem limite.",
};

export const NOME_NIVEL: Record<string, string> = { epico: "Épico", padrao: "Item", subtarefa: "Subtarefa" };

const MOTIVOS_FALHA: Record<string, string> = {
  dominio_nao_autorizado: "domínio não autorizado",
  usuario_desativado: "usuário desativado",
};

function nomePapel(valor: unknown): string {
  return NOME_PAPEL[valor as Papel] ?? String(valor);
}

/** Frase da linha do tempo da auditoria, como "Ana Lima deu o papel Gestor a Bruno Reis". */
export function descreverEvento(e: Evento): string {
  const ator = e.ator?.nome ?? "Alguém";
  const alvo = e.alvo?.nome ?? "uma pessoa";
  const d = e.detalhes;
  switch (e.tipo) {
    case "login":
      return d.provedor === "teste" ? `${ator} entrou pelo login de teste` : `${ator} entrou`;
    case "login_falha":
      return `Entrada recusada para ${String(d.email ?? alvo)}: ${MOTIVOS_FALHA[String(d.motivo)] ?? String(d.motivo)}`;
    case "logout":
      return `${ator} saiu`;
    case "cadastro_automatico":
      return `${alvo} foi cadastrado no primeiro acesso`;
    case "adm_instalacao":
      return `${alvo} foi cadastrado como ADM da plataforma na instalação`;
    case "papel_concedido":
      return `${ator} deu o papel ${nomePapel(d.papel)} a ${alvo}`;
    case "papel_revogado":
      return `${ator} tirou o papel ${nomePapel(d.papel)} de ${alvo}`;
    case "usuario_desativado": {
      const n = Number(d.sessoes_encerradas ?? 0);
      const sessoes = n === 0 ? "nenhuma sessão aberta" : n === 1 ? "1 sessão encerrada" : `${n} sessões encerradas`;
      return `${ator} desativou ${alvo} (${sessoes})`;
    }
    case "usuario_reativado":
      return `${ator} reativou ${alvo}`;
    case "dominio_adicionado":
      return `${ator} autorizou o domínio ${String(d.dominio)}`;
    case "dominio_removido":
      return `${ator} removeu o domínio ${String(d.dominio)}`;
    case "espaco_criado":
      return `${ator} criou o espaço ${String(d.espaco)}`;
    case "membro_adicionado":
      return `${ator} adicionou ${alvo} ao espaço ${String(d.espaco)} como ${NOME_PAPEL_ESPACO[String(d.papel)] ?? d.papel}`;
    case "membro_papel_alterado":
      return `${ator} mudou o papel de ${alvo} em ${String(d.espaco)}: ${NOME_PAPEL_ESPACO[String(d.de)] ?? d.de} → ${NOME_PAPEL_ESPACO[String(d.para)] ?? d.para}`;
    case "membro_removido":
      return `${ator} tirou ${alvo} do espaço ${String(d.espaco)}`;
    case "item_excluido":
      return `${ator} excluiu o item ${String(d.item)} (${String(d.resumo ?? "")})`;
    case "conclusao_com_bloqueio":
      return `${ator} concluiu ${String(d.item)} com bloqueio aberto (${(d.bloqueios as string[] | undefined)?.join(", ") ?? ""})`;
    case "anexo_excluido":
      return `${ator} excluiu o anexo ${String(d.arquivo)} de ${String(d.item)}`;
    case "comentario_excluido":
      return `${ator} excluiu um comentário de ${alvo} em ${String(d.item)}`;
    case "time_criado":
      return `${ator} criou o time ${String(d.time)}`;
    case "limite_anexos_alterado":
      return `${ator} mudou o limite de anexos de ${String(d.de)} MB para ${String(d.para)} MB`;
    default:
      return TIPOS_EVENTO[e.tipo] ?? e.tipo;
  }
}

/** Eventos que pedem atenção aparecem com destaque na linha do tempo. */
export function eventoDeAlerta(tipo: string): boolean {
  return ["login_falha", "usuario_desativado", "conclusao_com_bloqueio", "item_excluido"].includes(tipo);
}
