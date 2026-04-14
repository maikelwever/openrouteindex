from sqlalchemy import Connection, select

from openrouteindex.db import planet_osm_rels, rels_validity, rels_region
from openrouteindex.db.queries import FILTER_NOT_NODE_NETWORK, generate_tree_cte, noop, FILTER_TYPE_ROUTE
from openrouteindex.views.base import RelationTreeBase, RoutesWithUnconnectedWaysBase, BaseView

FILTER_ROUTES_MTB = planet_osm_rels.c.tags['route'].astext == 'mtb'
FILTER_ROUTES_HORSE = planet_osm_rels.c.tags['route'].astext == 'horse'
FILTER_ROUTES_RUNNING = planet_osm_rels.c.tags['route'].astext == 'running'


class MTBRouteView(RelationTreeBase):
    title = 'Mountainbikeroutes'
    filename = 'mtb.html'
    wheres = (FILTER_ROUTES_MTB, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'mtb'
    with_regions = True


class MTBRoutesUnconnectedView(RoutesWithUnconnectedWaysBase):
    title = 'Mountainbikeroutes met gaten'
    filename = 'gatendetectie_mtb.html'
    wheres = (FILTER_ROUTES_MTB, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'mtb'


class HorseRouteView(RelationTreeBase):
    title = 'Ruiterroutes'
    filename = 'paardrijden.html'
    wheres = (FILTER_ROUTES_HORSE, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'riding'
    with_regions = True


class HorseRoutesUnconnectedView(RoutesWithUnconnectedWaysBase):
    title = 'Ruiterroutes met gaten'
    filename = 'gatendetectie_paardrijden.html'
    wheres = (FILTER_ROUTES_HORSE, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'riding'


class RunningRouteView(RelationTreeBase):
    title = 'Hardlooproutes'
    filename = 'hardlopen.html'
    wheres = (FILTER_ROUTES_RUNNING, FILTER_NOT_NODE_NETWORK)
    with_regions = True


class RunningRoutesUnconnectedView(RoutesWithUnconnectedWaysBase):
    title = 'Hardlooproutes met gaten'
    filename = 'gatendetectie_hardlopen.html'
    wheres = (FILTER_ROUTES_RUNNING, FILTER_NOT_NODE_NETWORK)


class OtherRouteView(BaseView):
    title = 'Overige routes'
    filename = 'overige.html'
    template_name = 'multitree.html.j2'
    route_type_map = {
        'fitness_trail': 'Trimbanen',
        'inline_skates': 'Inline-skateroutes',
        'nordic_walking': 'Nordic walking routes',
        'wheelchair': 'Rolstoelroutes'
    }

    def get_context(self, conn: Connection, context=None):
        context = super().get_context(conn, context)
        context['include_region_code'] = True

        context['others'] = dict()
        for key, name in self.route_type_map.items():
            where_filter = planet_osm_rels.c.tags['route'].astext == key
            data = self._run_query(conn, where_filter)
            context['others'][name] = data, (where_filter, FILTER_NOT_NODE_NETWORK)

        return context

    def _run_query(self, conn: Connection, where):
        def transform_base(q):
            return q.where(where).where(FILTER_NOT_NODE_NETWORK)

        tree_cte = generate_tree_cte(transform_base, noop)
        query = select(
            tree_cte.c.id.label('id'),
            tree_cte.c.depth,
            planet_osm_rels.c.tags,
            planet_osm_rels.c.created,
            planet_osm_rels.c.version,
            rels_validity.c.connected.label('all_ways_connect'),
            rels_region.c.region_id.label('region_code')
        ).join(planet_osm_rels, planet_osm_rels.c.id == tree_cte.c.id) \
            .join(rels_validity, rels_validity.c.id == tree_cte.c.id, isouter=True) \
            .join(rels_region, rels_region.c.id == planet_osm_rels.c.id) \
            .order_by(tree_cte.c.sort_path)

        return conn.execute(query).fetchall()
