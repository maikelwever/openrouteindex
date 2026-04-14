from openrouteindex.db import planet_osm_rels
from openrouteindex.db.queries import FILTER_NOT_NODE_NETWORK, FILTER_TYPES_ROUTES, FILTER_NETWORK_INTER_NATIONAL, \
    FILTER_NETWORK_REGIONAL_LOCAL
from openrouteindex.views.base import RoutesWithUnconnectedWaysBase, RelationTreeBase, RegionRelationTreeBase


FILTER_ROUTES_WALKING = planet_osm_rels.c.tags['route'].astext.in_(('foot', 'hiking', 'walking'))


class WalkingNationalRoutesView(RelationTreeBase):
    title = '(Inter)nationale wandelroutes'
    filename = 'wandelen_iwn_nwn.html'
    wheres = (FILTER_NETWORK_INTER_NATIONAL, FILTER_ROUTES_WALKING, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'hiking'


class WalkingRegionalRoutesView(RegionRelationTreeBase):
    title = 'Wandelroutes in {}'
    filename = 'wandelen_in_{}.html'
    wheres = (FILTER_NETWORK_REGIONAL_LOCAL, FILTER_ROUTES_WALKING, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'hiking'


class WalkingRoutesUnconnectedView(RoutesWithUnconnectedWaysBase):
    title = 'Wandelroutes met gaten'
    filename = 'gatendetectie_wandelen.html'
    wheres = (FILTER_TYPES_ROUTES, FILTER_ROUTES_WALKING, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'hiking'
