# Documentação do Motor de Escala Militar

Este pacote contém a especificação funcional e técnica do motor de escala baseado em quadrinhos.

## Arquivos

- `docs/01-CONCEITOS.md`
- `docs/02-ALGORITMO.md`
- `docs/03-SNAPSHOT-OPERACIONAL.md`
- `docs/04-FOLGA-E-INDISPONIBILIDADE.md`
- `docs/05-EXEMPLOS.md`
- `docs/06-CASOS-DE-TESTE.md`
- `docs/07-ARQUITETURA-DJANGO.md`
- `docs/08-PROMPT-REPLIT.md`
- `docs/09-PERGUNTAS-PENDENTES.md`

## Ideia central

O motor não escolhe o militar por cálculo livre.

Ele reproduz a navegação manual do quadrinho:

1. menor coluna;
2. de baixo para cima;
3. esquerda para direita;
4. primeiro disponível vence.

Folga e indisponibilidade não alteram o quadrinho. Elas aparecem apenas no Snapshot Operacional.
