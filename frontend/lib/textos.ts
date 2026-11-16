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
};

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
    default:
      return TIPOS_EVENTO[e.tipo] ?? e.tipo;
  }
}

/** Eventos que pedem atenção aparecem com destaque na linha do tempo. */
export function eventoDeAlerta(tipo: string): boolean {
  return tipo === "login_falha" || tipo === "usuario_desativado";
}
