import json
from pathlib import Path

from sqlalchemy import Connection

from openrouteindex.views.base import BaseView


class IndexView(BaseView):
    title = 'Welkom op de OpenRouteIndex'
    filename = 'index.html'
    template_name = 'index.html.j2'


class StaticView(BaseView):
    def __init__(self, path: Path):
        self.path = path

    def get_filename(self):
        return self.path.name

    def render(self, conn: Connection, global_context: dict):
        with open(self.path, 'rb') as f:
            return f.read()


class TagInfoView(BaseView):
    filename = 'taginfo.json'

    def render(self, conn: Connection, global_context: dict):
        return json.dumps({
            "data_format": 1,
            "data_url": "https://openrouteindex.nl/taginfo.json",
            "data_updated": "20260407T200000Z",
            "project": {
                "name": "OpenRouteIndex",
                "description": "Index of routes for Dutch mappers to use as an overview. With broken route detector.",
                "project_url": "https://openrouteindex.nl",
                "contact_name": "Maikel Wever",
                "contact_email": "maikelwever@gmail.com"
            },
            'tags': [
                {
                    'key': 'type',
                    'value': 'route',
                    'description': 'Used to identify routes.',
                },
                {
                    'key': 'type',
                    'value': 'superroute',
                    'description': 'Used to group superroutes separately.',
                },
                {
                    'key': 'type',
                    'value': 'network',
                    'description': 'Used to group routes into subcategories to make for smaller pages',
                },
                {
                    'key': 'network:type',
                    'value': 'node_network',
                    'description': 'Used to discard routes that are part of node networks during initial sorting.',
                },
                {
                    'key': 'network:type',
                    'value': 'basic_network',
                    'description': 'Used to discard routes that are part of node networks during initial sorting.',
                },
                {
                    'key': 'bicycle:type',
                    'value': 'utility',
                    'description': 'Used to separate utility routes from recreational routes.',
                },
                {
                    'key': 'route',
                    'value': 'foot',
                    'description': 'Used to group walking routes.',
                },
                {
                    'key': 'route',
                    'value': 'hiking',
                    'description': 'Used to group walking routes (hiking is not separate because in the Netherlands, we have no significant mountains).',
                },
                {
                    'key': 'route',
                    'value': 'walking',
                    'description': 'Used to group walking routes.',
                },
                {
                    'key': 'route',
                    'value': 'bicycle',
                    'description': 'Used to group cycle routes.',
                },
                {
                    'key': 'route',
                    'value': 'cycling',
                    'description': 'Capture erroneously tagged cycle routes.',
                },
                {
                    'key': 'route',
                    'value': 'fitness_trail',
                    'description': 'Used to group fitness trails.',
                },
                {
                    'key': 'route',
                    'value': 'nordic_walking',
                    'description': 'Used to group nordic walking routes.',
                },
                {
                    'key': 'route',
                    'value': 'inline_skates',
                    'description': 'Used to group inline skating routes.',
                },
                {
                    'key': 'route',
                    'value': 'running',
                    'description': 'Used to group running (exercise) routes.',
                },
                {
                    'key': 'route',
                    'value': 'wheelchair',
                    'description': 'Used to group routes.',
                },
                {
                    'key': 'route',
                    'value': 'mtb',
                    'description': 'Used to group MTB routes.',
                },
                {
                    'key': 'route',
                    'value': 'horse',
                    'description': 'Used to group horse riding routes.',
                },
            ]
        })
