# 06 — Casos de Teste do Motor

## Objetivo

Este documento descreve casos de teste para validar se o motor reproduz a lógica manual da planilha.

Cada teste deve ser convertido em teste automatizado sempre que possível.

---

## Teste 001 — Primeiro candidato da base

### Dado

| Ordem | Militar | S1 | S2 |
|---:|---|---|---|
| 1 | Carlos | X | vazio |
| 2 | Rogério | X | vazio |
| 3 | Pire | X | vazio |
| 4 | Ribeiro | X | vazio |

### Quando

Gerar serviço 05/05.

### Então

Resultado esperado:

```text
Ribeiro
```

---

## Teste 002 — Candidato da base já preenchido

### Dado

| Ordem | Militar | S1 | S2 |
|---:|---|---|---|
| 1 | Carlos | X | vazio |
| 2 | Rogério | X | vazio |
| 3 | Pire | X | vazio |
| 4 | Ribeiro | X | 05/05 |

### Quando

Gerar serviço 06/05.

### Então

Resultado esperado:

```text
Pire
```

---

## Teste 003 — Indisponibilidade pula militar

### Dado

| Ordem | Militar | S2 |
|---:|---|---|
| 1 | Carlos | vazio |
| 2 | Rogério | vazio |
| 3 | Pire | preenchido |
| 4 | Ribeiro | preenchido |

Indisponibilidade:

```text
Rogério em 08/05
```

### Quando

Gerar serviço 08/05.

### Então

Resultado esperado:

```text
Carlos
```

---

## Teste 004 — Folga pula militar

### Dado

| Ordem | Militar | S2 |
|---:|---|---|
| 1 | Carlos | vazio |
| 2 | Rogério | vazio |
| 3 | Pire | preenchido |
| 4 | Ribeiro | preenchido |

Folga:

```text
Rogério bloqueado em 08/05
```

### Quando

Gerar serviço 08/05.

### Então

Resultado esperado:

```text
Carlos
```

---

## Teste 005 — Coluna inteira bloqueada vai para próxima coluna

### Dado

| Ordem | Militar | S2 | S3 |
|---:|---|---|---|
| 1 | Carlos | vazio | vazio |
| 2 | Rogério | vazio | vazio |
| 3 | Pire | preenchido | vazio |
| 4 | Ribeiro | preenchido | vazio |

Bloqueios:

```text
Carlos indisponível em 08/05
Rogério em folga em 08/05
```

### Quando

Gerar serviço 08/05.

### Então

O motor deve sair de S2, ir para S3 e reiniciar de baixo para cima.

Resultado esperado:

```text
Ribeiro
```

---

## Teste 006 — Cada serviço recalcula tudo

### Dado

| Ordem | Militar | S1 | S2 | S3 |
|---:|---|---|---|---|
| 1 | Carlos | X | vazio | vazio |
| 2 | Rogério | X | vazio | vazio |
| 3 | Pire | X | vazio | vazio |
| 4 | Ribeiro | X | vazio | vazio |

### Quando

Gerar serviços:

```text
05/05
06/05
07/05
08/05
```

### Então

Resultado esperado, sem bloqueios:

```text
05/05 → Ribeiro
06/05 → Pire
07/05 → Rogério
08/05 → Carlos
```

Depois disso, o próximo serviço começa em S3.

---

## Teste 007 — Quadrinhos separados, folga global

### Dado

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

### Quando

Rogério faz Preta em 05/05 e fica em folga em 06/05.

Gerar Vermelha em 06/05.

### Então

Rogério continua com célula vazia no quadrinho Vermelha, mas deve ser bloqueado no snapshot.

O motor deve escolher o próximo militar disponível.

---

## Teste 008 — Snapshot não altera quadrinho

### Dado

Rogério está em folga em 08/05.

### Quando

Gerar snapshot para 08/05.

### Então

O snapshot pode marcar Rogério como FOLGA.

Mas o quadrinho real de Rogério deve continuar vazio na célula correspondente.

---

## Teste 009 — Ordem por antiguidade

### Dado

Militares ordenados assim:

| Ordem | Militar |
|---:|---|
| 1 | Mais antigo |
| 2 | Intermediário |
| 3 | Mais moderno |

### Quando

Gerar serviço com todos empatados.

### Então

O primeiro analisado deve ser o mais moderno, isto é, o último da lista.

---

## Teste 010 — Próxima coluna reinicia pela base

### Dado

Coluna S2 sem candidatos válidos.

### Quando

Motor passa para S3.

### Então

A busca em S3 deve começar novamente pelo último militar da lista.
