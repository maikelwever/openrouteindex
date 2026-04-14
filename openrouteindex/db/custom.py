from sqlalchemy import Table

from openrouteindex.db.core import engine, metadata_obj


rels_ways = Table('rels_ways', metadata_obj, autoload_with=engine)
rels_geom = Table('rels_geom', metadata_obj, autoload_with=engine)
rels_region = Table('rels_region', metadata_obj, autoload_with=engine)
rels_validity = Table('rels_validity', metadata_obj, autoload_with=engine)
