"""Estilo aprovado e funções de apresentação; não realiza estimação estatística."""
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import numpy as np
import seaborn as sns

INK, MUTED, GRID = "#203440", "#60727C", "#E5EBEE"
TEAL, COPPER = "#087E8B", "#B86632"
PALETA = [TEAL, COPPER, "#526DA5", "#8B6C91"]
MAPA_CORES = sns.blend_palette(["#F2F7F7", "#B9DBD8", "#53A7AA", "#087E8B", "#173D50"], as_cmap=True)

def configurar_estilo():
    sns.set_theme(style="white", context="notebook", font="DejaVu Sans", palette=PALETA, rc={
        "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED,
        "ytick.color": INK, "axes.edgecolor": GRID, "svg.fonttype": "none",
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlelocation": "left", "axes.titlesize": 12,
        "axes.titleweight": "bold", "axes.labelsize": 10,
        "grid.color": GRID, "grid.linewidth": .8, "figure.dpi": 110,
    })

# Título, subtítulo, nota de leitura, dimensão e manutenção dos títulos dos painéis.
FIGURAS = {
    "17_coerencia_anual": ("As diferenças entre bairros persistem entre anos?", "Acúmulo de água · mesmos bairros · frequências padronizadas para chuva entre 10 e 50 mm", "Um ponto por bairro. Traços claros: IC exploratórios por semanas, cortados na borda quando passam do limite. Acima da diagonal, mais registros em 2021.", (12, 10), False),
    "18_associacoes_padronizadas": ("Perfil social sob uma mistura fixa de chuva", "Correlações descritivas · mesmo peso para três faixas entre 10 e 50 mm · coorte comum por cenário", "Os critérios mudam a seleção de bairros. Pontos não são testes de significância nem medidas de efeito causal.", (17, 9), True),
    "15_ciclo_horario": ("Em quais horários a chuva se concentra?", "Rede fixa de três estações · mesmos dias completos · média dos anos elegíveis", "Linha: média horária. Faixa: percentis 25–75 das médias anuais; não é intervalo de confiança.", (16, 8), True),
    "16_extremos_historicos": ("Dias de chuva forte ao longo dos anos", "Rede fixa · frequência entre os dias comuns válidos · três definições exploratórias", "Lacunas: anos sem cobertura suficiente. Limites de 50, 80 e 100 mm/dia não são níveis oficiais de alerta.", (16, 9), True),
    "12_duracao_chegada": ("Duração e chegada registrada dos órgãos", "2020–2021 · eventos em bairro-dias elegíveis · faixas de chuva diária", "Escalas diferentes por painel. Ponto: mediana; traço: percentis 25–75, não intervalo de confiança.", (15, 10), True),
    "13_janelas_chuva": ("Chuva recente e chuva acumulada", "2020–2021 · chuva anterior e registros nos blocos seguintes de seis horas", "Escalas diferentes por painel. P50/P90: percentis da chuva positiva de cada janela. IC de 95% por semanas.", (15, 9), True),
    "14_perfil_social": ("Perfil dos bairros e registros em dias chuvosos", "IPS e densidade de 2022 · registros de acúmulo de água em 2020–2021 · chuva acima de 30 mm", "Um ponto por bairro elegível. Associação ecológica sem controle de exposição ou monitoramento.", (15, 9), True),
    "01_rede_estacoes": ("Qual estação mede a chuva de cada bairro?", "Rede Alerta Rio · cada bairro ligado à estação mais próxima de um ponto interior", "Contorno escuro: bairros que dividem a mesma estação e, portanto, a mesma chuva. A distância é medida do ponto interior do bairro, não do seu centro populacional.", (13, 8.5), False),
    "02_cobertura": ("Presença de dados não garante completude", "Cobertura anual por estação · duas formas de observar a disponibilidade", "96 horários distintos não certificam espaçamento regular. Anos de borda podem ser parciais.", (17, 12), True),
    "03_totais_mensais": ("Quando os meses chuvosos coincidem?", "Vidigal, Tijuca e Campo Grande · totais mensais · 2014–2021", "Mesma escala nos três painéis. Faixas cinzas identificam meses sem total comparável.", (14, 10), True),
    "04_sazonalidade_vidigal": ("A chuva ao longo do ano no Vidigal", "2014–2021 · média mensal e variação entre os anos disponíveis", "Pontos: totais de cada ano. A amostra varia entre meses; as exclusões de horário afetam a comparação.", (13, 8), False),
    "05_chuva_antes_ocorrencias": ("Quanto havia chovido antes dos registros?", "Temporal de 8–9 de abril de 2019 · acumulado anterior de 24 horas", "Cada ocorrência usa sua estação mais próxima. Pontos podem se sobrepor; a figura não estima probabilidade.", (13, 8), False),
    "06_temporal_paineis": ("O temporal, estação por estação", "8–9 de abril de 2019 · chuva em 15 minutos e início dos registros", "Traços abaixo do eixo: início dos registros associados à estação. Mesma escala de chuva nos três painéis.", (14, 10), True),
    "08_sensibilidade": ("Quanto as escolhas mudam o resultado?", "Acúmulo de água · frequências por faixa de chuva · 2020–2021", "Os cenários podem usar amostras diferentes. As linhas ligam categorias, não uma curva ajustada.", (13, 8), False),
    "20_unidade_prefeitura": ("O limiar de 30 mm depende de onde se olha", "Acúmulo de água · 2020–2021 · mesma chuva, três unidades de contagem", "Estação-dia: registro em algum bairro ligado à estação. Cidade-dia: chuva da estação com mais chuva no dia. Barras: IC de 95% por semanas; faixas com menos de 20 unidades omitidas.", (12, 7), False),
    "09_comparacao_bairros": ("A frequência de registros varia entre bairros", "Acúmulo de água · 2020–2021 · ordem alfabética · mesma escala de cores", "Pelo menos 20 dias por faixa nos bairros apresentados. Valores arredondados; não é um ranking de vulnerabilidade.", (14, 17), False),
    "19_mapa_registros": ("Onde se concentram os registros de acúmulo de água?", "Bairros do Rio de Janeiro · 2020–2021 · contagem total e frequência sob chuva forte", "Hachurado (à direita): bairro fora dos critérios da seção 6, em geral com menos de 20 dias acima de 30 mm. A contagem depende da chuva e da área; a frequência não.", (16, 8), True),
    "10_fora_poligonos": ("Onde estão os registros fora dos bairros?", "Inspeção das coordenadas próximas aos limites municipais", "O mapa mostra pontos até 10 km dos limites. Coordenadas zeradas e fora da região permanecem na tabela.", (13, 8), False),
    "11_sazonalidade_comum": ("Três estações, os mesmos meses", "Sazonalidade · 2014–2021 · conjunto de meses completos em comum", "A comparação usa os mesmos meses nas três estações; o número de anos disponíveis varia entre meses.", (13, 8), False),
}

def acabamento(fig, nome):
    """Aplica a identidade visual sem modificar dados, limites ou artistas estatísticos."""
    if nome == "07_frequencia_chuva":
        return  # Composição dedicada, idêntica à prévia aprovada.
    # Escolher a cor do número pelo contraste com a célula, não por um corte arbitrário.
    if nome == "09_comparacao_bairros":
        def luminancia(rgb):
            rgb = np.asarray(rgb[:3])
            linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
            return float(linear @ np.array([.2126, .7152, .0722]))
        tinta = luminancia(plt.matplotlib.colors.to_rgb(INK))
        for ax in fig.axes:
            if not ax.images:
                continue
            mapa = ax.images[0]
            valores = mapa.get_array()
            for texto in ax.texts:
                coluna, linha = map(int, texto.get_position())
                fundo = luminancia(mapa.cmap(mapa.norm(valores[linha, coluna])))
                contraste_escuro = (max(fundo, tinta) + .05) / (min(fundo, tinta) + .05)
                contraste_claro = 1.05 / (fundo + .05)
                texto.set_color("white" if contraste_claro > contraste_escuro else INK)
    titulo, subtitulo, nota, tamanho, preservar_titulos = FIGURAS[nome]
    fig.set_size_inches(*tamanho)
    for texto in list(fig.texts):
        texto.remove()
    fig._suptitle = None
    for ax in fig.axes:
        if not preservar_titulos:
            ax.set_title("")
            ax.set_title("", loc="left")
        ax.title.set_color(INK)
        ax.spines[["top", "right"]].set_visible(False)
        for grid in [*ax.get_xgridlines(), *ax.get_ygridlines()]:
            grid.set_color(GRID)
            grid.set_alpha(1)
        leg = ax.get_legend()
        if leg is not None:
            leg.set_frame_on(False)
    # Mantém os painéis, eixos compartilhados, limites e colorbars da figura original.
    rect = (.035, .12, .93, .69) if nome == "09_comparacao_bairros" else (.035, .145, .93, .64)
    fig.set_layout_engine("constrained", rect=rect, h_pad=.12, w_pad=.10)
    fig.text(.055, .948, "QUANDO A CHUVA VIRA PROBLEMA", color=TEAL, fontsize=10, weight="bold")
    fig.text(.055, .895, titulo, fontsize=23, weight="bold", color=INK)
    fig.text(.055, .853, subtitulo, fontsize=11, color=MUTED)
    fig.add_artist(Line2D([.055, .965], [.113, .113], transform=fig.transFigure, color=GRID, linewidth=1))
    fig.text(.055, .075, nota, fontsize=9.5, color=MUTED)
    fig.text(.055, .035, "Fontes: Alerta Rio, COR e limites de bairros do IPP / Data.Rio. Critérios descritos no notebook.", fontsize=8.5, color=MUTED)

def figura_frequencias(agua, terra):
    agua, terra = agua.reset_index(), terra.reset_index()
    assert agua.faixa.equals(terra.faixa)
    assert agua.bairro_dias.equals(terra.bairro_dias)
    assert agua.dias_distintos.equals(terra.dias_distintos)
    INK, MUTED, GRID = "#203440", "#60727C", "#E5EBEE"
    TEAL, COPPER = "#087E8B", "#B86632"
    sns.set_theme(style="white", context="notebook", font="DejaVu Sans", palette=PALETA, rc={
        "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED,
        "ytick.color": INK, "axes.edgecolor": GRID, "svg.fonttype": "none",
        "figure.facecolor": "white", "axes.facecolor": "white",
    })
    fig = plt.figure(figsize=(15.5, 8.8))
    fig.text(.055, .947, "QUANDO A CHUVA VIRA PROBLEMA", color=TEAL, fontsize=10, weight="bold")
    fig.text(.055, .889, "Chuva e ocorrências no mesmo dia", fontsize=26, weight="bold")
    fig.text(.055, .847, "Bairros do Rio de Janeiro  ·  2020–2021  ·  Frequência por faixa de chuva diária", color=MUTED, fontsize=12)

    # Linhas alinhadas: categoria, duas estimativas e denominador compartilhado.
    bottom, height = .245, .51
    labels = fig.add_axes([.055, bottom, .10, height])
    ax1 = fig.add_axes([.185, bottom, .32, height])
    ax2 = fig.add_axes([.565, bottom, .23, height])
    sample = fig.add_axes([.845, bottom, .115, height])
    ys = np.arange(len(agua))
    for ax in [labels, ax1, ax2, sample]:
        ax.set_ylim(6.6, -.6)
        ax.axhspan(5.53, 6.47, color="#F1F6F7", zorder=0)

    labels.axis("off")
    labels.set_xlim(0, 1)
    fig.text(.055, .788, "CHUVA DIÁRIA", fontsize=9, color=MUTED, weight="bold")
    fig.text(.055, .767, "milímetros", fontsize=9, color=MUTED)
    for y, faixa in zip(ys, agua.faixa):
        labels.text(0, y, faixa.replace("–", " a ").replace(">", "> "), va="center", fontsize=11)

    def percentual(valor):
        return (f"{valor:.2f}" if valor < 1 else f"{valor:.1f}").replace(".", ",") + "%"

    for ax, dados, cor, titulo, x0, limite, ticks in [
        (ax1, agua, TEAL, "Acúmulo de água", .185, 40, [0, 10, 20, 30, 40]),
        (ax2, terra, COPPER, "Deslizamentos", .565, 7, [0, 2, 4, 6]),
    ]:
        fig.text(x0, .784, titulo, color=cor, fontsize=15, weight="bold")
        # Valores e IC vêm diretamente dos CSVs. O Seaborn aplica somente o estilo.
        ax.hlines(ys, dados.ic_inferior_pct, dados.ic_superior_pct, color=cor, linewidth=2.5, zorder=3)
        for campo in ["ic_inferior_pct", "ic_superior_pct"]:
            ax.vlines(dados[campo], ys-.075, ys+.075, color=cor, linewidth=1.2, zorder=3)
        ax.scatter(dados.frequencia_pct, ys, s=62, color=cor, edgecolor="white", linewidth=.9, zorder=4)
        for y, v in zip(ys, dados.frequencia_pct):
            ax.annotate(percentual(v), (v, y), xytext=(0 if v > 1 else 4, 11),
                        textcoords="offset points", ha="center" if v > 1 else "left",
                        va="bottom", color=cor, fontsize=10, weight="bold")
        ax.set_xlim(-limite*.025, limite)
        ax.set_xticks(ticks)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
        ax.set_yticks([])
        ax.grid(axis="x", color=GRID, linewidth=.7)
        ax.set_axisbelow(True)
        sns.despine(ax=ax, left=True, bottom=True)
        ax.tick_params(axis="x", length=0, pad=8, labelsize=10)

    sample.axis("off")
    sample.set_xlim(0, 1)
    fig.text(.845, .788, "AMOSTRA POR FAIXA", fontsize=9, color=MUTED, weight="bold")
    sample.text(.48, -.80, "bairro-dias", fontsize=9, color=MUTED, ha="right")
    sample.text(.98, -.80, "datas", fontsize=9, color=MUTED, ha="right")
    for y, row in agua.iterrows():
        sample.text(.48, y, f"{int(row.bairro_dias):,}".replace(",", "."), ha="right", va="center", fontsize=11)
        sample.text(.98, y, str(int(row.dias_distintos)), ha="right", va="center", fontsize=11, color=MUTED)

    fig.text(.185, .193, "Bairro-dias com pelo menos um registro (%)  ·  Escalas diferentes nos dois painéis", fontsize=10, color=MUTED)
    fig.add_artist(Line2D([.055, .96], [.164, .164], transform=fig.transFigure, color=GRID, linewidth=1))
    fig.text(.055, .132, "Ponto: frequência observada. Traço: intervalo exploratório de 95%, por reamostragem de semanas.", fontsize=9.5, color=MUTED)
    fig.text(.055, .103, f"Acima de 100 mm: {int(agua.iloc[-1].bairro_dias)} bairro-dias em {int(agua.iloc[-1].dias_distintos)} datas. A incerteza merece atenção.", fontsize=9.5, color=INK)
    fig.text(.055, .074, "Um bairro-dia combina um bairro e uma data. Associação no mesmo dia; não indica causalidade ou capacidade de previsão.", fontsize=9, color=MUTED)
    fig.text(.055, .031, "Fontes: COR e Alerta Rio / Data.Rio. Acumulados diários e registros iniciados no mesmo dia.", fontsize=8.5, color=MUTED)



    return fig
