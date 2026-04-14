from sqlalchemy import func

from openrouteindex.db import planet_osm_rels
from openrouteindex.db.queries import FILTER_NOT_NODE_NETWORK, FILTER_TYPES_ROUTES, FILTER_NETWORK_REGIONAL_LOCAL, \
    FILTER_NETWORK_INTER_NATIONAL
from openrouteindex.views.base import RoutesWithUnconnectedWaysBase, RelationTreeBase


FILTER_ROUTES_CYCLING = planet_osm_rels.c.tags['route'].astext.in_(('cycling', 'bicycle'))
FILTER_BICYCLE_TYPE_UTILITY = func.coalesce(planet_osm_rels.c.tags['bicycle:type'].astext, '') == 'utility'
FILTER_BICYCLE_TYPE_NOT_UTILITY = func.coalesce(planet_osm_rels.c.tags['bicycle:type'].astext, '') != 'utility'


class CyclingNationalRoutesView(RelationTreeBase):
    title = '(Inter)nationale fietsroutes'
    filename = 'fietsen_icn_ncn.html'
    wheres = (FILTER_NETWORK_INTER_NATIONAL, FILTER_ROUTES_CYCLING,
              FILTER_BICYCLE_TYPE_NOT_UTILITY, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'cycling'


class CyclingRegionalAndLocalRoutesView(RelationTreeBase):
    title = 'Regionale en lokale fietsroutes'
    filename = 'fietsen_rcn_lcn.html'
    wheres = (FILTER_NETWORK_REGIONAL_LOCAL, FILTER_ROUTES_CYCLING,
              FILTER_BICYCLE_TYPE_NOT_UTILITY, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'cycling'
    with_regions = True


class CyclingUtilityRoutesView(RelationTreeBase):
    title = 'Fietsverkeersroutes'
    filename = 'fietsverkeersroutes.html'
    wheres = (FILTER_ROUTES_CYCLING, FILTER_BICYCLE_TYPE_UTILITY, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'cycling'
    with_regions = True


class CyclingRoutesUnconnectedView(RoutesWithUnconnectedWaysBase):
    title = 'Fietsroutes met gaten'
    filename = 'gatendetectie_fietsen.html'
    wheres = (FILTER_TYPES_ROUTES, FILTER_ROUTES_CYCLING, FILTER_NOT_NODE_NETWORK)
    wmt_subdomain = 'cycling'
