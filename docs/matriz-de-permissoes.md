# Matriz de permissões — Gerenciador

Atualizada em 16/11/2026 · Jaqueline

Matriz de permissões do Gerenciador, com as decisões fechadas até 16/11/2026.

## Como usar

Legenda das células: Sim = pode; Não = não pode; Próprios = só nos itens, comentários ou anexos que a própria pessoa criou; Leitura = só visualiza.

## Plataforma

Papéis que valem para a ferramenta inteira. Todo usuário é cadastrado automaticamente no primeiro login (domínios jusbrasil.com.br e digesto.com.br) e entra sem acesso a nenhum espaço.

| Ação | ADM da plataforma | Gestor | Usuário com permissão de criar espaços | Usuário |
| --- | --- | --- | --- | --- |
| Configurar domínios do login | Sim | Não | Não | Não |
| Gerenciar campos padronizados e catálogo de status | Sim | Não | Não | Não |
| Definir limite de anexos (padrão 1 GB, até 2 GB) | Sim | Não | Não | Não |
| Manter catálogo de calendários e feriados | Sim | Sim | Não | Não |
| Dar ou tirar a permissão de criar espaços | Sim | Sim | Não | Não |
| Dar ou tirar o papel de Gestor | Sim | Sim | Não | Não |
| Desativar usuário e encerrar sessões na hora | Sim | Não | Não | Não |
| Ver auditoria da plataforma | Sim | Sim | Não | Não |
| Entrar em qualquer espaço de equipe para suporte (registrado na auditoria) | Sim | Não | Não | Não |
| Ler espaços de equipe e painéis que escolher, sem ser adicionado | Sim | Sim | Não | Não |
| Criar espaço de equipe (vira ADM dele) | Sim | Sim | Sim | Não |
| Criar espaço pessoal | Sim | Sim | Sim | Sim |
| Criar time | Sim | Sim | Sim | Não |
| Editar ou excluir time | Sim (qualquer) | Sim | Sim | Não |
| Abrir ticket pelos formulários de service desk | Sim | Sim | Sim | Sim |
| Ler espaços marcados como abertos | Sim | Sim | Sim | Sim |
| Acessar espaços pessoais de outras pessoas | Não | Não | Não | Não |
| Criar dashboards | Sim | Sim | Não | Não |
| Acessar o Espaço da Gestão | Sim | Sim | Não | Não |
| Manter a lista de endereços liberados para webhook | Sim | Não | Não | Não |

Times: qualquer pessoa que seja ADM de pelo menos um espaço também pode criar times; editar e excluir fica com quem criou o time e com o ADM da plataforma. Isso não cabe nas colunas acima porque depende do papel no espaço.

## Espaço de projeto

Papéis fixos por espaço: a mesma pessoa pode ser Membro em um espaço e ADM em outro. Espaços são privados por padrão.

| Ação | ADM do espaço | Membro | Leitor | Gestor | Qualquer usuário (espaço aberto) |
| --- | --- | --- | --- | --- | --- |
| Ver itens, quadros, Lista e Gantt | Sim | Sim | Sim | Sim | Sim |
| Criar itens | Sim | Sim | Não | Sim | Não |
| Editar itens e mudar status | Sim | Sim | Não | Sim | Não |
| Atribuir responsável | Sim | Sim | Não | Sim | Não |
| Comentar | Sim | Sim | Sim | Sim | Sim |
| Editar ou excluir comentários | Sim | Próprios | Próprios | Próprios | Próprios |
| Adicionar anexos | Sim | Sim | Sim | Sim | Sim |
| Excluir anexos | Sim | Próprios | Próprios | Próprios | Próprios |
| Vincular itens (itens relacionados) | Sim | Sim | Não | Sim | Não |
| Gerenciar sprints | Sim | Sim | Não | Não | Não |
| Excluir itens | Sim | Próprios | Não | Próprios | Não |
| Configurar campos personalizados, workflow e quadros | Sim | Não | Não | Sim | Não |
| Configurar automações do espaço | Sim | Não | Não | Sim | Não |
| Gerenciar membros, times e papéis | Sim | Não | Não | Sim | Não |
| Aprovar Solicitar acesso (escolhendo o papel) | Sim | Não | Não | Sim | Não |
| Marcar o espaço como aberto ou privado | Sim | Não | Não | Não | Não |
| Ver quais gestores acompanham o espaço | Sim | Sim | Não | Não | Não |
| Pedir acesso pelo botão Solicitar acesso | Sim - para outros espaços | Sim - para outros espaços | Sim | Sim | Sim |
| Criar painéis | Sim | Não | Não | Sim | Não |
| Criar dashboards e fixar no espaço ou painel | Sim | Não | Não | Sim | Não |
| Compartilhar filtro com o espaço inteiro | Sim | Sim | Não | Sim | Não |
| Editar ou apagar filtro compartilhado com o espaço | Sim | Próprios | Não | Sim | Não |
| Observar item (receber atualizações) | Sim | Sim | Sim | Sim | Sim |

Decidido em 16/11: Gestor e quem lê um espaço aberto podem comentar.

## Espaço de service desk

Qualquer usuário da empresa vira Solicitante ao abrir um ticket por um dos formulários do espaço. Os campos de gestão (Responsável, Time, Prioridade, datas) não aparecem para quem abre.

| Ação | ADM do espaço | Agente | Solicitante | Gestor |
| --- | --- | --- | --- | --- |
| Abrir ticket pelo formulário | Sim | Sim | Sim | Sim |
| Ver os próprios tickets | Sim | Sim | Sim | Sim |
| Ver a fila e os tickets de outras pessoas | Sim | Sim | Não | Leitura |
| Comentar e anexar no ticket | Sim | Sim | Próprios | Sim |
| Assumir ticket e mudar status | Sim | Sim | Não | Sim |
| Mudar Nível (N1 a N4) | Sim | Sim | Não | Sim |
| Preencher campos de gestão | Sim | Sim | Não | Sim |
| Ver contagem de SLA | Sim | Sim | Não | Leitura |
| Excluir tickets | Sim | Não | Não | Não |
| Criar e editar formulários | Sim | Não | Não | Sim |
| Configurar SLAs, metas por Nível e calendário | Sim | Não | Não | Sim |
| Decidir se pontos facultativos contam no SLA | Sim | Não | Não | Sim |
| Configurar workflow, campos e automações | Sim | Não | Não | Não |
| Gerenciar agentes e papéis | Sim | Não | Não | Sim |
| Ver relatório de SLA | Sim | Sim - só o próprio | Não | Sim |
| Escrever e ver notas internas | Sim | Sim | Não | Sim |

Decidido em 16/11: o Agente vê apenas o próprio relatório de SLA.

## Espaço pessoal

Só o dono enxerga, a menos que compartilhe. Fica fora do alcance do Gestor e do suporte do ADM da plataforma.

| Ação | Dono | Pessoa com quem foi compartilhado | Gestor | ADM da plataforma |
| --- | --- | --- | --- | --- |
| Ver itens | Sim | Sim | Não | Não |
| Criar, editar e mover itens | Sim | Não | Não | Não |
| Comentar | Sim | Não | Não | Não |
| Configurar leitura de agenda e Slack | Sim | Não | Não | Não |
| Confirmar tarefas sugeridas pela automação | Sim | Não | Não | Não |
| Compartilhar e remover compartilhamento | Sim | Não | Não | Não |
| Excluir itens ou o espaço | Sim | Não | Não | Não |

Decidido em 16/11: o compartilhamento do espaço pessoal é sempre só leitura.

## Regras gerais

- Papéis são fixos; não existe esquema configurável por permissão.
- Dar acesso a um time inteiro: quem entra ou sai do time ganha ou perde o acesso automaticamente.
- Item vinculado em espaço sem acesso aparece com a chave, a marca "acesso restrito" e o botão Solicitar acesso. O pedido vai para os ADMs do espaço, que aprovam escolhendo o papel, sem papel pré-selecionado.
- Concluir item ainda bloqueado: permitido, com alerta e confirmação registrada no histórico.
- Ficam registrados na auditoria: logins e falhas de login, entradas de suporte do ADM da plataforma, mudanças de papel, exclusões e conclusões com bloqueio aberto.
- Sessão dura 15 dias; usuário desativado pelo ADM da plataforma perde todas as sessões na hora.

## Status

- Status é campo obrigatório. Padrão da plataforma: Backlog, A fazer, Em andamento, Em validação, Aguardando terceiros, Bloqueado, Concluído e Cancelado.
- Status padrão são mantidos pelo ADM da plataforma. Status próprios são criados pelo ADM do espaço (ou Gestor) e só existem naquele espaço, sem aparecer nos demais.
- O ADM do espaço escolhe quais status, padrão e próprios, ficam disponíveis no espaço e define as transições.
- Todo status pertence a uma categoria (A fazer, Em andamento ou Concluído), o que permite painéis, Espaço da Gestão e SLA entre espaços.
- Ao criar um status com nome parecido com outro do espaço, o sistema avisa antes de salvar. Status em uso só pode ser apagado depois de mover os itens.
- O ADM da plataforma pode promover um status de espaço a padrão; ele passa a ficar disponível como opção nos outros espaços, sem ser imposto.
