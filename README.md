# MVP - Mapa de Inventário Hospitalar

Este projeto estrutura um produto minimamente viável para mapear hospitais municipais e estaduais, seus endereços, localização territorial e inventário inicial de equipamentos. A proposta usa os códigos existentes em `referencias/gestão (1)` como base conceitual e técnica, especialmente a lógica de dashboard, mapa georreferenciado, filtros, tabelas exportáveis e organização por indicadores.

O objetivo do MVP é responder a uma pergunta prática de gestão pública: quais hospitais possuem equipamentos ociosos, em manutenção, descartáveis ou com potencial de reaproveitamento, e como esses ativos podem ser priorizados para triagem, recondicionamento e redistribuição?

## Como executar

```bash
pip install -r requirements.txt
python app.py
```

Depois, acesse:

```text
http://127.0.0.1:8053
```

## Estrutura criada

```text
app.py
requirements.txt
data/
  entrada/
    hospitais_inventario.csv
  processado/
docs/
  plano_mvp.md
  kpis.md
  analise_ex_ante.md
  referencias_dados.md
  dicionario_dados.md
referencias/
  TD_2817_Analise_ExAnte.pdf
  gestão (1)/
```

## Dados de entrada

O arquivo principal do MVP é `data/entrada/hospitais_inventario.csv`. A versão atual foi gerada a partir da base oficial do CNES/DataSUS, competência 202603, filtrando hospitais/candidatos municipais do estado do Rio de Janeiro com gestão municipal e cadastro ativo.

Arquivos derivados da extração:

| Arquivo | Conteúdo |
| --- | --- |
| `data/entrada/hospitais_inventario.csv` | base resumida usada pelo painel |
| `data/entrada/hospitais_municipais_rj_cnes_202603.csv` | cadastro dos hospitais/candidatos municipais |
| `data/entrada/inventario_equipamentos_municipais_rj_cnes_202603.csv` | inventário detalhado de equipamentos por CNES |
| `data/entrada/referencia_local_hospitais.csv` | dados complementares extraídos da planilha local atualizada |
| `data/entrada/unidades_saude_municipais_rj_cnes_202603.csv` | UBS, postos de saúde e UPAs/pronto atendimento municipais ativos no RJ |
| `docs/contatos_hospitais_municipais_rj.md` | documentação com telefone e e-mail dos hospitais, quando disponíveis no CNES |
| `docs/contatos_hospitais_municipais_rj.csv` | versão tabular dos contatos para planilha |

Critério inicial de seleção:

- UF RJ, identificada pelo código de unidade iniciado em `33`.
- Gestão municipal (`TP_GESTAO = M`).
- Cadastro ativo, sem motivo de desativação.
- Nome contendo `HOSPITAL MUNICIPAL` ou combinação entre tipo de estabelecimento hospitalar (`CO_TIPO_ESTABELECIMENTO = 006`) e natureza jurídica `MUNICIPIO` (`CO_NATUREZA_JUR = 1244`).

O inventário usa os campos do CNES `QT_EXISTENTE`, `QT_USO` e `QT_SUS`. Como o CNES não informa diretamente descarte ou manutenção, o MVP calcula `OCIOSOS` como estimativa inicial: `QT_EXISTENTE - QT_USO`. Os campos `MANUTENCAO` e `DESCARTE` permanecem zerados até validação técnica local.

Campos mantidos no arquivo usado pelo painel:

| Campo | Descrição |
| --- | --- |
| ID_HOSPITAL | Identificador único da unidade |
| NOME_HOSPITAL | Nome do hospital |
| ESFERA | Municipal, Estadual ou A classificar |
| ENDERECO | Endereço completo |
| MUNICIPIO | Município da unidade |
| REGIAO | Região de saúde ou recorte territorial |
| LAT / LON | Coordenadas geográficas |
| LEITOS | Quantidade de leitos, quando disponível |
| EQUIPAMENTOS_TOTAL | Total de equipamentos cadastrados |
| OPERACIONAIS | Equipamentos em uso |
| OCIOSOS | Equipamentos sem uso corrente |
| MANUTENCAO | Equipamentos que demandam avaliação ou reparo |
| DESCARTE | Equipamentos sem viabilidade prevista, a validar tecnicamente |

Caso o CSV não exista, o aplicativo tenta carregar a planilha de referência em `referencias/gestão (1)/dados/brutos/endereço_caps.xlsx`, usando a aba `leitos` para montar uma base inicial de hospitais. Nesse caso, o inventário aparece como pendente, deixando claro quais unidades precisam de qualificação de dados.

## Atualizar a base CNES

O script de importação está em `scripts/importar_cnes_rj.py`. Ele espera que a base oficial baixada do CNES esteja em:

```text
data/processado/BASE_DE_DADOS_CNES_202603.ZIP
```

Para regenerar os CSVs:

```bash
python scripts/importar_cnes_rj.py
```

Resultado da extração atual:

| Métrica | Valor |
| --- | ---: |
| Hospitais/candidatos municipais RJ | 108 |
| Municípios cobertos | 58 |
| Linhas de inventário de equipamentos | 1.997 |
| Equipamentos existentes | 25.946 |
| Equipamentos ociosos estimados | 2.568 |
| Hospitais/candidatos com telefone no CNES | 89 |
| Hospitais/candidatos com e-mail no CNES | 65 |

## Contatos dos hospitais

A documentação de contatos está em `docs/contatos_hospitais_municipais_rj.md`, com versão em planilha em `docs/contatos_hospitais_municipais_rj.csv`.

Os campos foram extraídos diretamente do CNES:

- `NU_TELEFONE`: telefone cadastral da unidade.
- `NO_EMAIL`: e-mail cadastral da unidade.

Quando o CNES não trouxe telefone ou e-mail, o registro foi mantido como `Nao informado no CNES`. Essa ausência deve ser tratada como um KPI de qualificação cadastral e como tarefa de validação junto à Secretaria de Saúde, hospitais ou gestores locais.

## Fontes de dados

- CNES/DataSUS: base nacional de estabelecimentos e equipamentos, baixada pelo endpoint oficial de downloads do CNES.
- Portal CNES/DataSUS: documentação pública informa que o CNES contém estabelecimentos de saúde, modalidades de atendimento e gestão responsável.
- Secretaria Municipal de Saúde do Rio de Janeiro: página institucional informa que unidades sob gestão municipal devem manter cadastro CNES atualizado mensalmente e que esses dados são usados para faturamento e correspondência com capacidade operacional.
- PDF IPEA `TD_2817_Analise_ExAnte.pdf`: usado como referência metodológica para problema, público, teoria da mudança, governança, indicadores, metas, monitoramento e avaliação.

Documentação detalhada:

- `docs/referencias_dados.md`: fontes, links, critérios de seleção, linhagem, scripts, limitações e processo de atualização.
- `docs/dicionario_dados.md`: dicionário dos campos dos CSVs usados pelo MVP.

## Funcionalidades do MVP

- Mapa com hospitais georreferenciados.
- Filtros por município, esfera administrativa e potencial de reaproveitamento.
- Indicadores sintéticos: hospitais mapeados, equipamentos cadastrados, potencial de reuso e inventário pendente.
- Gráficos por esfera e por potencial de reaproveitamento.
- Tabela exportável para validação com hospitais, secretaria, engenharia clínica e parceiros técnicos.
- Base documental para política pública, KPIs e análise ex ante.
- Aba `Hospitais`, com seleção individual da unidade, localização, porte, acessos diários quando houver fonte integrada, quantitativo por tipo de equipamento e status operacional.
- Aba `Unidades de saude`, com UBS, postos de saúde e UPAs/pronto atendimento municipais, filtros, mapa clicável e microdados.

## Aba Hospitais

A aba `Hospitais` permite consultar uma unidade por vez. Para cada hospital, o painel apresenta:

- filtro por região de saúde;
- seleção de hospital por lista ou por clique no ponto do mapa;
- localização em mapa;
- porte da unidade, preferencialmente classificado por leitos CNES;
- média de acessos, somente quando houver fonte documentada de produção/atendimento;
- total de equipamentos existentes, em uso e ociosos estimados;
- quantitativo por tipo de equipamento;
- tabela de equipamentos com colunas de existente, em uso, ocioso, manutenção, descarte e para instalação.

Limitação atual: o CNES informa equipamentos existentes, em uso e vinculados ao SUS, mas não informa diretamente manutenção, descarte, equipamentos aguardando instalação ou média diária de acessos. Por isso, esses campos aparecem como zerados ou não documentados no painel até integração com dados de engenharia clínica, patrimônio, almoxarifado, chamados técnicos, SIH/SIA, prontuário, sistema local ou relatório formal de produção. A coluna `Ocioso` é uma estimativa inicial calculada como `QT_EXISTENTE - QT_USO`.

Uso operacional: escolha uma região para reduzir o mapa aos hospitais daquele território. Em seguida, clique em um hospital no mapa ou selecione-o na lista; os cards, gráficos e tabela passam a exibir o microdado da unidade selecionada.

## Aba Unidades de saude

A aba `Unidades de saude` amplia a visão territorial para além dos hospitais, incluindo UBS, unidades de atenção básica, Clínicas da Família, postos de saúde e UPAs/pronto atendimento municipais ativos no CNES.

Resultado da extração atual:

| Categoria | Quantidade |
| --- | ---: |
| UBS / Atenção básica | 2.452 |
| Clínica da Família | 126 |
| UPA / Pronto atendimento | 342 |
| Posto de saúde | 77 |
| Total | 2.871 |

Critérios principais:

- UF RJ, identificada pelo código de unidade iniciado em `33`;
- gestão municipal (`TP_GESTAO = M`);
- cadastro ativo, sem motivo de desativação;
- Clínica da Família: nome contendo `CLINICA DA FAMILIA`;
- UBS/atenção básica: tipo CNES `001 - UNIDADE BASICA DE SAUDE` ou nomes como UBS, USF, Unidade de Saúde da Família e Centro de Saúde;
- UPA/pronto atendimento: tipo CNES `008 - PRONTO ATENDIMENTO` ou nome contendo UPA/Unidade de Pronto Atendimento;
- posto de saúde: nome contendo `POSTO DE SAUDE`.

O mapa permite filtrar por tipo e município. Ao clicar em uma unidade, o painel exibe CNES, nome, categoria, município, endereço, telefone e e-mail quando disponíveis.

## Referência local atualizada

A planilha `referencias/gestão (1)/dados/brutos/endereço_caps.xlsx` foi reprocessada e gerou `data/entrada/referencia_local_hospitais.csv`.

O que foi aproveitado:

- aba `leitos`: CNES, hospital, município, endereço, telefone, coordenadas e quantidade de leitos do recorte da planilha;
- aba `regiao`: vínculo do `id_regiao` com a região de saúde;
- aba `APS`: indicações de área programática/serviço, sobretudo para Rio de Janeiro; os hospitais sem CNES nessa aba foram rastreados na base CNES/DataSUS 202603 e preenchidos na própria planilha;
- abas `caps`, `srts_UAI_UAA` e `CECOs`: seguem úteis para uma segunda etapa de mapa da rede de saúde mental.

Resultado do cruzamento:

| Métrica | Valor |
| --- | ---: |
| Hospitais na planilha local | 69 |
| Hospitais com telefone na planilha local | 69 |
| Hospitais da planilha local que cruzam com a base CNES municipal do MVP | 46 |
| Hospitais da aba APS com CNES preenchido por rastreamento | 3 |

Observação: a coluna `Leitos` da planilha local parece representar um recorte específico da rede, pois seus valores são bem menores que os leitos totais extraídos do CNES. Por isso, ela foi incorporada como `LEITOS_REFERENCIA`, sem substituir o porte hospitalar calculado por leitos CNES.

Hospitais rastreados e preenchidos na aba `APS`:

| Hospital na planilha | CNES | Nome CNES |
| --- | --- | --- |
| Hospital Municipal Pedro II | 6995462 | SMS HOSPITAL MUNICIPAL PEDRO II AP 53 |
| Hospital Municipal Evandro Freire | 7166494 | SMS HOSPITAL MUNICIPAL EVANDRO FREIRE AP 31 |
| Hospital Municipal Lourenço Jorge | 2270609 | SMS HOSPITAL MUNICIPAL LOURENCO JORGE AP 40 |

O arquivo original da planilha foi preservado em `referencias/gestão (1)/dados/brutos/endereço_caps.backup_antes_cnes.xlsx`. O resultado do rastreamento também foi salvo em `data/entrada/aps_hospitais_cnes.csv`.

## Política pública e análise ex ante

O PDF de referência do IPEA foi usado como sustentação metodológica. A lógica incorporada ao projeto segue os elementos centrais da análise ex ante: problema bem delimitado, público afetado, teoria da mudança, governança, modelo de implementação, indicadores, metas e sistema de monitoramento.

No contexto deste MVP, o problema público é a existência de equipamentos médicos ociosos, subutilizados, em manutenção indefinida ou descartados prematuramente, enquanto outras unidades enfrentam déficit de recursos tecnológicos. A intervenção proposta organiza dados, atores e fluxos decisórios para transformar inventário disperso em inteligência de redistribuição.

## KPIs estratégicos

Os KPIs foram organizados em quatro níveis:

| Dimensão | Exemplos de indicadores |
| --- | --- |
| Insumo | hospitais mapeados, completude do inventário, equipamentos cadastrados |
| Processo | tempo médio de triagem, taxa de classificação, taxa de validação técnica |
| Resultado | potencial de reuso, taxa de recondicionamento, taxa de redistribuição, economia estimada |
| Impacto | unidades beneficiadas, regiões atendidas, redução de descarte, ampliação de acesso |

As metas sugeridas para o piloto estão detalhadas em `docs/kpis.md`, com horizontes de 30, 60, 90 e 120 dias.

## Parcerias estratégicas

O MVP pressupõe cooperação entre hospitais municipais e estaduais, Secretaria de Saúde, engenharia clínica, CEFET ou centro técnico equivalente, equipe de dados e unidades demandantes. O papel do CEFET pode ser especialmente relevante na avaliação técnica, recondicionamento, formação de recursos humanos e validação dos critérios de reaproveitamento.

## Próximas evoluções

1. Integrar fonte oficial de hospitais municipais e estaduais.
2. Padronizar inventário por tipo de equipamento, fabricante, modelo, número patrimonial e estado operacional.
3. Incluir camada de demanda territorial por região de saúde.
4. Adicionar fluxo de validação técnica e trilha de auditoria.
5. Evoluir o score de reaproveitamento com critérios de custo, risco, criticidade e impacto social.
6. Integrar LLM para interpretar relatórios técnicos e observações textuais.
7. Implementar banco SQLite ou PostgreSQL para operação multiusuário.

# Contribuições para o resumo da proposta

## Item 5 — Evidências e plausibilidade

A plausibilidade da proposta fundamenta-se na ampla disponibilidade de dados administrativos, patrimoniais e operacionais da área da saúde, incluindo inventários hospitalares, sistemas de gestão de ativos, registros de manutenção, documentos técnicos e informações associadas ao uso, descarte ou substituição de equipamentos médicos. Embora essas bases sejam frequentemente heterogêneas, fragmentadas e pouco padronizadas, elas contêm sinais relevantes para a identificação de padrões de ociosidade, subutilização, descontinuidade operacional e potencial de reaproveitamento.

Do ponto de vista tecnológico, o problema é compatível com abordagens consolidadas de engenharia de dados, inteligência artificial e saúde digital. Técnicas de integração, limpeza, reconciliação e harmonização semântica permitem estruturar bases analíticas a partir de fontes dispersas, enquanto modelos de Machine Learning podem ser aplicados à classificação do estado dos equipamentos, detecção de padrões de uso, previsão de ociosidade e priorização de ativos com maior potencial de reaproveitamento.

Complementarmente, modelos de linguagem de grande escala (LLMs) podem ser utilizados para interpretar registros não estruturados, como relatórios técnicos, descrições operacionais, chamados administrativos e observações de manutenção. Esses modelos permitem extrair informações relevantes, padronizar descrições, enriquecer bases de dados e apoiar consultas em linguagem natural, ampliando a capacidade de análise e a transparência do processo decisório.

A proposta adota uma abordagem realista de apoio à decisão, na qual os modelos computacionais não substituem a governança institucional, a avaliação técnica especializada ou os critérios regulatórios, mas qualificam o processo decisório por meio de evidências estruturadas, rastreáveis e interpretáveis. Essa combinação entre maturidade tecnológica, disponibilidade de dados, capacidade institucional e foco em eficiência operacional sustenta a viabilidade de desenvolvimento de um sistema capaz de promover a redistribuição mais eficiente de equipamentos médicos, com potencial de redução de desperdícios e ampliação do acesso a serviços de saúde.

## Item 6 — Estratégia metodológica

A estratégia metodológica será baseada na construção de uma arquitetura integrada de dados e apoio à decisão, combinando técnicas de engenharia de dados, Machine Learning e modelos de linguagem, em ciclos iterativos de desenvolvimento, validação e aprimoramento em contexto aplicado.

Na primeira etapa, será realizado o mapeamento, ingestão e integração de múltiplas fontes de dados, incluindo inventários estruturados, registros administrativos, informações patrimoniais, históricos de manutenção e documentos técnicos. Serão aplicados procedimentos de limpeza, padronização, vinculação de registros, tratamento de inconsistências e harmonização semântica, com o objetivo de construir uma base analítica unificada, interoperável e auditável.

Na segunda etapa, serão desenvolvidos modelos analíticos para classificação e priorização de equipamentos com potencial de reaproveitamento. Técnicas de Machine Learning supervisionado e não supervisionado serão utilizadas para identificar padrões de ociosidade, estimar condições operacionais, segmentar perfis de uso e recomendar prioridades de triagem. Em paralelo, modelos de linguagem serão empregados para extração de informações de registros textuais, padronização de descrições técnicas, identificação de evidências relevantes e geração de representações estruturadas que ampliem a qualidade e a interpretabilidade dos dados.

Na terceira etapa, será implementado um sistema de apoio à decisão voltado à triagem, recondicionamento e redistribuição de equipamentos médicos, integrando critérios técnicos, logísticos, territoriais e de impacto social. O sistema deverá operar como um mecanismo de inteligência aplicada, no qual os modelos de Machine Learning contribuem para classificação, priorização e recomendação, enquanto os LLMs atuam como interface cognitiva de consulta, explicação e apoio à interpretação dos dados.

Por fim, a metodologia prevê a validação em contexto real, por meio de projeto piloto em uma rede, território ou conjunto de instituições parceiras. Essa validação permitirá avaliar a qualidade dos dados, o desempenho dos modelos, a aderência institucional, a viabilidade operacional e o impacto da solução sobre a gestão de equipamentos médicos. A partir dos resultados do piloto, será possível estruturar estratégias de escalabilidade incremental e replicação em outros contextos do sistema de saúde.

## Indicadores de impacto e KPIs

Para apoiar a avaliação objetiva dos resultados, a proposta poderá incorporar indicadores-chave de desempenho (KPIs) organizados em dimensões técnicas, operacionais, econômicas e sociais. Esses indicadores permitirão acompanhar tanto o desempenho da solução tecnológica quanto seus efeitos concretos sobre a gestão de equipamentos e o acesso aos serviços de saúde.

Entre os indicadores técnicos, destacam-se: percentual de registros padronizados e integrados à base analítica, taxa de completude dos dados, acurácia dos modelos de classificação, capacidade de identificação de equipamentos ociosos ou subutilizados e nível de rastreabilidade das recomendações geradas pelo sistema.

Na dimensão operacional, poderão ser monitorados indicadores como tempo médio de triagem dos equipamentos, número de ativos avaliados, percentual de equipamentos classificados com potencial de reaproveitamento, tempo de encaminhamento para recondicionamento e taxa de conversão entre equipamentos identificados, recondicionados e redistribuídos.

Na dimensão econômica, os KPIs poderão incluir estimativa de economia gerada pela reutilização de equipamentos, redução de custos associados à aquisição de novos ativos, diminuição de perdas por descarte prematuro e melhor aproveitamento do patrimônio público ou institucional já existente.

Na dimensão social e territorial, poderão ser avaliados indicadores como número de unidades beneficiadas, regiões atendidas, ampliação da disponibilidade de equipamentos em áreas com maior demanda, redução de desigualdades territoriais no acesso a recursos tecnológicos em saúde e contribuição para a sustentabilidade por meio da redução de descarte e prolongamento do ciclo de vida dos equipamentos.

## Nível de maturidade tecnológica (TRL)

A proposta pode ser posicionada em uma trajetória evolutiva de maturidade tecnológica, considerando a escala TRL (Technology Readiness Level). Em seu estágio inicial, a solução parte de fundamentos já consolidados em engenharia de dados, inteligência artificial, interoperabilidade e apoio à decisão, o que permite situar a proposta em um nível intermediário de maturidade conceitual e experimental.

Na fase de desenvolvimento, o projeto poderá avançar de um TRL inicial associado à formulação do conceito, modelagem da arquitetura e validação em ambiente controlado para níveis superiores, nos quais componentes tecnológicos são integrados, testados com dados reais e avaliados em contexto operacional. A construção do pipeline de dados, dos modelos de Machine Learning, da integração com LLMs e do sistema de apoio à decisão corresponde a uma etapa de demonstração tecnológica em ambiente relevante.

Com a implementação do projeto piloto em instituições parceiras, a solução poderá alcançar um nível mais avançado de prontidão, demonstrando sua viabilidade técnica, operacional e institucional em cenário real. Essa progressão de TRL será importante para orientar a estratégia de escalabilidade, reduzir riscos de implementação e demonstrar aos avaliadores que a proposta possui caminho claro entre pesquisa aplicada, validação e adoção prática.

## Parcerias estratégicas

A execução da proposta depende de articulação entre atores institucionais com competências complementares. Hospitais, secretarias de saúde, unidades públicas ou filantrópicas e instituições gestoras de equipamentos poderão contribuir com dados, demandas reais, validação operacional e participação no piloto.

Instituições tecnológicas e de ensino, como o CEFET, poderão atuar como centros de recondicionamento, avaliação técnica, desenvolvimento tecnológico, formação de recursos humanos e validação de processos. Essa participação é estratégica para conectar conhecimento aplicado, infraestrutura técnica e capacidade de inovação orientada a problemas concretos do sistema de saúde.

Também poderão ser mobilizadas parcerias com órgãos públicos, redes de saúde, centros de pesquisa, laboratórios de inovação, núcleos de engenharia clínica e especialistas em regulação sanitária, governança de dados e proteção de informações sensíveis. Essas parcerias fortalecem a viabilidade institucional da proposta, ampliam a capacidade de acesso a dados e permitem alinhar a solução a requisitos técnicos, éticos, legais e operacionais.

De forma integrada, as parcerias estratégicas devem garantir que o sistema proposto não seja apenas uma solução tecnológica isolada, mas uma plataforma de governança, inteligência e cooperação interinstitucional para ampliar o reaproveitamento de equipamentos médicos, reduzir desperdícios e melhorar a distribuição de recursos em saúde.

## Síntese estratégica

A proposta apresenta viabilidade técnica e institucional por combinar dados existentes da área da saúde, métodos consolidados de engenharia de dados, modelos de Machine Learning, LLMs e validação em contexto aplicado. Seu diferencial está na transformação de registros dispersos e pouco padronizados em inteligência operacional para apoiar decisões sobre triagem, recondicionamento e redistribuição de equipamentos médicos.

Ao incorporar KPIs, trajetória de maturidade tecnológica (TRL) e parcerias estratégicas, o projeto se fortalece perante os avaliadores por demonstrar não apenas uma hipótese tecnicamente plausível, mas também um caminho mensurável, validável e escalável para gerar impacto econômico, social e territorial no sistema de saúde.
