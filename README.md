# Quando a chuva vira problema

**Chuva e ocorrências urbanas nos bairros do Rio de Janeiro**

Projeto da disciplina **Análise Exploratória de Dados e Visualização**, FGV EMAp, 2026.2.

**Autores:** Pedro Henrique Vasconcelos Neves e Gabriel Andrade Souza.

## Sobre o projeto

Como a frequência de ocorrências registradas varia com a chuva? Essa associação
é semelhante entre os bairros do Rio de Janeiro?

O projeto combina medições dos pluviômetros do Sistema Alerta Rio, registros do
Centro de Operações Rio (COR) e limites de bairros do Instituto Pereira Passos
(IPP). A análise explora a distribuição temporal e espacial da chuva, um temporal
específico e a frequência de registros de acúmulo de água e deslizamentos em dias
com diferentes volumes de chuva.

O [notebook principal](analise.ipynb) reúne perguntas, preparação dos dados,
visualizações, interpretações, conclusões e um apêndice de auditoria.

O percurso principal segue a narrativa do artigo: pergunta, transformação dos
dados, gráfico e interpretação. As tabelas extensas, os procedimentos completos,
a cobertura histórica detalhada e as figuras de apoio ficam no apêndice. A
conclusão integra os achados e apresenta recomendações compatíveis com os dados;
o quadro final explicita a contribuição para cada pergunta da proposta.

## Escopo da análise

| Eixo | Recorte | Objetivo |
|---|---|---|
| Evolução mensal e sazonalidade | Vidigal, Tijuca e Campo Grande, 2014–2021 | Comparar volumes de chuva e sua distribuição ao longo do ano |
| Ciclo horário e extremos | Rede fixa das mesmas três estações; anos definidos pela cobertura | Descrever horários da chuva e frequências anuais de dias ≥50, ≥80 e ≥100 mm |
| Estudo de caso | Temporal de 8 e 9 de abril de 2019 | Examinar a chuva anterior ao início dos registros e conferir a interpretação dos horários |
| Chuva e ocorrências | Pares bairro × dia, 2020–2021 | Calcular frequências por faixa de chuva, incluindo dias sem registros |
| Comparação territorial | Bairros com cobertura e amostras suficientes | Explorar diferenças sob faixas semelhantes de chuva |
| Janelas anteriores de chuva | 1 h, 4 h, 24 h e 96 h; blocos de seis horas em 2020–2021 | Comparar associações com registros posteriores, na mesma amostra |
| Duração e chegada registrada | Eventos em bairro-dias elegíveis, 2020–2021 | Descrever tempos por grupo e faixa de chuva, auditando datas e IDs |
| Perfil social e habitação | IPS, densidade e indicadores publicados na planilha do IPS; registros de 2020–2021 | Explorar associações com frequências padronizadas e verificar diferenças entre anos |

A proposta original previa 2015–2025 e perguntas mais amplas. O notebook documenta
o recorte efetivamente analisado e suas limitações. A extensão dos extremos até
1997, atualização e esclarecimento territorial dos indicadores de habitação e uma avaliação ajustada do atendimento
permanecem possibilidades de extensão. A primeira chegada registrada é medida
em relação ao início do registro, sem pressupor que corresponda ao chamado.

## Principais resultados

Na execução atual:

- **81 meses** são simultaneamente comparáveis nas três estações em 2014–2021.
- A análise diária reúne **121.423 bairro-dias elegíveis**, de 167 bairros e 731 datas.
- A frequência de bairro-dias com registro de acúmulo de água passa de **0,048%**
  na faixa de 0 mm para **12,833%** na faixa acima de 30 até 50 mm.
- Na faixa acima de 100 mm, a frequência é **30,928%**, com apenas 97 bairro-dias
  distribuídos em nove datas distintas. A amostra exige cautela na interpretação.
- **79 bairros** atendem aos critérios da comparação territorial exibida.
- Na rede histórica fixa, **dez anos** atendem aos critérios: 2011 e 2013–2021.
  As maiores médias horárias ocorrem às 19h em Campo Grande e às 20h no Vidigal e
  na Tijuca, considerando os intervalos iniciados nesses horários locais.

Nenhuma faixa da análise agregada alcança 50% de bairro-dias com registro de
acúmulo de água. Isso não exclui frequências maiores em bairros específicos.
Os valores são descritivos e dependem dos recortes e critérios documentados.
A execução gera uma síntese atualizada em `resultados/sintese.md`.

## Dados e metodologia

| Dados | Origem | Uso |
|---|---|---|
| Leituras de chuva | Sistema Alerta Rio, disponibilizadas no datalake municipal | Totais diários e mensais, cobertura e acumulados anteriores a eventos |
| Ocorrências urbanas | COR, disponibilizadas no datalake municipal | Tipo, início e localização dos registros |
| Limites de bairros | IPP, disponibilizados no datalake municipal | Associação espacial e definição das unidades territoriais |
| Censo e IPS 2022 | Data.Rio | IPS, densidade e indicadores de favelas e inadequação de domicílios; as referências dos indicadores diferem da edição do índice |

Os arquivos brutos são preservados em `dados/brutos/`. O processamento trata
qualidade das chaves, duplicatas, horários, falhas e cobertura antes de produzir
os totais usados nas comparações. Lacunas não recuperadas não são preenchidas
com zero.

Na análise diária, cada bairro recebe uma estação fixa, escolhida pela proximidade
a um ponto representativo interior ao seu polígono. O denominador inclui todos os
bairro-dias elegíveis, com ou sem registros. Os intervalos exploratórios de 95%
usam reamostragem de semanas, levando os bairros de cada semana conjuntamente.
O notebook também compara alternativas de cobertura, distância e convenção de
horário.

A comparação entre janelas usa somente medições disponíveis nas quatro janelas,
encerradas 15 minutos antes de blocos fixos de seis horas. Os blocos sem registros
também entram no denominador. As faixas positivas usam percentis próprios de cada
janela; diferenças entre curvas não demonstram superioridade preditiva.

Na análise de tempos, durações negativas ou sem fim são excluídas. A primeira
chegada exige ID único na base completa e horário entre início e fim do evento.
As exclusões e a disponibilidade de cada medida são apresentadas no notebook.

O ciclo horário e os extremos históricos usam dias inteiramente observados nas
três estações, com intervalos alinhados à grade de 15 minutos, sem recuperação de
falhas. A comparação principal exige 90% de dias comuns válidos no ano e 80% em
cada mês. O ciclo horário dá o mesmo peso a cada ano elegível. Os extremos são
avaliados como proporção de dias válidos, com limiares exploratórios de 50, 80 e
100 mm e sensibilidade da cobertura anual mínima a 85% e 95%.

Leituras fora da grade impedem certificar dias antigos sob os mesmos critérios;
os anos de 2023–2024 também têm cobertura insuficiente. As lacunas são explicitadas,
sem arredondar horários. O recorte resultante não permite concluir sobre tendência
climática de toda a cidade desde 1997. Os limiares não representam alertas oficiais.

### Comparabilidade territorial e indicadores de habitação

A seção 8 do notebook mantém a comparação inicial com IPS e densidade e acrescenta
uma análise com indicadores da [planilha original do IPS](dados/brutos/data_rio/IPSBairros-DataRio.xlsx).
A ficha registra 2019 para favelas não urbanizadas, com população do Censo 2010 e
urbanização do SABREN; sua definição menciona RA apesar da publicação por bairro.
Essa ambiguidade limita a interpretação territorial. O indicador de inadequação
tem referência 2021 e se restringe aos domicílios com renda per capita inferior a
meio salário mínimo e cadastro ativo
no CadÚnico; não representa todos os domicílios do bairro.

A análise usa frequências de acúmulo de água nas faixas (10,20], (20,30] e
(30,50] mm/dia, com peso de 1/3 para cada faixa. Essa padronização descreve uma
mistura hipotética comum de chuva. Dias de até 10 mm ou acima de 50 mm ficam fora
desse recorte; a medida difere da frequência anterior para todos os dias >30 mm.

O cenário principal exige cobertura de 90% em cada ano, estação a até 5 km e pelo
menos cinco dias por faixa em cada ano. Os mesmos bairros são comparados em 2020
e 2021; a sensibilidade restringe a distância a 3 km ou eleva a cobertura a 95%.
Os intervalos exploratórios usam 400 reamostragens conjuntas de semanas. Mudanças
de cenário alteram a seleção de bairros; não corrigem monitoramento, exposição
ou composição da chuva dentro das faixas. As correlações sociais são descritivas.

Definições, correspondências e ausências são auditadas no notebook. A execução
gera em `resultados/` as tabelas `definicoes_habitacao.csv`,
`auditoria_habitacao_bairros.csv`, `coortes_territoriais.csv`,
`taxas_padronizadas.csv`, `correlacoes_sociais.csv`, `estabilidade_bairros.csv` e
`suporte_faixas_chuva.csv`. Esta última documenta a viabilidade dos cortes de chuva
usando apenas a exposição, a cobertura e a distância, sem selecionar por ocorrências.

### Limites de interpretação

- Ausência de registro no COR não comprova ausência de problema urbano.
- Uma estação aproxima a chuva do bairro; diferentes bairros podem compartilhar
  a mesma estação e o mesmo temporal.
- O total diário pode incluir chuva posterior ao início de uma ocorrência.
  As frequências apresentadas não constituem previsões nem demonstram causalidade.
- O recorte de 2020–2021 inclui a pandemia e pode refletir condições particulares
  de circulação e monitoramento.
- As diferenças territoriais não identificam, por si só, vulnerabilidade social
  ou prioridades de obras.

Os critérios completos, as análises de sensibilidade e as referências estão no notebook.

## Como executar

### 1. Preparar o ambiente

O ambiente usado na verificação foi **Python 3.14.6**, com as versões fixadas em
[requirements.txt](requirements.txt). Na raiz do projeto:

```bash
python -m venv .venv
```

Ative o ambiente no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou no Linux/macOS:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

### 2. Conferir as entradas

A análise espera os arquivos em `dados/brutos/`, na estrutura existente no projeto.
O notebook não baixa dados durante a execução. Se os arquivos não estiverem
presentes na cópia local, consulte os scripts de coleta antes de executar.

- `scripts/baixar_datario.py`: coleta tabelas do datalake municipal via BigQuery;
  requer projeto Google Cloud, credenciais e dependências específicas de coleta.
- `scripts/baixar_data_rio.py`: coleta camadas e arquivos do Data.Rio.

O `requirements.txt` cobre a análise com as entradas já disponíveis; não é um
ambiente completo para os scripts independentes de coleta.

### 3. Executar o notebook

```bash
python scripts/executar_notebook.py
```

O comando executa todas as células em um processo novo, captura tabelas e figuras
e salva o notebook após a conclusão bem-sucedida. O processamento pode levar alguns
minutos. Em caso de falha, o script cria `tmp/execucao_falhou.ipynb` para inspeção;
esse arquivo temporário não faz parte da entrega.

Também é possível abrir `analise.ipynb` em um editor com suporte a Jupyter,
selecionar o ambiente instalado e executar todas as células a partir da raiz.
A opção `--kernel` do script usa um kernel Jupyter separado.

### 4. Verificar o processamento

```bash
python -m unittest discover -s tests -v
```

Os testes verificam tratamento de lacunas, limites temporais, denominadores,
precedência da exposição, fronteiras dos blocos e exclusões nos tempos de chegada.
Também verificam a agregação horária, exclusões por relógio e o denominador dos
extremos na amostra de dias comuns.
Na comparação territorial, verificam a invariância da taxa padronizada à mistura
de chuva, a preservação de faixas e indicadores ausentes e a exigência da mesma
coorte entre anos.

## Organização do repositório

```text
analise.ipynb          Narrativa e análise principal, com saídas incorporadas
requirements.txt      Versões das dependências da análise
scripts/              Processamento, estilo das figuras, execução e coleta
tests/                Testes das regras de processamento
dados/
  brutos/             Entradas preservadas
  processados/        Tabelas derivadas, regeneradas na execução
resultados/           Figuras PNG/SVG, tabelas CSV e síntese dos resultados
docs/                 Enunciado do professor e proposta original
apresentacao/         Materiais históricos do marco 2
```

O módulo `scripts/analise_dados.py` concentra os cálculos e as validações.
`scripts/analises_complementares.py` implementa as janelas anteriores de chuva,
os tempos registrados e a associação com o perfil social.
`scripts/historico_chuva.py` implementa a auditoria da rede fixa, o ciclo horário
e as frequências de extremos com cobertura comparável.
`scripts/estilo_graficos.py` concentra a apresentação das figuras com Matplotlib
e Seaborn.

`dados/processados/`, `resultados/` e `tmp/` são ignorados pelo Git e recriados
quando necessários. As saídas principais também estão incorporadas no notebook
executado. Arquivos temporários podem ser apagados entre execuções.

## Documentação e entrega da disciplina

- [Enunciado do professor](docs/AED20262_projeto.pdf).
- [Proposta original](docs/Proposta%20Quando%20a%20chuva%20vira%20problema.pdf).
- [Repositório no GitHub](https://github.com/PedroVNeves/Quando_a_chuva_vira_problema).

A entrega final exige notebook, repositório com código e documentação,
apresentação de dez minutos e declaração de contribuições. Os materiais em
`apresentacao/` pertencem ao marco 2 e ainda precisam ser atualizados para a
entrega final. A declaração de contribuições ainda deve ser adicionada.
Antes da entrega, o grupo deve conferir a incorporação dos comentários do
professor e a correspondência entre notebook, apresentação e versão publicada.

### Exploração interativa

Na seção 5 do notebook, um seletor de bairro apresenta as frequências e os
denominadores nas três faixas de chuva, usando a mesma amostra do gráfico estático.
O componente incorpora os dados e não depende de serviços externos. Requer um
visualizador que permita HTML com JavaScript; execute a célula em um notebook
confiável no Jupyter. Visualizadores que bloqueiam scripts e exportações estáticas
continuam contando com o gráfico completo imediatamente anterior.
