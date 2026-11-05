"""Preparação reproduzível para analise.ipynb; os arquivos brutos são somente lidos."""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import pyarrow.dataset as ds
import pyarrow.compute as pc

FUSO = "America/Sao_Paulo"
CRS_METRICO = "EPSG:31983"
GRUPOS = {"5": "Acúmulo de água", "6": "Acúmulo de água", "31": "Acúmulo de água",
          "32": "Acúmulo de água", "33": "Acúmulo de água", "28": "Deslizamentos"}
FAIXAS = ["0", ">0–10", ">10–20", ">20–30", ">30–50", ">50–100", ">100"]
LIMITES = [-1e-9, 0, 10, 20, 30, 50, 100, np.inf]


def carregar_cor(bq):
    bruto = pd.read_parquet(Path(bq) / "adm_cor_comando/ocorrencias.parquet")
    cor = bruto.drop_duplicates().copy()
    # IDs reaparecem em anos distintos. Não eliminar eventos apenas por id_evento.
    if cor[["id_evento", "data_inicio"]].isna().any().any():
        raise ValueError("COR com chave incompleta: revisar antes de analisar.")
    if cor.duplicated(["id_evento", "data_inicio"]).any():
        raise ValueError("COR com versões conflitantes para ID e início.")
    pop = pd.read_parquet(Path(bq) / "adm_cor_comando/procedimento_operacional_padrao.parquet")
    cor = cor.merge(pop, on="id_pop", how="left", validate="many_to_one")
    cor["inicio_local"] = cor.data_inicio.dt.tz_convert(FUSO)
    cor["dia"] = cor.inicio_local.dt.tz_localize(None).dt.normalize()
    cor["grupo"] = cor.id_pop.map(GRUPOS)
    cor["linha_origem"] = np.arange(len(cor))
    auditoria = pd.Series({"Linhas brutas": len(bruto), "Cópias idênticas removidas": len(bruto)-len(cor),
        "Repetições de ID isolado": int(bruto.id_evento.duplicated().sum()),
        "Repetições de ID + início": int(cor.duplicated(["id_evento", "data_inicio"]).sum())})
    return cor, auditoria


def associar_bairros(cor, bairros):
    foco = cor.loc[cor.grupo.notna()].copy().set_index("linha_origem", drop=False)
    validas = foco.latitude.between(-90, 90) & foco.longitude.between(-180, 180)
    pontos = gpd.GeoDataFrame(index=foco.index[validas], geometry=gpd.points_from_xy(
        foco.loc[validas, "longitude"], foco.loc[validas, "latitude"]), crs="EPSG:4326")
    candidatos = gpd.sjoin(pontos, bairros[["id_bairro", "nome", "geometry"]].to_crs(pontos.crs),
                           how="left", predicate="intersects")
    n = candidatos.groupby(level=0).id_bairro.nunique()
    unicos = candidatos.loc[candidatos.index.map(n) == 1]
    unicos = unicos.groupby(level=0)[["id_bairro", "nome"]].first()
    foco = foco.join(unicos, validate="one_to_one")
    foco["situacao_espacial"] = "Coordenadas ausentes ou inválidas"
    foco.loc[validas, "situacao_espacial"] = "Fora dos polígonos"
    foco.loc[foco.index.isin(n[n > 1].index), "situacao_espacial"] = "Mais de um bairro"
    foco.loc[foco.id_bairro.notna(), "situacao_espacial"] = "Bairro único"
    return foco


def estacoes_geograficas(estacoes):
    e = estacoes.dropna(subset=["latitude", "longitude"]).copy()
    return gpd.GeoDataFrame(e, geometry=gpd.points_from_xy(e.longitude, e.latitude),
                           crs="EPSG:4326").to_crs(CRS_METRICO)


def mapa_bairro_estacao(bairros, estacoes):
    """Uma estação fixa por ponto interior de bairro, independente das ocorrências."""
    b = bairros[["id_bairro", "nome", "geometry"]].to_crs(CRS_METRICO).copy()
    b.geometry = b.geometry.representative_point()
    e = estacoes_geograficas(estacoes)
    candidatos = gpd.sjoin_nearest(b, e[["id_estacao", "estacao", "geometry"]],
                                   how="left", distance_col="distancia_m")
    n = candidatos.groupby("id_bairro").id_estacao.nunique()
    # Empates não são resolvidos pela ordem das linhas.
    resultado = candidatos.drop_duplicates("id_bairro").drop(columns=["index_right", "geometry"])
    resultado["empate"] = resultado.id_bairro.map(n).gt(1)
    resultado.loc[resultado.empate, ["id_estacao", "estacao", "distancia_m"]] = None
    resultado["distancia_km"] = resultado.distancia_m / 1000
    return pd.DataFrame(resultado)


def ler_estacao(base, id_estacao, referencia):
    bruto = base.to_table(filter=ds.field("id_estacao") == id_estacao).to_pandas()
    futuras = pd.to_datetime(bruto.data_particao).gt(pd.Timestamp(referencia))
    sem_futuro = bruto.loc[~futuras]
    unicas = sem_futuro.drop_duplicates()
    completas = unicas.dropna(subset=["id_estacao", "data_particao", "horario"]).copy()
    completas["instante"] = pd.to_datetime(completas.data_particao.astype(str) + " " + completas.horario.astype(str))
    if completas.instante.duplicated().any():
        raise ValueError(f"Leituras conflitantes na estação {id_estacao}.")
    fora_grade = ~completas.instante.eq(completas.instante.dt.floor("15min"))
    valores = completas.filter(like="acumulado_chuva_")
    diagnostico = {"id_estacao": id_estacao, "registros_brutos": len(bruto),
        "datas_futuras": int(futuras.sum()), "copias_identicas": len(sem_futuro)-len(unicas),
        "chaves_incompletas": len(unicas)-len(completas), "fora_grade_15min": int(fora_grade.sum()),
        "leituras_com_negativos": int(valores.lt(0).any(axis=1).sum())}
    return completas.set_index("instante").sort_index(), diagnostico


def totais_periodo(leituras, inicio, fim, frequencia="D", recuperar=True):
    """Soma intervalos terminados em 00:15 ... 00:00 seguinte.

    Grade nominal local. Períodos que tocam transições do horário de verão são
    excluídos conservadoramente: a fonte sem offset não permite recuperar a hora
    repetida. Não inferimos zero de um acumulado móvel que não subiu.
    """
    passo = pd.Timedelta(minutes=15)
    inicio, fim = pd.Timestamp(inicio).normalize(), pd.Timestamp(fim).normalize()
    leituras = leituras.loc[inicio-pd.Timedelta(days=1):fim+pd.Timedelta(days=2)].copy()
    if not leituras.index.equals(leituras.index.floor("15min")):
        raise ValueError("Leituras fora da grade no recorte de cálculo: não arredondar automaticamente.")
    if leituras.filter(like="acumulado_chuva_").lt(0).any().any():
        raise ValueError("Precipitação negativa no recorte de cálculo.")
    grade = pd.date_range(inicio + passo, fim + pd.Timedelta(days=1), freq=passo)
    serie = leituras.acumulado_chuva_15_min
    observada = serie.reindex(grade)
    # A medição à meia-noite encerra o intervalo do dia/mês anterior.
    atribuicao = grade - pd.Timedelta(nanoseconds=1)
    periodo = atribuicao.to_period("M" if frequencia == "MS" else "D").to_timestamp()
    indice_periodos = pd.date_range(inicio, fim, freq=frequencia)
    dados = pd.DataFrame({"valor": observada.to_numpy(), "periodo": periodo}, index=grade)
    resultado = dados.groupby("periodo").agg(observadas=("valor", "count"), esperadas=("valor", "size"))
    resultado["observado_mm"] = dados.groupby("periodo").valor.sum(min_count=1)
    resultado = resultado.reindex(indice_periodos)
    resultado.index.name = "dia" if frequencia == "D" else "mes"
    resultado["recuperado_mm"] = 0.0
    resultado["leituras_recuperadas"] = 0
    resultado["recuperacao_cruza_periodo"] = False
    # Inclui os dois lados dos intervalos para detectar a mudança à meia-noite.
    ambiguo = grade.tz_localize(FUSO, ambiguous="NaT", nonexistent="NaT").isna()
    ambiguo |= (grade-passo).tz_localize(FUSO, ambiguous="NaT", nonexistent="NaT").isna()
    resultado["relogio_incerto"] = pd.Series(ambiguo, index=periodo).groupby(level=0).any().reindex(indice_periodos, fill_value=False)
    falhas = []
    ausente = observada.isna()
    grupos = (ausente != ausente.shift()).cumsum()
    for _, trecho in observada[ausente].groupby(grupos[ausente]):
        hs = trecho.index
        registro = {"inicio": hs[0], "fim": hs[-1], "n": len(hs), "recuperado_mm": np.nan,
                    "situacao": "Lacuna não recuperada", "janela": None}
        depois = hs[-1] + passo
        if recuperar:
            for coluna, tamanho in [("acumulado_chuva_1_h", 4), ("acumulado_chuva_4_h", 16), ("acumulado_chuva_24_h", 96)]:
                if len(hs) >= tamanho or depois not in leituras.index:
                    continue
                janela = pd.date_range(depois - (tamanho-1)*passo, depois, freq=passo)
                if janela.tz_localize(FUSO, ambiguous="NaT", nonexistent="NaT").isna().any():
                    continue
                restante = serie.reindex(janela).drop(hs)
                acumulado = leituras.at[depois, coluna]
                if pd.isna(acumulado) or restante.isna().any():
                    continue
                estimativa = acumulado - restante.sum()
                if estimativa < -0.05:
                    registro["situacao"] = "Janela inconsistente"
                    break
                registro.update(recuperado_mm=max(0., estimativa), janela=coluna,
                                situacao="Recuperada pelo acumulado")
                ps = (hs-pd.Timedelta(nanoseconds=1)).to_period("M" if frequencia == "MS" else "D").to_timestamp().unique()
                if len(ps) != 1:
                    resultado.loc[ps, "recuperacao_cruza_periodo"] = True
                else:
                    resultado.loc[ps[0], "recuperado_mm"] += max(0., estimativa)
                    resultado.loc[ps[0], "leituras_recuperadas"] += len(hs)
                break
        falhas.append(registro)
    resultado["nao_recuperadas"] = resultado.esperadas - resultado.observadas - resultado.leituras_recuperadas
    resultado["cobertura_observada_pct"] = 100 * resultado.observadas / resultado.esperadas
    resultado["soma_disponivel_mm"] = resultado.observado_mm + resultado.recuperado_mm
    completo = resultado.nao_recuperadas.eq(0) & ~resultado.relogio_incerto & ~resultado.recuperacao_cruza_periodo
    resultado["total_mm"] = resultado.soma_disponivel_mm.where(completo)
    resultado["total_so_observado_mm"] = resultado.observado_mm.where(resultado.observadas.eq(resultado.esperadas) & ~resultado.relogio_incerto)
    resultado["situacao"] = np.select([resultado.relogio_incerto, resultado.recuperacao_cruza_periodo, completo],
        ["Convenção histórica de horário", "Recuperação atravessa período", "Completo após tratamento"], default="Parcial")
    return resultado, pd.DataFrame(falhas, columns=["inicio", "fim", "n", "recuperado_mm", "situacao", "janela"])


def preparar_chuva(bq, referencia, inicio_diario="2020-01-01", fim_diario="2021-12-31"):
    base = ds.dataset(Path(bq) / "clima_pluviometro/taxa_precipitacao_alertario.parquet")
    ids = set()
    for lote in base.to_batches(columns=["id_estacao"]):
        ids.update(pc.unique(lote["id_estacao"]).to_pylist())
    ids = sorted(ids - {None}, key=int)
    auditoria, anual, diarios, mensais, falhas = [], [], [], [], []
    for id_estacao in ids:
        leituras, diag = ler_estacao(base, id_estacao, referencia)
        auditoria.append(diag)
        # Cobertura anual em anos civis completos: anos de borda ficam explicitamente parciais.
        dias = leituras.acumulado_chuva_15_min.resample("D").count()
        for ano in range(leituras.index.min().year, leituras.index.max().year+1):
            calendario = pd.date_range(f"{ano}-01-01", f"{ano}-12-31", freq="D")
            n = dias.reindex(calendario, fill_value=0)
            anual.append({"id_estacao": id_estacao, "ano": ano,
                "dias_com_medicao_pct": 100*n.gt(0).mean(),
                "dias_96_leituras_pct": 100*n.eq(96).mean(),
                "ano_de_borda": ano in [leituras.index.min().year, leituras.index.max().year]})
        for cenario, deslocamento in [("Local", 0), ("Relógio UTC", -3)]:
            recorte = leituras.loc[pd.Timestamp(inicio_diario)-pd.Timedelta(days=2):pd.Timestamp(fim_diario)+pd.Timedelta(days=2)].copy()
            recorte.index = recorte.index + pd.Timedelta(hours=deslocamento)
            diario, lacunas = totais_periodo(recorte, inicio_diario, fim_diario)
            diarios.append(diario.reset_index().assign(id_estacao=id_estacao, cenario=cenario))
            falhas.append(lacunas.assign(id_estacao=id_estacao, escala="diaria", cenario=cenario))
        if id_estacao in ["1", "4", "26"]:
            mensal, lacunas = totais_periodo(leituras, "2014-01-01", "2021-12-31", "MS")
            mensais.append(mensal.reset_index().assign(id_estacao=id_estacao))
            falhas.append(lacunas.assign(id_estacao=id_estacao, escala="mensal", cenario="Local"))
    if sum(r["registros_brutos"] for r in auditoria) != base.count_rows():
        raise ValueError("Há registros sem estação; incluir sua auditoria antes de continuar.")
    return dict(auditoria=pd.DataFrame(auditoria), anual=pd.DataFrame(anual),
                diarios=pd.concat(diarios, ignore_index=True), mensais=pd.concat(mensais, ignore_index=True),
                falhas=pd.concat(falhas, ignore_index=True))


def construir_painel(mapa, diarios, foco, cor, inicio="2020-01-01", fim="2021-12-31"):
    calendario = pd.DataFrame({"dia": pd.date_range(inicio, fim, freq="D")})
    grade = mapa.merge(calendario, how="cross")
    painel = grade.merge(diarios, on=["id_estacao", "dia"], how="left", validate="many_to_one")
    eventos = foco.loc[foco.id_bairro.notna() & foco.dia.between(inicio, fim)]
    for grupo, coluna in [("Acúmulo de água", "n_agua"), ("Deslizamentos", "n_deslizamento")]:
        contagem = eventos.loc[eventos.grupo.eq(grupo)].groupby(["id_bairro", "dia"]).size().rename(coluna)
        painel = painel.join(contagem, on=["id_bairro", "dia"], validate="one_to_one")
        painel[coluna] = painel[coluna].fillna(0).astype(int)
    atividade = cor.groupby("dia").size()
    painel["registros_cor_cidade"] = painel.dia.map(atividade).fillna(0).astype(int)
    painel["dia_com_registro_cor"] = painel.registros_cor_cidade.gt(0)
    painel["chuva_valida"] = painel.total_mm.notna()
    painel["elegivel"] = painel.chuva_valida & painel.dia_com_registro_cor
    painel["faixa"] = pd.cut(painel.total_mm, LIMITES, labels=FAIXAS)
    assert not painel.duplicated(["id_bairro", "dia"]).any()
    return painel


def frequencias(painel, coluna="n_agua", n_boot=600, semente=2026):
    """IC exploratório por reamostragem conjunta de semanas de calendário.

    Mantém todos os bairros de cada semana juntos; não presume independência
    entre bairros no mesmo temporal. Não corrige subnotificação nem dependência
    entre semanas. Faixas sem eventos não recebem IC degenerado [0, 0].
    """
    dados = painel.copy()
    dados["evento"] = dados[coluna].gt(0).astype(int)
    dados["semana"] = dados.dia.dt.to_period("W-SUN").dt.start_time
    resumo = dados.groupby("faixa", observed=False).agg(
        bairro_dias=("evento", "size"), dias_distintos=("dia", "nunique"),
        semanas=("semana", "nunique"), dias_com_registro=("evento", "sum"), registros=(coluna, "sum"))
    resumo["frequencia_pct"] = 100 * resumo.dias_com_registro / resumo.bairro_dias.replace(0, np.nan)
    resumo["ic_inferior_pct"], resumo["ic_superior_pct"] = np.nan, np.nan
    if dados.empty:
        return resumo
    agregados = dados.groupby(["semana", "faixa"], observed=False).evento.agg(["size", "sum"])
    semanas = pd.date_range(dados.semana.min(), dados.semana.max(), freq="7D")
    n = agregados["size"].unstack("faixa").reindex(index=semanas, columns=FAIXAS, fill_value=0).fillna(0).to_numpy()
    y = agregados["sum"].unstack("faixa").reindex(index=semanas, columns=FAIXAS, fill_value=0).fillna(0).to_numpy()
    rng = np.random.default_rng(semente)
    pesos = rng.multinomial(len(semanas), np.ones(len(semanas))/len(semanas), size=n_boot)
    denominadores = pesos @ n
    amostras = np.divide(100*(pesos @ y), denominadores, out=np.full((n_boot, len(FAIXAS)), np.nan), where=denominadores > 0)
    for i, faixa in enumerate(FAIXAS):
        r = resumo.loc[faixa]
        if r.semanas >= 5 and 0 < r.dias_com_registro < r.bairro_dias and np.isfinite(amostras[:, i]).sum() >= .9*n_boot:
            resumo.loc[faixa, ["ic_inferior_pct", "ic_superior_pct"]] = np.nanpercentile(amostras[:, i], [2.5, 97.5])
    return resumo
