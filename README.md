# Quando a chuva vira problema

**Chuva e ocorrências urbanas nos bairros do Rio de Janeiro**

Projeto da disciplina **Análise Exploratória de Dados e Visualização**, FGV EMAp, 2026.2.

**Autores:** Pedro Henrique Vasconcelos Neves e Gabriel Andrade Souza.

## Sobre o projeto

Como a frequência de ocorrências registradas varia com a chuva e entre os bairros do
Rio de Janeiro? O ponto de partida é uma afirmação da prefeitura: um dia com mais de
30 mm num pluviômetro teria mais de 50% de chance de alagamento.

O projeto cruza as medições dos pluviômetros do Sistema Alerta Rio, os registros do
Centro de Operações Rio (COR), os limites de bairros do Instituto Pereira Passos (IPP)
e indicadores sociais do Data.Rio. A análise diária cobre 2020–2021, os dois anos em
que é possível comparar dias com e sem registros em todos os bairros.

Tudo está no [notebook principal](analise.ipynb), escrito como artigo: cada seção tem
pergunta, método, gráfico e resposta. Os procedimentos completos e as auditorias
ficam no apêndice.

## Principais resultados

- **A frequência de registros cresce com a chuva.** A frequência de bairro-dias com
  acúmulo de água passa de 0,05% sem chuva para 12,8% entre 30 e 50 mm. A conta usa
  121.423 bairro-dias de 167 bairros.
- **A afirmação da prefeitura depende da unidade.** Acima de 30 mm, há registro em 16%
  dos bairro-dias, em 44% das estação-dias e em 94% das cidade-dias. O patamar de 50% é
  plausível para a área de uma estação, mas não para um bairro isolado.
- **A chuva anterior também importa.** Mais chuva nas 1 h, 4 h, 24 h ou 96 h
  anteriores se associa a mais registros, sem uma janela melhor que as outras.
- **Os registros se concentram em poucos bairros.** A Barra da Tijuca soma 202 dos
  1.724 registros, e dez bairros reúnem 41% do total. Sob a mesma chuva, os bairros
  diferem, e essas diferenças se repetem em parte de 2020 para 2021 (ρ = 0,65 em 100
  bairros).
- **O perfil social não explica as diferenças de forma uniforme.** Bairros com IPS
  maior tendem a ter mais registros, ao contrário da hipótese inicial, o que pode
  refletir mais monitoramento. Densidade e o indicador de favelas ficam perto de zero,
  e domicílios inadequados só mostram associação em 2020.
- **A chuva se concentra no início da noite** nas três estações com série histórica
  comparável. A série não permite afirmar que os extremos aumentaram.

Os resultados descrevem **registros** do COR, não todos os problemas da cidade, e
mostram associações, não causas.

## Estrutura do notebook

| Seção | Conteúdo | Pergunta da proposta |
|---|---|---|
| 1 | Dados, recortes e ligação entre estação e bairro | — |
| 2 | Onde e quando chove: totais, sazonalidade, ciclo horário e extremos | 1 |
| 3 | Temporal de abril de 2019 e conferência dos horários | — |
| 4 | Chuva e frequência de registros; afirmação da prefeitura | 2 e 3 |
| 5 | Pancada ou acumulado: janelas anteriores de chuva | 4 |
| 6 | Diferenças entre bairros, mapa e persistência entre anos | 2 e 5 |
| 7 | Perfil social e habitação | 6 |
| 8 | Duração dos registros e primeira chegada dos órgãos | 7 |
| 9 | Conclusões, limites e balanço da proposta | — |

A proposta previa 2015–2025. A seção 1 explica por que a análise diária ficou em
2020–2021, e a seção 9.2 mostra o que foi respondido de cada pergunta.

## Dados

| Dados | Origem | Uso |
|---|---|---|
| Leituras de chuva a cada 15 min | Sistema Alerta Rio, via datalake municipal (BigQuery `datario`) | Totais diários e mensais, acumulados anteriores, extremos |
| Ocorrências urbanas | COR, via datalake municipal | Tipo, horário, local, duração e chegada dos órgãos |
| Limites de bairros | IPP, via datalake municipal | Associação espacial |
| Censo 2022 e IPS Bairros 2022 | Data.Rio | Densidade, IPS e indicadores de habitação |

Os arquivos brutos ficam em `dados/brutos/` e foram coletados com
`scripts/baixar_datario.py` e `scripts/baixar_data_rio.py`.

## Como executar

Ambiente usado: **Python 3.14.6**, com as versões fixadas em
[requirements.txt](requirements.txt). Na raiz do projeto:

```bash
python -m venv .venv
```

Ative o ambiente (`.\.venv\Scripts\Activate.ps1` no PowerShell ou
`source .venv/bin/activate` no Linux/macOS) e instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Execute o notebook do início ao fim:

```bash
python scripts/executar_notebook.py
```

O comando roda todas as células em um processo novo e salva o notebook com as
saídas. Leva alguns minutos. Também é possível abrir `analise.ipynb` no Jupyter ou no
VS Code e executar todas as células a partir da raiz.

O notebook não baixa dados. Os scripts de coleta exigem credenciais do Google Cloud e
dependências que não estão no `requirements.txt`.

## Organização do repositório

```text
analise.ipynb      Notebook principal, com as saídas incorporadas
requirements.txt   Dependências da análise
scripts/           Cálculos, figuras, execução do notebook e coleta de dados
dados/brutos/      Entradas usadas na análise
docs/              Enunciado da disciplina e proposta original
apresentacao/      Apresentação final (final.pdf) e a do marco 2
```

| Script | Função |
|---|---|
| `analise_dados.py` | Preparação da chuva e das ocorrências, painel bairro-dia e frequências |
| `analises_complementares.py` | Janelas anteriores, tempos registrados, perfil social e padronização |
| `historico_chuva.py` | Rede histórica fixa, ciclo horário e extremos |
| `estilo_graficos.py` | Identidade visual e títulos das figuras |
| `graficos_interativos.py` | Versões interativas (Plotly) de dois gráficos |
| `executar_notebook.py` | Execução completa do notebook |

A execução gera `dados/processados/` e `resultados/` (figuras PNG/SVG, tabelas CSV e
`sintese.md`). Essas pastas não vão para o Git.

## Gráficos interativos

Dois gráficos têm versão interativa logo abaixo da versão estática:

- **Seção 4:** frequência de registros por faixa de chuva, com detalhes no tooltip e
  opção de escala logarítmica.
- **Seção 6.1:** mapa de calor por bairro, com menu para reordenar os bairros.

Eles precisam de um visualizador que execute JavaScript (Jupyter ou VS Code, com o
notebook confiável) e de internet para carregar o Plotly. A pré-visualização do
GitHub não os exibe; nela valem os gráficos estáticos.

## Documentos da disciplina

- [Enunciado do projeto](docs/AED20262_projeto.pdf)
- [Proposta original](docs/Proposta%20Quando%20a%20chuva%20vira%20problema.pdf)
