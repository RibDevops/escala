# Prompt consolidado — Motor de Escala Vertical em Django

Quero que você atue como um arquiteto de software sênior, especialista em Python, Django, motores de geração de escala, modelagem de regras operacionais e refatoração de sistemas legados. Sua missão é analisar um sistema Django já existente e especificar, projetar e implementar a evolução do motor de geração de escalas para um novo modelo operacional chamado **Motor de Escala Vertical**, preservando a lógica humana de montagem manual usada em planilha Excel operacional.

O projeto existente já está em andamento e deve ser aproveitado, não substituído do zero. O repositório atual informado é: [https://github.com/RibDevops/escala.git](https://github.com/RibDevops/escala.git).

## Contexto principal

O motor atual deve ser substituído ou evoluído para reproduzir exatamente o comportamento humano de um escalante olhando uma planilha Excel. Esse comportamento não é um balanceamento matemático tradicional, não usa IA, não usa pesos estatísticos complexos e não deve priorizar distância cronológica desde o último serviço. A prioridade central é sempre a **menor quantidade total de serviços reais** registrados por militar.

A lógica foi derivada de uma planilha de exemplo com “quadrinhos pretos” e “quadrinhos vermelhos”, listas de serviços por data e uma tabela de indisponibilidades. Nessa lógica, a matriz visual não representa dias fixos nas colunas. As colunas representam a sequência histórica de serviços de cada militar:

- Coluna A = primeiro serviço do militar
- Coluna B = segundo serviço
- Coluna C = terceiro serviço
- e assim por diante

Ou seja, a linha do militar é um histórico cronológico visual de serviços.

## Regras fechadas do motor

### 1. Regra principal de prioridade

O algoritmo deve sempre procurar primeiro **quem tem menor quantidade total de serviços reais registrados**.

Exemplo:

- Lima = 0 serviços
- Souza = 0 serviços
- Pires = 1 serviço
- Carlos = 2 serviços
- João = 3 serviços

Os de menor quantidade têm prioridade absoluta.

### 2. Regra de desempate visual

Quando dois ou mais militares tiverem a mesma menor quantidade de serviços reais, a busca deve obedecer a ordem visual fixa da matriz:

1. De baixo para cima.
2. Se necessário, da esquerda para a direita.

O militar mais abaixo é o mais moderno e deve ser priorizado.

### 3. Regra quando ninguém da menor quantidade puder assumir

Se nenhum militar do grupo com menor quantidade puder assumir por folga, indisponibilidade, férias, bloqueio ou conflito, o sistema deve **reiniciar a leitura completa da matriz da esquerda para a direita até achar alguém válido**.

Além disso, a lógica operacional aceita que a matriz cresça para a direita sem limite. Se necessário, o sistema cria uma nova coluna futura para continuar a progressão histórica.

### 4. Regra de folga

A folga:

- é configurada em horas;
- começa a contar na saída do serviço;
- é global entre escalas;
- não cria novo serviço real;
- apenas bloqueia temporariamente posições futuras da matriz operacional.

Exemplo prático:

- Saiu do serviço no dia 10;
- com 48 horas de folga;
- só pode entrar novamente no dia 13.

Outro exemplo:

- fez escala preta no dia 08/05/26;
- se ao gerar a escala vermelha ele estiver entre os de menor quantidade, não poderá assumir os dias 09 e 10 se ainda estiver em folga;
- poderá voltar quando a folga permitir, por exemplo dia 16, conforme a distribuição do mês.

### 5. Relação entre escala preta e vermelha

A geração deve considerar que:

- a escala preta deve ser gerada inteira antes da vermelha;
- a folga é global;
- preta bloqueia vermelha;
- vermelha bloqueia preta.

Observação: se você concluir tecnicamente que a melhor abordagem é gerar o mês completo de uma vez, considerando preto e vermelho juntos no mesmo processamento, você pode propor isso como melhoria, desde que preserve integralmente a lógica operacional descrita.

### 6. Indisponibilidades

As indisponibilidades funcionam como bloqueio simples por data ou por período.

Exemplos de regras:

- indisponibilidade individual por dia;
- indisponibilidade por intervalo;
- o algoritmo deve ignorar somente as datas afetadas;
- o histórico do militar permanece preservado.

### 7. Inatividade e retorno

Quando um militar fica inativo:

- seus registros antigos continuam visíveis;
- o histórico continua valendo;
- ao retornar à atividade, ele continua com seu histórico anterior.

### 8. Atualização dinâmica da matriz

A matriz operacional temporária deve ser atualizada **a cada novo serviço individual registrado durante a mesma execução**.

Ou seja:

- registra um serviço;
- atualiza a matriz temporária;
- aplica bloqueios temporários de folga e indisponibilidade;
- recalcula a próxima escolha.

Isso é essencial para que o militar em folga deixe de aparecer artificialmente como candidato de menor quantidade naquele momento operacional.

### 9. Frequência da geração

A geração é **mensal**.

### 10. Postos por dia

Existem mais de um posto por dia, mas isso já é tratado separadamente como **tipo de escala**. Portanto, o motor deve respeitar a separação das escalas por aba/tipo de escala.

### 11. Falha de alocação

Não deve existir cenário real de “ninguém pode assumir”, porque a matriz pode crescer para a direita sem limite. Se ninguém puder no ponto atual, o sistema continua a progressão criando nova coluna quando necessário.

## Conceito arquitetural obrigatório

O sistema deve trabalhar com **duas matrizes**:

### Matriz histórica persistente

Persistida no banco de dados, contendo apenas:

- serviços reais já realizados/registrados.

### Matriz operacional temporária

Gerada durante o processamento, contendo:

- serviços reais do período em geração;
- folgas temporárias;
- indisponibilidades;
- férias;
- bloqueios operacionais.

Essa matriz existe apenas durante a execução e deve ser reconstruída sempre que uma nova geração for iniciada.

## Exemplo de referência operacional

Considere um conjunto histórico como:

- s1carlos: 09/02/26, 07/05/26, 08/05/26, 13/05/26
- s1rogerio: 08/02/26, 01/03/26, 04/04/26, 09/04/26
- s1 mozer: 06/02/26, 02/03/26, 05/04/26, 25/04/26
- s1 pire: 05/02/26, 05/05/26, 06/05/26, 12/05/26
- sd ribeiro: 02/02/26, 03/03/26, 08/04/26, 11/05/26

Nesse cenário, o próximo registro pode gerar a continuação da linha de `sd ribeiro` com `14/05/26`, se ele for o primeiro válido dentro da lógica da matriz.

## Exemplo da planilha usada como referência

A planilha de exemplo contém, entre outros pontos:

- quadrinhos pretos antes e depois;
- quadrinhos vermelhos antes e depois;
- serviços em datas como 05/05/26 até 13/05/26;
- indisponibilidades como:
  - s1carlos em 06/05/26;
  - s1 pire em 13/05/26;
  - sd ribeiro em 12/05/26 e 13/05/26.

Ela também mostra o processo manual:

1. gerar tabela de indisponibilidades;
2. localizar a coluna com menor quantidade de serviços;
3. iniciar a leitura de baixo para cima;
4. verificar indisponibilidade do nome encontrado para a data do serviço;
5. se houver choque, continuar a busca;
6. registrar a data no primeiro militar válido;
7. reconstruir dinamicamente a tabela a cada novo registro.

## Objetivo do que você deve entregar

Quero que você produza uma resposta completa, técnica e pronta para implementação, contendo:

### 1. Diagnóstico e estratégia de evolução do sistema existente

- como encaixar o novo motor no projeto Django atual;
- quais partes reaproveitar;
- quais partes refatorar;
- quais riscos existem na migração.

### 2. Especificação funcional do motor

Descreva detalhadamente:

- comportamento esperado;
- entradas;
- saídas;
- fluxo da geração mensal;
- relação entre escalas preta e vermelha;
- comportamento da folga;
- comportamento de indisponibilidade;
- reconstrução da matriz temporária.

### 3. Regras de negócio formalizadas

Liste as regras em formato claro, auditável e implementável.

### 4. Modelagem técnica em Django

Proponha a modelagem necessária para o motor considerando que parte do cadastro já existe no projeto.

Explique como integrar ou adaptar modelos para:

- serviços reais;
- tipos de escala;
- indisponibilidades por data/período;
- configurações de folga em horas;
- logs operacionais da geração;
- representação persistente do histórico.

### 5. Classe principal do motor

Projete a classe principal do motor com nome compatível com o sistema já existente, ou proponha um nome melhor caso exista outro padrão no projeto.

Essa classe deve conter métodos como:

- carregar_matriz_historica()
- construir_matriz_operacional()
- buscar_menor_quantidade()
- ordenar_candidatos_visualmente()
- verificar_folga()
- verificar_indisponibilidade()
- verificar_conflito_entre_escalas()
- encontrar_primeiro_valido()
- registrar_servico()
- atualizar_matriz_operacional()
- gerar_escala_mensal()

### 6. Pseudocódigo completo

Escreva o pseudocódigo completo do algoritmo principal, passo a passo.

### 7. Código inicial em Django/Python

Forneça uma implementação inicial profissional, com:

- código limpo;
- alta legibilidade;
- comentários úteis;
- foco em manutenção futura;
- logs operacionais;
- fácil depuração.

### 8. Estratégia de integração

Explique como plugar o novo motor no projeto existente em Django com MySQL e interface HTML baseada em Django Templates.

### 9. Interface operacional

Considere que a visualização estilo Excel é desejada. Proponha telas ou componentes para:

- visualização da matriz histórica;
- visualização da matriz temporária da execução;
- auditoria da escolha do militar por serviço;
- geração automática mensal;
- ajuste manual posterior;
- exportação.

### 10. Exportações

Prever exportações necessárias, inclusive em formatos úteis para operação.

### 11. Testes

Crie cenários de teste cobrindo:

- menor quantidade de serviços reais;
- desempate por ordem visual;
- folga global entre preta e vermelha;
- indisponibilidade por data;
- indisponibilidade por período;
- retorno de militar inativo;
- crescimento da matriz para a direita;
- reconstrução da matriz a cada novo registro;
- geração mensal completa.

## Restrições obrigatórias

- Não transformar o motor em um balanceador estatístico.
- Não substituir a lógica visual por score matemático.
- Não usar IA para escolher militares.
- Não ignorar a matriz visual histórica.
- Não apagar histórico anterior quando o militar ficar inativo.
- Não tratar a folga como novo serviço real.

## Stack e contexto técnico já definidos

- Projeto existente em Django;
- Banco MySQL;
- Interface HTML com Django Templates;
- Sistema já possui parte dos cadastros;
- O foco agora é o motor de geração da escala.

## Qualidade esperada da resposta

Quero uma resposta extremamente organizada, com linguagem de engenharia de software, pronta para servir de base real de implementação, refatoração e evolução do projeto existente.

## Anexos conceituais para considerar na análise

Leve em conta os seguintes fatos consolidados:

- a matriz representa histórico cronológico de serviços;
- a prioridade principal é menor quantidade total de serviços reais;
- o desempate é visual, de baixo para cima e depois da esquerda para a direita;
- a leitura da matriz pode reiniciar completamente para achar alguém válido;
- a folga conta a partir da saída do serviço e bloqueia preta e vermelha;
- a matriz temporária precisa ser recalculada durante a execução;
- a geração é mensal;
- as escalas são tratadas separadamente por tipo;
- a tela estilo Excel é desejada;
- o sistema precisa de exportação.
