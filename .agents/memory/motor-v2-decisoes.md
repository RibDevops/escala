---
name: Motor v2 — Decisões de Algoritmo
description: Decisões confirmadas pelo escalante (via ChatGPT) para o MotorEscalaVertical v2
---

## Regras confirmadas

**Count por tipo, não total:**
Ao navegar o quadrinho Preta, usar apenas o count do quadrinho Preta. Vermelha usa apenas count Vermelha. Nunca somar todos os tipos. count = ajuste_inicial + quantidade + soma(LancamentoManualQuadrinho) — tudo conta como "coluna ocupada".

**Why:** A planilha manual tem um quadrinho separado por tipo. O count total era uma simplificação incorreta que dava prioridade errada quando um militar tinha muitos serviços em um tipo mas poucos em outro.

**Ordem de geração: por tipo (não cronológica):**
Toda a Preta primeiro → depois toda a Vermelha → demais tipos (TipoServico.ordem ASC). A folga_global é compartilhada.

**Why:** Reproduz o procedimento manual da planilha. Cronológico seria tecnicamente mais preciso, mas não é como o escalante trabalha.

**Navegação: menor coluna → BASE → TOPO:**
Menor count (menor coluna) é mais prioritário. Dentro da mesma coluna: BASE (mais moderno, maior índice) primeiro. Ao mudar de coluna, reinicia do BASE. Cada serviço = nova execução completa.

**Why:** Fiel à planilha. "sorted por count + desempate" é matematicamente equivalente, mas o Snapshot formal deixa a lógica auditável e testável.

**Snapshot Operacional formal:**
Classes: `EstadoCelula` (enum), `LinhaSnapshot` (dataclass), `SnapshotOperacional` (dataclass). Criado por serviço, descartado após. O quadrinho real nunca recebe marcação de folga/indisponibilidade.

**Fallback configurável:**
`ConfiguracaoEscala.permitir_quebrar_folga` (BooleanField, default=True). Se True: quebra folga com alerta ⚠ + forcar_escala=True. Se False: dia sem cobertura + alerta 🚨. Indisponibilidade NUNCA quebra.

**Count acumulativo anual:**
O quadrinho não reseta por mês. Um militar com 5 Pretas acumuladas começa em S6 no mês seguinte.

## Implementação

- `escalas/services.py` — Motor v2 completo
- `escalas/models.py` — `ConfiguracaoEscala.permitir_quebrar_folga` adicionado
- Migration: `0020_add_permitir_quebrar_folga.py`
- `engine_escala.py` — legado, NÃO usar, apenas referência
