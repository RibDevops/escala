# 05 — Exemplos de Geração Manual

## Exemplo 1 — Busca simples

Estado inicial:

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | Carlos | X | vazio | vazio |
| 2 | Rogério | X | vazio | vazio |
| 3 | Pire | X | vazio | vazio |
| 4 | Ribeiro | X | vazio | vazio |

Serviço: 05/05.

Busca de baixo para cima:

1. Ribeiro — S2 vazio e disponível.

Resultado:

```text
05/05 → Ribeiro
```

Tabela atualizada:

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | Carlos | X | vazio | vazio |
| 2 | Rogério | X | vazio | vazio |
| 3 | Pire | X | vazio | vazio |
| 4 | Ribeiro | X | 05/05 | vazio |

## Exemplo 2 — Próximo serviço recalcula tudo

Serviço: 06/05.

Menor coluna: S2.

Busca de baixo para cima:

1. Ribeiro — S2 preenchido.
2. Pire — S2 vazio e disponível.

Resultado:

```text
06/05 → Pire
```

Tabela atualizada:

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | Carlos | X | vazio | vazio |
| 2 | Rogério | X | vazio | vazio |
| 3 | Pire | X | 06/05 | vazio |
| 4 | Ribeiro | X | 05/05 | vazio |

## Exemplo 3 — Segue na mesma coluna

Serviço: 07/05.

Menor coluna: S2.

Busca:

1. Ribeiro — preenchido.
2. Pire — preenchido.
3. Rogério — vazio e disponível.

Resultado:

```text
07/05 → Rogério
```

## Exemplo 4 — Fecha coluna e passa para a próxima

Após alguns serviços:

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | Carlos | X | 08/05 | vazio |
| 2 | Rogério | X | 07/05 | vazio |
| 3 | Pire | X | 06/05 | vazio |
| 4 | Ribeiro | X | 05/05 | vazio |

Todos possuem S2 preenchido.

Próximo serviço: 09/05.

Menor coluna agora: S3.

Busca recomeça de baixo para cima:

1. Ribeiro.
2. Pire.
3. Rogério.
4. Carlos.

## Exemplo 5 — Indisponibilidade

| Ordem | Militar | S2 | Situação em 08/05 |
|---:|---|---|---|
| 1 | Carlos | vazio | disponível |
| 2 | Rogério | vazio | indisponível |
| 3 | Pire | preenchido | — |
| 4 | Ribeiro | preenchido | — |

Busca:

1. Ribeiro — preenchido.
2. Pire — preenchido.
3. Rogério — indisponível.
4. Carlos — disponível.

Resultado:

```text
08/05 → Carlos
```

## Exemplo 6 — Folga

| Ordem | Militar | S2 | Situação em 08/05 |
|---:|---|---|---|
| 1 | Carlos | vazio | disponível |
| 2 | Rogério | vazio | folga |
| 3 | Pire | preenchido | — |
| 4 | Ribeiro | preenchido | — |

Resultado:

```text
08/05 → Carlos
```

## Exemplo 7 — Acabou a coluna

| Ordem | Militar | S2 | S3 | Situação em 08/05 |
|---:|---|---|---|---|
| 1 | Carlos | vazio | vazio | indisponível |
| 2 | Rogério | vazio | vazio | folga |
| 3 | Pire | preenchido | vazio | disponível |
| 4 | Ribeiro | preenchido | vazio | disponível |

Em S2:

- Ribeiro preenchido.
- Pire preenchido.
- Rogério bloqueado.
- Carlos bloqueado.

Não há candidato válido em S2.

Vai para S3 e reinicia de baixo para cima.

Primeiro disponível em S3:

```text
Ribeiro
```

Resultado:

```text
08/05 → Ribeiro
```

## Exemplo 8 — Quadrinhos diferentes e folga global

Quadrinho Preta:

| Militar | S1 | S2 |
|---|---|---|
| Carlos | X | vazio |
| Rogério | X | vazio |

Quadrinho Vermelha:

| Militar | S1 | S2 |
|---|---|---|
| Carlos | X | vazio |
| Rogério | X | vazio |

Serviço 05/05 Preta:

Busca de baixo para cima.

Resultado:

```text
05/05 Preta → Rogério
```

Rogério entra em folga global.

Próximo serviço Vermelha, se cair dentro da folga de Rogério:

- O quadrinho Vermelha continua vazio para Rogério.
- Mas Rogério aparece bloqueado no snapshot.
- O motor segue para o próximo candidato disponível.
