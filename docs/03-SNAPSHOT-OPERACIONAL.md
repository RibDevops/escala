# 03 — Snapshot Operacional

## 1. Definição

Snapshot Operacional é uma visão temporária do quadrinho no momento em que um serviço será registrado.

Ele não é salvo no banco.

Ele não altera o quadrinho.

Ele existe apenas para ajudar a navegação.

## 2. Por que usar snapshot?

Sem snapshot, o motor mistura duas responsabilidades:

1. Verificar regras de negócio.
2. Navegar pelo quadrinho.

Com snapshot, essas responsabilidades ficam separadas.

Primeiro o sistema prepara a situação.
Depois o algoritmo apenas navega.

## 3. O que o snapshot deve conter

Para cada militar e cada coluna relevante, o snapshot deve informar:

- militar;
- posição na lista;
- coluna;
- estado da célula;
- motivo do bloqueio, se houver.

Estados sugeridos:

- DISPONIVEL
- PREENCHIDO
- FOLGA
- INDISPONIVEL
- BLOQUEADO

## 4. Exemplo

Quadrinho original:

| Ordem | Militar | S2 |
|---:|---|---|
| 1 | Carlos | vazio |
| 2 | Rogério | vazio |
| 3 | Pire | preenchido |
| 4 | Ribeiro | preenchido |

Situação em 08/05:

- Rogério está em folga.
- Carlos está disponível.

Snapshot:

| Ordem | Militar | Coluna | Estado | Motivo |
|---:|---|---|---|---|
| 1 | Carlos | S2 | DISPONIVEL | — |
| 2 | Rogério | S2 | FOLGA | Bloqueado por folga global |
| 3 | Pire | S2 | PREENCHIDO | Já possui lançamento em S2 |
| 4 | Ribeiro | S2 | PREENCHIDO | Já possui lançamento em S2 |

Navegação de baixo para cima:

1. Ribeiro — preenchido.
2. Pire — preenchido.
3. Rogério — folga.
4. Carlos — disponível.

Resultado: Carlos.

## 5. O snapshot não muda o quadrinho

Importante:

- Folga não preenche célula.
- Indisponibilidade não preenche célula.
- Férias não preenche célula.
- Licença não preenche célula.

Essas marcações aparecem apenas no snapshot.

## 6. Fluxo recomendado

Para cada serviço:

```text
carregar quadrinho real
        ↓
gerar snapshot temporário
        ↓
aplicar bloqueios
        ↓
navegar pelo snapshot
        ↓
encontrar primeiro DISPONIVEL
        ↓
registrar no quadrinho real
        ↓
atualizar folga global
        ↓
descartar snapshot
```

## 7. Benefícios

O snapshot facilita:

- depuração;
- logs;
- explicação ao usuário;
- testes automatizados;
- manutenção;
- inclusão de novas regras.

Exemplo de log útil:

```text
Serviço 08/05 — Vermelha
Quadrinho: Vermelha
Menor coluna: S2
Busca: BASE → TOPO

Ribeiro: PREENCHIDO
Pire: PREENCHIDO
Rogério: FOLGA
Carlos: DISPONIVEL

Escolhido: Carlos
```
