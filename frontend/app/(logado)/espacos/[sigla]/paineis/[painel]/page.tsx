"use client";

import { useParams } from "next/navigation";
import { VisaoEspaco } from "@/components/VisaoEspaco";

/** Painel: os itens de uma frente do espaço. Status, campos e workflow são os do espaço. */
export default function PaginaPainel() {
  const { sigla, painel } = useParams<{ sigla: string; painel: string }>();
  return <VisaoEspaco sigla={sigla} painelId={painel} />;
}
