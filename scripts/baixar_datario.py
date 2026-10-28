"""Baixa todas as tabelas dos datasets do datario usados no projeto para dados/brutos/bigquery/.

Tabelas com coluna GEOGRAPHY são salvas como GeoParquet (EPSG:4326), as demais como Parquet.

Uso: python scripts/baixar_datario.py [ID_DO_PROJETO_GCP]
Na primeira execução, o pandas-gbq abre o navegador para login na conta Google.
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
from google.cloud import bigquery, bigquery_storage
from pandas_gbq import auth

PROJETO = sys.argv[1] if len(sys.argv) > 1 else "biblioteca-escolar-501619"
DATASETS = ["adm_cor_comando", "clima_pluviometro", "dados_mestres"]
DESTINO = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "bigquery"

creds, _ = auth.get_credentials(project_id=PROJETO)
client = bigquery.Client(project=PROJETO, credentials=creds)
storage = bigquery_storage.BigQueryReadClient(credentials=creds)


def baixar_tabela(sql, parcial):
    # Escreve em lotes para não carregar tabelas grandes inteiras na memória
    writer = None
    for lote in client.query(sql).result().to_arrow_iterable(bqstorage_client=storage):
        if writer is None:
            writer = pq.ParquetWriter(parcial, lote.schema)
        writer.write_batch(lote)
    if writer is not None:
        writer.close()


def baixar_geotabela(sql, parcial, colunas_geo):
    # GEOGRAPHY vem como WKB e vira geometria; a primeira coluna geográfica é a ativa
    df = client.query(sql).result().to_dataframe(bqstorage_client=storage)
    # DATE vem com o tipo "dbdate" do BigQuery, que só abre com o pacote db-dtypes; vira data comum do pandas
    for c in df.columns[df.dtypes.astype(str) == "dbdate"]:
        df[c] = pd.to_datetime(df[c])
    for c in colunas_geo:
        df[c] = gpd.GeoSeries.from_wkb(df[c], crs="EPSG:4326")
    gpd.GeoDataFrame(df, geometry=colunas_geo[0]).to_parquet(parcial)


for ds in DATASETS:
    (DESTINO / ds).mkdir(parents=True, exist_ok=True)
    for item in client.list_tables(f"datario.{ds}"):
        tabela = client.get_table(item.reference)
        arquivo = DESTINO / ds / f"{tabela.table_id}.parquet"
        if arquivo.exists():
            print(f"já existe, pulando: {arquivo.name}")
            continue

        colunas_geo = [c.name for c in tabela.schema if c.field_type == "GEOGRAPHY"]
        colunas = [
            f"ST_ASBINARY(`{c.name}`) AS `{c.name}`" if c.name in colunas_geo else f"`{c.name}`"
            for c in tabela.schema
        ]
        sql = f"SELECT {', '.join(colunas)} FROM `datario.{ds}.{tabela.table_id}`"
        print(f"baixando {ds}.{tabela.table_id} ({tabela.num_rows:,} linhas)...", flush=True)

        parcial = arquivo.with_suffix(".parquet.tmp")
        if colunas_geo:
            baixar_geotabela(sql, parcial, colunas_geo)
        else:
            baixar_tabela(sql, parcial)
        if parcial.exists():
            parcial.rename(arquivo)
        print(f"  ok: {arquivo.relative_to(DESTINO.parent.parent.parent)}", flush=True)
