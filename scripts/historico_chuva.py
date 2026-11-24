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


def alinhar_grade(leituras):
    """Realinha à grade de 15 min as leituras com o desvio fixo da estação.

    Até 2010, cada estação histórica registra todas as leituras com o mesmo desvio
    em relação à grade (3 min 20 s no Vidigal, 20 s na Tijuca, 8 min em Campo
    Grande). Só esse desvio dominante é corrigido, sempre para o instante anterior
    da grade; outros desvios continuam fora da grade e não certificam horas.
    """
    idx = leituras.index
    desvio = idx - idx.floor('15min')
    fora = desvio != pd.Timedelta(0)
    if not fora.any():
        return leituras, 0
    dominante = pd.Series(desvio[fora]).mode().iloc[0]
    candidato = idx - dominante
    # Se o instante realinhado já existe na grade, a leitura fica onde estava.
    realinhar = (desvio == dominante) & ~candidato.isin(idx[~fora])
    saida = leituras.copy()
    saida.index = idx.where(~realinhar, candidato)
    if not saida.index.is_unique:
        raise ValueError('Realinhamento gerou instantes duplicados.')
    return saida, int(realinhar.sum())


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
        l, realinhadas = alinhar_grade(l)
        h, a = agregar_horas(l)
        horas.append(h.reset_index().assign(id_estacao=id_, estacao=nome))
        auditorias.append(dict(id_estacao=id_, estacao=nome, realinhadas=realinhadas, **a))
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
    return dict(cobertura=anual.reset_index(), cobertura_mensal=mensal, dias=tabela.reset_index(),
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


def comparar_periodos(dias, periodos=((1997, 2010), (2011, 2024)), limite=50.):
    """Cada estação sozinha: anos com cobertura própria e frequência de dias fortes por período.

    Sem exigir as três estações no mesmo dia, cada estação aproveita mais anos. Um
    ano entra com pelo menos 90% dos dias completos e 80% em cada mês, na estação.
    """
    linhas, anos_estacao = [], []
    t = dias.set_index('dia')
    for id_, nome in REDE_HISTORICA.items():
        v = t[id_]
        cob = pd.DataFrame({'valido': v.notna(), 'ano': v.index.year, 'mes': v.index.month})
        anual = cob.groupby('ano').valido.mean()
        mensal = cob.groupby(['ano', 'mes']).valido.mean().groupby('ano').min()
        anos = anual.index[anual.ge(.9) & mensal.ge(.8)]
        anos_estacao.append({'estacao': nome, 'anos': len(anos), 'lista': ', '.join(map(str, anos))})
        for inicio, fim in periodos:
            sel = v.loc[v.index.year.isin([a for a in anos if inicio <= a <= fim])].dropna()
            por_ano = sel.ge(limite).groupby(sel.index.year).mean()*100
            linhas.append({'estacao': nome, 'periodo': f'{inicio}–{fim}', 'anos': len(por_ano),
                           'dias_validos': len(sel), 'dias_fortes': int(sel.ge(limite).sum()),
                           'frequencia_pct': 100*sel.ge(limite).mean(),
                           'menor_ano_pct': por_ano.min(), 'maior_ano_pct': por_ano.max()})
    return pd.DataFrame(linhas), pd.DataFrame(anos_estacao)
