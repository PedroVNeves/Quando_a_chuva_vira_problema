# Declaração de contribuições

Projeto final de Análise Exploratória de Dados e Visualização, FGV EMAp, 2026.2.
"Quando a chuva vira problema".

## Composição da equipe

Inicialmente o projeto começou com os integrantes:

- Gabriel Andrade Souza
- Pedro Henrique Vasconcelos Neves

## Quem fez o quê

### Em conjunto

- proposta do projeto (marco 1): problema, dados e perguntas de domínio.

### Pedro Henrique Vasconcelos Neves

Primeira etapa do projeto, até a entrega intermediária (marco 2):

- escolha das bases de dados: pluviômetros do Alerta Rio e ocorrências do COR, no
  datalake municipal, e Censo 2022 e IPS Bairros 2022, no Data.Rio;
- definição do formato de armazenamento e scripts de coleta (`scripts/baixar_datario.py`
  e `scripts/baixar_data_rio.py`);
- primeiro tratamento dos dados e preparação das bases usadas nas avaliações iniciais,
  incluindo o preenchimento de falhas da chuva do Vidigal pelo acumulado da leitura
  seguinte;
- slides da apresentação do marco 2.

### Gabriel Andrade Souza

Primeira etapa, junto com Pedro:

- auditoria de cobertura e qualidade da chuva (datas futuras, cópias duplicadas, chaves
  incompletas, cobertura por estação e ano);
- catálogo dos tipos de ocorrência do COR, conferência de coordenadas e datas e
  associação das ocorrências aos bairros;
- narrativa e roteiro do marco 2.

Da entrega intermediária à entrega final:

- desenho da comparação por bairro-dia, com os dias sem registro no denominador, e das
  medidas de incerteza;
- análises das sete perguntas: frequência por faixa de chuva, afirmação da prefeitura
  em três unidades, janelas anteriores, diferenças e persistência entre bairros, perfil
  social e tamanho do bairro, registros dentro e fora das favelas, duração e primeira
  chegada, ciclo horário e extremos desde 1997;
- correções nos dados: relógio local do COR, realinhamento dos horários de 1997–2010 e
  equivalência de nomes de bairros entre as bases;
- base adicional de limites de favelas, incluída na coleta do Data.Rio;
- notebook final em forma de artigo, figuras, gráficos interativos, README e
  organização do repositório;
- apresentação final.