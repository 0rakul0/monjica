# Plano do MVP

## Objetivo

Construir um mapa operacional de hospitais municipais e estaduais, contendo nome, endereco, localizacao, esfera administrativa e inventario inicial de equipamentos. O MVP deve apoiar a decisao sobre quais unidades possuem ativos ociosos, em manutencao, descartaveis ou com potencial de reaproveitamento.

## Produto minimo

1. Base unica de hospitais e inventario.
2. Mapa georreferenciado com filtros por municipio, esfera e potencial de reaproveitamento.
3. Tabela exportavel para revisao pelos parceiros.
4. Indicadores de desempenho para acompanhamento do piloto.
5. Documentacao da logica de politica publica com base em analise ex ante.

## Campos minimos da base

| Campo | Descricao |
| --- | --- |
| ID_HOSPITAL | Identificador unico da unidade |
| NOME_HOSPITAL | Nome oficial ou nome operacional |
| ESFERA | Municipal, Estadual ou A classificar |
| ENDERECO | Endereco completo |
| MUNICIPIO | Municipio da unidade |
| REGIAO | Regiao de saude ou divisao territorial adotada |
| LAT / LON | Coordenadas geograficas |
| LEITOS | Quantidade de leitos, quando disponivel |
| EQUIPAMENTOS_TOTAL | Total de equipamentos cadastrados |
| OPERACIONAIS | Equipamentos em uso |
| OCIOSOS | Equipamentos sem uso corrente |
| MANUTENCAO | Equipamentos que demandam avaliacao ou reparo |
| DESCARTE | Equipamentos sem viabilidade prevista |

## Ciclo de implementacao

1. Diagnostico: consolidar hospitais, enderecos, coordenadas e inventario inicial.
2. Priorizacao: classificar potencial de reaproveitamento e criticidade territorial.
3. Validacao tecnica: revisar dados com hospitais, engenharia clinica e centro de recondicionamento.
4. Piloto: selecionar territorio ou rede de unidades para testar fluxo de triagem.
5. Escala: institucionalizar governanca, indicadores, rotina de atualizacao e pactuacao entre parceiros.

## Uso do MVP

```bash
pip install -r requirements.txt
python app.py
```

O painel sera executado em `http://127.0.0.1:8053`.
