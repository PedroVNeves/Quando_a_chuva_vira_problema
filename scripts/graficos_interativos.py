"""Versões interativas (Plotly) dos gráficos principais.

Usam as mesmas tabelas dos gráficos estáticos; não recalculam nenhuma estatística.
"""
import html
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from scripts.estilo_graficos import INK, MUTED, GRID, TEAL, COPPER

ESCALA_CORES = [[0, "#F2F7F7"], [.25, "#B9DBD8"], [.5, "#53A7AA"], [.75, "#087E8B"], [1, "#173D50"]]
FONTES = "Fontes: Alerta Rio, COR e limites de bairros do IPP / Data.Rio."


def _pct(valor):
    if pd.isna(valor):
        return "—"
    if valor == 0:
        return "0%"
    return ((f"{valor:.2f}" if valor < 1 else f"{valor:.1f}") + "%").replace(".", ",")


def _inteiro(valor):
    return f"{int(valor):,}".replace(",", ".")


def _faixa(texto):
    return str(texto).replace("–", " a ").replace(">", "> ") + " mm"


def _layout(fig, titulo, subtitulo, nota, altura, margem_esquerda=60):
    fig.update_layout(
        title=dict(
            text=f"<b>{titulo}</b><br><span style='font-size:13px;color:{MUTED}'>{subtitulo}</span>",
            x=.02, xanchor="left", yref="container", y=1, yanchor="top", pad=dict(t=26),
            font=dict(size=21, color=INK)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", color=INK, size=12),
        template="none", paper_bgcolor="white", plot_bgcolor="white", height=altura,
        margin=dict(l=margem_esquerda, r=30, t=130, b=125),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(size=12, color=INK)),
    )
    fig.add_annotation(
        text=f"{nota}<br><span style='font-size:10px'>{FONTES}</span>",
        xref="paper", yref="paper", x=0, y=0, yshift=-55, xanchor="left", yanchor="top",
        showarrow=False, align="left", font=dict(size=11, color=MUTED))
    return fig


def interativo_frequencias(agua, terra):
    """Frequência por faixa de chuva, com IC e denominadores no tooltip."""
    agua, terra = agua.reset_index(), terra.reset_index()
    assert agua.faixa.equals(terra.faixa)
    faixas = [_faixa(f) for f in agua.faixa]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=.06,
                        subplot_titles=("<b>Acúmulo de água</b>", "<b>Deslizamentos</b>"))
    for coluna, (dados, cor) in enumerate([(agua, TEAL), (terra, COPPER)], start=1):
        detalhes = [
            [_pct(r.frequencia_pct),
             f"{_pct(r.ic_inferior_pct)} a {_pct(r.ic_superior_pct)}" if pd.notna(r.ic_inferior_pct) else "sem intervalo (amostra insuficiente)",
             _inteiro(r.dias_com_registro), _inteiro(r.bairro_dias), _inteiro(r.dias_distintos)]
            for r in dados.itertuples()]
        fig.add_trace(go.Scatter(
            x=dados.frequencia_pct, y=faixas, mode="markers", name=("Acúmulo de água", "Deslizamentos")[coluna-1],
            marker=dict(size=12, color=cor, line=dict(color="white", width=1)),
            error_x=dict(type="data", symmetric=False, color=cor, thickness=2.5, width=5,
                         array=(dados.ic_superior_pct - dados.frequencia_pct).to_numpy(),
                         arrayminus=(dados.frequencia_pct - dados.ic_inferior_pct).to_numpy()),
            customdata=detalhes,
            hovertemplate=("<b>Chuva diária: %{y}</b><br>Frequência: %{customdata[0]}<br>"
                           "IC 95%: %{customdata[1]}<br>%{customdata[2]} de %{customdata[3]} bairro-dias com registro"
                           "<br>%{customdata[4]} datas distintas<extra></extra>"),
            showlegend=False), row=1, col=coluna)
        fig.update_xaxes(ticksuffix="%", gridcolor=GRID, zeroline=False, rangemode="tozero",
                         title_text="Bairro-dias com pelo menos um registro", title_font=dict(size=11, color=MUTED),
                         row=1, col=coluna)
    fig.update_yaxes(categoryorder="array", categoryarray=faixas, autorange="reversed", showgrid=False,
                     title_text="Chuva diária", title_font=dict(size=11, color=MUTED), row=1, col=1)
    fig.update_yaxes(showgrid=False, row=1, col=2)
    for anotacao, cor in zip(fig.layout.annotations, [TEAL, COPPER]):
        anotacao.update(font=dict(size=14, color=cor), x=anotacao.x, xanchor="center")
    # A escala logarítmica aproxima as faixas de pouca chuva, com frequências abaixo de 1%.
    escalas = [dict(label=nome, method="relayout", args=[{"xaxis.type": tipo, "xaxis2.type": tipo}])
               for nome, tipo in [("Escala linear", "linear"), ("Escala logarítmica", "log")]]
    fig.update_layout(updatemenus=[dict(type="buttons", direction="right", buttons=escalas, x=1, xanchor="right",
                                        y=1.13, yanchor="bottom", bgcolor="white", bordercolor=GRID,
                                        font=dict(size=11, color=INK))])
    nota = ("Passe o mouse sobre um ponto para ver o intervalo e o denominador. Traço: intervalo exploratório de 95% por semanas. "
            "<br>Escalas diferentes nos dois painéis; na escala logarítmica, faixas com 0% não aparecem. Associação no mesmo dia, sem causalidade.")
    return _layout(fig, "Chuva e ocorrências no mesmo dia",
                   "Bairros do Rio de Janeiro · 2020–2021 · frequência por faixa de chuva diária", nota, altura=560,
                   margem_esquerda=110)


def interativo_bairros(comparacao, faixas=("0–10", ">10–30", ">30")):
    """Mapa de calor por bairro, com ordenação selecionável e denominadores no tooltip."""
    dados = comparacao.assign(faixa_ampla=comparacao.faixa_ampla.astype(str))
    freq = dados.pivot(index="nome", columns="faixa_ampla", values="frequencia_pct").reindex(columns=list(faixas))
    dias = dados.pivot(index="nome", columns="faixa_ampla", values="dias").reindex(columns=list(faixas))
    com = dados.pivot(index="nome", columns="faixa_ampla", values="com_registro").reindex(columns=list(faixas))
    rotulos = [_faixa(f) for f in faixas]

    def sem_acento(indice):
        return indice.str.normalize("NFKD").str.encode("ascii", errors="ignore").str.decode("ascii")

    freq = freq.sort_index(key=sem_acento)  # empates nas outras ordens ficam em ordem alfabética
    ordens = {
        "Ordem alfabética": freq.index,
        "Maior frequência acima de 30 mm": freq.sort_values(faixas[-1], ascending=False, kind="stable").index,
        "Maior frequência entre 10 e 30 mm": freq.sort_values(faixas[1], ascending=False, kind="stable").index,
    }

    def arrumar(ordem):
        z = freq.loc[ordem]
        texto = z.round(0).astype("Int64").astype(str).to_numpy()
        detalhes = np.dstack([com.loc[ordem].astype(int).astype(str).to_numpy(),
                              dias.loc[ordem].astype(int).astype(str).to_numpy(),
                              z.map(_pct).to_numpy()])
        return dict(z=z.to_numpy(), y=list(ordem), text=texto, customdata=detalhes)

    inicial = arrumar(ordens["Ordem alfabética"])
    fig = go.Figure(go.Heatmap(
        x=rotulos, colorscale=ESCALA_CORES, zmin=0, zmax=100, xgap=2, ygap=2,
        texttemplate="%{text}", textfont=dict(size=10),
        colorbar=dict(title=dict(text="Bairro-dias<br>com registro (%)", font=dict(size=11, color=MUTED)),
                      ticksuffix="%", thickness=12, len=.35, y=.97, yanchor="top", outlinewidth=0),
        hovertemplate=("<b>%{y}</b> · chuva %{x}<br>Frequência: %{customdata[2]}"
                       "<br>%{customdata[0]} de %{customdata[1]} dias com registro<extra></extra>"),
        **inicial))
    botoes = [dict(label=nome, method="restyle",
                   args=[{chave: [valor] for chave, valor in arrumar(ordem).items()}])
              for nome, ordem in ordens.items()]
    fig.update_layout(updatemenus=[dict(buttons=botoes, direction="down", x=0, xanchor="left", y=1, yanchor="bottom",
                                        pad=dict(b=34), bgcolor="white", bordercolor=GRID,
                                        font=dict(size=12, color=INK), showactive=True)])
    fig.update_xaxes(side="top", tickfont=dict(size=12), title_text="")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=11), ticksuffix="  ")
    nota = (f"{len(freq)} bairros com pelo menos 20 dias em cada faixa. Use o menu para reordenar e passe o mouse para ver os denominadores."
            "<br>Frequência de registros, não ranking de vulnerabilidade: monitoramento, área e exposição também variam.")
    fig = _layout(fig, "A frequência de registros varia entre bairros",
                  "Acúmulo de água · 2020–2021 · bairro-dias com registro por faixa de chuva diária",
                  nota, altura=22*len(freq) + 300, margem_esquerda=190)
    fig.update_layout(margin=dict(t=170))
    return fig


def mostrar_interativo(fig, nome, descricao, pasta=Path("resultados")):
    """Salva o HTML do gráfico e devolve um iframe isolado para exibir no notebook.

    O Plotly é carregado pela CDN, o que mantém o notebook leve, mas exige internet.
    """
    altura = int(fig.layout.height or 500)
    pagina = fig.to_html(include_plotlyjs="cdn", full_html=True, default_height=f"{altura}px",
                         config={"displaylogo": False, "responsive": True,
                                 "toImageButtonOptions": {"filename": nome, "scale": 2}})
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.html").write_text(pagina, encoding="utf-8")
    # O <div> externo evita o aviso do IPython para HTML que começa com <iframe>.
    return (f'<div><iframe title="{html.escape(descricao, quote=True)}" sandbox="allow-scripts allow-downloads" '
            f'style="width:100%;height:{altura + 24}px;border:1px solid {GRID};border-radius:8px" '
            f'srcdoc="{html.escape(pagina, quote=True)}"></iframe></div>')
