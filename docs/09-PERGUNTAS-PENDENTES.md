# 09 — Perguntas Pendentes para Fechar a Regra

Estas perguntas devem ser respondidas antes da implementação final.

## 1. Nota como critério de antiguidade

O campo `nota` deve ser usado como critério de desempate quando dois militares possuem:

- mesmo posto;
- mesma data de promoção?

Regra proposta:

```text
nota maior = mais antigo
```

Confirmar: sim ou não.

## 2. Ordem de processamento dos tipos

Como a folga é global, a ordem de processamento muda o resultado.

Qual estratégia deve ser oficial?

### Opção A — Cronológica

Processar os serviços pela data real:

```text
05/05 Preta
06/05 Vermelha
07/05 Preta
08/05 Vermelha
```

### Opção B — Por tipo

Processar todos os serviços de um tipo primeiro:

```text
Todas as Pretas
Todas as Vermelhas
Todas as Roxas
```

### Opção C — Configurável

Permitir que a OM escolha a estratégia.

Recomendação técnica: deixar configurável, com preferência para CRONOLÓGICA quando a folga global precisar refletir a realidade dia a dia.

## 3. Fallback de folga

Quando não houver ninguém disponível porque todos estão em folga, o sistema pode quebrar folga?

Opções:

- Não. Deixar dia sem cobertura.
- Sim. Escolher o primeiro candidato bloqueado apenas por folga e gerar alerta.
- Configurável por OM.

Recomendação: configurável.

## 4. Indisponibilidade pode ser quebrada?

Regra recomendada:

Indisponibilidade real nunca pode ser quebrada automaticamente.

Confirmar.

## 5. Cálculo exato da folga

Confirmar regra exata.

Exemplo:

- Serviço em 05/05.
- Duração: 24h.
- Folga: 48h.

Quais datas ficam bloqueadas?

Registrar explicitamente no sistema e nos testes.

## 6. Carry-over entre meses

Confirmar se serviços do mês anterior devem bloquear os primeiros dias do mês seguinte.

Recomendação: sim.

## 7. Logs de decisão

O sistema deve salvar logs detalhados de cada escolha?

Exemplo:

```text
08/05 Vermelha
Ribeiro: preenchido
Pire: preenchido
Rogério: folga
Carlos: disponível
Escolhido: Carlos
```

Recomendação: sim, pelo menos durante geração de previsão.
