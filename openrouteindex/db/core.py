from openrouteindex import config

from sqlalchemy import create_engine, MetaData, Table, Engine

engine: Engine = create_engine(
    config.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://'),
    echo=config.DEBUG, plugins=["geoalchemy2"],
)
metadata_obj = MetaData()

osm2pgsql_properties = Table('osm2pgsql_properties', metadata_obj, autoload_with=engine)
region = Table('region', metadata_obj, autoload_with=engine)

planet_osm_line = Table('planet_osm_line', metadata_obj, autoload_with=engine)
planet_osm_nodes = Table('planet_osm_nodes', metadata_obj, autoload_with=engine)
planet_osm_rels = Table('planet_osm_rels', metadata_obj, autoload_with=engine)
planet_osm_ways = Table('planet_osm_ways', metadata_obj, autoload_with=engine)

rel_name_tag = planet_osm_rels.c.tags['name'].astext
