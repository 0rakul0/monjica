# Dicionario de dados

Este dicionario descreve os principais campos dos CSVs usados pelo MVP.

## `hospitais_inventario.csv`

| Campo | Origem | Descricao |
| --- | --- | --- |
| `ID_HOSPITAL` | CNES `CO_CNES` | identificador CNES do hospital |
| `NOME_HOSPITAL` | CNES `NO_FANTASIA` | nome fantasia da unidade |
| `ESFERA` | derivado | esfera administrativa usada no MVP; nesta versao, Municipal |
| `ENDERECO` | CNES | endereco consolidado com logradouro, numero, complemento/bairro e CEP |
| `MUNICIPIO` | CNES `NO_MUNICIPIO` | municipio gestor/localizado |
| `REGIAO` | planilha local quando disponivel | regiao de saude ou `A classificar` |
| `LAT` | CNES | latitude normalizada |
| `LON` | CNES | longitude normalizada |
| `LEITOS` | CNES `rlEstabComplementar` | soma de leitos existentes no CNES |
| `EQUIPAMENTOS_TOTAL` | CNES `rlEstabEquipamento` | soma de `QT_EXISTENTE` |
| `OPERACIONAIS` | CNES `rlEstabEquipamento` | soma de `QT_USO` |
| `OCIOSOS` | calculado | `QT_EXISTENTE - QT_USO`, agregado por hospital |
| `MANUTENCAO` | placeholder | depende de dados de engenharia clinica |
| `DESCARTE` | placeholder | depende de dados patrimoniais/validacao tecnica |

Campo planejado, ainda nao populado:

| Campo | Origem esperada | Descricao |
| --- | --- | --- |
| `MEDIA_ACESSOS` | fonte documentada de producao/atendimento | media diaria, semanal ou mensal de acessos, conforme metodologia declarada |

## `hospitais_municipais_rj_cnes_202603.csv`

| Campo | Descricao |
| --- | --- |
| `CO_UNIDADE` | codigo composto da unidade no CNES |
| `CO_CNES` | codigo CNES do estabelecimento |
| `NO_FANTASIA` | nome fantasia cadastrado |
| `NO_RAZAO_SOCIAL` | razao social cadastrada |
| `CRITERIO_SELECAO` | regra pela qual a unidade entrou na base |
| `ENDERECO` | endereco consolidado |
| `NO_BAIRRO` | bairro |
| `CO_CEP` | CEP |
| `NO_MUNICIPIO` | municipio |
| `CO_MUNICIPIO_GESTOR` | codigo do municipio gestor |
| `NU_TELEFONE` | telefone cadastral |
| `NO_EMAIL` | e-mail cadastral |
| `LAT` | latitude normalizada |
| `LON` | longitude normalizada |
| `CO_NATUREZA_JUR` | natureza juridica CNES |
| `TP_GESTAO` | tipo de gestao; `M` indica gestao municipal |
| `CO_TIPO_ESTABELECIMENTO` | tipo do estabelecimento; `006` indica hospital |
| `CO_ATIVIDADE_PRINCIPAL` | atividade principal cadastrada |
| `TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')` | data de atualizacao cadastral no CNES |

## `inventario_equipamentos_municipais_rj_cnes_202603.csv`

| Campo | Descricao |
| --- | --- |
| `CO_UNIDADE` | codigo composto da unidade CNES |
| `CO_CNES` | codigo CNES do hospital |
| `NO_FANTASIA` | nome fantasia do hospital |
| `NO_MUNICIPIO` | municipio |
| `CO_TIPO_EQUIPAMENTO` | codigo do tipo de equipamento |
| `DS_TIPO_EQUIPAMENTO` | descricao do tipo de equipamento |
| `CO_EQUIPAMENTO` | codigo do equipamento |
| `DS_EQUIPAMENTO` | descricao do equipamento |
| `QT_EXISTENTE` | quantidade existente cadastrada |
| `QT_USO` | quantidade em uso cadastrada |
| `QT_SUS` | quantidade disponivel ao SUS, quando informada |
| `QT_OCIOSO_ESTIMADO` | `QT_EXISTENTE - QT_USO`, com minimo zero |

## `referencia_local_hospitais.csv`

| Campo | Descricao |
| --- | --- |
| `ID_HOSPITAL` | CNES informado na planilha local |
| `HOSPITAL_REFERENCIA` | nome do hospital na planilha local |
| `MUNICIPIO_REFERENCIA` | municipio na planilha local |
| `REGIAO_REFERENCIA` | regiao derivada da aba `regiao` |
| `ENDERECO_REFERENCIA` | endereco da planilha local |
| `LEITOS_REFERENCIA` | leitos do recorte da planilha local |
| `LAT` | latitude da planilha local |
| `LOG` | longitude da planilha local |
| `TELEFONE_REFERENCIA` | telefone da planilha local |
| `EMAIL_REFERENCIA` | e-mail da planilha local, quando houver |

## `aps_hospitais_cnes.csv`

| Campo | Descricao |
| --- | --- |
| `nome_servico_planilha` | nome original na aba `APS` |
| `CNES` | CNES localizado na base CNES/DataSUS 202603 |
| `nome_servico_cnes` | nome fantasia localizado no CNES |
| `municipio_cnes` | municipio localizado no CNES |
| `endereco_cnes` | endereco localizado no CNES |

## `unidades_saude_municipais_rj_cnes_202603.csv`

| Campo | Descricao |
| --- | --- |
| `CO_UNIDADE` | codigo composto da unidade CNES |
| `CO_CNES` | codigo CNES da unidade |
| `NO_FANTASIA` | nome fantasia |
| `NO_RAZAO_SOCIAL` | razao social |
| `CATEGORIA_UNIDADE` | classificacao usada no MVP: UBS/Atencao basica, Clinica da familia, Posto de saude ou UPA/Pronto atendimento |
| `DS_TIPO_ESTABELECIMENTO` | tipo de estabelecimento no CNES |
| `ENDERECO` | endereco consolidado |
| `NO_BAIRRO` | bairro |
| `CO_CEP` | CEP |
| `NO_MUNICIPIO` | municipio |
| `CO_MUNICIPIO_GESTOR` | codigo do municipio gestor |
| `NU_TELEFONE` | telefone cadastral |
| `NO_EMAIL` | e-mail cadastral |
| `LAT` | latitude normalizada |
| `LON` | longitude normalizada |
| `CO_NATUREZA_JUR` | natureza juridica |
| `TP_GESTAO` | tipo de gestao |
| `CO_TIPO_ESTABELECIMENTO` | codigo do tipo de estabelecimento |
| `TO_CHAR(DT_ATUALIZACAO,'DD/MM/YYYY')` | data de atualizacao cadastral |

## `correcoes_coordenadas_unidades.csv`

| Campo | Descricao |
| --- | --- |
| `CO_CNES` | CNES da unidade corrigida |
| `NO_FANTASIA` | nome da unidade |
| `LAT_CORRIGIDA` | latitude corrigida |
| `LON_CORRIGIDA` | longitude corrigida |
| `FONTE_CORRECAO` | fonte ou metodo usado na correcao |
| `OBSERVACAO` | observacao sobre precisao e necessidade de validacao |
