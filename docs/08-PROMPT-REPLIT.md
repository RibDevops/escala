# 08 — Prompt para Replit

Use este prompt no Replit para orientar a IA antes de alterar o código.

---

## Prompt

Você está trabalhando em um sistema Django de escala militar.

Antes de alterar qualquer código, leia a documentação dentro da pasta `docs/`.

Documentos principais:

- `01-CONCEITOS.md`
- `02-ALGORITMO.md`
- `03-SNAPSHOT-OPERACIONAL.md`
- `04-FOLGA-E-INDISPONIBILIDADE.md`
- `05-EXEMPLOS.md`
- `06-CASOS-DE-TESTE.md`
- `07-ARQUITETURA-DJANGO.md`

O motor de escala deve reproduzir exatamente o procedimento manual da planilha.

Não tente otimizar a regra.

Não substitua a navegação do quadrinho por ordenação simples de contagem.

A lógica correta é:

1. Cada tipo de serviço possui seu próprio quadrinho.
2. O quadrinho é o histórico oficial.
3. O quadrinho nunca é alterado por folga ou indisponibilidade.
4. Folga e indisponibilidade são filtros temporários de elegibilidade.
5. Antes de cada serviço, deve ser criado um Snapshot Operacional.
6. Cada serviço gera uma nova execução completa do algoritmo.
7. A busca sempre começa pela menor coluna.
8. Dentro da coluna, a busca é sempre de baixo para cima.
9. Se todos da coluna estiverem preenchidos ou bloqueados, ir para a próxima coluna à direita.
10. Ao mudar de coluna, reiniciar a busca pelo militar mais moderno, isto é, pela base da tabela.
11. O primeiro candidato disponível encontrado deve ser escolhido.
12. Depois de registrar o serviço, atualizar a folga global.
13. A folga global vale para Preta, Vermelha, Roxa e demais tipos.
14. O snapshot deve ser descartado após cada serviço.

A ordenação dos militares deve representar a tabela visual:

- mais antigo no topo;
- mais moderno na base.

Critérios de ordenação:

1. `posto__ordem_hierarquica` crescente, pois menor ordem significa mais antigo;
2. `data_ultima_promocao` crescente, pois promoção mais antiga significa mais antigo;
3. `nota` decrescente, se a nota for confirmada como critério de antiguidade;
4. critério estável final, como `nome_guerra` ou `id`.

A navegação deve ocorrer do final da lista para o início.

Exemplo:

```text
lista[0] = mais antigo
lista[n-1] = mais moderno

A busca começa em lista[n-1].
```

Arquitetura solicitada:

Implemente ou refatore o motor usando a ideia de Snapshot Operacional.

Evite que a função principal fique cheia de `if` misturando:

- navegação;
- folga;
- indisponibilidade;
- banco de dados;
- atualização de quadrinho;
- logs.

Separar responsabilidades:

1. carregar militares;
2. carregar quadrinhos;
3. carregar indisponibilidades;
4. montar estado operacional;
5. montar snapshot;
6. navegar no snapshot;
7. registrar serviço;
8. atualizar folga global;
9. gerar logs.

Antes de implementar, responda com um plano técnico contendo:

1. Quais arquivos serão alterados.
2. Quais classes/funções serão criadas.
3. Como o snapshot será representado.
4. Como será feita a navegação de baixo para cima e esquerda para direita.
5. Como será garantido que o quadrinho não será alterado por folga ou indisponibilidade.
6. Como serão criados testes para os casos descritos em `06-CASOS-DE-TESTE.md`.

Só depois do plano aprovado, implemente.

---

## Atenção

O comportamento antigo baseado apenas em `sorted(counts)` não representa fielmente a planilha.

O motor deve seguir a navegação do quadrinho.

O objetivo é reproduzir o procedimento manual, não criar uma escala matematicamente otimizada.
