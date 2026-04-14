from sqlalchemy import select, Connection

from openrouteindex.config import STATIC_DIR
from openrouteindex.db.core import region, osm2pgsql_properties
from openrouteindex.views.base import BaseView
from openrouteindex.views.cycling import CyclingNationalRoutesView, CyclingRegionalAndLocalRoutesView, CyclingRoutesUnconnectedView, \
    CyclingUtilityRoutesView
from openrouteindex.views.debug import DebugRouteAsGeoJSONView, RouteDebugMapView, get_invalid_relations
from openrouteindex.views.other_routes import MTBRouteView, MTBRoutesUnconnectedView, HorseRouteView, \
    HorseRoutesUnconnectedView, RunningRouteView, RunningRoutesUnconnectedView, OtherRouteView
from openrouteindex.views.static import IndexView, TagInfoView, StaticView
from openrouteindex.views.walking import WalkingNationalRoutesView, WalkingRegionalRoutesView, \
    WalkingRoutesUnconnectedView


def build_environment(conn: Connection) -> tuple[list[BaseView], dict]:
    regions = conn.execute(select(region.c.id, region.c.name).order_by(region.c.name)).fetchall()
    import_timestamp = str(conn.scalar(select(osm2pgsql_properties.c.value)
                                       .where(osm2pgsql_properties.c.property == 'import_timestamp')))

    global_context = dict(
        timestamp=import_timestamp,
        regions=regions,
    )

    pages: list[BaseView] = [
        IndexView(),
        TagInfoView(),
        *[StaticView(path) for path in STATIC_DIR.iterdir()],

        # Wandelroutes
        WalkingNationalRoutesView(),
        *[WalkingRegionalRoutesView(code, name) for code, name in regions],
        WalkingRoutesUnconnectedView(),

        # Fietsroutes
        CyclingNationalRoutesView(),
        CyclingRegionalAndLocalRoutesView(),
        CyclingUtilityRoutesView(),
        CyclingRoutesUnconnectedView(),

        # Others
        MTBRouteView(),
        MTBRoutesUnconnectedView(),
        HorseRouteView(),
        HorseRoutesUnconnectedView(),
        RunningRouteView(),
        RunningRoutesUnconnectedView(),
        OtherRouteView(),

        # Route debugger
        RouteDebugMapView(),
        *[DebugRouteAsGeoJSONView(relation_id) for relation_id in get_invalid_relations(conn)],
    ]
    return pages, global_context
