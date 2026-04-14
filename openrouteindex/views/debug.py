from geoalchemy2.functions import ST_AsGeoJSON, ST_Transform, ST_LineMerge
from sqlalchemy import select, func, literal, cast, JSON, case, Connection

from openrouteindex.db import planet_osm_rels, rels_validity, planet_osm_line, rels_ways
from openrouteindex.db.queries import generate_tree_cte, FILTER_TYPES_ROUTES, FILTER_NOT_NODE_NETWORK, \
    FILTER_ROUTES_RELEVANTS, noop
from openrouteindex.views.base import SimpleDatabaseView, BaseView


class DebugRouteAsGeoJSONView(SimpleDatabaseView):
    title = 'Debug route as GeoJSON'
    query = select(
        func.json_serialize(func.json_build_object(
            literal("type"), literal("FeatureCollection"),
            literal("features"), func.json_agg(
                func.json_build_object(
                    literal("type"), literal("Feature"),
                    literal("geometry"),
                    cast(ST_AsGeoJSON(ST_Transform(ST_LineMerge(planet_osm_line.c.way), 4326)), JSON),
                    literal("properties"), func.json_build_object(
                        literal("id"), rels_ways.c.way_id,
                        literal("stroke"), case(
                            (func.cardinality(func.array_positions(
                                rels_validity.c.unconnected_ways, rels_ways.c.way_id)) > 0, literal("red")),
                            else_=literal("lime"),
                        ),
                    ),
                )
            ),
        ))
    ).select_from(planet_osm_rels) \
        .join(rels_validity, rels_validity.c.id == planet_osm_rels.c.id) \
        .join(rels_ways, rels_ways.c.rel_id == planet_osm_rels.c.id) \
        .join(planet_osm_line, planet_osm_line.c.osm_id == rels_ways.c.way_id)

    def __init__(self, relation_id: int):
        self.relation_id = relation_id
        self.filename = f'debug_rel_{relation_id}.json'

    def get_query(self):
        query = super().get_query()
        return query.where(planet_osm_rels.c.id == self.relation_id)

    def render(self, conn: Connection, context):
        return conn.scalar(self.get_query())


class RouteDebugMapView(BaseView):
    title = 'Route debugger'
    filename = 'routedebugger.html'
    template_name = 'route_debug.html.j2'


def filter_routes_networks(query):
    return query.where(FILTER_TYPES_ROUTES, FILTER_ROUTES_RELEVANTS, FILTER_NOT_NODE_NETWORK)


def get_invalid_relations(conn: Connection):
    tree_cte = generate_tree_cte(filter_routes_networks, noop)
    q =  select(tree_cte.c.id).distinct() \
        .join(rels_validity, rels_validity.c.id == tree_cte.c.id, isouter=True) \
        .where(rels_validity.c.connected == False)

    return conn.scalars(q).fetchall()