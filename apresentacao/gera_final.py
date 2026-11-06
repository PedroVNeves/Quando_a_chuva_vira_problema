"""Gera os slides da entrega final em HTML a partir das figuras do notebook.

Uso (na raiz do projeto, depois de executar o notebook):
    python apresentacao/gera_final.py

Lê as figuras de resultados/ e escreve apresentacao/final.html, com as figuras
embutidas. Os números citados vêm da execução atual do notebook.
"""
import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "apresentacao"


def recortar(imagem):
    """Tira o cabeçalho e o rodapé da figura: no slide, o título do slide os substitui."""
    cinza = np.asarray(imagem.convert("L")).astype(int)
    altura, largura = cinza.shape
    com_tinta = np.where((cinza < 235).sum(axis=1) > 0)[0]
    # Cabeçalho: termina no primeiro espaço vazio com mais de 50 px depois do subtítulo.
    saltos = np.diff(com_tinta)
    i = np.argmax(saltos > 50)
    topo = com_tinta[i + 1] - 12 if saltos[i] > 50 else 0
    # Rodapé: começa na régua cinza que atravessa a figura, a mais baixa delas.
    reguas = [r for r in range(altura // 2, altura)
              if ((cinza[r] < 245) & (cinza[r] > 200)).sum() > .8 * largura]
    base = max(reguas) - 6 if reguas else altura
    corte = cinza[topo:base]
    colunas = np.where((corte < 235).sum(axis=0) > 0)[0]
    return imagem.crop((max(colunas[0] - 12, 0), topo, min(colunas[-1] + 12, largura), base))


def figura(nome):
    """Embute a figura do notebook, recortada, no HTML, para o arquivo funcionar sozinho."""
    buffer = io.BytesIO()
    recortar(Image.open(RAIZ / "resultados" / f"{nome}.png")).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def stat(numero, rotulo):
    return f'<div class="stat"><span class="num">{numero}</span><span class="lbl">{rotulo}</span></div>'


def slide_figura(titulo, nome, alt, lateral, classe=""):
    return f"""
<section class="slide">
  <h2>{titulo}</h2>
  <div class="fig-side {classe}">
    <img class="fig" src="{figura(nome)}" alt="{alt}">
    <div class="side">{lateral}</div>
  </div>
  <div class="fonte">Fontes: Alerta Rio, COR, IPP e Data.Rio · figura e critérios no notebook</div>
</section>"""


slides = []

slides.append("""
<section class="slide dark title-slide">
  <div class="kicker">Entrega final · Análise Exploratória de Dados e Visualização</div>
  <h1 class="hero">Quando a chuva<br>vira problema</h1>
  <p class="hero-sub">Chuva e ocorrências urbanas nos bairros do Rio de Janeiro</p>
  <div class="hero-stats">
    <div><span class="num">32</span><span class="lbl">pluviômetros do Alerta Rio ligados a 167 bairros</span></div>
    <div><span class="num">121.423</span><span class="lbl">bairro-dias comparados em 2020–2021, com e sem registros</span></div>
    <div><span class="num">5</span><span class="lbl">bases públicas cruzadas por espaço e tempo</span></div>
  </div>
  <div class="hero-foot">
    Pedro Henrique Vasconcelos Neves e Gabriel Andrade Souza · FGV EMAp 2026.2<br>
    github.com/PedroVNeves/Quando_a_chuva_vira_problema
  </div>
</section>""")

slides.append("""
<section class="slide">
  <h2>O ponto de partida: uma afirmação da prefeitura</h2>
  <div class="two-col body-center">
    <div class="col-text">
      <blockquote>Um dia com mais de <b>30 mm</b> num pluviômetro já tem mais de <b>50% de chance</b> de alagamento.</blockquote>
      <p class="lead">Isso vale para qualquer bairro? E por que a mesma chuva parece causar problemas diferentes em lugares diferentes?</p>
      <p class="muted">Medimos <b>registros</b> do Centro de Operações Rio (COR): nem todo alagamento vira registro, e as relações são associações, não causas.</p>
    </div>
    <div class="cards">
      <div class="card"><div class="tag">1</div><div><b>Onde e quando chove?</b></div></div>
      <div class="card"><div class="tag">2–3</div><div><b>Mais chuva, mais registros? Existe o limiar de 50%?</b></div></div>
      <div class="card"><div class="tag">4</div><div><b>Pesa mais a pancada ou o acumulado?</b></div></div>
      <div class="card"><div class="tag">5–6</div><div><b>Os bairros diferem? O perfil social explica?</b></div></div>
      <div class="card"><div class="tag">7</div><div><b>Quanto duram os registros e quando os órgãos chegam?</b></div></div>
    </div>
  </div>
</section>""")

slides.append(slide_figura(
    "Cada bairro recebe a chuva de uma estação",
    "01_rede_estacoes", "Mapa dos bairros ligados à estação mais próxima, coloridos pela distância",
    stat("4 bairros", "por estação, em mediana; no máximo 15")
    + stat("2,0 km", "distância mediana entre o bairro e a sua estação")
    + '<p class="muted">Bases: chuva a cada 15 min (Alerta Rio), ocorrências (COR), limites de bairros (IPP), Censo e IPS 2022 (Data.Rio).</p>'
    + '<p class="muted">A estação é escolhida sem olhar ocorrências. Na Zona Oeste ela fica mais longe: a chuva medida é uma aproximação.</p>'))

slides.append("""
<section class="slide">
  <h2>A ideia central: contar também os dias sem problema</h2>
  <div class="flow">
    <div class="box"><span class="num">122.077</span><span class="lbl">pares bairro × dia em 2020–2021 (167 bairros × 731 dias)</span></div>
    <div class="arrow">→</div>
    <div class="box"><span class="num">121.423</span><span class="lbl">elegíveis: a estação do bairro tem o total do dia completo</span></div>
    <div class="arrow">→</div>
    <div class="box accent"><span class="num">1.162</span><span class="lbl">com pelo menos um registro de acúmulo de água (1.724 registros)</span></div>
  </div>
  <div class="formula">frequência = bairro-dias <b>com registro</b> ÷ bairro-dias <b>elegíveis</b>, por faixa de chuva</div>
  <p class="muted center">Olhar só os dias com ocorrência mostra quanto choveu quando houve problema, mas não a chance de haver problema quando chove.<br>
  Falhas dos pluviômetros não viram zero: o dia sai da comparação.</p>
</section>""")

slides.append(slide_figura(
    "A chuva se concentra no início da noite",
    "15_ciclo_horario", "Chuva média por hora nas estações Vidigal, Tijuca e Campo Grande",
    stat("19h–20h", "pico médio de chuva nas três estações com série histórica comparável")
    + stat("10 anos", "atendem aos critérios de cobertura, entre 1997 e 2024")
    + '<p class="muted">Com dez anos e lacunas, não dá para afirmar que os dias de chuva extrema ficaram mais frequentes.</p>',
    "wide"))

slides.append(slide_figura(
    "Mais chuva, mais registros, mas longe de 50% por bairro",
    "07_frequencia_chuva", "Frequência de bairro-dias com registro por faixa de chuva diária",
    stat("0,05%", "dos bairro-dias sem chuva têm registro de acúmulo de água")
    + stat("12,8%", "entre 30 e 50 mm")
    + stat("30,9%", "acima de 100 mm, com só 9 datas")
    + '<p class="muted">Ponto: frequência; traço: intervalo de 95%. Mudar as escolhas de método altera as frequências em no máximo 2,5 pontos percentuais.</p>'))

slides.append("""
<section class="slide">
  <h2>A afirmação da prefeitura depende de onde se olha</h2>
  <div class="fig-side">
    <img class="fig" src="%s" alt="Frequência de registros por faixa de chuva em três unidades: bairro, estação e cidade">
    <div class="side">
      <div class="unit"><span class="num">16%%</span><span class="lbl"><b>bairro-dia</b>: registro no próprio bairro</span></div>
      <div class="unit hl"><span class="num">44%%</span><span class="lbl"><b>estação-dia</b>: registro em algum bairro da estação</span></div>
      <div class="unit"><span class="num">94%%</span><span class="lbl"><b>cidade-dia</b>: registro em qualquer bairro</span></div>
      <p class="muted">Dias acima de 30 mm, faixa cinza do gráfico. Na unidade da prefeitura, a estação, o patamar de 50%% é plausível. Para um bairro isolado, não: um alerta por bairro baseado nos 30 mm superestimaria o risco.</p>
    </div>
  </div>
  <div class="fonte">Fontes: Alerta Rio, COR, IPP e Data.Rio · figura e critérios no notebook</div>
</section>""" % figura("20_unidade_prefeitura"))

slides.append(slide_figura(
    "Pancada ou acumulado: todas as janelas contam",
    "13_janelas_chuva", "Frequência de registros por classe de chuva anterior em quatro janelas",
    '<p class="lead-s">Medimos a chuva das <b>1 h, 4 h, 24 h e 96 h anteriores</b> a blocos de seis horas, para que a chuva venha antes do registro.</p>'
    + stat("485.753", "bairro-blocos na mesma amostra para as quatro janelas")
    + '<p class="muted">Em todas, mais chuva anterior vem com mais registros. As janelas usam cortes relativos (P50, P90), então a comparação não aponta uma vencedora.</p>'))

slides.append(slide_figura(
    "Poucos bairros concentram os registros",
    "19_mapa_registros", "Mapas por bairro: total de registros e frequência sob chuva forte",
    stat("41%", "dos 1.724 registros estão em dez bairros; a Barra da Tijuca sozinha tem 202")
    + '<p class="muted">Sob chuva forte (direita), as frequências mais altas ficam na Zona Sul e no entorno do Centro: Lagoa, Catete, Manguinhos.</p>'
    + '<p class="muted">Muitos registros não é o mesmo que muitos registros por chuva: a Barra teve só 16 dias acima de 30 mm.</p>',
    "wide"))

slides.append(slide_figura(
    "As diferenças entre bairros se repetem de um ano para o outro",
    "17_coerencia_anual", "Frequência padronizada de cada bairro em 2020 contra 2021",
    stat("ρ = 0,65", "correlação de postos entre 2020 e 2021, nos mesmos 100 bairros")
    + stat("67 de 100", "bairros mudam até 5 pontos percentuais")
    + '<p class="muted">Um ponto por bairro; faixa cinza: diferença de até 5 pontos. A frequência é padronizada: cada bairro é comparado como se tivesse recebido a mesma mistura de chuva (10–50 mm). As diferenças não parecem acaso, mas a amostra não sustenta um ranking.</p>',
    "square"))

slides.append(slide_figura(
    "O perfil social não explica as diferenças",
    "18_associacoes_padronizadas", "Correlação entre indicadores sociais e a frequência padronizada",
    stat("ρ = 0,27", "IPS: bairros com IPS maior têm mais registros, ao contrário da hipótese inicial")
    + '<p class="muted">Ponto cheio: 2020–2021; marcadores vazios: cada ano. Densidade, favelas e domicílios inadequados ficam na faixa de relação fraca.</p>'
    + '<p class="muted">Registros dependem de alguém notificar: o resultado do IPS pode refletir mais monitoramento, não menos vulnerabilidade.</p>'))

slides.append(slide_figura(
    "Um acúmulo de água dura cerca de duas horas, com qualquer chuva",
    "12_duracao_chegada", "Duração dos registros e primeira chegada dos órgãos por faixa de chuva",
    stat("2,1–2,2 h", "duração mediana do acúmulo de água em todas as faixas de chuva")
    + stat("0,8–2,8 h", "primeira chegada mediana entre áreas de planejamento, em dias acima de 30 mm")
    + '<p class="muted">A chegada é contada desde o início do registro, não do chamado: descreve os registros, não mede a eficiência dos órgãos.</p>'))

slides.append("""
<section class="slide dark">
  <h2>O que aprendemos</h2>
  <div class="steps">
    <div class="step"><span class="n">1</span><div><b>O limiar depende da escala</b><p>30 mm leva a 44% de registro na área de uma estação, mas a 16% em um bairro.</p></div></div>
    <div class="step"><span class="n">2</span><div><b>O lugar importa</b><p>Sob a mesma chuva, os bairros diferem, e as diferenças se repetem entre anos.</p></div></div>
    <div class="step"><span class="n">3</span><div><b>O perfil social não explica</b><p>IPS, densidade e habitação não têm relação uniforme com mais registros.</p></div></div>
    <div class="step"><span class="n">4</span><div><b>Recomendação</b><p>Acompanhar registros com seus denominadores e dias sem ocorrência; separar início, chamado, chegada e fim do atendimento.</p></div></div>
  </div>
  <p class="closing">Limites: registros não são todos os alagamentos; uma estação representa vários bairros; 2020–2021 inclui a pandemia.</p>
</section>""")

CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #1F2D3A; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.slide { width: 1280px; height: 720px; padding: 44px 56px; position: relative; overflow: hidden; background: #FFFFFF; page-break-after: always; break-after: page; }
.slide:last-child { page-break-after: auto; break-after: auto; }
h1, h2 { font-family: Cambria, Georgia, serif; margin: 0; color: #0B2E4F; }
h2 { font-size: 34px; line-height: 1.15; margin-bottom: 22px; }
p { font-size: 18px; line-height: 1.45; margin: 0 0 14px; }
.muted { color: #52616E; font-size: 15.5px; }
.center { text-align: center; }
.lead { font-size: 21px; color: #0B2E4F; }
.lead-s { font-size: 16.5px; color: #0B2E4F; }
blockquote { margin: 0 0 24px; padding: 18px 22px; border-left: 6px solid #B86632; background: #FBF3EE; font-family: Cambria, Georgia, serif; font-size: 26px; line-height: 1.35; color: #0B2E4F; }

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
.two-col .col-text { flex: 1.1; }
.two-col .cards { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.card { display: flex; gap: 16px; align-items: center; background: #EEF6F6; border-radius: 12px; padding: 12px 16px; font-size: 17px; line-height: 1.3; }
.tag { flex: 0 0 50px; height: 40px; border-radius: 20px; background: #007F86; color: #FFFFFF; font-weight: bold; font-size: 15px; display: flex; align-items: center; justify-content: center; }

.fig-side { display: flex; gap: 32px; align-items: center; height: 560px; }
.fig-side .fig { flex: 0 0 auto; max-width: 860px; max-height: 560px; }
.fig-side.wide .fig { max-width: 900px; }
.fig-side.square .fig { max-width: 600px; }
.fig-side .side { flex: 1; min-width: 0; }
.fig { display: block; }
.stat { margin-bottom: 18px; }
.stat .num { display: block; font-family: Cambria, Georgia, serif; font-size: 36px; font-weight: bold; color: #007F86; line-height: 1.1; }
.stat .lbl { display: block; font-size: 15.5px; color: #1F2D3A; line-height: 1.35; }
.unit { display: flex; gap: 14px; align-items: center; margin-bottom: 12px; padding: 8px 12px; border-radius: 10px; }
.unit .num { flex: 0 0 96px; font-family: Cambria, Georgia, serif; font-size: 38px; font-weight: bold; color: #007F86; }
.unit .lbl { font-size: 15px; line-height: 1.3; }
.unit.hl { background: #FBF3EE; }
.unit.hl .num { color: #B86632; }

.flow { display: flex; align-items: stretch; gap: 14px; margin: 40px 0 36px; }
.flow .box { flex: 1; background: #EEF6F6; border-radius: 14px; padding: 22px 24px; }
.flow .box.accent { background: #087E8B; }
.flow .box.accent .num, .flow .box.accent .lbl { color: #FFFFFF; }
.flow .num { display: block; font-family: Cambria, Georgia, serif; font-size: 44px; font-weight: bold; color: #007F86; }
.flow .lbl { display: block; font-size: 17px; line-height: 1.35; margin-top: 6px; }
.flow .arrow { display: flex; align-items: center; font-size: 36px; color: #9FB3BC; }
.formula { text-align: center; font-size: 24px; color: #0B2E4F; background: #F7F9FA; border: 1px solid #D5DEE4; border-radius: 12px; padding: 20px; margin-bottom: 28px; }

.steps { display: grid; grid-template-columns: 1fr 1fr; gap: 22px 32px; margin-top: 12px; }
.step { display: flex; gap: 18px; align-items: flex-start; background: rgba(255,255,255,0.07); border-radius: 14px; padding: 24px 26px; }
.step .n { flex: 0 0 42px; height: 42px; border-radius: 50%; background: #007F86; color: #FFFFFF; font-weight: bold; font-size: 19px; display: flex; align-items: center; justify-content: center; }
.step b { font-size: 22px; color: #FFFFFF; }
.step p { font-size: 17px; color: #CFE3EA; margin: 8px 0 0; }
.fonte { position: absolute; left: 56px; bottom: 18px; font-size: 12px; color: #8A98A3; }
.closing { position: absolute; left: 56px; right: 56px; bottom: 44px; font-size: 16px; color: #A9C3CE; }
"""

documento = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Quando a chuva vira problema · Entrega final</title>
<style>{CSS}</style></head><body>{"".join(slides)}</body></html>"""
(SAIDA / "final.html").write_text(documento, encoding="utf-8")
print(len(slides), "slides")
