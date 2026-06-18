# 04 — Folga e Indisponibilidade

## 1. Folga

Folga é o período de descanso obrigatório após um serviço.

Durante a folga, o militar não deve ser escalado para nenhum tipo de serviço.

A folga é global.

Exemplo:

Se o militar fez Preta em 05/05, ele pode ficar bloqueado para Vermelha em 06/05.

## 2. Configuração da folga

A folga pode ser configurada em horas.

Exemplo:

- duração do serviço: 24 horas;
- folga mínima: 48 horas.

Nesse caso, após o serviço, o militar fica bloqueado pelo período configurado conforme a regra operacional do sistema.

## 3. Regra operacional recomendada

A regra deve ser explícita no código.

Exemplo conceitual:

```text
serviço em 05/05
serviço dura 24h
folga mínima 48h
militar fica bloqueado conforme janela calculada pela configuração
```

O importante é que essa janela seja única e global para todos os tipos de serviço.

## 4. Folga não altera quadrinho

A folga não deve preencher nenhuma célula do quadrinho.

Ela só aparece no Snapshot Operacional como motivo de bloqueio.

## 5. Indisponibilidade

Indisponibilidade é um bloqueio real cadastrado no sistema.

Exemplos:

- férias;
- licença médica;
- missão;
- afastamento;
- dispensa.

Indisponibilidade também não altera o quadrinho.

Ela aparece no Snapshot Operacional como motivo de bloqueio.

## 6. Diferença entre folga e indisponibilidade

| Critério | Folga | Indisponibilidade |
|---|---|---|
| Origem | Gerada pelo serviço | Cadastrada no sistema |
| Vale para todos os tipos? | Sim | Sim |
| Altera quadrinho? | Não | Não |
| Conta como serviço? | Não | Não |
| Deve aparecer no snapshot? | Sim | Sim |
| Pode ser ignorada? | Somente se houver regra de fallback | Normalmente não |

## 7. Fallback

O fallback deve ser tratado com muito cuidado.

Regra sugerida:

1. O motor tenta encontrar militar disponível normalmente.
2. Se ninguém estiver disponível por causa de folga, pode existir fallback configurável.
3. Se todos estiverem com indisponibilidade real, o dia deve ficar sem cobertura e gerar alerta crítico.

Recomendação:

O fallback deve ser uma configuração explícita, nunca um comportamento escondido.

Exemplo:

```text
permitir_quebrar_folga_em_ultimo_caso = True/False
```

## 8. Carry-over

A folga pode atravessar a virada do mês.

Exemplo:

- Serviço em 30/04.
- Folga bloqueia 01/05 e 02/05.

Ao gerar a escala de maio, o motor deve consultar serviços anteriores que ainda geram folga no início do mês.

## 9. Regra central

Folga e indisponibilidade são filtros de elegibilidade.

Elas não mudam o histórico.

Elas apenas impedem que um militar seja escolhido em determinada data.
