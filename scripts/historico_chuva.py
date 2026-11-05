"""Ciclo horário e extremos em rede fixa, com dias estritamente observados."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from scripts.analise_dados import ler_estacao, FUSO

REDE_HISTORICA = {'1': 'Vidigal', '4': 'Tijuca', '26': 'Campo Grande'}
LIMITES_EXTREMOS = [50., 80., 100.]


def agregar_horas(leituras):
    """Quatro intervalos observados por hora; meia-noite encerra o dia anterior.

    Intervalos fora da grade, negativos ou com relógio ambíguo/inexistente não
    certificam uma hora. Não se recupera nem redistribui chuva entre horas.
    """
    idx = leituras.index
    if not idx.is_unique:
        raise ValueError('Instantes duplicados na série histórica.')
    grade = idx == idx.floor('15min')
    horario = idx.tz_localize(FUSO, ambiguous='NaT', nonexistent='NaT').notna()
    horario &= (idx-pd.Timedelta(minutes=15)).tz_localize(
        FUSO, ambiguous='NaT', nonexistent='NaT').notna()
    s = leituras.acumulado_chuva_15_min
    valido = grade & horario & s.notna() & s.ge(0)
    t = pd.DataFrame({'valor': s.where(valido), 'hora': (idx-pd.Timedelta(nanoseconds=1)).floor('h')})
    g = t.groupby('hora').valor.agg(['count', 'sum'])
    g['chuva_mm'] = g['sum'].where(g['count'].eq(4))
    auditoria = {'leituras':len(s), 'fora_grade':int((~grade).sum()),
        'negativas':int(s.lt(0).sum()), 'relogio_invalido':int((~horario).sum())}
    return g[['chuva_mm']], auditoria


def historico_rede(bq, referencia):
    """1997–2024 é o domínio auditado; cobertura determina os anos exibidos."""
    base = ds.dataset(Path(bq)/'clima_pluviometro/taxa_precipitacao_alertario.parquet')
    horas, auditorias, auditorias_anuais = [], [], []
    for id_, nome in REDE_HISTORICA.items():
        print(f'Histórico: {nome}', flush=True)
        l, _ = ler_estacao(base, id_, referencia)
        por_ano = pd.DataFrame({'ano':l.index.year,
            'fora_grade':l.index != l.index.floor('15min')}).groupby('ano').agg(
                leituras=('fora_grade','size'), fora_grade=('fora_grade','sum')).reset_index()
        por_ano['fora_grade_pct'] = 100*por_ano.fora_grade/por_ano.leituras
        auditorias_anuais.append(por_ano.assign(estacao=nome))
        h, a = agregar_horas(l)
        horas.append(h.reset_index().assign(id_estacao=id_, estacao=nome))
        auditorias.append(dict(id_estacao=id_, estacao=nome, **a))
    h = pd.concat(horas, ignore_index=True)
    h['dia'] = h.hora.dt.normalize()
    dias = h.groupby(['id_estacao','dia']).chuva_mm.agg(horas_validas='count', total_mm='sum').reset_index()
    dias.loc[dias.horas_validas.ne(24), 'total_mm'] = np.nan
    tabela = dias.pivot(index='dia', columns='id_estacao', values='total_mm')
    calendario = pd.date_range('1997-01-01','2024-12-31',freq='D')
    tabela = tabela.reindex(index=calendario, columns=list(REDE_HISTORICA))
    tabela.index.name = 'dia'
    comum = tabela.notna().all(axis=1)
    cobertura = pd.DataFrame({'valido':comum, 'ano':calendario.year, 'mes':calendario.month},index=calendario)
    anual = cobertura.groupby('ano').valido.agg(dias_validos='sum',dias_calendario='size')
    anual['cobertura_pct'] = 100*anual.dias_validos/anual.dias_calendario
    mensal = cobertura.groupby(['ano','mes']).valido.mean().mul(100).rename('cobertura_pct').reset_index()
    anual['menor_cobertura_mensal_pct'] = mensal.groupby('ano').cobertura_pct.min()
    anual['elegivel'] = anual.cobertura_pct.ge(90) & anual.menor_cobertura_mensal_pct.ge(80)
    elegiveis = anual.index[anual.elegivel]
    if len(elegiveis) < 8:
        raise ValueError('Menos de oito anos comparáveis: revisar alcance antes de interpretar extremos.')
    selecionada = tabela.loc[comum & tabela.index.year.isin(elegiveis)]
    # Mesmos dias completos nas três estações; 24 horas igualmente representadas.
    horarios = h.loc[h.dia.isin(selecionada.index)].copy()
    horarios['ano'], horarios['hora_local'] = horarios.hora.dt.year, horarios.hora.dt.hour
    horarios['molhada'] = horarios.chuva_mm.gt(0)
    por_ano_hora = horarios.groupby(['estacao','ano','hora_local']).agg(
        media_mm=('chuva_mm','mean'), horas=('chuva_mm','size'),
        horas_com_chuva_pct=('molhada','mean')).reset_index()
    por_ano_hora.horas_com_chuva_pct *= 100
    ciclo = por_ano_hora.groupby(['estacao','hora_local']).agg(
        media_mm=('media_mm','mean'), p25_mm=('media_mm', lambda x:x.quantile(.25)),
        p75_mm=('media_mm', lambda x:x.quantile(.75)), anos=('ano','size'),
        horas_com_chuva_pct=('horas_com_chuva_pct','mean')).reset_index()
    extremos = frequencias_extremos(tabela, comum, anual, mensal)
    return dict(cobertura=anual.reset_index(), cobertura_mensal=mensal,
                auditoria=pd.DataFrame(auditorias), auditoria_anual=pd.concat(auditorias_anuais,ignore_index=True), ciclo=ciclo,
                ciclo_por_ano=por_ano_hora, extremos=extremos)


def frequencias_extremos(tabela, comum, anual, mensal):
    """Denominador = dias comuns válidos; rede, datas e limiares fixos."""
    saida = []
    minima_mensal = mensal.groupby('ano').cobertura_pct.min()
    for cobertura in [85,90,95]:
        anos = anual.index[anual.cobertura_pct.ge(cobertura) & minima_mensal.ge(80)]
        for id_, nome in REDE_HISTORICA.items():
            valores = tabela.loc[comum & tabela.index.year.isin(anos), id_]
            for limite in LIMITES_EXTREMOS:
                t = pd.DataFrame({'extremo':valores.ge(limite), 'ano':valores.index.year})
                g = t.groupby('ano').extremo.agg(dias_validos='size',dias_extremos='sum').reset_index()
                g['frequencia_pct'] = 100*g.dias_extremos/g.dias_validos
                g['estacao'],g['limite_mm'],g['cobertura_min_pct'] = nome,limite,cobertura
                saida.append(g)
    return pd.concat(saida,ignore_index=True)
