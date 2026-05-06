# Plano do MVP

## Objetivo do piloto

Estruturar um piloto local no estado do Rio de Janeiro para apoiar a triagem, o recondicionamento e a redistribuição de equipamentos médico-hospitalares subutilizados na rede pública. O foco inicial do MVP não é resolver toda a política pública de uma vez, mas organizar um diagnóstico territorial confiável, uma base integrada de estabelecimentos e um fluxo inicial de apoio à decisão.

## Recorte territorial e institucional

- Território inicial: estado do Rio de Janeiro.
- Unidade de gestão territorial: regiões de saúde do RJ.
- Unidades prioritárias: hospitais municipais e estaduais.
- Rede complementar: Clínicas da Família, UBS, postos de saúde e UPA.
- Atores esperados no piloto: hospitais, secretarias de saúde, equipe de dados, engenharia clínica e parceiro técnico de recondicionamento.

## Pergunta prática que o MVP responde

Quais unidades da rede pública do RJ concentram equipamentos com maior potencial de reaproveitamento, em quais regiões isso se concentra e como esse diagnóstico pode apoiar um fluxo piloto de redistribuição com base territorial?

## Produto mínimo viável

1. Base única de estabelecimentos, hospitais e inventário inicial.
2. Regionalização consistente por região de saúde do RJ.
3. Painel com leitura macro, micro e logística do piloto.
4. Indicadores para acompanhamento de execução, resultado e impacto.
5. Documentação técnica e narrativa alinhadas à proposta do edital.

## Arquitetura narrativa do painel

Cada aba foi pensada como um eixo independente do piloto e como uma parte da narrativa do edital:

| Aba | Papel no piloto | O que demonstra |
| --- | --- | --- |
| Visão geral | diagnóstico territorial | panorama da rede, concentração regional e regiões com maior índice de reaproveitamento |
| Hospitais | triagem microassistencial | leitura detalhada da unidade, porte, inventário e priorização local |
| Clínicas da Família | capacidade receptora na APS | presença territorial da APS e lacunas para integração de inventário |
| Unidades de saúde | infraestrutura territorial ampliada | capilaridade da rede pública e contexto das unidades não hospitalares |
| Inteligência MONJICA | motor analítico | score, recomendação e critérios de apoio à decisão |
| Fluxo de redistribuição | operacionalização | conexão entre origem, destino e prioridade logística |

## Campos mínimos da base

| Campo | Descrição |
| --- | --- |
| ID_HOSPITAL | Identificador único da unidade |
| NOME_HOSPITAL | Nome oficial ou nome operacional |
| ESFERA | Municipal, Estadual ou A classificar |
| ENDERECO | Endereço completo |
| MUNICIPIO | Município da unidade |
| REGIAO | Região de saúde do RJ |
| LAT / LON | Coordenadas geográficas |
| LEITOS | Quantidade de leitos, quando disponível |
| EQUIPAMENTOS_TOTAL | Total de equipamentos cadastrados |
| OPERACIONAIS | Equipamentos em uso |
| OCIOSOS | Equipamentos sem uso corrente |
| MANUTENCAO | Equipamentos que demandam avaliação ou reparo |
| DESCARTE | Equipamentos sem viabilidade prevista |

## Ciclo de implementação do piloto

1. Diagnóstico territorial: consolidar hospitais, unidades, endereços, coordenadas, regiões e inventário inicial.
2. Triagem analítica: calcular potencial de reaproveitamento, criticidade e prioridades.
3. Validação técnica: revisar dados com hospitais, engenharia clínica e parceiro técnico.
4. Piloto operacional: selecionar uma ou duas regiões prioritárias para simular ou executar o fluxo.
5. Monitoramento: acompanhar KPIs, qualidade da base e aderência institucional.
6. Escalabilidade: preparar replicação para outros recortes do SUS a partir da experiência do RJ.

## Critérios de sucesso do MVP

- Cobrir a rede pública prioritária do RJ com regionalização consistente.
- Identificar regiões com maior pressão de reaproveitamento.
- Permitir leitura micro por hospital e por unidade receptora.
- Produzir evidência clara para decisão sobre o piloto operacional.
- Deixar rastreável o que já está documentado e o que ainda precisa de integração.

## Uso do MVP

```bash
pip install -r requirements.txt
python app.py
```

O painel será executado em `http://127.0.0.1:8053`.
