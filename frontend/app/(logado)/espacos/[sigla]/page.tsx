"use client";

import { useParams } from "next/navigation";
import { VisaoEspaco } from "@/components/VisaoEspaco";

export default function PaginaEspaco() {
  const { sigla } = useParams<{ sigla: string }>();
  return <VisaoEspaco sigla={sigla} />;
}
