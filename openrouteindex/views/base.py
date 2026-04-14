from sqlalchemy import select, literal, Connection

from openrouteindex.db import planet_osm_rels, rels_validity, rels_region, region, rel_name_tag
from openrouteindex.db.queries import generate_tree_cte
from openrouteindex.jinja import templates


class BaseView:
    def get_filename(self) -> str:
        if hasattr(self, 'filename'):
            return self.filename
        raise NotImplementedError

    def get_title(self) -> str:
        if hasattr(self, 'title'):
            return self.title
        raise NotImplementedError

    def get_template_name(self) -> str:
        if hasattr(self, 'template_name'):
            return self.template_name
        raise NotImplementedError

    def get_context(self, conn: Connection, context=None) -> dict:
        if context is None:
            ctx = {}
        else:
            ctx = context.copy()

        ctx['title'] = self.get_title()
        ctx['wmt_subdomain'] = getattr(self, 'wmt_subdomain', None)
        return ctx

    def render(self, conn: Connection, global_context: dict) -> str | bytes:
        context = self.get_context(conn, global_context)
        return templates.get_template(self.get_template_name()).render(**context)


class SimpleDatabaseView(BaseView):
    def get_query(self):
        if hasattr(self, 'query'):
            return self.query
        raise NotImplementedError

    def get_data(self, conn: Connection):
        return conn.execute(self.get_query()).fetchall()

    def get_context(self, conn: Connection, context=None):
        context = super().get_context(conn, context)
        data = self.get_data(conn)
        return dict(data=data, **context)


class RelationTreeBase(SimpleDatabaseView):
    template_name = 'tree.html.j2'
    with_regions = False

    def get_wheres(self):
        return getattr(self, 'wheres', [])

    def transform_base(self, query):
        wheres = self.get_wheres()
        if wheres:
            for where in wheres:
                query = query.where(where)
        return query

    def transform_child(self, query):
        return query

    def get_selects(self):
        selects = getattr(self, 'selects', [])
        if self.with_regions:
            selects.append(rels_region.c.region_id.label('region_code'))
        return selects

    def get_context(self, conn: Connection, context=None):
        context = super().get_context(conn, context)
        context['include_region_code'] = self.with_regions
        context['wheres'] = self.get_wheres()
        return context

    def get_query(self):
        tree_cte = generate_tree_cte(self.transform_base, self.transform_child)
        query = select(
            tree_cte.c.id.label('id'),
            tree_cte.c.depth,
            planet_osm_rels.c.tags,
            planet_osm_rels.c.created,
            planet_osm_rels.c.version,
            rels_validity.c.connected.label('all_ways_connect'),
            *self.get_selects(),
        ).join(planet_osm_rels, planet_osm_rels.c.id == tree_cte.c.id) \
            .join(rels_validity, rels_validity.c.id == tree_cte.c.id, isouter=True) \
            .order_by(tree_cte.c.sort_path)

        if self.with_regions:
            query = query.join(rels_region, rels_region.c.id == planet_osm_rels.c.id)

        return query


class RegionRelationTreeBase(RelationTreeBase):
    def __init__(self, region_code: str, region_name: str):
        self.region_code = region_code
        self.region_name = region_name

    def get_title(self):
        return self.title.format(self.region_name)

    def get_filename(self):
        return self.filename.format(self.region_name.lower())

    def transform_base(self, query):
        return super().transform_base(query) \
            .join(rels_region, planet_osm_rels.c.id == rels_region.c.id) \
            .join(region, rels_region.c.region_id == region.c.id) \
            .where(region.c.id == self.region_code)


class RoutesWithUnconnectedWaysBase(SimpleDatabaseView):
    template_name = 'tree.html.j2'

    def get_query(self):
        query = select(
            planet_osm_rels.c.id,
            literal(1).label('depth'),
            planet_osm_rels.c.tags,
            planet_osm_rels.c.created,
            planet_osm_rels.c.version,
            rels_validity.c.connected.label('all_ways_connect'),
            rels_region.c.region_id.label('region_code')
        ).join(rels_validity, isouter=True) \
            .join(rels_region) \
            .where(rels_validity.c.connected == False) \
            .order_by(rel_name_tag)

        for where in self.get_wheres():
            query = query.where(where)

        return query

    def get_wheres(self):
        return getattr(self, 'wheres', [])

    def get_context(self, conn: Connection, context=None):
        context = super().get_context(conn, context)
        context['include_region_code'] = True
        context['wheres'] = self.get_wheres()
        return context
