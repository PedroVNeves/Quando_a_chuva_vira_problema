"""Baixa as bases de perfil dos bairros publicadas no Data.Rio / ArcGIS para dados/brutos/data_rio/.

Camadas de mapa são salvas como GeoParquet (EPSG:4326); arquivos (xlsx, pdf) são baixados como estão.

Uso: python scripts/baixar_data_rio.py
"""
from pathlib import Path
from urllib.request import urlretrieve

import geopandas as gpd

DESTINO = Path(__file__).resolve().parent.parent / "dados" / "brutos" / "data_rio"

CENSO = "https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Censo/Limites_administrativos_Censo_2022/MapServer"
IPS = "https://services1.arcgis.com/OlP4dGNtIcnD3RYf/arcgis/rest/services/IPSBairros/FeatureServer"
ITEM = "https://www.arcgis.com/sharing/rest/content/items/{}/data"

CAMADAS = {
    "censo2022_ap.parquet": f"{CENSO}/0",
    "censo2022_ra.parquet": f"{CENSO}/1",
    "censo2022_bairros.parquet": f"{CENSO}/2",
    "ips2022_bairros.parquet": f"{IPS}/0",
}
ARQUIVOS = {
    "IPSBairros-DataRio.xlsx": ITEM.format("97a1d3ba9c4f4f0c967cbb5cc8738ca7"),
    "IPSBairros2022_relatorio.pdf": ITEM.format("0431a6811e834acf988d0bffc6def65f"),
}

DESTINO.mkdir(parents=True, exist_ok=True)

for nome, camada in CAMADAS.items():
    # Todas as camadas têm menos registros que o limite por consulta do servidor (2000)
    gdf = gpd.read_file(f"{camada}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson")
    gdf.to_parquet(DESTINO / nome)
    print(f"ok: {nome} ({len(gdf)} linhas)", flush=True)

for nome, url in ARQUIVOS.items():
    urlretrieve(url, DESTINO / nome)
    print(f"ok: {nome}", flush=True)
