from sqlalchemy import func, select, cast, literal, BigInteger, exists, TEXT
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.sql.expression import any_

from openrouteindex.constants import RELEVANT_ROUTE_VALUES, RELEVANT_TYPE_VALUES, RELEVANT_NODE_NETWORK_VALUES, \
    REGIONAL_AND_LOCAL_NETWORKS, INTER_AND_NATIONAL_NETWORKS
from openrouteindex.db import planet_osm_rels


FILTER_TYPE_ROUTE = planet_osm_rels.c.tags['type'].astext == 'route'
FILTER_TYPE_SUPERROUTE = planet_osm_rels.c.tags['type'].astext == 'superroute'
FILTER_TYPE_SUPERROUTE_OR_NETWORK = planet_osm_rels.c.tags['type'].astext.in_(('superroute', 'network'))

FILTER_TYPES_ROUTES = planet_osm_rels.c.tags['type'].astext.in_(RELEVANT_TYPE_VALUES)
FILTER_ROUTES_RELEVANTS = planet_osm_rels.c.tags['route'].astext.in_(RELEVANT_ROUTE_VALUES)
FILTER_NOT_NODE_NETWORK = func.coalesce(planet_osm_rels.c.tags['network:type'].astext, '').not_in(RELEVANT_NODE_NETWORK_VALUES)

FILTER_NETWORK_REGIONAL_LOCAL = planet_osm_rels.c.tags['network'].astext.in_(REGIONAL_AND_LOCAL_NETWORKS)
FILTER_NETWORK_INTER_NATIONAL = planet_osm_rels.c.tags['network'].astext.in_(INTER_AND_NATIONAL_NETWORKS)


def generate_tree_cte(transform_base=None, transform_recursive=None):
    p = planet_osm_rels.alias('p')
    m = func.jsonb_array_elements(p.c.members).table_valued('value')

    base = select(
        planet_osm_rels.c.id.label('id'),
        planet_osm_rels.c.id.label('root_id'),
        literal(1).label('depth'),
        array([planet_osm_rels.c.id]).label('path'),
        array([
            func.coalesce(planet_osm_rels.c.tags['name'].astext, planet_osm_rels.c.tags['ref'].astext)
            + literal('-')
            + cast(planet_osm_rels.c.id, TEXT)
        ]).label('sort_path'),
    ).where(
        ~exists(
            select(literal(1))
            .select_from(p.join(m, literal(True)))
            .where(
                (cast(m.c.value, JSONB)['type'].astext == 'R') &
                (cast(m.c.value, JSONB)['ref'].astext.cast(BigInteger) == planet_osm_rels.c.id)
            )
        )
    )

    if transform_base:
        base = transform_base(base)

    rel_tree = base.cte(name='rel_tree', recursive=True)
    parent = rel_tree.alias('parent')
    r = planet_osm_rels.alias('r')
    m2 = func.jsonb_array_elements(r.c.members).table_valued('value')

    child = planet_osm_rels.alias('child')
    recursive = select(
        child.c.id.label('id'),
        parent.c.root_id,
        (parent.c.depth + 1).label('depth'),
        (parent.c.path.op('||')(child.c.id)).label('path'),
        (parent.c.sort_path.op('||')(
            func.coalesce(child.c.tags['name'].astext, child.c.tags['ref'].astext)
            + literal('-') + cast(child.c.id, TEXT)
        )).label('sort_path'),
    ).select_from(
        parent
        .join(r, r.c.id == parent.c.id)
        .join(m2, literal(True), isouter=False)
        .join(child, (cast(m2.c.value, JSONB)['type'].astext == 'R') &
              (cast(m2.c.value, JSONB)['ref'].astext.cast(BigInteger) == child.c.id))
    ).where(~(child.c.id == any_(parent.c.path)))

    if transform_recursive:
        recursive = transform_recursive(recursive)

    return rel_tree.union_all(recursive)


def noop(query):
    return query
