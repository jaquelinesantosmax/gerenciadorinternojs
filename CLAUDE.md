# Gerenciador — instruções para o Claude

## O projeto

O Gerenciador é um sistema interno da Jusbrasil no modelo do Jira (projetos, tarefas e service desk) que vai substituir o Jira em algumas equipes. É usado só por equipes Jusbrasil e Digesto, sem venda externa.

A dona do projeto é a Jaqueline, da área de Operações (LOps B2B). Ela não é desenvolvedora e nunca usou Git ou GitHub. Explique cada passo em linguagem simples, em português, e diga exatamente o que ela precisa clicar ou digitar.

O desenho foi fechado em outra conversa. Leia estes arquivos antes de qualquer trabalho:

- `docs/decisoes-de-desenho.md`: decisões de produto, regras e a ordem de construção.
- `docs/matriz-de-permissoes.md`: quem pode fazer o quê, célula a célula.
- `docs/previa-detalhe-do-item-v3.html`: referência visual aprovada para todas as telas.

Se algum ponto não estiver nesses arquivos, pergunte. Não preencha lacunas por conta própria.

## Regras de trabalho

1. Nunca tome uma decisão de produto sem perguntar à Jaqueline antes. Decisões técnicas internas podem ser tomadas, mas conte quais foram e por quê.
2. Você é o desenvolvedor e também valida as próprias funcionalidades. Escreva testes automatizados para cada funcionalidade e rode todos antes de dizer que algo está pronto. Releia o código alterado procurando erros antes de entregar.
3. Não altere nada no Jira da empresa (jus.atlassian.net). Ele serve só de referência, para leitura.
4. Visual: Design System Jusbrasil.
   - Fonte Inter.
   - Cores: #007A5F (principal), #004D3B (fundos de destaque), #63B424 (botões de ação), #F1F4F8 (fundos), #101729 (texto) e branco sobre fundos escuros.
   - Títulos: H1 22px Semibold #007A5F, H2 18px Semibold #007A5F, H3 14px Medium #007A5F. Corpo 14px Regular #101729. Legenda 12px Light #383F49.
   - Bordas arredondadas: 8px em cards, 12px em painéis e 20px em etiquetas.
   - Só ícones de contorno. Sem gradientes, sem sombras decorativas e sem sublinhado sob títulos.
   - A identidade segue a prévia v3 (ficha com faixa lateral escura e linha do tempo) e foge do visual genérico de interfaces geradas por IA.
5. Todos os textos das telas em português do Brasil.
6. Ao fim de cada etapa, mostre como ligar o sistema e abrir no navegador, e dê um roteiro curto do que testar.
7. Ao fim de cada etapa, lembre a Jaqueline de pedir à TI a credencial OAuth do Google da empresa (login e agenda), enquanto ela não tiver chegado.

## Stack

- Backend: Python (pasta `backend`).
- Frontend: Next.js com TypeScript (pasta `frontend`).
- Banco de dados: PostgreSQL.
- `infra`: scripts para ligar o banco e o sistema no computador da Jaqueline com um comando.
- Hospedagem: ainda não definida. Por enquanto tudo roda localmente. O armazenamento de anexos deve ser construído de forma trocável.

## Ambiente local

- Computador Windows, sem permissão de administrador garantida. Nada pode depender de instalação com administrador.
- O projeto fica em `C:\Users\Jaqueline.santos\projetos\gerenciadorinternojs`, fora do OneDrive, para evitar travamentos de sincronização. O original dos documentos continua no OneDrive. Se ela atualizar um documento lá, copie para `docs/`.
- Ferramentas portáteis (Node.js e PostgreSQL) ficam em `C:\Users\Jaqueline.santos\ferramentas`, fora do repositório.
- Python 3.12 e Git estão instalados pelo winget.
- O login de desenvolvimento é um login de teste, feito para ser trocado pelo login Google sem mexer no resto do sistema.

## Repositório

- GitHub: github.com/jaquelinesantosmax/gerenciadorinternojs (privado, na conta pessoal da Jaqueline).
- Mais tarde ele será transferido para a organização jusbrasil. É preciso pedir à TI a permissão ou a transferência antes dos testes externos.
- Nunca envie ao GitHub senhas, arquivos `.env`, dados do banco ou anexos.

## Ordem de construção

A ordem completa está em `docs/decisoes-de-desenho.md`, seção "Ordem de construção".

- Etapa 1 – Fundação: entregue em 16/11 (login de teste, cadastro automático, sessão, papéis da plataforma e auditoria).
- Etapa 2 – Espaços e itens: entregue em 16/11 para validação da Jaqueline (espaços de projeto e pessoais, membros, painéis, tipos, campos padronizados e personalizados, itens, detalhe do item, comentários, anexos e itens relacionados).
- Etapa 3a – Status, workflow e quadros: entregue em 16/11 para validação (status por espaço, status próprios com aviso de nome parecido, fluxo de transições, quadros Kanban e simples com colunas e limite, quadro por painel, abas Lista, Quadro e Gantt).
- Etapa 3b – Scrum e métricas: entregue em 16/11 para validação (backlog e sprints, várias sprints ativas, estimativa em pontos, horas ou contagem, burndown, velocidade, relatório de sprint, fluxo acumulado e tempo de ciclo).
- Etapa 4 – Permissões completas: entregue em 16/11 para validação (matriz por espaço com Gestor, suporte, espaço aberto e compartilhado; Times com membros e acesso por time, vale o maior papel; Gestor acompanha; suporte do ADM da plataforma por 4h com motivo e auditoria; Solicitar acesso pelo espaço e pelo item restrito, com aprovação escolhendo o papel; compartilhamento do espaço pessoal só leitura; página Explorar espaços). Próxima: Etapa 5 (service desk e SLA).
- Gráficos seguem a skill dataviz: cores validadas pelo validador (azul #2a78d6, laranja #eb6834, verde #007a5f), legenda, dica ao passar o mouse e "Ver tabela".
- O servidor roda sem recarga automática (no Windows ela travava). Depois de mudar código do servidor, rode infra\desligar.cmd e infra\ligar.cmd.
- Ficou para depois, de propósito: mover item entre espaços (a tabela de apelidos já existe) e Observar item (Etapa 8). Avisar o ADM de pedidos de acesso novos fica para Notificações (Etapa 8); por enquanto os pedidos aparecem nas configurações do espaço.
- Dados que dependem das regras (status, fluxo, quadros, histórico) não vão nas migrações: ficam no comando `python -m gerenciador.cli preparar-dados`, que o infra\ligar roda depois das migrações.
- Ao registrar uma decisão nova em `docs/decisoes-de-desenho.md`, atualize também as duas cópias no OneDrive da Jaqueline, se elas não tiverem mudado por lá.
