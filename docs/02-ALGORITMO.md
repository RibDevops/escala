# 02 — Algoritmo Manual do Motor de Escala

## 1. Filosofia do algoritmo

O motor não deve tentar otimizar a escala por conta própria.

Ele deve reproduzir o procedimento manual da planilha.

A regra principal é:

> Para cada serviço, criar uma nova fotografia da situação, navegar pelo quadrinho e registrar o primeiro militar disponível.

Cada serviço gera uma nova execução completa do algoritmo.

O algoritmo nunca continua de onde parou.

## 2. Ordem geral

Para cada serviço a ser registrado:

1. Identificar o tipo de serviço da data: Preta, Vermelha, Roxa etc.
2. Selecionar o quadrinho correspondente ao tipo de serviço.
3. Criar um Snapshot Operacional para aquela data.
4. Aplicar ao snapshot:
   - células já preenchidas do quadrinho;
   - indisponibilidades;
   - folga global;
   - outros bloqueios configurados.
5. Encontrar a menor coluna com possibilidade de lançamento.
6. Percorrer a coluna de baixo para cima.
7. Escolher o primeiro militar com célula vazia e estado DISPONÍVEL.
8. Registrar o serviço no quadrinho real.
9. Atualizar a agenda global de folga.
10. Descartar o snapshot.
11. Repetir tudo para o próximo serviço.

## 3. Menor coluna

A menor coluna é a coluna mais à esquerda que ainda possui célula vazia para algum militar.

Exemplo:

| Militar | S1 | S2 | S3 |
|---|---|---|---|
| Carlos | X | vazio | vazio |
| Rogério | X | vazio | vazio |
| Pire | X | X | vazio |
| Ribeiro | X | X | vazio |

A menor coluna é S2.

## 4. Navegação dentro da coluna

A navegação sempre começa no último militar da lista, ou seja, no mais moderno.

Exemplo:

| Ordem | Militar | S2 |
|---:|---|---|
| 1 | S1 Carlos | vazio |
| 2 | S1 Rogério | vazio |
| 3 | S1 Pire | preenchido |
| 4 | Sd Ribeiro | preenchido |

Ordem de análise:

1. Sd Ribeiro — S2 preenchido, ignora.
2. S1 Pire — S2 preenchido, ignora.
3. S1 Rogério — S2 vazio, analisa disponibilidade.
4. S1 Carlos — só será analisado se Rogério estiver bloqueado.

Resultado, se Rogério estiver disponível: S1 Rogério.

## 5. Primeiro candidato disponível vence

Não se analisa todos os candidatos para depois comparar.

A regra é:

> Encontrou o primeiro candidato disponível, registra e encerra a busca daquele serviço.

## 6. Indisponibilidade

Se o militar encontrado estiver indisponível na data, ele é ignorado apenas para aquele serviço.

O sistema continua procurando na mesma coluna.

Exemplo:

| Ordem | Militar | S2 | Situação em 08/05 |
|---:|---|---|---|
| 1 | Carlos | vazio | disponível |
| 2 | Rogério | vazio | indisponível |
| 3 | Pire | preenchido | — |
| 4 | Ribeiro | preenchido | — |

Busca:

1. Ribeiro — preenchido.
2. Pire — preenchido.
3. Rogério — vazio, mas indisponível.
4. Carlos — vazio e disponível.

Resultado: Carlos.

## 7. Folga

Se o militar encontrado estiver em folga, ele é ignorado apenas para aquele serviço.

O sistema continua procurando na mesma coluna.

Exemplo:

| Ordem | Militar | S2 | Situação em 08/05 |
|---:|---|---|---|
| 1 | Carlos | vazio | disponível |
| 2 | Rogério | vazio | folga |
| 3 | Pire | preenchido | — |
| 4 | Ribeiro | preenchido | — |

Resultado: Carlos.

## 8. Quando a coluna acaba

Se todos os candidatos da menor coluna estiverem preenchidos ou bloqueados, o sistema deve ir para a próxima coluna à direita.

Ao ir para a próxima coluna, a busca recomeça do último militar da lista, ou seja, do mais moderno.

Exemplo:

| Ordem | Militar | S2 | S3 |
|---:|---|---|---|
| 1 | Carlos | vazio | vazio |
| 2 | Rogério | vazio | vazio |
| 3 | Pire | preenchido | vazio |
| 4 | Ribeiro | preenchido | vazio |

Situação em 08/05:

- Rogério indisponível.
- Carlos indisponível.

Nenhum candidato válido em S2.

O sistema vai para S3 e reinicia a busca:

1. Ribeiro.
2. Pire.
3. Rogério.
4. Carlos.

## 9. Atualização após registrar serviço

Quando um serviço é registrado:

1. A data é lançada na primeira célula vazia da linha do militar dentro do quadrinho daquele tipo de serviço.
2. O quadrinho correspondente é atualizado.
3. A agenda global de folga é atualizada.
4. O snapshot é descartado.

## 10. Cada serviço é independente

Após registrar um serviço, o próximo serviço deve recomeçar o processo do zero.

Isso significa recalcular:

- menor coluna;
- snapshot;
- bloqueios;
- disponibilidade;
- navegação.

O sistema não guarda a posição do último militar analisado.

## 11. Quadrinhos diferentes e folga global

Cada tipo de serviço possui seu quadrinho próprio.

Exemplo:

- Quadrinho Preta.
- Quadrinho Vermelha.

Mas a folga é global.

Se um militar fez Preta, ele pode ser bloqueado para Vermelha.

Se fez Vermelha, pode ser bloqueado para Preta.

## 12. Geração cronológica x geração por tipo

Como a folga é global, a forma mais fiel à realidade é processar os serviços pela ordem de ocorrência no calendário.

Exemplo:

1. 05/05 Preta.
2. 06/05 Vermelha.
3. 07/05 Preta.
4. 08/05 Vermelha.

Porém, se a regra operacional exigir gerar toda a Preta primeiro e depois toda a Vermelha, o motor deve deixar essa ordem configurável.

A recomendação técnica é permitir duas estratégias:

- CRONOLOGICA: processa as datas em ordem real.
- POR_TIPO: processa todos os dias de um tipo antes do próximo tipo.

Em ambos os casos, a folga global deve ser respeitada.
