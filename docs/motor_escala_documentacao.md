# Motor de Escala — Documentação Técnica Oficial

**Sistema:** Sistema de Escala Militar FAB  
**Arquivo de implementação:** `escalas/services.py` — classe `MotorEscalaVertical`  
**Versão do documento:** 1.0  

---

## Índice

1. [Explicação Operacional Humana](#1-explicação-operacional-humana)
2. [Regras do Algoritmo](#2-regras-do-algoritmo)
3. [Casos Práticos Completos](#3-casos-práticos-completos)
4. [Pseudocódigo Completo](#4-pseudocódigo-completo)

---

## 1. Explicação Operacional Humana

### O que o operador fazia manualmente no Excel

O escalante trabalhava com uma planilha onde:

- Cada **linha** representava um militar (da base ao topo — mais moderno primeiro)
- Cada **coluna** representava a sequência de serviços (1º serviço, 2º serviço, 3º serviço...)
- Cada **célula** continha a data em que aquele serviço foi realizado

Ao escalar o próximo dia, o operador seguia este processo mental:

> "Qual é a menor coluna ocupada? Quem ainda está nessa coluna?  
> Vou de baixo para cima. O primeiro disponível recebe o serviço."

**Passo a passo manual:**

1. Olha a tabela e identifica a **menor coluna** (menor número de serviços)
2. Verifica militares nessa coluna, **começando pela base** (mais moderno, mais júnior)
3. Pergunta para cada um: *"Está em férias? Está em folga de serviço recente?"*
4. O **primeiro que responder não** recebe o serviço
5. Anota a data na célula correspondente
6. Aquele militar agora passou para a coluna seguinte (count +1)
7. Marca os próximos dias como bloqueados por folga para ele
8. Repete o processo para o próximo dia

Se **toda** a menor coluna estiver bloqueada apenas por folga (não por férias), o operador quebraria a folga do primeiro disponível e escalaria com uma observação. Se todos estiverem de férias, o dia fica sem cobertura.

### Princípios fundamentais da lógica humana

| Princípio | Descrição |
|---|---|
| **Menor coluna é soberana** | Nunca se usa count maior enquanto houver alguém disponível no count menor |
| **Base para o topo** | A varredura começa sempre pelo mais moderno |
| **Folga respeita todos os tipos** | Preto bloqueia Vermelho e vice-versa |
| **Férias nunca se quebram** | Nenhuma circunstância força um militar de férias |
| **Tudo recalculado a cada dia** | Não existe memória de quem foi o último |

---

## 2. Regras do Algoritmo

### Declarações explícitas

> **Não existe fila persistente.**  
> **Não existe ponteiro entre dias.**  
> **Não existe round-robin.**  
> **Tudo é recalculado a cada serviço, do zero.**  
> **A menor coluna é soberana.**  
> **A varredura é sempre BASE → TOPO.**  
> **A indisponibilidade NUNCA é quebrada.**  
> **A folga SÓ pode ser quebrada no fallback, quando toda a menor coluna falhar apenas por folga.**

---

### Passo 1 — Limpeza e reversão de quadrinhos

Antes de gerar, todos os itens existentes da escala são apagados e seus quadrinhos revertidos (`quantidade -= 1` para cada item). Isso garante que uma nova geração parte de um estado limpo e consistente com o banco.

### Passo 2 — Carregar militares

Os militares ativos da OM são carregados em ordem de antiguidade:

```
ORDER BY posto__ordem_hierarquica ASC,
         data_ultima_promocao ASC,
         nome_guerra ASC
```

- **Índice 0** = TOPO (mais antigo — Ten, Cel, etc.)
- **Índice n-1** = BASE (mais moderno — Cb, Sd, mais júnior)

Para cada militar é calculada uma **chave de desempate**:

```
desempate[militar] = (n - 1) - índice
```

Isso inverte a ordem: BASE recebe desempate=0 (menor = maior prioridade), TOPO recebe desempate=n-1 (maior = menor prioridade). Quando dois militares empatharem no count, o de menor desempate vence — ou seja, o mais moderno sempre ganha.

### Passo 3 — Carregar matriz histórica (Quadrinho)

O `count` de cada militar é carregado do banco:

- Fonte: tabela `Quadrinho`
- Filtro: `tipo_escala` atual + `ano` atual
- Soma: **todos os tipos de serviço juntos** (Preto + Vermelho + Roxo = um único número)
- Fórmula: `count[militar] = soma(Quadrinho.total)` para todos os tipos

Este número é a **coluna do militar na planilha** — define toda a prioridade.

### Passo 4 — Carregar indisponibilidades

São carregadas as indisponibilidades reais do período (férias, licença, missão). Opcionalmente, bloqueios pré e pós-férias são incluídos conforme configuração. Estas datas são **absolutas e nunca quebradas**.

### Passo 5 — Carry-over inter-mês

Se um militar serviu nos últimos dias do mês anterior dentro da janela de folga (`duração + folga_mínima`), os primeiros dias do mês corrente são marcados como bloqueados por folga. Isso evita que um militar que serviu no dia 31/mai seja escalado no dia 01/jun.

O carry-over é **global**: qualquer tipo de serviço (Preto ou Vermelho) no mês anterior bloqueia todos os tipos no início do próximo mês.

### Passo 6 — Ordem de processamento dos tipos

Os tipos de serviço são processados em sequência, por `TipoServico.ordem ASC`:

```
Preto (ordem=0): dias 01 → 31 — todos gerados completamente
Vermelho (ordem=1): dias 01 → 31 — todos gerados completamente
Roxo (ordem=2): etc.
```

A folga gerada por um serviço Preto no dia 28 **já estará ativa** quando o Vermelho do dia 29 for processado, pois compartilham o mesmo `folga_global`.

### Passo 7 — Processar cada dia (núcleo do algoritmo)

Para cada dia de cada tipo de serviço:

**7.1 — Ordenação:**

```
militares_ordenados = sorted(militares,
    key = (count_operacional[militar], desempate[militar])
)
```

Resultado: lista com todos os de menor count primeiro, desempatados por BASE→TOPO.

**7.2 — Varredura principal:**

Percorre a lista em ordem. Para cada militar:
- Verifica indisponibilidade real → se sim, pula (sem exceção)
- Verifica folga global → se sim, pula
- Se disponível → escala, incrementa count, marca folga, retorna

A varredura **esgota toda a menor coluna** antes de tocar qualquer militar com count maior. Isso é garantido pela ordenação: todos os count=3 aparecem juntos antes dos count=4.

**7.3 — Fallback (somente se varredura principal falhar completamente):**

Classifica os militares em dois grupos:
- `bloqueados_só_por_folga`: sem indisponibilidade real, apenas folga
- `bloqueados_por_indisponibilidade`: com férias/licença real

Se existem militares `bloqueados_só_por_folga`:
- Escala o primeiro da lista (menor count, BASE→TOPO)
- Gera **alerta** de folga relaxada
- Marca `forcar_escala=True` no item

Se TODOS estão com indisponibilidade real:
- O dia fica **vazio** — nenhum militar é forçado
- Gera **alerta crítico**

### Passo 8 — Registrar serviço

Ao escalar um militar:

**Persistido no banco:**
- `EscalaItem` criado com a data e o militar
- `Quadrinho.quantidade += 1` (histórico real)

**Em memória apenas (descartado ao fim da geração):**
- `counts_operacional[militar] += 1`
- `folga_global[militar]` recebe os próximos `duração + folga_mínima` dias como bloqueados

### Janela de folga

```
janela_bloqueio = duração_do_serviço (dias) + folga_mínima (dias)
```

Configurável em `ConfiguracaoEscala` ou por `TipoEscala.folga_minima_horas`. Por padrão: 1 dia de duração + 2 dias de folga = **janela de 3 dias**.

---

## 3. Casos Práticos Completos

### Configuração base dos exemplos

| Posto | Nome | Count inicial |
|---|---|---|
| Ten | ALVES | índice 0 — TOPO |
| 1º Sgt | BORGES | índice 1 |
| 2º Sgt | CAMPOS | índice 2 |
| 3º Sgt | SILVA | índice 3 |
| Cb | SANTOS | índice 4 — BASE |

Desempates (n=5): ALVES=4, BORGES=3, CAMPOS=2, SILVA=1, SANTOS=0

---

### Caso 1 — Varredura normal com coluna mínima

**Estado:** todos com count=0

**Ordenação do dia 01:**
```
SANTOS (0, desempate=0)  ← BASE, máxima prioridade no empate
SILVA  (0, desempate=1)
CAMPOS (0, desempate=2)
BORGES (0, desempate=3)
ALVES  (0, desempate=4)
```

**Resultado:** SANTOS escalado (dia 01), count vira 1.

**Ordenação do dia 02:**
```
SILVA  (0, desempate=1)  ← agora SANTOS saiu da frente
CAMPOS (0, desempate=2)
BORGES (0, desempate=3)
ALVES  (0, desempate=4)
SANTOS (1, desempate=0)  ← foi para o final da coluna
```

**Resultado:** SILVA escalado (dia 02).

---

### Caso 2 — Folga bloqueando, mas outro disponível na mesma coluna

**Estado:** todos count=2. SANTOS serviu ontem (dia 04) → em folga até dia 07.

**Dia 05:**
```
SILVA  (2, desempate=1)  ← disponível ✓
CAMPOS (2, desempate=2)  ← disponível ✓
BORGES (2, desempate=3)  ← disponível ✓
ALVES  (2, desempate=4)  ← disponível ✓
SANTOS (2, desempate=0)  ← em folga ✗
```

Apesar de SANTOS ter desempate=0 (maior prioridade), ele está em folga. O sistema não salta para count=3. Tenta SILVA → disponível → **SILVA escalado**.

---

### Caso 3 — Toda a menor coluna em folga (fallback com quebra)

**Estado:** todos count=3, todos em folga por terem servido recentemente.

**Nenhum disponível na varredura principal.**

**Fallback:**
- Todos estão em `bloqueados_só_por_folga` (sem indisponibilidade real)
- Sistema pega o primeiro da lista ordenada: SANTOS (count=3, desempate=0)
- **Quebra a folga** de SANTOS, escala com alerta: *"folga relaxada — fallback"*
- Count 4 **não é utilizado**

---

### Caso 4 — Indisponibilidade real bloqueia, coluna avança

**Estado:** SANTOS em férias dias 10-20. Todos count=5.

**Dia 10:**
```
SANTOS (5, desempate=0)  ← férias ✗ — NUNCA quebrado
SILVA  (5, desempate=1)  ← disponível ✓
```
**SILVA escalado.** SANTOS está de férias — não entra no fallback de folga.

**Dia 11:** SILVA agora count=6. SANTOS ainda de férias.
```
CAMPOS (5, desempate=2)  ← disponível ✓
BORGES (5, desempate=3)
ALVES  (5, desempate=4)
SANTOS (5, desempate=0)  ← férias ✗
SILVA  (6, desempate=1)
```
**CAMPOS escalado.**

**Dia 21 (SANTOS volta):**
```
SANTOS (5, desempate=0)  ← count ainda é 5, menor de todos ✓
ALVES  (5, desempate=4)  ← ainda count=5 se não foi escalado
...
```
SANTOS volta para a frente automaticamente, pois count=5 é menor que os demais que foram escalados durante as férias. **Nenhuma ação manual necessária.**

---

### Caso 5 — Empate entre postos diferentes

**Estado:** 2º Sgt CAMPOS count=4, Cb SANTOS count=4.

Ambos empatados em count. Desempate:
- SANTOS: índice 4 → desempate=0 (BASE)
- CAMPOS: índice 2 → desempate=2

**SANTOS vence sempre**, independente do posto. O Cb tem prioridade sobre o 2º Sgt quando os counts são iguais.

---

### Caso 6 — Folga global entre tipos (Preto bloqueia Vermelho)

**Configuração:** janela de folga = 3 dias.

**Geração Preto dia 28/mai:** BORGES escalado → bloqueado dias 29, 30, 31.

**Geração Vermelho dia 29/mai:** ao chegar no BORGES na varredura → está em folga global → pula. Outro militar escalado no Vermelho.

**Geração Vermelho dia 01/jun (carry-over):** BORGES ainda pode estar bloqueado se o serviço de dia 28 + 3 dias alcançar junho (28+3=31mai, então dia 01/jun já está livre neste exemplo). Mas se o serviço fosse dia 30/mai → bloqueado até 02/jun.

---

### Caso 7 — Militar indisponível em toda menor coluna (sem fallback válido)

**Estado:** SILVA e SANTOS em férias. Ambos count=2 (menor). BORGES, CAMPOS, ALVES count=3.

**Dia X:**
```
SANTOS (2, desempate=0)  ← férias ✗
SILVA  (2, desempate=1)  ← férias ✗
CAMPOS (3, desempate=2)  ← disponível ✓
```

Não existe fallback de folga aqui — os bloqueados são por indisponibilidade real. O sistema **simplesmente continua a varredura** para count=3 e escala CAMPOS normalmente. Dia não fica vazio.

> Nota: o dia só ficaria vazio se **todos** os militares (de todas as colunas) estivessem com indisponibilidade real.

---

## 4. Pseudocódigo Completo

```
FUNÇÃO gerar_escala(escala):

  # ── FASE 1: PREPARAÇÃO ──────────────────────────────────────────

  limpar_itens_existentes(escala)
    para cada item em escala.itens:
      Quadrinho[item.militar][item.tipo_servico].quantidade -= 1
    deletar todos os itens

  militares = carregar_militares_ativos(om)
    ORDER BY posto.ordem_hierarquica ASC,
             data_ultima_promocao ASC,
             nome_guerra ASC
  n = len(militares)
  índice[militar]    = posição na lista (0=TOPO, n-1=BASE)
  desempate[militar] = (n - 1) - índice[militar]
    # BASE(n-1) → desempate=0 (maior prioridade)
    # TOPO(0)   → desempate=n-1 (menor prioridade)

  counts_historicos[militar] = 0 para todos
  para cada Quadrinho onde tipo_escala=atual E ano=atual:
    counts_historicos[quadrinho.militar] += quadrinho.total
    # soma TODOS os tipos de serviço (Preto+Vermelho+Roxo)

  counts_operacional = cópia de counts_historicos
  folga_global[militar] = conjunto_vazio para todos

  indisponibilidades = carregar_indisponibilidades(militares, período)
    # inclui pré/pós-férias se configurado
    # NUNCA quebradas

  # Carry-over inter-mês
  para cada serviço do mês anterior dentro da janela_bloqueio:
    primeiro_dia_bloqueado = max(dia_01_do_mês, data_serviço + 1 dia)
    último_dia_bloqueado   = data_serviço + janela_bloqueio
    folga_global[militar] += dias de primeiro_dia_bloqueado até último_dia_bloqueado

  # ── FASE 2: PROCESSAMENTO ───────────────────────────────────────

  janela_bloqueio = duração_serviço_dias + folga_mínima_dias

  tipos_em_ordem = ORDER BY tipo_servico.ordem ASC
  # Preto completo → Vermelho completo → Roxo completo → etc.

  para cada tipo_servico em tipos_em_ordem:
    para cada dia em dias_do_tipo ORDER BY data ASC:

      # ── ORDENAÇÃO (recalculada do zero a cada dia) ────────────
      militares_ordenados = sort(militares,
        chave = (counts_operacional[m], desempate[m])
      )
      # Menor count primeiro.
      # Empate: menor desempate = BASE = mais moderno = maior prioridade.
      # Toda a menor coluna aparece ANTES de qualquer coluna maior.

      # ── VARREDURA PRINCIPAL ───────────────────────────────────
      escalado = NENHUM

      para cada militar em militares_ordenados:
        se dia em indisponibilidades[militar]:
          registrar_log("indisponibilidade")
          continuar  # pula, NUNCA quebra

        se dia em folga_global[militar]:
          registrar_log("folga")
          continuar  # pula, pode ser quebrada no fallback

        # Disponível!
        escalado = militar
        parar

      se escalado != NENHUM:
        registrar_serviço(dia, escalado)
        continuar para próximo dia

      # ── FALLBACK (toda varredura principal falhou) ────────────
      bloqueados_só_por_folga = [
        m para m em militares_ordenados
        se dia NÃO em indisponibilidades[m]
        E dia em folga_global[m]
      ]

      se bloqueados_só_por_folga não vazio:
        escolhido = bloqueados_só_por_folga[0]
        # já está na ordem correta: menor count, BASE→TOPO
        gerar_alerta("folga relaxada → " + escolhido.nome)
        registrar_serviço(dia, escolhido, forcar_escala=True)

      senão:
        # Todos com indisponibilidade real
        gerar_alerta_crítico("dia sem cobertura")
        dia_sem_militar.adicionar(dia)
        # Não escala ninguém. Indisponibilidade NUNCA quebrada.

  # ── FUNÇÃO AUXILIAR: registrar_serviço ──────────────────────────

  FUNÇÃO registrar_serviço(dia, militar, forcar_escala=False):

    # Banco de dados (persiste):
    EscalaItem.criar(escala, militar, dia, forcar_escala)
    Quadrinho[militar][dia.tipo_servico].quantidade += 1

    # Memória apenas (descartado ao fim da geração):
    counts_operacional[militar] += 1
    para k de 1 até janela_bloqueio inclusive:
      folga_global[militar].adicionar(dia.data + k dias)
```

---

## Resumo das garantias do sistema

| Garantia | Status |
|---|---|
| Menor coluna sempre tem prioridade | **Garantida pela ordenação** |
| Varredura sempre BASE → TOPO no empate | **Garantida pelo desempate invertido** |
| Toda a menor coluna é esgotada antes da próxima | **Garantida — ordenação agrupa counts iguais** |
| Indisponibilidade nunca quebrada | **Garantida — excluída inclusive do fallback** |
| Folga só quebrada quando toda coluna falha por folga | **Garantida — fallback classifica o motivo** |
| Count é global (todos os tipos somados) | **Garantida — `_carregar_matriz_historica` soma tudo** |
| Folga é global entre tipos | **Garantida — `folga_global` compartilhado** |
| Sem ponteiro, sem fila, sem round-robin | **Garantida — `sorted()` reexecutado a cada dia** |
| Militar indisponível retorna automaticamente | **Garantida — count dele não sobe durante ausência** |
