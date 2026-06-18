# 01 — Conceitos do Motor de Escala

## 1. Objetivo

Este documento descreve os conceitos principais do motor de escala militar baseado em quadrinhos.

O sistema não deve escolher o “melhor militar” por cálculo livre. Ele deve reproduzir o procedimento manual usado na planilha: navegar pelo quadrinho, de baixo para cima e da esquerda para a direita, filtrando quem está impedido naquela data.

## 2. Quadrinho

O quadrinho é o histórico oficial de serviços de um tipo de serviço.

Exemplos de tipos de serviço:

- Preta
- Vermelha
- Roxa

Cada tipo possui seu próprio quadrinho.

Exemplo:

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | S1 Carlos | X | vazio | vazio |
| 2 | S1 Rogério | X | vazio | vazio |
| 3 | S1 Pire | X | vazio | vazio |
| 4 | Sd Ribeiro | X | vazio | vazio |

O quadrinho é histórico. Ele nunca deve ser alterado por folga ou indisponibilidade.

## 3. Ordem da tabela

A tabela de militares deve ser montada por antiguidade.

Regra:

- Mais antigo fica no topo.
- Mais moderno fica na base.

Exemplo:

| Ordem | Militar |
|---:|---|
| 1 | Mais antigo |
| 2 | Intermediário |
| 3 | Intermediário |
| 4 | Mais moderno |

A escalação começa pelo mais moderno, ou seja, de baixo para cima.

## 4. Antiguidade

A antiguidade é definida pela ordenação dos militares.

Critérios esperados:

1. Posto / graduação: menor `ordem_hierarquica` significa mais antigo.
2. Dentro do mesmo posto: data de promoção mais antiga significa militar mais antigo.
3. Em caso de mesma data de promoção: nota maior pode ser usada como critério de antiguidade, se confirmado pela regra da OM.
4. Persistindo empate: usar critério estável, como `nome_guerra` ou `id`, apenas para garantir determinismo.

## 5. Primeiro da escala x primeiro a ser escalado

Existe diferença entre:

- Primeiro da escala: militar mais antigo, fica no topo da tabela.
- Primeiro a ser escalado: militar mais moderno disponível, encontrado de baixo para cima.

Exemplo:

| Ordem | Militar | S2 |
|---:|---|---|
| 1 | S1 Carlos | vazio |
| 2 | S1 Rogério | vazio |
| 3 | S1 Pire | preenchido |
| 4 | Sd Ribeiro | preenchido |

A leitura é:

1. Sd Ribeiro
2. S1 Pire
3. S1 Rogério
4. S1 Carlos

Como Ribeiro e Pire já estão preenchidos em S2, o primeiro candidato vazio é Rogério.

Resultado: S1 Rogério é analisado antes de S1 Carlos.

## 6. Agenda global

A agenda global reúne impedimentos que valem para todos os tipos de serviço.

Inclui:

- Folga após serviço.
- Indisponibilidade cadastrada.
- Férias.
- Licença.
- Missão.
- Outros afastamentos.

A agenda global não pertence ao quadrinho Preta ou Vermelha. Ela vale para todos.

Exemplo:

Se o militar fez Preta em 05/05, ele pode ficar bloqueado para Vermelha em 06/05, dependendo da folga configurada.

## 7. Folga global

A folga é global entre os tipos de serviço.

Se um militar fez serviço Preta, ele fica impedido também para Vermelha, Roxa ou qualquer outro serviço durante o período de folga.

A folga não altera o quadrinho. Ela apenas bloqueia o militar durante a escolha.

## 8. Indisponibilidade

Indisponibilidade é um bloqueio real cadastrado no sistema.

Exemplos:

- Férias.
- Licença médica.
- Missão.
- Dispensa.

Indisponibilidade não conta como serviço e não altera o quadrinho.

## 9. Snapshot Operacional

Antes de registrar cada serviço, o sistema deve criar uma visão temporária do estado atual.

Essa visão é chamada de Snapshot Operacional.

Ela serve para responder:

> Quem está realmente elegível para este serviço, nesta data, neste quadrinho?

O snapshot é temporário e descartável.

Ele pode marcar cada militar como:

- DISPONÍVEL
- PREENCHIDO
- FOLGA
- INDISPONÍVEL
- OUTRO_BLOQUEIO

O quadrinho original não é modificado por essas marcações.

## 10. Regra central

O quadrinho é o histórico.

O snapshot é a visão temporária.

A navegação escolhe o primeiro militar disponível encontrado no snapshot, seguindo:

1. Menor coluna.
2. De baixo para cima.
3. Da esquerda para a direita.
4. Primeiro candidato disponível vence.
