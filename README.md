# Gerenciador

Sistema interno da Jusbrasil para projetos, tarefas e service desk, no modelo do Jira. Por enquanto roda só no computador da Jaqueline.

## Pastas

| Pasta | O que tem |
| --- | --- |
| `backend` | O servidor do sistema, em Python. Guarda as regras e conversa com o banco de dados. |
| `frontend` | As telas, em Next.js com TypeScript. |
| `infra` | Scripts para ligar, desligar e testar o sistema com dois cliques. |
| `docs` | Desenho do sistema: decisões, matriz de permissões e prévia visual. |

## Como ligar o sistema

1. Abra a pasta `infra` no Explorador de Arquivos.
2. Clique duas vezes em **`ligar.cmd`**. Uma janela preta mostra o andamento. Na primeira vez, ela instala as bibliotecas e leva alguns minutos.
3. Quando aparecer "Pronto!", o navegador abre em **http://localhost:3000**. A janela preta pode ser fechada.

Para desligar, clique duas vezes em **`infra\desligar.cmd`**.

## Outros scripts da pasta `infra`

| Script | Para quê |
| --- | --- |
| `testar.cmd` | Roda todos os testes automáticos do servidor e das telas. |
| `criar-adm.cmd` | Cadastra um ADM da plataforma direto no banco (uso na instalação). |
| `ligar-banco.ps1` | Liga só o banco de dados (usado pelos testes). |

Se algo der errado, os registros ficam em `infra\logs`.

## Login

Enquanto a credencial Google da empresa não chega, o sistema usa um **login de teste**: entra qualquer e-mail @jusbrasil.com.br ou @digesto.com.br, sem senha. Ele só funciona no ambiente de desenvolvimento e será trocado pelo botão Entrar com Google, sem mudar o resto do sistema.

## O que precisa estar instalado

Nenhum destes precisa de permissão de administrador.

- Git e Python 3.12 (instalados pelo winget, só para o usuário).
- Node.js e PostgreSQL, em versão portátil, em `C:\Users\Jaqueline.santos\ferramentas`.

## Para quem desenvolve

- Servidor: FastAPI, SQLAlchemy e Alembic (migrações em `backend/migracoes`). Testes com pytest em `backend/testes`, num banco separado (`gerenciador_teste`).
- Telas: Next.js (App Router). Testes com Vitest e Testing Library. As telas chamam `/api/...`, e o Next repassa esses pedidos ao servidor.
- A configuração local, incluindo a senha do banco, fica em `infra/.env`. Esse arquivo é criado sozinho e nunca vai para o GitHub.
- Login: cada forma de entrar entrega uma identidade confirmada para `gerenciador/identidade.py:entrar()`, que cuida do resto (domínio, cadastro automático, sessão e auditoria). O login Google vai ser só mais uma forma de entrar.
