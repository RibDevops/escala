# 07 — Arquitetura Recomendada para Django

## 1. Objetivo

Este documento sugere uma arquitetura para implementar o motor de escala no Django sem misturar regras de negócio, navegação e persistência.

## 2. Separação de responsabilidades

O motor deve ser dividido em camadas:

1. Carregamento de dados.
2. Construção do estado operacional.
3. Criação do snapshot.
4. Navegação do quadrinho.
5. Registro do serviço.
6. Atualização da folga global.
7. Logs e alertas.

## 3. Classes sugeridas

### MotorEscala

Responsável por coordenar a geração.

Métodos sugeridos:

```python
class MotorEscala:
    def gerar(self):
        pass

    def processar_servico(self, dia):
        pass
```

### EstadoOperacional

Guarda o estado atual da geração.

Campos sugeridos:

```python
@dataclass
class EstadoOperacional:
    militares: list
    quadrinhos: dict
    indisponibilidades: dict
    folga_global: dict
    servicos_registrados: list
```

### SnapshotOperacional

Representa a visão temporária de um serviço.

```python
@dataclass
class SnapshotOperacional:
    data: date
    tipo_servico: TipoServico
    linhas: list
```

### LinhaSnapshot

Representa a situação de um militar numa coluna.

```python
@dataclass
class LinhaSnapshot:
    militar: Militar
    ordem: int
    coluna: int
    estado: str
    motivo: str | None = None
```

### NavegadorQuadrinho

Responsável apenas por navegar.

Não deve saber calcular folga.

Não deve consultar banco.

Não deve saber regra de férias.

```python
class NavegadorQuadrinho:
    def encontrar_primeiro_disponivel(self, snapshot):
        pass
```

## 4. Estados de célula

Usar constantes ou Enum.

```python
from enum import Enum

class EstadoCelula(Enum):
    DISPONIVEL = "DISPONIVEL"
    PREENCHIDO = "PREENCHIDO"
    FOLGA = "FOLGA"
    INDISPONIVEL = "INDISPONIVEL"
    BLOQUEADO = "BLOQUEADO"
```

## 5. Pseudocódigo principal

```python
def processar_servico(dia):
    quadrinho = obter_quadrinho_do_tipo(dia.tipo_servico)

    snapshot = criar_snapshot(
        quadrinho=quadrinho,
        data=dia.data,
        folga_global=estado.folga_global,
        indisponibilidades=estado.indisponibilidades,
    )

    candidato = navegador.encontrar_primeiro_disponivel(snapshot)

    if not candidato:
        registrar_alerta_sem_cobertura(dia)
        return

    registrar_servico(dia, candidato.militar)
    atualizar_quadrinho(candidato.militar, dia.tipo_servico, dia.data)
    atualizar_folga_global(candidato.militar, dia.data)
```

## 6. Pseudocódigo do navegador

```python
def encontrar_primeiro_disponivel(snapshot):
    for coluna in snapshot.colunas_da_esquerda_para_direita():
        for linha in snapshot.linhas_de_baixo_para_cima():
            celula = snapshot.obter_celula(linha, coluna)

            if celula.estado == EstadoCelula.DISPONIVEL:
                return celula

    return None
```

## 7. Construção do snapshot

```python
def criar_snapshot(quadrinho, data, folga_global, indisponibilidades):
    linhas = []

    for militar in militares_ordenados:
        primeira_coluna_vazia = localizar_primeira_coluna_vazia(militar, quadrinho)

        for coluna in colunas_relevantes:
            if celula_preenchida(militar, coluna):
                estado = PREENCHIDO
                motivo = "Já preenchido no quadrinho"
            elif data in indisponibilidades[militar.id]:
                estado = INDISPONIVEL
                motivo = "Indisponibilidade cadastrada"
            elif data in folga_global[militar.id]:
                estado = FOLGA
                motivo = "Folga global"
            else:
                estado = DISPONIVEL
                motivo = None

            linhas.append(LinhaSnapshot(...))

    return SnapshotOperacional(...)
```

## 8. Observação importante

O snapshot não deve ser persistido.

Ele pode ser usado para:

- log;
- preview;
- debug;
- explicação visual;
- testes.

Mas o banco deve guardar apenas:

- serviço real;
- quadrinho real;
- indisponibilidades reais;
- configurações;
- alertas, se necessário.

## 9. Logs recomendados

Para cada serviço, gravar log como:

```text
Serviço: 08/05 — Vermelha
Quadrinho: Vermelha
Menor coluna: S2
Ordem: BASE → TOPO

Ribeiro: PREENCHIDO
Pire: PREENCHIDO
Rogério: FOLGA
Carlos: DISPONIVEL

Escolhido: Carlos
```

Esses logs são fundamentais para validar o motor contra a planilha manual.

## 10. Recomendação final

Evitar implementar o motor apenas com `sorted(counts)`.

A regra correta é navegação sobre quadrinho.

A contagem pode ajudar a montar o quadrinho, mas a escolha do militar deve seguir o procedimento:

1. menor coluna;
2. baixo para cima;
3. esquerda para direita;
4. primeiro disponível vence.
