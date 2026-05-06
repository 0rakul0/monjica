# MVP - Mapa de Inventario Hospitalar

Este projeto estrutura um produto minimamente viavel para apoiar um piloto local no estado do Rio de Janeiro voltado a triagem, recondicionamento e redistribuicao de equipamentos medico-hospitalares subutilizados. A base tecnica reaproveita referencias existentes em `referencias/gestao (1)` e foi evoluida para um sistema principal com painel web, ETL, banco SQLite e camada analitica.

## Objetivo do piloto

Responder a uma pergunta pratica de gestao publica: quais unidades da rede publica do RJ possuem ativos com potencial de reaproveitamento, em quais regioes esse problema se concentra e como isso pode orientar um fluxo inicial de redistribuicao?

## Posicionamento para o edital

O projeto esta focado, por enquanto, em um piloto local no RJ. Esse recorte deixa a proposta mais clara e defensavel:

- usa dados reais e acessiveis;
- organiza a rede por regiao de saude;
- permite validacao em campo;
- transforma o painel em infraestrutura de apoio a uma politica publica piloto.

## Leitura do painel por eixo do projeto

Cada aba do sistema foi desenhada para contemplar um aspecto da proposta:

| Aba | Papel no piloto | O que entrega |
| --- | --- | --- |
| `Visao geral` | diagnostico territorial | panorama da rede, concentracao regional e comparacao entre regioes |
| `Hospitais` | triagem microassistencial | leitura detalhada por hospital, CNES, porte, localizacao e inventario |
| `Clinicas da Familia` | capacidade receptora na APS | leitura territorial da atencao primaria e lacunas de integracao |
| `Unidades de saude` | infraestrutura territorial ampliada | mapa da rede municipal para alem dos hospitais |
| `Inteligencia MONJICA` | apoio analitico | score, recomendacoes e priorizacao de ativos |
| `Fluxo de redistribuicao` | operacionalizacao | origem, destino e prioridade logistica |

## Estrutura principal

```text
app.py
requirements.txt
core/
  normalizacao.py
  referencias_rj.py
data/
  entrada/
  processado/
banco/
  monjica.db
docs/
  plano_mvp.md
  kpis.md
  analise_ex_ante.md
  referencias_dados.md
  dicionario_dados.md
paginas/
scripts/
sql/
referencias/
```

## Como executar

```bash
pip install -r requirements.txt
python app.py
```

Depois, acesse:

```text
http://127.0.0.1:8053
```

## Banco de dados e pipeline

O banco principal e criado em:

```text
banco/monjica.db
```

Fluxo principal:

1. importar ou atualizar a base CNES do RJ;
2. executar o ETL para montar estabelecimentos, municipios, inventario e perfil hospitalar;
3. calcular o score MONJICA;
4. abrir o painel para leitura territorial e operacional.

Comandos principais:

```bash
python scripts/importar_cnes_rj.py
python scripts/etl_monjica.py
python scripts/score_monjica.py
python app.py
```

## O que o ETL organiza

- estabelecimentos de saude;
- municipios com regionalizacao do RJ;
- inventario de equipamentos CNES;
- perfil hospitalar consolidado;
- demanda regional inicial;
- equipamentos expandidos para scoring;
- trilha de log da carga.

## Regionalizacao

As regioes de saude do RJ foram integradas ao sistema principal e agora orientam os filtros e mapas do painel. Essa regionalizacao e usada tanto na camada visual quanto no ETL, para que o piloto tenha um recorte territorial consistente desde a base ate a interface.

## Dados de entrada principais

| Arquivo | Conteudo |
| --- | --- |
| `data/entrada/hospitais_inventario.csv` | base resumida usada pelo painel |
| `data/entrada/hospitais_municipais_rj_cnes_202603.csv` | cadastro dos hospitais/candidatos municipais |
| `data/entrada/inventario_equipamentos_municipais_rj_cnes_202603.csv` | inventario detalhado de equipamentos por CNES |
| `data/entrada/unidades_saude_municipais_rj_cnes_202603.csv` | UBS, postos, UPA e Clinicas da Familia |
| `data/entrada/referencia_local_hospitais.csv` | dados complementares da referencia local |
| `data/entrada/correcoes_coordenadas_unidades.csv` | correcoes manuais documentadas |

## Limitacoes atuais

- o CNES nao informa diretamente manutencao, descarte e numero patrimonial individual;
- o inventario de Clinicas da Familia ainda depende de fonte adicional;
- medias de acessos diarios nao estao padronizadas em uma base unica para todas as unidades;
- a demanda regional ainda parte de estimativa inicial e deve evoluir para fonte institucional.

## Documentos de apoio

Use os arquivos em `docs/` como referencia principal para narrativa, KPIs, fontes e dicionario de dados:

- `docs/plano_mvp.md`
- `docs/analise_ex_ante.md`
- `docs/kpis.md`
- `docs/referencias_dados.md`
- `docs/dicionario_dados.md`
