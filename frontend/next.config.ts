import type { NextConfig } from "next";

// As telas chamam /api/... no mesmo endereço; o Next repassa para o servidor Python.
// Assim o cookie de sessão fica no mesmo site das telas.
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  poweredByHeader: false,
  // O selo do Next no canto da tela cobria o botão Sair durante o desenvolvimento.
  devIndicators: false,
  async rewrites() {
    return [{ source: "/api/:caminho*", destination: `${backend}/api/:caminho*` }];
  },
};

export default config;
