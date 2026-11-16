# Gerenciador de Projetos e Tarefas — Decisões de desenho

Atualizado em 16/11/2026 · Jaqueline

Registro de todas as decisões de desenho do Gerenciador, atualizado a cada decisão nova. É a base para a escrita do código. A matriz completa de permissões está em matriz-de-permissoes.md, e a referência visual aprovada em previa-detalhe-do-item-v3.html, ambos nesta pasta.

## Visão e escopo

- Objetivo: descontinuar o uso do Jira por equipes específicas, com um sistema no modelo do Jira para projetos, tarefas e service desk.
- Público: só equipes Jusbrasil e Digesto, em formato SaaS (sem venda externa).
- Referência: o Jira genérico e suas funcionalidades. Os projetos atuais (JSOL, TLF, IL, LEXJS, SJS e outros) servem de referência, sem amarrar o desenho a eles.
- Migração de dados do Jira: fora de prioridade por enquanto.
- Entregáveis: permissionamento hierárquico; gerenciamento de campos; campos padronizados obrigatórios e opcionais; visões Kanban, Gantt e Lista; filtros personalizados; espaços e painéis; Espaço da Gestão; conexão com GitHub, Slack e e-mail; painel de automações em canvas; chat assistente de IA.
- MVP: permissões, campos, espaços, painéis e as três visões como base, seguidos dos demais entregáveis.

Regras de trabalho com o Claude

- O Jira pode ser lido como referência, sem alterar nada no ambiente.
- Nenhuma decisão é tomada sem perguntar à Jaqueline.
- O Claude atua como desenvolvedor e faz a validação das próprias funcionalidades; os testes de aceite são feitos pelas equipes.
- Desenho numa conversa do claude.ai; código com o Claude Code.

## Stack e infraestrutura

| Camada | Decisão |
| --- | --- |
| Backend | Python |
| Frontend | Next.js com TypeScript |
| Banco de dados | PostgreSQL |
| Hospedagem | Definida no final do projeto; até lá, tudo roda no computador da Jaqueline; armazenamento de anexos construído de forma trocável |
| Visual | Design System Jusbrasil, com identidade própria e fora do padrão genérico de interfaces geradas por IA. Referência aprovada: a prévia v3 do detalhe do item (ficha com faixa lateral escura e linha do tempo) |
| Desenvolvimento | Claude Code (app desktop), repositório privado github.com/jaquelinesantosmax/gerenciadorinternojs; login de teste até a credencial Google da TI chegar |

Base da escolha: as linguagens homologadas pela empresa (Scala, Java, Python, Go e JS, com Next.js/TypeScript já aprovado em apps internos) e o padrão de fato de PostgreSQL no Cloud SQL.

Design System Jusbrasil: fonte Inter; títulos H1 22px Semibold #007A5F, H2 18px Semibold #007A5F, H3 14px Medium #007A5F, corpo 14px Regular #101729, legenda 12px Light #383F49; cores #007A5F (principal), #004D3B (fundos de destaque), #63B424 (botões de ação), #F1F4F8 (fundos), #101729 (texto), branco sobre fundos escuros; bordas de 8px em cards, 12px em painéis e 20px em etiquetas; só ícones de contorno, sem gradientes, sem sombras decorativas e sem sublinhado sob títulos.

## Login e usuários

- Login por SSO com a conta Google da empresa; sem senha na ferramenta.
- Domínios autorizados: jusbrasil.com.br e digesto.com.br.
- Cadastro automático no primeiro login, com nome, e-mail e foto do Google; a pessoa entra sem acesso a nenhum espaço.
- Sessão de 15 dias, guardada em cookie protegido; todo login, falha e logout vai para a auditoria.
- Sem sincronização com o diretório do Google por enquanto. Para cobrir desligamentos, o ADM da plataforma pode desativar um usuário e encerrar todas as sessões dele na hora.
- O primeiro ADM da plataforma é cadastrado manualmente na instalação.
- Decidido em 16/11: depois da instalação, só um ADM da plataforma pode dar ou tirar o papel de ADM da plataforma, com registro na auditoria; a plataforma nunca fica sem ADM.
- Decidido em 16/11: a sessão de 15 dias renova a cada uso e só cai depois de 15 dias seguidos sem uso.
- Decidido em 16/11: o ADM da plataforma pode reativar um usuário desativado; a pessoa volta com os mesmos papéis e acessos, com registro na auditoria.
- Decidido em 16/11: ao remover um domínio autorizado, quem tem e-mail daquele domínio sai do sistema na hora e não consegue mais entrar; cadastros e papéis ficam guardados caso o domínio volte, e a remoção vai para a auditoria com o número de sessões encerradas.
- Decidido em 16/11: quem entra sem acesso a nenhum espaço vê o aviso "Você ainda não tem acesso a nenhum espaço. Peça acesso ao ADM do espaço em que vai trabalhar.", com o botão Criar espaço pessoal (a partir da Etapa 2).
- Dependência externa: credenciais OAuth criadas no Google Cloud da empresa, com endereços de retorno por ambiente. Até lá, o desenvolvimento usa um login de teste.

## Permissões

A versão oficial, célula a célula, está em matriz-de-permissoes.md. Resumo:

- Plataforma: ADM da plataforma, Gestor, usuário com permissão de criar espaços e usuário comum.
- Gestor: atribuído pelo ADM da plataforma ou por outro Gestor; atua em qualquer espaço de equipe que escolher, privado ou aberto, sem ser adicionado, com poderes equivalentes aos de ADM do espaço; nunca acessa espaços pessoais. A administração terá a lista de Gestores com quem concedeu e quando, e cada concessão vai para a auditoria.
- Espaço de projeto: ADM do espaço, Membro e Leitor. Espaço de service desk: ADM do espaço, Agente e Solicitante.
- Papéis fixos por espaço; a mesma pessoa pode ter papéis diferentes em espaços diferentes.
- Espaços são privados por padrão; o ADM pode marcar como aberto para leitura, comentários e anexos de toda a empresa.
- O ADM do espaço vê quais Gestores acompanham o espaço.
- Acesso de um time inteiro de uma vez; quem entra ou sai do time ganha ou perde o acesso.
- Times: criados por quem é ADM de algum espaço ou Gestor; editados por quem criou, Gestor ou ADM da plataforma. Lista única para toda a ferramenta.
- Espaço pessoal: qualquer usuário cria; estrutura simplificada como o quadro "Processos e projetos", com os mesmos campos obrigatórios; compartilhamento sempre só leitura; fora do alcance do Gestor e do suporte do ADM da plataforma.
- Solicitar acesso: o pedido vai aos ADMs do espaço, que aprovam escolhendo o papel, sem papel pré-selecionado.
- O ADM da plataforma entra em qualquer espaço de equipe para suporte, com registro na auditoria.

## Estrutura: espaços, quadros, itens e campos

Espaços

- Tipos: projeto, service desk e pessoal. Na criação, o ADM escolhe um modelo (Scrum, Kanban, Gestão de tarefas ou Service desk) que já traz workflow, campos e um quadro.
- O espaço guarda itens, campos e workflow; um espaço pode ter vários quadros sobre os mesmos itens (como o TLF, com Kanban e Sprint).

Painéis

- Painel é um sub-espaço dentro de um espaço, como as frentes do projeto JSOL (Estratégico - Operações Jusbrasil Soluções): Suporte B2B, Legal Ops, Salesforce Soluções, Defesa AI e MC&I. No Jira, cada frente é um quadro Kanban com filtro por etiqueta (ex.: Suporte B2B = etiqueta "suporte").
- Dashboards (páginas com gráficos e contadores) são um recurso separado dos painéis, com seção própria abaixo.
- Painéis são opcionais: um espaço pode não ter nenhum e funcionar direto (ex.: Legal Experts JS). Quando existem, o item indica seu painel pelo campo "Painel" e pertence a um único painel; nesses espaços o campo é obrigatório, e nos espaços sem painéis ele não aparece.
- Painéis não têm membros próprios: quem tem acesso ao espaço vê todos os painéis dele.
- Status, campos e workflow ficam no nível do espaço; cada painel tem apenas quadro e colunas próprios.
- Painéis são criados pelo ADM do espaço e pelo Gestor.

Quadros e visões

- Scrum: backlog, sprints com início, fim e objetivo, estimativa por pontos, horas ou contagem de itens, burndown, velocidade e relatório de sprint.
- Kanban: fluxo contínuo, limite de itens por coluna com alerta, backlog opcional, fluxo acumulado e tempo de ciclo.
- Simples: colunas por status, sem sprint nem limite, para acompanhamento de tarefas.
- Coluna do quadro não é o mesmo que status: uma coluna pode agrupar vários status.
- Lista e Gantt valem para qualquer quadro; no Gantt, vínculos "Bloqueia" aparecem como setas de dependência.

Itens

- Hierarquia: Épico > História, Tarefa ou Bug > Subtarefa. O ADM do espaço pode criar tipos próprios (como "Processo" no LEXJS).
- Item que muda de espaço guarda a chave antiga como apelido, para não quebrar vínculos com o GitHub.

Campos padronizados

| Obrigatórios | Opcionais |
| --- | --- |
| Resumo, Tipo, Espaço, Relator (automático), Status, Responsável, Prioridade, Time, Data de início e Data de entrega | Descrição, Data real da entrega, Co-responsáveis, Categorias, Pai, Itens relacionados, Anexos, Origem da solicitação, Estimativa (story points) e Justificativa do atraso |

- Justificativa do atraso passa a ser obrigatória quando a entrega real passa da data de entrega.
- Estimativa (story points) pode ficar oculta em espaços só Kanban.
- No service desk, a Data de início é preenchida com a data de abertura; os campos de gestão não aparecem para quem abre e são exigidos quando o ticket sai da fila para atuação; a Data de entrega vem do SLA de resolução.
- Os demais campos são personalizados, criados pelo ADM do espaço.

## Status e workflow

- Status é obrigatório. Padrão da plataforma: Backlog, A fazer, Em andamento, Em validação, Aguardando terceiros, Bloqueado, Concluído e Cancelado.
- Status padrão são mantidos pelo ADM da plataforma. Status próprios são criados pelo ADM do espaço ou Gestor e só existem naquele espaço: mudanças num espaço não poluem os demais.
- O ADM escolhe quais status, padrão e próprios, ficam disponíveis no espaço e define as transições do workflow, como no Jira.
- Todo status pertence a uma categoria (A fazer, Em andamento ou Concluído), base para painéis, Espaço da Gestão e SLA entre espaços.
- Nome parecido com um status existente gera aviso antes de salvar (evita casos como "BLOCKED" e "Bloqueado" no TLF).
- Status em uso só é apagado depois de mover os itens.
- O ADM da plataforma pode promover um status de espaço a padrão, que passa a ficar disponível como opção, sem ser imposto.
- Concluir item ainda bloqueado: permitido, com alerta listando os bloqueios e confirmação registrada no histórico, em todos os workflows.

## Itens relacionados e anexos

Itens relacionados

- Sete tipos fixos, sem criação de novos: Bloqueia / é bloqueado por; Relacionado a; Duplica / é duplicado por; Clona / é clonado de; Causa / é causado por; Dividido em / dividido de; Escalado para / é escalação de.
- Vínculo sempre bidirecional e entre espaços diferentes; separado da hierarquia Pai e filho.
- Aparece no item, como coluna e filtro na Lista, como ícone de bloqueio no card do Kanban e como seta no Gantt.
- Clonar um item cria o vínculo "Clona" automaticamente.
- Item em espaço sem acesso: chave visível, marca "acesso restrito" e botão Solicitar acesso.
- Sem links externos (URL, Confluence, Google Docs) no item.
- Validações: sem vínculo com o próprio item, sem vínculo repetido, aviso de bloqueio circular.

Anexos

- Padrão do Jira Cloud: 1 GB por arquivo, ajustável até 2 GB pelo ADM da plataforma; sem bloqueio por tipo de arquivo.
- Vários arquivos de uma vez, arrastar e soltar, colar print; imagens também na descrição e nos comentários.
- Pré-visualização de imagens comuns e PDF; HTML, SVG e executáveis sempre baixados, nunca abertos na ferramenta.
- Links de download temporários; só quem tem acesso ao item vê os anexos.
- Estimativa de custo de armazenamento a ser apresentada na decisão de hospedagem.

## Service desk e SLA

Service desk

- Solicitantes internos. Qualquer usuário abre ticket pelo portal, usando formulários criados pelo ADM do espaço; cada espaço pode ter vários formulários.
- O solicitante vê só os campos do formulário e acompanha só os próprios tickets.
- Níveis N1 a N4 como campo "Nível", com status simples (não embutidos no status, como hoje no SJS).

SLA

- Todo service desk nasce com "Primeira resposta" e "Resolução"; o ADM do espaço pode criar outros.
- Cada SLA define quando começa, quando pausa (ex.: Aguardando solicitante) e quando para; o que conta como primeira resposta fica explícito.
- Metas por regra, avaliadas em ordem: formulário, prioridade ou Nível. O N4 pode ter meta diferente do N1.
- Mudança de prioridade ou escalação de Nível troca a meta mantendo o tempo já decorrido; o solicitante tem um prazo único.
- Ticket reaberto começa um novo ciclo de SLA do zero.
- No ticket: contagem regressiva com três estados (no prazo, perto de vencer, vencido); fila e Lista ordenam por tempo restante.
- Notificação antes de vencer e no vencimento; eventos de SLA podem disparar automações.
- Relatório de cumprimento por período, agente e Nível, com o tempo em cada Nível. O Agente vê só o próprio relatório.

## Calendários e feriados 2027

- Catálogo central mantido pelo ADM da plataforma e pelo Gestor; cada service desk escolhe qual calendário usar. Fuso de Brasília.
- Três calendários: Comercial SP, Comercial BA e Comercial RJ, cada um com feriados nacionais, estaduais e municipais da capital.
- Pontos facultativos ficam marcados como tal, e o ADM do espaço decide se contam no SLA. Corpus Christi e terça de Carnaval entram no catálogo como feriado municipal onde são; o ADM da plataforma ou o Gestor decide se são considerados.

| Data | Feriado | Abrangência |
| --- | --- | --- |
| 01/01 (sex) | Confraternização Universal | Nacional |
| 20/01 (qua) | São Sebastião | Municipal Rio |
| 25/01 (seg) | Aniversário de São Paulo | Municipal SP |
| 08/02 (seg) | Carnaval | Ponto facultativo |
| 09/02 (ter) | Carnaval | Ponto facultativo; feriado municipal em Salvador (a confirmar no decreto 2027) |
| 10/02 (qua) | Quarta-feira de Cinzas | Ponto facultativo |
| 26/03 (sex) | Paixão de Cristo | Nacional |
| 21/04 (qua) | Tiradentes | Nacional |
| 23/04 (sex) | São Jorge | Estadual RJ |
| 01/05 (sáb) | Dia do Trabalho | Nacional |
| 27/05 (qui) | Corpus Christi | Municipal SP, Rio e Salvador; ponto facultativo nacional |
| 24/06 (qui) | São João | Municipal Salvador |
| 02/07 (sex) | Independência da Bahia | Estadual BA |
| 09/07 (sex) | Revolução Constitucionalista | Estadual SP |
| 07/09 (ter) | Independência | Nacional |
| 12/10 (ter) | Nossa Senhora Aparecida | Nacional |
| 02/11 (ter) | Finados | Nacional |
| 15/11 (seg) | Proclamação da República | Nacional |
| 20/11 (sáb) | Consciência Negra | Nacional (Lei 14.759/2023) |
| 08/12 (qua) | Nossa Senhora da Conceição | Municipal Salvador |
| 25/12 (sáb) | Natal | Nacional |

Fontes: [Investnews](https://investnews.com.br/off-work/calendario-feriados-2027/amp/), [DCI](https://www.dci.com.br/dci-sp/sao-paulo-tera-nove-feriados-prolongados-em-2027-veja-o-calendario/), [Diário do Rio](https://diariodorio.com/rio-de-janeiro/2026/10/12/feriados-no-rio-de-janeiro-em-2027.html), [Econet](https://blog.econeteditora.com.br/?p=28584), [Band](https://www.band.com.br/noticias/feriados-fevereiro-2026-carnaval-e-datas-municipais-nas-capitais-202602021048). Feriados municipais religiosos dependem de decreto anual; o catálogo permanece editável.

## Integrações, notificações e IA

| Integração | Decisão |
| --- | --- |
| GitHub | Igual ao Jira de hoje: vínculo pela chave do item no título do PR, nome da branch ou mensagem do commit; o item mostra PRs, commits, builds e deploys |
| Slack | Notificações e criação de tarefas; ativação opcional para cada usuário; instalada nos dois workspaces (digesto.slack.com e jusbrasil.slack.com); quem está nos dois escolhe em qual recebe as notificações |
| E-mail | Notificações |
| Google Agenda | Entra no MVP para o espaço pessoal: cada pessoa autoriza a leitura da própria agenda; tarefas sugeridas a partir de reuniões só entram depois de confirmadas |
| Claude (IA) | Via conector MCP: cada pessoa usa os próprios créditos e a IA responde, cria e edita itens com as permissões daquela pessoa. Habilitação depende de um Owner do plano Claude da empresa |

- Notificações sempre aparecem dentro da ferramenta, além de e-mail e Slack conforme a preferência de cada pessoa.
- O login do conector MCP usa a mesma identidade Google.
- Ações do Claude pelo conector MCP: buscar e resumir itens, criar e editar itens, comentar, mudar status e atribuir, sempre com as permissões da pessoa. Nunca exclui itens nem altera configurações de espaço.

## Automações

- Automações configuradas por espaço ou painel, num canvas dentro do sistema.
- Criam e editam regras apenas o ADM do espaço e o Gestor.
- Regras de painel podem alterar itens somente nos espaços em que quem criou a regra é ADM ou Gestor.
- As regras agem como "Automação do espaço", com o nome de quem criou registrado em cada execução.
- Ação de chamar sistema externo (webhook) entra no MVP, só para destinos de uma lista de endereços liberados, com registro na auditoria do que foi enviado. Lista mantida só pelo ADM da plataforma; inicial: sales-ops-solucoes.app.n8n.cloud, hooks.slack.com (workspaces digesto e jusbrasil), api.github.com restrito à organização jusbrasil, *.apps.jusbr.com e jus.atlassian.net.
- Atribuição automática de tickets do service desk personalizável pelo ADM do espaço, por formulário ou Nível: rodízio entre agentes do espaço ou de um time, menor carga, pessoa fixa ou sem atribuição (fica na fila); opção de pular agentes ausentes.

Estrutura base:

- Regra = gatilho + condições + ações, montada arrastando blocos.
- Gatilhos: item criado, status mudou, campo alterado, comentário, vínculo, SLA perto de vencer ou vencido, eventos do GitHub, mensagem no Slack, reunião na agenda, horário agendado, botão manual.
- Ações: mudar status, alterar campo, atribuir (fixo, rodízio ou quem abriu), comentar, criar item, vincular, escalar Nível, notificar.
- Proteções: histórico de execução, pausa, modo de teste, limite contra disparo em cadeia.
- Modelos prontos: concluir pai quando subtarefas terminam, rodízio de tickets, aviso de bloqueio resolvido, alerta de SLA no Slack.

## Filtros personalizados

- MVP só com construtor visual (campo, condição e valor); modo avançado de escrita, como o JQL, fica para depois.
- Filtros podem ser pessoais ou compartilhados com pessoas, times ou um espaço inteiro; qualquer membro do espaço pode compartilhar com o espaço inteiro.
- Assinatura de filtro (envio periódico por e-mail ou Slack) fora do MVP.
- Exportar o resultado de um filtro para planilha (CSV ou Excel) entra no MVP; a exportação traz só os itens que a pessoa pode ver.
- Filtro compartilhado com o espaço só pode ser editado ou apagado por quem criou, pelo ADM do espaço e pelo Gestor.
- Valores relativos: eu, hoje, esta semana, sprint atual, SLA vencido, sem responsável.
- Filtros salvos com nome e favoritos.
- O mesmo filtro serve na Lista, como base de quadro, em painéis, nas condições de automações e no Espaço da Gestão.
- O resultado respeita as permissões de quem vê.

## Dashboards

- Dashboards são criados pelo ADM da plataforma, pelo ADM do espaço e pelo Gestor.
- Quando o dashboard inclui espaços a que a pessoa não tem acesso, os blocos mostram o aviso "parte dos dados está oculta".
- Um dashboard pode ser fixado num espaço ou painel, aparecendo como uma aba ao lado do quadro, da Lista e do Gantt.
- Compartilhamento igual ao dos filtros: pessoal, pessoas, times ou espaço inteiro.
- Página com blocos numa grade, arrastáveis e redimensionáveis; cada bloco usa um filtro salvo, que pode cobrir vários espaços e painéis.
- Atualização automática; quem abre só vê o que tem acesso.
- Blocos para o MVP: contador; pizza ou barras por campo; criados versus concluídos; lista de itens; carga por responsável; cumprimento de SLA; burndown e velocidade de sprint; Saúde da sprint.
- Saúde da sprint mostra saudável, em atenção ou em risco pelo pior critério ligado; critérios ajustáveis por quem monta o dashboard, cada um com limite de atenção e de risco: progresso versus tempo, escopo adicionado após o início, itens bloqueados, sem responsável, sem estimativa, com entrega vencida e parados no mesmo status há mais de X dias.

## Espaço da Gestão

- Tela inicial do Gestor; o ADM da plataforma também tem acesso.
- Individual: cada um escolhe quais espaços e painéis acompanhar (nunca espaços pessoais) e pode compartilhar a seleção com outro Gestor.
- Cartão por espaço ou painel com sinal geral (saudável, em atenção, em risco) e números: em andamento, atrasados, concluídos no período, bloqueados e, quando houver, saúde da sprint e cumprimento de SLA.
- Sinal geral: a plataforma traz regras padrão como sugestão, e cada Gestor pode alterá-las no seu Espaço da Gestão.
- Faixa de destaques: épicos com data nos próximos 30 dias, itens de prioridade alta atrasados e SLAs vencidos; os dois últimos com fundo vermelho pastel.
- Linha do tempo consolidada dos épicos dos espaços acompanhados, no MVP.
- Clicar em cartão ou número abre o espaço, painel ou lista correspondente; dashboards podem ser fixados ali.

## Notificações

- Canais: dentro da ferramenta (sino com contador, sempre ativo), e-mail e Slack (opcional, no workspace escolhido). Ninguém é notificado das próprias ações.
- Eventos: atribuição; menção; comentário novo; mudança de status; prazo de entrega amanhã e vencido; bloqueio resolvido; SLA perto de vencer e vencido; atualizações do ticket para o solicitante; pedido de acesso e resposta; sprint iniciada ou encerrada; tarefas sugeridas pela agenda; avisos definidos em automações.
- Botão "Observar" no item, com pop-up de confirmação, para receber as atualizações sem ser responsável nem relator.
- Cada pessoa ajusta, numa grade de evento por canal, onde recebe cada aviso. Menção e atribuição sempre aparecem dentro da ferramenta e também podem ir para e-mail e Slack.
- Resumo diário por e-mail, opcional, juntando os avisos num só envio.

## Detalhe do item

- Descrição e comentários com o mesmo editor de texto formatado: negrito, itálico, títulos, listas, tabelas, links, blocos de código, imagens coladas e menções (@pessoa notifica; chave de item vira link).
- Abas: Comentários, Histórico (cada alteração com quem, quando, valor anterior e novo) e Atividade (os dois juntos). Comentários, Histórico e Atividade sempre do mais recente para o mais antigo.
- Service desk: o agente escolhe entre responder ao solicitante ou escrever nota interna (visível só para agentes, ADM e Gestor). Só a resposta ao solicitante conta como primeira resposta no SLA. Visual: resposta ao solicitante em amarelo e nota interna em cinza, tanto na caixa de escrita quanto na linha do tempo.
- Comentário editado mostra a marca "editado" e a versão anterior fica no histórico.
- Comentário excluído deixa a linha "comentário excluído por fulano em tal data".

## Ordem de construção

Aprovada em 16/11. Todo o desenvolvimento roda no computador da Jaqueline, que acompanha pelas prévias no Claude e pelo sistema rodando localmente; ao fim de cada etapa, o Claude valida as funcionalidades. Testes externos com as equipes só depois, num ambiente hospedado a definir.

1. Fundação: login Google, cadastro automático, sessão, papéis da plataforma e auditoria.
2. Espaços e itens: espaços, painéis, tipos, campos, anexos, itens relacionados e detalhe do item.
3. Status, workflow e quadros: catálogo de status, transições, Scrum, Kanban, simples, Lista e Gantt. A partir daqui, piloto possível (ex.: Legal Experts JS).
4. Permissões completas: matriz por espaço, espaço aberto, Solicitar acesso, Gestor e times.
5. Service desk e SLA: formulários, Nível, notas internas, atribuição, SLAs, calendários.
6. Filtros e dashboards.
7. Espaço da Gestão.
8. Notificações.
9. Automações.
10. Integrações e IA: GitHub, Google Agenda e conector MCP.

## Pendências

Decisões em aberto

- [ ] Hospedagem (GCP ou outra) e estimativa de custo de armazenamento: definir no final do projeto.

Dependências externas

- [ ] Credenciais OAuth no Google Cloud da empresa (login e agenda). Até lá, o desenvolvimento usa um login de teste; lembrar a Jaqueline deste ponto ao fim de cada etapa.
- [ ] Owner do plano Claude para habilitar o conector MCP.
- [ ] Repositório "gerenciadorinternojs" criado privado na conta pessoal da Jaqueline (sem permissão para criar na organização jusbrasil); pedir à TI permissão ou a transferência para a organização antes dos testes externos.

## Referências do levantamento no Jira

Leitura feita sem nenhuma alteração no ambiente jus.atlassian.net.

- 273 projetos, entre clássicos e next-gen, dos tipos software, business e service desk; 37 quadros Scrum, 114 Kanban e 99 simples.
- Hoje o Jira só obriga Projeto, Tipo e Resumo, o que explica dados incompletos.
- Status duplicados em dois idiomas no TLF e no IL; 22 status no SJS, com os níveis N1 a N4 embutidos.
- SJS: dois SLAs (primeira resposta e resolução, ambos de 2h, em horário comercial); no SJS-547 o SLA de primeira resposta seguia correndo após a primeira resposta registrada, ponto a validar no sistema novo.
- GitHub: vínculo pela chave do item; o LOPS-4144 mostra PRs com a chave antiga THD-641, por isso o apelido de chave ao mover itens.
- Esquemas de permissão e configuração de SLA não são expostos pelo conector; o desenho segue o modelo padrão do Jira.
