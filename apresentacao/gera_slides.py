"""Gera os slides do marco 2 em HTML a partir das saídas do notebook.

Uso: python gera_slides.py <notebook> <pasta_saida>
Escreve <pasta_saida>/marco2.html (todos os slides), slide_N.html (um por slide, para conferência) e img/.
"""
import base64
import html
import json
import sys
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

nb = json.load(open(sys.argv[1], encoding="utf-8"))
SAIDA = Path(sys.argv[2])
(SAIDA / "img").mkdir(parents=True, exist_ok=True)


def imagem(celula):
    for o in nb["cells"][celula]["outputs"]:
        png = o.get("data", {}).get("image/png")
        if png:
            nome = f"img/celula{celula}.png"
            (SAIDA / nome).write_bytes(base64.b64decode(png))
            return nome
    raise ValueError(f"célula {celula} sem imagem")


def saidas_html(celula):
    """Saídas da célula na ordem: tabelas em HTML e textos impressos."""
    partes = []
    for o in nb["cells"][celula]["outputs"]:
        d = o.get("data", {})
        if "text/html" in d:
            partes.append(f'<div class="out-html">{"".join(d["text/html"])}</div>')
        elif "text" in o:
            partes.append(f'<pre class="out-txt">{html.escape("".join(o["text"]).strip())}</pre>')
    return partes


def codigo(fonte):
    return highlight(fonte, PythonLexer(), HtmlFormatter(noclasses=True, style="friendly", nowrap=True))


def celula_nb(fonte, saidas, rotulo):
    return f"""
<div class="cell">
  <div class="cell-label">{rotulo}</div>
  <pre class="code">{codigo(fonte)}</pre>
  <div class="outputs">{''.join(saidas)}</div>
</div>"""


def fonte(celula):
    return "".join(nb["cells"][celula]["source"])


# ---------------------------------------------------------------- imagens dos gráficos
img_temporal = imagem(55)
img_cobertura = imagem(62)
img_vidigal = imagem(65)
img_mapa = imagem(72)

# ---------------------------------------------------------------- prints de células
print_head = celula_nb(fonte(26), saidas_html(26), "notebook · célula: leitura das ocorrências")

# Associação aos bairros: trecho central da célula e a primeira tabela de saída
trecho_sjoin = """cor_bairros_candidatos = gpd.sjoin(
    pontos_associacao_cor, bairros_associacao_cor, how="left", predicate="intersects",
)
quantidade_bairros_cor = cor_bairros_candidatos.groupby(level=0)["id_bairro_geo"].nunique()
...
resumo_associacao_cor = pd.crosstab(cor_com_bairro["Situação espacial"], cor_com_bairro["Grupo inicial"])
display(resumo_associacao_cor)"""
tabela_situacao, texto_top10, tabela_top10 = saidas_html(35)
# As duas tabelas lado a lado; o texto impresso fica sobre a tabela a que se refere
print_sjoin = celula_nb(
    trecho_sjoin,
    [tabela_situacao, f'<div class="stack">{texto_top10}{tabela_top10}</div>'],
    "notebook · trecho da célula: associação aos bairros",
)

# Validação externa do temporal: só a tabela-resumo das hipóteses de fuso
trecho_validacao = """for rotulo, fuso in [("Horário civil do Rio", "America/Sao_Paulo"),
                     ("UTC-3 fixo", "Etc/GMT+3"), ("UTC", "UTC")]:
    cenario = preparar_horarios_chuva(chuva_validacao_2019, fuso)
    ...
display(resumo_validacao_2019.round(2))"""
print_validacao = celula_nb(trecho_validacao, saidas_html(50)[:1], "notebook · trecho da célula: validação com a referência da UFF")

# ---------------------------------------------------------------- slides
slides = []

slides.append(f"""
<section class="slide dark title-slide">
  <div class="kicker">Marco 2 · Entrega intermediária</div>
  <h1 class="hero">Quando a chuva<br>vira problema</h1>
  <p class="hero-sub">Chuva e ocorrências urbanas nos bairros do Rio de Janeiro</p>
  <div class="hero-stats">
    <div><span class="num">33</span><span class="lbl">pluviômetros do Alerta Rio, leituras a cada 15 min desde 1997</span></div>
    <div><span class="num">91.406</span><span class="lbl">ocorrências do COR, de 2015 a abril de 2024</span></div>
    <div><span class="num">5</span><span class="lbl">bases públicas cruzadas por espaço e tempo</span></div>
  </div>
  <div class="hero-foot">
    Pedro Henrique Vasconcelos Neves e Gabriel Andrade Souza<br>
    Análise Exploratória de Dados e Visualização · FGV EMAp 2026.2 · github.com/PedroVNeves/Quando_a_chuva_vira_problema
  </div>
</section>""")

slides.append("""
<section class="slide">
  <h2>Quanta chuva, e em que lugar, vira problema?</h2>
  <div class="two-col body-center">
    <div class="col-text">
      <p class="lead">E por que a mesma chuva parece causar estragos diferentes em bairros diferentes?</p>
      <p>Combinamos medições dos pluviômetros, registros do Centro de Operações Rio (COR), limites de bairros e indicadores sociais.</p>
      <p class="muted">Neste marco: definição e preparação dos dados, cobertura das medições e primeiros resultados descritivos. Ainda não estimamos limiar nem vulnerabilidade.</p>
    </div>
    <div class="cards">
      <div class="card">
        <div class="tag">H1</div>
        <div><b>A chuva varia entre os meses do ano</b>
        <div class="status">Explorada no Vidigal, 2014–2021</div></div>
      </div>
      <div class="card">
        <div class="tag">H2</div>
        <div><b>Dias com mais chuva têm mais registros de acúmulo de água</b>
        <div class="status">Primeiro cruzamento: temporal de abril de 2019</div></div>
      </div>
      <div class="card">
        <div class="tag">H3</div>
        <div><b>A relação entre chuva e ocorrências varia entre bairros</b>
        <div class="status">Associação das ocorrências aos bairros feita</div></div>
      </div>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Cinco bases públicas, ligadas por espaço e tempo</h2>
  <div class="sources">
    <div class="src"><b>Chuva</b><span>Sistema Alerta Rio</span><em>datalake · BigQuery</em></div>
    <div class="src"><b>Ocorrências</b><span>Centro de Operações Rio</span><em>datalake · BigQuery</em></div>
    <div class="src"><b>Bairros</b><span>Limites do IPP</span><em>datalake · BigQuery</em></div>
    <div class="src"><b>Censo 2022</b><span>IBGE, agregado pelo IPP</span><em>Data.Rio</em></div>
    <div class="src"><b>IPS 2022</b><span>Índice de Progresso Social</span><em>Data.Rio</em></div>
  </div>
  <p class="caption-top">Cada ocorrência traz tipo, horário e coordenada: é o que permite ligá-la à estação mais próxima, à chuva das horas anteriores e ao bairro.</p>
  <div class="print-wide">{print_head}</div>
</section>""")

slides.append("""
<section class="slide">
  <h2>Por que Parquet e GeoParquet, e não JSON ou GeoJSON</h2>
  <div class="two-col">
    <div class="col-text formats">
      <p class="muted">Parquet guarda os dados por coluna, comprimidos e com o tipo de cada coluna. GeoParquet é o mesmo formato com a geometria em binário e o sistema de coordenadas junto.</p>
      <div class="bars">
        <div class="bars-title">Chuva de 15 min: 29,3 milhões de leituras</div>
        <div class="bar-row"><span class="bar-lbl">Parquet</span><span class="bar main" style="width:24px"></span><span class="bar-val">596 MB</span></div>
        <div class="bar-row"><span class="bar-lbl">JSON*</span><span class="bar other" style="width:300px"></span><span class="bar-val">~7,5 GB</span></div>
      </div>
      <div class="bars">
        <div class="bars-title">Lotes: 1 milhão de polígonos</div>
        <div class="bar-row"><span class="bar-lbl">GeoParquet</span><span class="bar main" style="width:21px"></span><span class="bar-val">5 s para abrir</span></div>
        <div class="bar-row"><span class="bar-lbl">GeoJSON*</span><span class="bar other" style="width:300px"></span><span class="bar-val">~75 s</span></div>
      </div>
      <p class="footnote">* Estimado a partir de amostras de 200 mil leituras e 100 mil lotes salvas nos dois formatos.</p>
    </div>
    <div class="uses">
      <div class="use"><b>Ler só um dia, sem abrir a série inteira</b>
        <code>pd.read_parquet(arquivo, filters=[("data_particao", "==", date(2019, 4, 8))])</code>
        <span>3.168 leituras do temporal em ~5 s, em vez de carregar 29 milhões de linhas</span></div>
      <div class="use"><b>Ler só as colunas necessárias</b>
        <code>pd.read_parquet(arquivo, columns=["data_inicio", "latitude", "longitude"])</code>
        <span>Usado na conferência de cobertura e de coordenadas das ocorrências</span></div>
      <div class="use"><b>Datas chegam como datas, com fuso</b>
        <code>ocorrencias["data_inicio"].dt.tz_convert("America/Sao_Paulo")</code>
        <span>Em JSON viriam como texto; aqui já chegam como instante em UTC</span></div>
      <div class="use"><b>Mapas prontos para cruzar</b>
        <code>gpd.sjoin(pontos, gpd.read_parquet("bairro.parquet"))</code>
        <span>A geometria já vem com o sistema de coordenadas: cruzamos ocorrências com bairros e passamos para metros com <code class="inline">to_crs</code> para medir distâncias</span></div>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Onde a chuva é medida</h2>
  <div class="fig-side">
    <img class="fig" src="{img_mapa}" alt="Mapa dos 33 pluviômetros do Alerta Rio sobre os limites de bairros">
    <div class="side">
      <div class="stat"><span class="num">33</span><span class="lbl">pluviômetros com coordenadas</span></div>
      <div class="stat"><span class="num">1,8 km</span><span class="lbl">distância mediana entre ocorrência e estação mais próxima</span></div>
      <div class="stat"><span class="num">3,6 km</span><span class="lbl">90% das ocorrências estão a até essa distância</span></div>
      <p class="muted">A rede é mais densa no leste e mais espaçada no oeste: a mesma regra de “estação mais próxima” envolve distâncias diferentes.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Antes de comparar volumes, medir a cobertura</h2>
  <div class="fig-side tall">
    <img class="fig" src="{img_cobertura}" alt="Mapa de calor do percentual de dias com medição por estação e ano">
    <div class="side">
      <div class="stat"><span class="num">1</span><span class="lbl">leitura com data em 2099, fora das análises</span></div>
      <div class="stat"><span class="num">99</span><span class="lbl">cópias idênticas removidas na leitura</span></div>
      <div class="stat"><span class="num">7.178</span><span class="lbl">leituras sem horário, fora dos cruzamentos por hora</span></div>
      <p class="muted">Estações entram na rede em anos diferentes, e em 2023 só 80–90% dos dias têm medição. Presença diária não garante todos os horários.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>No Vidigal, de novembro a abril chove quase o dobro</h2>
  <div class="fig-side">
    <img class="fig" src="{img_vidigal}" alt="Chuva mensal média no Vidigal, 2014 a 2021">
    <div class="side">
      <div class="stat"><span class="num">167 mm</span><span class="lbl">média de fevereiro, a maior; setembro é a menor, com 67 mm. Nov–abr: 134 mm/mês; mai–out: 75</span></div>
      <div class="stat"><span class="num">96 de 96</span><span class="lbl">meses aceitos depois de tratar as falhas de leitura</span></div>
      <p class="muted">As falhas foram preenchidas pelo acumulado de 1 h da leitura seguinte, que já inclui os 15 min ausentes, e nenhuma tinha chuva. Quatro eram horários que não existiram no início do horário de verão.</p>
      <p class="muted">Exigir 100% das leituras deixava só 79 meses e distorcia o resultado.</p>
    </div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Das 91.406 ocorrências às 4.705 localizadas em um bairro</h2>
  <div class="two-col wide-right">
    <div class="col-text funnel">
      <div class="step-f"><span class="bar-f" style="width:100%"></span><span class="num">91.406</span><span class="lbl">ocorrências do COR, todos os tipos (2015 a abril de 2024)</span></div>
      <div class="step-f"><span class="bar-f" style="width:5.5%"></span><span class="num">5.058</span><span class="lbl">tipos ligados à chuva (5,5%): 4.882 de acúmulo de água e 176 de deslizamentos</span></div>
      <div class="step-f"><span class="bar-f" style="width:5.1%"></span><span class="num">4.705</span><span class="lbl">com o ponto dentro de um único bairro (93% das 5.058)</span></div>
      <p class="muted">O bairro sai da coordenada porque o campo de bairro do COR vem vazio em ~40% dos registros. Os 349 pontos fora dos polígonos ficam marcados, sem serem empurrados para o bairro mais próximo.</p>
    </div>
    <div class="print-side">{print_sjoin}</div>
  </div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Por que o temporal de 8 e 9 de abril de 2019</h2>
  <div class="reasons">
    <div class="reason"><span class="n">1</span><div><b>É o dia mais chuvoso do período com ocorrências</b>
      <p>Em 9/04, quatro estações passaram de 330 mm em 24 h e metade da rede passou de 170 mm. Entre 2015 e abril de 2024, só três dias têm máximo maior, e todos são erros de uma estação isolada (como 2.023 mm na Penha com as vizinhas perto de zero).</p></div></div>
    <div class="reason"><span class="n">2</span><div><b>São dois dias porque o evento atravessou a meia-noite</b>
      <p>A chuva começou no fim da tarde do dia 8, e os acumulados de 24 h chegaram ao pico no dia 9, quando as ocorrências continuaram.</p></div></div>
    <div class="reason"><span class="n">3</span><div><b>Tem uma referência externa publicada</b>
      <p>Um trabalho da UFF (2020) reproduz os valores do Alerta Rio para 14 estações nesse temporal. Comparar com o nosso arquivo testa em que fuso a chuva está registrada.</p></div></div>
  </div>
  <div class="print-small">{print_validacao}</div>
</section>""")

slides.append(f"""
<section class="slide">
  <h2>Primeiro cruzamento: chuva antes de cada ocorrência</h2>
  <div class="fig-side">
    <img class="fig" src="{img_temporal}" alt="Chuva acumulada em 24 h antes de cada ocorrência, 8 e 9 de abril de 2019">
    <div class="side">
      <div class="stat"><span class="num">85</span><span class="lbl">ocorrências ligadas a uma leitura de até 15 min antes, na estação mais próxima</span></div>
      <div class="stat"><span class="num">28 de 28</span><span class="lbl">valores da UFF batem com o arquivo no horário local; em UTC, nenhum</span></div>
      <p class="muted">Os registros aparecem conforme o acumulado sobe. Mesmo assim, 8 e 9/04 não estão entre os dias com mais ocorrências da base (30º e 59º): o número de registros não depende só da chuva.</p>
    </div>
  </div>
</section>""")

slides.append("""
<section class="slide dark">
  <h2>O que ainda falta</h2>
  <div class="steps">
    <div class="step"><span class="n">1</span><div><b>Horários</b><p>Confirmar a convenção de horário da série inteira de chuva, inclusive o horário de verão.</p></div></div>
    <div class="step"><span class="n">2</span><div><b>Dias com e sem ocorrência</b><p>Comparar faixas de chuva incluindo os dias sem registros, sob cobertura adequada.</p></div></div>
    <div class="step"><span class="n">3</span><div><b>Janelas e limiar</b><p>Testar 15 min, 1 h, 24 h e 96 h, e o limiar de 30 mm/dia citado pela prefeitura.</p></div></div>
    <div class="step"><span class="n">4</span><div><b>Bairros e perfil</b><p>Comparar bairros em condições semelhantes de chuva e integrar Censo e IPS.</p></div></div>
  </div>
  <p class="closing">Temos bases definidas, critérios documentados e primeiros achados descritivos. Ocorrência registrada não é alagamento real, e áreas mais monitoradas registram mais.</p>
</section>""")

CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #1F2D3A; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.slide { width: 1280px; height: 720px; padding: 52px 64px; position: relative; overflow: hidden; background: #FFFFFF; page-break-after: always; break-after: page; }
.slide:last-child { page-break-after: auto; break-after: auto; }
h1, h2 { font-family: Cambria, Georgia, serif; margin: 0; color: #0B2E4F; }
h2 { font-size: 38px; line-height: 1.15; margin-bottom: 28px; }
p { font-size: 18px; line-height: 1.45; margin: 0 0 14px; }
.muted { color: #52616E; font-size: 16px; }
.lead { font-size: 22px; color: #0B2E4F; }

.dark { background: #0B2E4F; color: #E8F1F5; }
.dark h1, .dark h2 { color: #FFFFFF; }
.title-slide { padding: 64px 72px; }
.kicker { font-size: 16px; letter-spacing: 2px; text-transform: uppercase; color: #6FC7CC; margin-bottom: 18px; }
.hero { font-size: 72px; line-height: 1.02; }
.hero-sub { font-size: 24px; color: #CFE3EA; margin-top: 18px; }
.hero-stats { display: flex; gap: 28px; margin-top: 44px; }
.hero-stats > div { flex: 1; background: rgba(255,255,255,0.07); border-radius: 14px; padding: 18px 22px; }
.hero-stats .num { display: block; font-family: Cambria, Georgia, serif; font-size: 44px; color: #FFFFFF; font-weight: bold; }
.hero-stats .lbl { display: block; font-size: 15px; color: #CFE3EA; margin-top: 4px; line-height: 1.35; }
.hero-foot { position: absolute; left: 72px; bottom: 44px; font-size: 14px; color: #A9C3CE; line-height: 1.6; }

.two-col { display: flex; gap: 44px; align-items: flex-start; }
.body-center { height: 540px; align-items: center; }
.two-col .col-text { flex: 1; }
.two-col .cards { flex: 1.15; display: flex; flex-direction: column; gap: 16px; }
.two-col.wide-right .col-text { flex: 0 0 270px; padding-top: 10px; }
.two-col.wide-right .print-side { flex: 1; min-width: 0; }
.two-col.wide-left .fig { flex: 0 0 660px; width: 660px; }
.two-col.wide-left .col-text { padding-top: 40px; }
.two-col.wide-left .col-text { flex: 1; min-width: 0; }
.card { display: flex; gap: 18px; align-items: flex-start; background: #EEF6F6; border-radius: 14px; padding: 18px 20px; font-size: 18px; line-height: 1.35; }
.tag { flex: 0 0 52px; height: 52px; border-radius: 50%; background: #007F86; color: #FFFFFF; font-weight: bold; font-size: 18px; display: flex; align-items: center; justify-content: center; }
.status { margin-top: 6px; font-size: 15px; color: #8A4B26; }

.sources { display: flex; gap: 14px; margin-bottom: 20px; }
.src { flex: 1; background: #EEF6F6; border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.src b { font-size: 18px; color: #0B2E4F; }
.src span { font-size: 15px; }
.src em { font-style: normal; font-size: 13px; color: #007F86; font-weight: 600; }
.caption-top { font-size: 17px; margin-bottom: 14px; }

.fig-side { display: flex; gap: 40px; align-items: center; height: 560px; }
.fig-side .fig { flex: 0 0 auto; max-width: 780px; max-height: 560px; }
.fig-side.tall .fig { max-height: 580px; }
.fig-side .side { flex: 1; min-width: 0; }
.fig { display: block; }
.stat { margin-bottom: 20px; }
.stat .num { display: block; font-family: Cambria, Georgia, serif; font-size: 40px; font-weight: bold; color: #007F86; line-height: 1.1; }
.stat .lbl { display: block; font-size: 16px; color: #1F2D3A; line-height: 1.35; }

.cell { border: 1px solid #D5DEE4; border-radius: 10px; overflow: hidden; background: #FFFFFF; }
.cell-label { font-size: 12px; color: #52616E; background: #F2F5F7; padding: 6px 12px; border-bottom: 1px solid #D5DEE4; letter-spacing: 0.5px; }
.code { margin: 0; padding: 10px 14px; background: #F7F9FA; font-family: Consolas, "Courier New", monospace; font-size: 12.5px; line-height: 1.45; white-space: pre; border-bottom: 1px solid #E3E9ED; }
.outputs { padding: 8px 12px; }
.out-txt { margin: 0 0 6px; font-family: Consolas, "Courier New", monospace; font-size: 12.5px; }
.out-html table { border-collapse: collapse; border: none; font-family: "Segoe UI", Arial, sans-serif; }
.out-html th, .out-html td { padding: 3px 7px; text-align: right; border: none; border-bottom: 1px solid #EEF1F3; white-space: nowrap; }
.out-html thead th { border-bottom: 1px solid #9AA8B2; }
.out-html tbody tr:nth-child(odd) { background: #F7F9FA; }
.out-html style { display: none; }
.print-wide .out-html table { font-size: 10.5px; }
.print-wide .code { font-size: 14px; }
.print-wide .out-html th, .print-wide .out-html td { padding: 5px 7px; }
.print-side .code { font-size: 11.5px; }
.print-side .outputs { display: flex; gap: 22px; align-items: flex-start; }
.print-side .out-txt { margin: 0 0 4px; white-space: normal; font-size: 11.5px; }
.print-side .out-html table { font-size: 12px; }
.print-side .out-html th, .print-side .out-html td { padding: 3px 9px; }
.print-small .code { font-size: 10.5px; padding: 8px 10px; }
.print-small .out-html table { font-size: 11px; }
.print-small { margin-top: 14px; }
.print-small .outputs { padding: 6px 10px; }

.steps { display: grid; grid-template-columns: 1fr 1fr; gap: 24px 36px; margin-top: 16px; }
.step { display: flex; gap: 20px; align-items: flex-start; background: rgba(255,255,255,0.07); border-radius: 14px; padding: 30px 28px; }
.step .n { flex: 0 0 44px; height: 44px; border-radius: 50%; background: #007F86; color: #FFFFFF; font-weight: bold; font-size: 20px; display: flex; align-items: center; justify-content: center; }
.step b { font-size: 24px; color: #FFFFFF; }
.step p { font-size: 18px; color: #CFE3EA; margin: 8px 0 0; }
.formats .muted { margin-bottom: 22px; }
.bars { margin-bottom: 22px; }
.bars-title { font-size: 16px; font-weight: 600; color: #0B2E4F; margin-bottom: 8px; }
.bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.bar-lbl { flex: 0 0 96px; font-size: 15px; }
.bar { height: 22px; border-radius: 4px; display: inline-block; }
.bar.main { background: #007F86; }
.bar.other { background: #C9A58C; }
.bar-val { font-size: 15px; font-weight: 600; white-space: nowrap; }
.footnote { font-size: 12px; color: #52616E; }
.uses { flex: 1.35; display: flex; flex-direction: column; gap: 12px; }
.use { background: #EEF6F6; border-radius: 12px; padding: 12px 16px; display: flex; flex-direction: column; gap: 5px; }
.use b { font-size: 16px; color: #0B2E4F; }
.use code { font-family: Consolas, "Courier New", monospace; font-size: 12.5px; background: #FFFFFF; border-radius: 6px; padding: 5px 8px; color: #1F2D3A; }
.use code.inline, .use span code { padding: 0 4px; font-size: 13px; }
.use span { font-size: 14px; color: #52616E; line-height: 1.35; }
.funnel .step-f { position: relative; margin-bottom: 18px; }
.funnel .bar-f { display: block; height: 10px; border-radius: 5px; background: #007F86; margin-bottom: 6px; min-width: 6px; }
.funnel .num { display: block; font-family: Cambria, Georgia, serif; font-size: 34px; font-weight: bold; color: #007F86; line-height: 1.1; }
.funnel .lbl { display: block; font-size: 15px; line-height: 1.35; }
.funnel .muted { font-size: 14px; margin-top: 4px; }
.reasons { display: flex; gap: 20px; margin-bottom: 16px; }
.reason { flex: 1; display: flex; gap: 14px; align-items: flex-start; background: #EEF6F6; border-radius: 14px; padding: 16px 18px; }
.reason .n { flex: 0 0 36px; height: 36px; border-radius: 50%; background: #007F86; color: #FFFFFF; font-weight: bold; font-size: 17px; display: flex; align-items: center; justify-content: center; }
.reason b { font-size: 17px; color: #0B2E4F; line-height: 1.3; display: block; }
.reason p { font-size: 14.5px; line-height: 1.4; margin: 6px 0 0; }
.closing { position: absolute; left: 64px; right: 64px; bottom: 52px; font-size: 18px; color: #E8F1F5; }
"""


def documento(corpo, titulo):
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{titulo}</title>
<style>{CSS}</style></head><body>{corpo}</body></html>"""


titulo = "Quando a chuva vira problema · Marco 2"
(SAIDA / "marco2.html").write_text(documento("".join(slides), titulo), encoding="utf-8")
for i, s in enumerate(slides, 1):
    (SAIDA / f"slide_{i}.html").write_text(documento(s, titulo), encoding="utf-8")
print(len(slides), "slides")
