"""Extensões descritivas da proposta; entradas brutas permanecem intactas."""
from pathlib import Path
from datetime import date
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import geopandas as gpd
import pyarrow.dataset as ds
from scripts.analise_dados import FUSO, ler_estacao

FAIXAS_SOCIAIS = ['>10–20', '>20–30', '>30–50']
INDICADORES_SOCIAIS = {
    'ips_2022': 'IPS agregado',
    'densidade_2022': 'Densidade (Censo 2022)',
    'favelas_pct': 'Indicador de favelas (IPS)',
    'inadequacao_cadunico_pct': 'Domicílios inadequados (CadÚnico)',
}


def chave_nome(s):
    return s.astype('string').map(lambda v: ''.join(c for c in unicodedata.normalize('NFKD', v.casefold())
        if not unicodedata.combining(c)).strip() if pd.notna(v) else pd.NA)


def ler_indicadores_habitacao(arquivo):
    """Lê valores publicados e ficha técnica, sem editar a planilha original."""
    ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(arquivo) as z:
        strings = [''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        def linhas(caminho):
            resultado = {}
            for r in ET.fromstring(z.read(caminho)).findall('s:sheetData/s:row', ns):
                dados = {}
                for c in r.findall('s:c', ns):
                    v = c.find('s:v', ns)
                    valor = v.text if v is not None else ''
                    if c.attrib.get('t') == 's':
                        valor = strings[int(valor)]
                    dados[c.attrib['r'].rstrip('0123456789')] = valor
                resultado[int(r.attrib['r'])] = dados
            return resultado
        indicadores, ficha = None, None
        for caminho in z.namelist():
            if caminho.startswith('xl/worksheets/sheet') and caminho.endswith('.xml'):
                rows = linhas(caminho)
                if 'Favelas' in rows.get(7, {}).get('I', '') and 'CadÚnico' in rows.get(7, {}).get('J', ''):
                    indicadores = rows
                if 'Não Urbanizadas' in rows.get(33, {}).get('B', ''):
                    ficha = rows
        if indicadores is None or ficha is None:
            raise ValueError('Estrutura da planilha IPS mudou; conferir cabeçalhos e definições.')
        valores = []
        for i, r in indicadores.items():
            if i > 9 and r.get('A') and r.get('B') and 'I' in r and 'J' in r:
                valores.append({'nome_ips':r['A'], 'favelas_pct':r['I'],
                                'inadequacao_cadunico_pct':r['J']})
        t = pd.DataFrame(valores)
        for col in ['favelas_pct', 'inadequacao_cadunico_pct']:
            t[col] = pd.to_numeric(t[col], errors='coerce')
            if (~t[col].dropna().between(0, 1)).any():
                raise ValueError(f'Proporção fora de 0–1: {col}; revisar unidade.')
            t[col] *= 100
        metadados = pd.DataFrame([dict(indicador=col, unidade='percentual (valor original ×100)',
            titulo=ficha[r]['B'], definicao=ficha[r]['C'], fonte=ficha[r]['D'],
            referencia_publicada=ficha[r]['F']) for col, r in
            [('favelas_pct',33), ('inadequacao_cadunico_pct',34)]])
    return t, metadados


def associar_habitacao(social, indicadores):
    s, t = social.copy(), indicadores.copy()
    s['chave'], t['chave'] = chave_nome(s.nome), chave_nome(t.nome_ips)
    for x in [s,t]:
        if x.chave.isna().any() or x.chave.duplicated().any():
            raise ValueError('Nomes ausentes ou duplicados na associação da habitação.')
    return s.merge(t, on='chave', how='left', validate='one_to_one', indicator='vinculo_habitacao')


def padronizar_faixas(dados):
    """Peso fixo de 1/3 por faixa. Ausência de faixa não vira frequência zero."""
    g = dados.groupby(['id_bairro','faixa_fina'], observed=True).evento.agg(n='size', eventos='sum')
    n = g.n.unstack().reindex(columns=FAIXAS_SOCIAIS).fillna(0)
    y = g.eventos.unstack().reindex(columns=FAIXAS_SOCIAIS).fillna(0)
    taxas = y.div(n.replace(0,np.nan))
    resumo = pd.DataFrame({'dias':n.sum(axis=1), 'eventos':y.sum(axis=1),
        'menor_n_faixa':n.min(axis=1),
        'frequencia_padronizada_pct':100*taxas.mean(axis=1, skipna=False)})
    return resumo


def diagnosticar_suporte_chuva(painel):
    """Viabilidade das faixas, usando somente chuva, cobertura e distância."""
    p = painel.copy()
    p['ano'] = p.dia.dt.year
    saida = []
    for limites,minimo in [([10,20,30,40,50],5),([10,20,30,50],10),([10,20,30,50],5)]:
        conjuntos = []
        for ano in [2020,2021]:
            t = p.loc[p.ano.eq(ano)].copy()
            cobertura = t.groupby('id_bairro').elegivel.mean()
            t['faixa'] = pd.cut(t.total_mm,limites)
            t = t.loc[t.elegivel & t.distancia_km.le(5) & t.faixa.notna()]
            n = t.groupby(['id_bairro','faixa'],observed=False).size().unstack(fill_value=0)
            conjuntos.append(set(n.index[n.ge(minimo).all(axis=1) & (n.index.map(cobertura)>=.9)]))
        saida.append({'limites_mm':str(limites),'minimo_por_faixa_ano':minimo,
                      'bairros_2020':len(conjuntos[0]), 'bairros_2021':len(conjuntos[1]),
                      'coorte_comum':len(conjuntos[0]&conjuntos[1])})
    return pd.DataFrame(saida)


def comparar_territorio_social(painel, social, n_boot=400):
    """Padronização por bairro seguida das correlações com o perfil social."""
    taxas, auditoria = padronizar_territorio(painel, n_boot)
    taxas, correlacoes = correlacionar_social(taxas.drop(columns='nome', errors='ignore'), social)
    return taxas, correlacoes, auditoria


def padronizar_territorio(painel, n_boot=400):
    """Coorte comum entre anos por cenário; padronização direta descritiva."""
    p = painel.copy()
    if p.duplicated(['id_bairro','dia']).any():
        raise ValueError('Bairro-dia duplicado na análise territorial.')
    p['ano'] = p.dia.dt.year
    p['faixa_fina'] = pd.cut(p.total_mm, [10,20,30,50], labels=FAIXAS_SOCIAIS)
    p['evento'] = p.n_agua.gt(0).astype(int)
    p['semana'] = p.dia.dt.to_period('W-SUN').dt.start_time
    saidas, auditorias = [], []
    for cenario, distancia, cobertura in [('Principal',5,.9), ('Até 3 km',3,.9), ('Cobertura 95%',5,.95)]:
        cobertura_ano = p.groupby(['id_bairro','ano']).elegivel.mean()
        base = p.loc[p.elegivel & p.distancia_km.le(distancia) & p.faixa_fina.notna()].copy()
        ids_ano = []
        for ano in [2020,2021]:
            r = padronizar_faixas(base.loc[base.ano.eq(ano)])
            ids = r.index[r.menor_n_faixa.ge(5) & (r.index.map(cobertura_ano.xs(ano,level='ano')) >= cobertura)]
            ids_ano.append(set(ids))
        ids_comuns = sorted(ids_ano[0] & ids_ano[1])
        auditorias.append({'cenario':cenario, 'distancia_max_km':distancia,
            'cobertura_min_pct':100*cobertura, 'bairros_2020':len(ids_ano[0]),
            'bairros_2021':len(ids_ano[1]), 'coorte_comum':len(ids_comuns)})
        for periodo, anos in [('2020',[2020]),('2021',[2021]),('2020–2021',[2020,2021])]:
            t = base.loc[base.id_bairro.isin(ids_comuns) & base.ano.isin(anos)].copy()
            if t.empty:
                continue
            r = padronizar_faixas(t)
            ag = t.groupby(['semana','id_bairro','faixa_fina'],observed=True).evento.agg(['size','sum'])
            colunas = pd.MultiIndex.from_product([ids_comuns,FAIXAS_SOCIAIS],names=['id_bairro','faixa_fina'])
            semanas = pd.date_range(t.semana.min(),t.semana.max(),freq='7D')
            ns = ag['size'].unstack(['id_bairro','faixa_fina']).reindex(index=semanas,columns=colunas).fillna(0).to_numpy()
            ys = ag['sum'].unstack(['id_bairro','faixa_fina']).reindex(index=semanas,columns=colunas).fillna(0).to_numpy()
            rng = np.random.default_rng(2026)
            w = rng.multinomial(len(semanas),np.ones(len(semanas))/len(semanas),size=n_boot)
            den = w@ns
            amostras = np.divide(100*(w@ys),den,out=np.full(den.shape,np.nan),where=den>0)
            amostras = amostras.reshape(n_boot,len(ids_comuns),3).mean(axis=2)
            for i, id_ in enumerate(ids_comuns):
                boot = amostras[:,i]
                valido = np.isfinite(boot)
                r.loc[id_,'replicas_validas_pct'] = 100*valido.mean()
                r.loc[id_,'ic_inferior_pct'] = np.nan
                r.loc[id_,'ic_superior_pct'] = np.nan
                # Sem IC artificial quando não há variação ou faltam faixas em réplicas.
                if valido.mean() >= .9 and np.ptp(boot[valido]) > 0:
                    r.loc[id_,['ic_inferior_pct','ic_superior_pct']] = np.percentile(boot[valido],[2.5,97.5])
            r['cenario'],r['periodo'] = cenario,periodo
            r['datas_distintas'],r['estacoes_distintas'] = t.dia.nunique(),t.id_estacao.nunique()
            saidas.append(r.reset_index())
    taxas = pd.concat(saidas,ignore_index=True)
    if 'nome' in painel:
        nomes = painel.drop_duplicates('id_bairro').set_index('id_bairro').nome
        taxas.insert(1, 'nome', taxas.id_bairro.map(nomes))
    return taxas, pd.DataFrame(auditorias)


def correlacionar_social(taxas, social):
    """Correlação de postos entre a frequência padronizada e cada indicador social."""
    colunas = ['id_bairro',*INDICADORES_SOCIAIS] + (['nome'] if 'nome' not in taxas else [])
    taxas = taxas.merge(social[colunas],on='id_bairro',how='left',validate='many_to_one')
    correlacoes = []
    for (cenario,periodo),t in taxas.groupby(['cenario','periodo']):
        for indicador,rotulo in INDICADORES_SOCIAIS.items():
            v = t[[indicador,'frequencia_padronizada_pct']].dropna()
            rho = v.rank().corr().iloc[0,1] if len(v)>=10 else np.nan
            correlacoes.append({'cenario':cenario,'periodo':periodo,'indicador':indicador,
                'rotulo':rotulo,'bairros':len(v),'rho_descritivo':rho})
    return taxas, pd.DataFrame(correlacoes)


def analisar_duracoes(foco, painel, cor, orgaos):
    """Duração e primeira chegada registrada, apenas IDs globalmente únicos."""
    eventos = foco.loc[foco.dia.between('2020-01-01', '2021-12-31')].copy()
    eventos = eventos.merge(painel.loc[painel.elegivel, ['id_bairro', 'dia', 'total_mm']],
                            on=['id_bairro', 'dia'], validate='many_to_one')
    eventos['duracao_h'] = (eventos.data_fim-eventos.data_inicio).dt.total_seconds()/3600
    eventos['duracao_valida'] = eventos.duracao_h.ge(0) & eventos.data_fim.notna()
    eventos['faixa_chuva'] = pd.cut(eventos.total_mm, [-1e-9, 10, 30, np.inf],
                                   labels=['0–10', '>10–30', '>30'])
    # ID isolado não basta quando há reutilização em anos distintos.
    ambiguos = set(cor.loc[cor.id_evento.duplicated(keep=False), 'id_evento'])
    primeira = orgaos.groupby('id_evento').data_chegada.min().rename('primeira_chegada')
    eventos = eventos.join(primeira, on='id_evento', validate='many_to_one')
    eventos['chegada_h'] = (eventos.primeira_chegada-eventos.data_inicio).dt.total_seconds()/3600
    eventos['chegada_valida'] = (~eventos.id_evento.isin(ambiguos)
        & eventos.duracao_valida & eventos.chegada_h.ge(0)
        & eventos.primeira_chegada.le(eventos.data_fim))
    auditoria = pd.Series({
        'Eventos em bairro-dias elegíveis': len(eventos),
        'Sem fim': int(eventos.data_fim.isna().sum()),
        'Fim anterior ao início': int(eventos.duracao_h.lt(0).sum()),
        'Durações válidas': int(eventos.duracao_valida.sum()),
        'IDs reutilizados (excluídos da chegada)': int(eventos.id_evento.isin(ambiguos).sum()),
        'Sem chegada registrada': int(eventos.primeira_chegada.isna().sum()),
        'Chegada anterior ao início': int(eventos.chegada_h.lt(0).sum()),
        'Chegada posterior ao fim': int(eventos.primeira_chegada.gt(eventos.data_fim).sum()),
        'Chegadas válidas': int(eventos.chegada_valida.sum()),
    }, name='Eventos')
    partes = []
    for medida, validade in [('duracao_h', 'duracao_valida'), ('chegada_h', 'chegada_valida')]:
        resumo = eventos.groupby(['grupo', 'faixa_chuva'], observed=True).agg(
            eventos=('id_evento', 'size'), datas=('dia', 'nunique'))
        validos = eventos.loc[eventos[validade]]
        g = validos.groupby(['grupo', 'faixa_chuva'], observed=True)[medida]
        resumo = resumo.join(g.agg(n='size', mediana='median'), how='left')
        resumo = resumo.join(g.quantile([.25, .75]).unstack().rename(columns={.25:'p25', .75:'p75'}))
        resumo['n'] = resumo.n.fillna(0).astype(int)
        resumo['disponibilidade_pct'] = 100*resumo.n/resumo.eventos
        resumo['medida'] = medida
        partes.append(resumo.reset_index())
    tipos = eventos.groupby(['id_pop', 'pop_titulo', 'faixa_chuva'], observed=True).size().rename('registros').reset_index()
    return eventos, pd.concat(partes, ignore_index=True), auditoria, tipos


def perfil_social(bairros, mapa, painel, data_rio):
    """Associação por nomes normalizados únicos; sem aproximação textual."""
    def chave(s):
        return s.astype('string').map(lambda v: ''.join(c for c in unicodedata.normalize('NFKD', v.casefold())
            if not unicodedata.combining(c)).strip() if pd.notna(v) else pd.NA)
    b = bairros[['id_bairro', 'nome', 'geometry']].copy()
    b['chave'] = chave(b.nome)
    b['area_km2'] = b.to_crs('EPSG:31983').geometry.area/1e6
    ips = gpd.read_parquet(Path(data_rio)/'ips2022_bairros.parquet')
    censo = gpd.read_parquet(Path(data_rio)/'censo2022_bairros.parquet')
    ips['chave'], censo['chave'] = chave(ips.bairrostr), chave(censo.nome)
    for t in [b, ips, censo]:
        if t.chave.isna().any() or t.chave.duplicated().any():
            raise ValueError('Chaves sociais ausentes ou ambíguas; revisar associação.')
    b = b.drop(columns='geometry').merge(ips[['chave', 'ips_2022']], on='chave', how='left', validate='one_to_one')
    b = b.merge(censo[['chave', 'Total_de_pessoas_2022']], on='chave', how='left', validate='one_to_one')
    b['densidade_2022'] = b.Total_de_pessoas_2022/b.area_km2
    cobertura = painel.groupby('id_bairro').elegivel.mean()
    base = painel.loc[painel.elegivel & painel.total_mm.gt(30)].copy()
    base['evento'] = base.n_agua.gt(0)
    resumo = base.groupby('id_bairro').agg(dias=('evento', 'size'), eventos=('evento', 'sum'))
    resumo['frequencia_pct'] = 100*resumo.eventos/resumo.dias
    b = b.merge(resumo, on='id_bairro', how='left', validate='one_to_one')
    b = b.merge(mapa[['id_bairro', 'distancia_km', 'id_estacao']], on='id_bairro', validate='one_to_one')
    b['cobertura'] = b.id_bairro.map(cobertura)
    b['comparavel'] = b.dias.ge(20) & b.cobertura.ge(.9) & b.distancia_km.le(5)
    return b


JANELAS = ['acumulado_chuva_1_h', 'acumulado_chuva_4_h',
           'acumulado_chuva_24_h', 'acumulado_chuva_96_h']


def chuva_antes_blocos(bq, ids, referencia):
    """Blocos fixos de 6 h: exposição termina 15 min antes do início do bloco."""
    base = ds.dataset(Path(bq)/'clima_pluviometro/taxa_precipitacao_alertario.parquet')
    base = base.filter((ds.field('data_particao') >= date(2019, 12, 31))
                       & (ds.field('data_particao') <= date(2021, 12, 31)))
    grade = pd.date_range('2020-01-01', '2021-12-31 18:00', freq='6h')
    tabelas, auditoria = [], []
    for id_ in ids:
        print(f'Janelas anteriores: estação {id_}', flush=True)
        l, _ = ler_estacao(base, id_, referencia)
        t = l[JANELAS].reindex(grade-pd.Timedelta(minutes=15)).copy()
        t.index = grade
        # Acumulados negativos ou inversão entre janelas são inconsistentes.
        negativas = t.lt(0).any(axis=1)
        inversoes = (t[JANELAS].diff(axis=1).iloc[:, 1:] < -.05).any(axis=1)
        valida = t.notna().all(axis=1) & ~negativas & ~inversoes
        auditoria.append({'id_estacao':id_, 'blocos':len(t), 'comuns_validos':int(valida.sum()),
                          'negativos':int(negativas.sum()), 'inversoes':int(inversoes.sum())})
        t.loc[~valida, :] = np.nan
        t['bloco'], t['id_estacao'] = grade, id_
        tabelas.append(t.reset_index(drop=True))
    return pd.concat(tabelas, ignore_index=True), pd.DataFrame(auditoria)


def comparar_janelas(leituras, mapa, foco, cor, n_boot=600):
    """Frequência em blocos futuros fixos, com amostra comum às quatro janelas."""
    base = mapa[['id_bairro', 'id_estacao']].merge(leituras, on='id_estacao', validate='many_to_many')
    base = base.dropna(subset=JANELAS).copy()
    base['dia'] = base.bloco.dt.normalize()
    atividade = cor.groupby('dia').size()
    base = base.loc[base.dia.map(atividade).fillna(0).gt(0)].copy()
    eventos = foco.loc[foco.id_bairro.notna()].copy()
    eventos['bloco'] = eventos.inicio_local.dt.tz_localize(None).dt.floor('6h')
    for grupo, col in [('Acúmulo de água', 'n_agua'), ('Deslizamentos', 'n_deslizamento')]:
        cont = eventos.loc[eventos.grupo.eq(grupo)].groupby(['id_bairro','bloco']).size().rename(col)
        base = base.join(cont, on=['id_bairro','bloco'], validate='one_to_one')
        base[col] = base[col].fillna(0).astype(int)
    base['semana'] = base.dia.dt.to_period('W-SUN').dt.start_time
    semanas = pd.date_range(base.semana.min(), base.semana.max(), freq='7D')
    rng = np.random.default_rng(2026)
    pesos = rng.multinomial(len(semanas), np.ones(len(semanas))/len(semanas), size=n_boot)
    saidas, cortes = [], []
    categorias = ['Sem chuva', 'Positiva até P50', 'P50–P90', 'Acima de P90']
    for janela in JANELAS:
        # Cortes por estação-bloco: bairros que compartilham estação não multiplicam a distribuição.
        valores = base.drop_duplicates(['id_estacao','bloco'])[janela]
        q50, q90 = valores.loc[valores.gt(0)].quantile([.5, .9])
        if not 0 < q50 < q90:
            raise ValueError('Quantis não distintos; revisar as categorias de chuva.')
        cortes.append({'janela':janela, 'p50_positivo_mm':q50, 'p90_positivo_mm':q90,
                       'bairro_blocos':len(base), 'datas':base.dia.nunique()})
        base['classe'] = pd.cut(base[janela], [-1e-9,0,q50,q90,np.inf], labels=categorias)
        for grupo, col in [('Acúmulo de água','n_agua'), ('Deslizamentos','n_deslizamento')]:
            base['evento'] = base[col].gt(0).astype(int)
            resumo = base.groupby('classe', observed=False).agg(n=('evento','size'),
                eventos=('evento','sum'), datas=('dia','nunique'), semanas=('semana','nunique'))
            ag = base.groupby(['semana','classe'], observed=False).evento.agg(['size','sum'])
            ns = ag['size'].unstack().reindex(index=semanas, columns=categorias).fillna(0).to_numpy()
            ys = ag['sum'].unstack().reindex(index=semanas, columns=categorias).fillna(0).to_numpy()
            den = pesos@ns
            boot = np.divide(100*(pesos@ys), den, out=np.full(den.shape,np.nan), where=den>0)
            resumo['frequencia_pct'] = 100*resumo.eventos/resumo.n.replace(0,np.nan)
            resumo['ic_inferior_pct'], resumo['ic_superior_pct'] = np.nan,np.nan
            for i, cat in enumerate(categorias):
                r = resumo.loc[cat]
                if r.semanas >= 5 and 0 < r.eventos < r.n and np.isfinite(boot[:,i]).sum() >= .9*n_boot:
                    resumo.loc[cat,['ic_inferior_pct','ic_superior_pct']] = np.nanpercentile(boot[:,i],[2.5,97.5])
            resumo['janela'], resumo['grupo'] = janela, grupo
            saidas.append(resumo.reset_index())
    return pd.concat(saidas, ignore_index=True), pd.DataFrame(cortes)
