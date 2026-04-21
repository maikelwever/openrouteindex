#!/usr/bin/env python3

import decimal
import ftplib
import json
import os.path
import sys
import time

from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import Popen
from urllib.parse import urlparse, urlsplit

import osmium
import psycopg
import requests

from tqdm import tqdm
from psycopg.rows import scalar_row
from psycopg.types.json import Jsonb

from openrouteindex import config
from openrouteindex.constants import RELEVANT_ROUTE_VALUES, RELEVANT_TYPE_VALUES, RELEVANT_NODE_NETWORK_VALUES

SCRIPT_START_TIME = datetime.now()


def qdlog(msg: str):
    """
    A Quick and Dirty Logging function that prefixes every message with the time passed since the script started.
    """
    since_start = datetime.now() - SCRIPT_START_TIME

    hours, remainder = divmod(since_start.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    hours, minutes, seconds = int(hours), int(minutes), int(seconds)

    print(f'[{hours:02d}:{minutes:02d}:{seconds:02d}] {msg}')


def _get_current_db_set():
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS import_state (filename TEXT)')
            return cur.execute('SELECT filename FROM import_state LIMIT 1').fetchone()


def _set_current_db_set(filename):
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS import_state (filename TEXT)')
            cur.execute('DELETE FROM import_state')
            cur.execute('INSERT INTO import_state (filename) VALUES (%s)', (filename,))


def download_latest_set() -> Path | None:
    r = requests.head('https://download.geofabrik.de/europe/netherlands-latest.osm.pbf', allow_redirects=True)
    remote_filename = os.path.basename(urlparse(r.url).path)

    current_filename = _get_current_db_set()
    if current_filename == remote_filename:
        qdlog(' > Latest dataset already imported into database')
        return None

    geofabrik_dir = config.GEO_DIR
    geofabrik_dir.mkdir(exist_ok=True)
    local_filename = geofabrik_dir / remote_filename

    if not local_filename.exists():
        qdlog(' > Latest dataset not on disk, downloading...')
        for file in geofabrik_dir.iterdir():
            if file.is_file():
                file.unlink()

        r = requests.get(r.url, stream=True)
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        block_size = 10 * 1024 * 1024

        try:
            with tqdm(total=total_size, unit="B", unit_scale=True) as progress_bar:
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=block_size):
                        progress_bar.update(len(chunk))
                        f.write(chunk)

        except:
            try:
                local_filename.unlink()
            except:
                pass

            raise

    return local_filename


def tag_multivalue_filter(key, *values):
    return osmium.filter.TagFilter(*((key, v) for v in values))


def reduce_dataset(local_filename: Path) -> Path:
    new_filename = local_filename.parent / f'reduced-{local_filename.name}'
    if new_filename.exists():
        return new_filename

    qdlog(' > Reducing dataset size...')
    fp = osmium.FileProcessor(local_filename) \
        .with_filter(osmium.filter.EntityFilter(osmium.osm.RELATION)) \
        .with_filter(tag_multivalue_filter('type', *RELEVANT_TYPE_VALUES)) \
        .with_filter(tag_multivalue_filter('route', *RELEVANT_ROUTE_VALUES))

    with osmium.BackReferenceWriter(new_filename, local_filename,
                                    relation_depth=20, remove_tags=False, overwrite=True) as w:
        for obj in fp:
            w.add(obj)

    return new_filename


def call_osm2pgsql(local_filename: Path):
    qdlog(' > Wiping database...')
    wipe_file = config.SQL_DIR / 'wipe.sql'
    proc = Popen(['psql', config.DATABASE_URL, '-f', str(wipe_file)])
    proc.communicate()

    qdlog(f' > Importing {local_filename.name} into database...')

    osm2pgsql_config = config.PROJECT_DIR / 'osm2pgsql.lua'
    proc = Popen(['osm2pgsql', '-d', config.DATABASE_URL, '-c', '-s', str(local_filename),
                  '-O', 'flex', '-S', str(osm2pgsql_config), '--extra-attributes'])
    proc.communicate()
    if proc.returncode != 0:
        qdlog(' ! osm2pgsql failed')
        sys.exit(proc.returncode)


def fetch_from_overpass(relation_ids):
    max_retries = 60
    retries = 0

    query_head = '[out:json]; (\n'
    query_foot = '\n); out body; >; out skel qt;\n'
    query_rels = [f'relation({id});' for id in relation_ids]
    query = query_head + '\n'.join(query_rels) + query_foot

    qdlog(f' > Fetching {len(relation_ids)} relations from Overpass API...')

    while retries < max_retries:
        try:
            response = requests.post(
                'https://overpass-api.de/api/interpreter',
                data={'data': query},
                headers={'User-Agent': 'OpenRouteIndex (https://github.com/maikelwever/openrouteindex)'}
            )
            response.raise_for_status()
            return response.json(parse_float=decimal.Decimal)
        except requests.exceptions.RequestException as e:
            qdlog(f'\t ! failed to fetch from Overpass API, try {retries} of {max_retries}: {e}')
            retries += 1
            time.sleep(3)

    qdlog(' ! Overpass API failed to fetch data, giving up.')
    sys.exit(1)


def fetch_missing_data():
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            relations_missing_ways = cur.execute('''
                SELECT DISTINCT r.id
                FROM planet_osm_rels r
                    CROSS JOIN LATERAL jsonb_array_elements(r.members) AS m(elem)
                    LEFT JOIN planet_osm_line l ON osm_id = ( m.elem->>'ref')::bigint
                WHERE m.elem->>'type' = 'W'
                    AND l IS NULL
                    AND r.tags->>'type' = ANY(%s)
                    AND r.tags->>'route' = ANY(%s)
                    AND COALESCE(r.tags->>'network:type', '') != ANY(%s)
            ''', (list(RELEVANT_TYPE_VALUES), list(RELEVANT_ROUTE_VALUES), list(RELEVANT_NODE_NETWORK_VALUES))).fetchall()

            missing_relations = cur.execute('''
                SELECT DISTINCT(m.elem->>'ref')::bigint
                FROM planet_osm_rels r
                    CROSS JOIN LATERAL jsonb_array_elements(r.members) AS m(elem)
                    LEFT JOIN planet_osm_rels rl ON rl.id = (m.elem->>'ref')::bigint
                WHERE m.elem->>'type' = 'R'
                  AND rl IS NULL
                  AND r.tags->>'type' = ANY(%s)
                  AND r.tags->>'route' = ANY(%s)
                  AND COALESCE(r.tags->>'network:type', '') != ANY(%s)
            ''', (list(RELEVANT_TYPE_VALUES), list(RELEVANT_ROUTE_VALUES), list(RELEVANT_NODE_NETWORK_VALUES))).fetchall()

            qdlog(f' > Found {len(relations_missing_ways)} relations missing ways, {len(missing_relations)} relations missing relations')
            all_missing = set(relations_missing_ways) | set(missing_relations)

        return fetch_from_overpass(all_missing)


def add_missing_data():
    missing_data = fetch_missing_data()
    missing_data = missing_data.get('elements', [])

    relations = dict((i['id'], i) for i in missing_data if i.get('type', '') == 'relation')
    ways = dict((i['id'], i) for i in missing_data if i.get('type', '') == 'way')
    nodes = dict((i['id'], i) for i in missing_data if i.get('type', '') == 'node')
    way_ids = list(ways.keys())

    qdlog(' > Checking for pre-existing data that is also in the missing data set')
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            already_existing = cur.execute('select osm_id from planet_osm_line where osm_id = any(%s)', (way_ids,)).fetchall()

    rel_info_list = [(i['id'], Jsonb(i['members']), Jsonb(i['tags'])) for i in relations.values()]
    way_info_list = []
    line_info_list = []
    for way in ways.values():
        if way['id'] in already_existing:
            continue

        way_info_list.append((
            way['id'], way.get('nodes', []),
        ))
        coords = []
        for node_id in way.get('nodes', []):
            node = nodes[node_id]
            coords.append(f"{node['lon']} {node['lat']}")

        line_info_list.append((
            way['id'], 'LINESTRING (' + ', '.join(coords) + ')',
        ))

    qdlog(f' > Inserting (up to) {len(rel_info_list)} relations, {len(way_info_list)} ways, {len(line_info_list)} lines into database...')
    way_query = "INSERT INTO planet_osm_ways (id, created, version, nodes, tags) VALUES (%s, NOW(), 1, %s, '{}') ON CONFLICT DO NOTHING"
    line_query = "INSERT INTO planet_osm_line (osm_id, way) VALUES (%s, ST_Transform(ST_GeomFromText(%s, 4326), 3857))"
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            cur.executemany(way_query, way_info_list)
            cur.executemany(line_query, line_info_list)

    relation_query = "INSERT INTO planet_osm_rels (id, created, version, members, tags) VALUES (%s, NOW(), 1, %s, %s) ON CONFLICT DO NOTHING" ## ON CONFLICT (id) DO UPDATE SET members = EXCLUDED.members, tags = EXCLUDED.tags"
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor(row_factory=scalar_row) as cur:
            cur.executemany(relation_query, rel_info_list)

    qdlog(' > Inserted missing data into database.')


def process_database():
    qdlog(' > Running database processing SQL')
    graph_sql = config.SQL_DIR / 'graph.sql'
    proc = Popen(['psql', config.DATABASE_URL, '-f', str(graph_sql)])
    proc.communicate()
    if proc.returncode != 0:
        qdlog(' ! running graph.sql failed')
        sys.exit(proc.returncode)


def upload_to_ftp():
    if not config.FTP_URL:
        qdlog(' ! Upload to FTP enabled, but connection info not set !')
        return

    qdlog(' > Uploading to FTP')
    ftp_info = urlsplit(config.FTP_URL)

    ftp_path = ftp_info.path.lstrip('/')
    ftp_host = ftp_info.hostname
    ftp_user = ftp_info.username
    ftp_password = ftp_info.password
    if ftp_info.scheme == 'ftps':
        ftp = ftplib.FTP_TLS
    else:
        ftp = ftplib.FTP

    local_files = set()
    with ftp(host=ftp_host, user=ftp_user, passwd=ftp_password) as conn:
        conn.cwd(ftp_path)
        remote_files = set(name for name, _ in conn.mlsd() if name not in ['.', '..', '.DS_Store'])

        for file in config.OUTPUT_DIR.iterdir():
            if file.is_file():
                local_files.add(file.name)
                with open(file, 'rb') as f:
                    print(f'Uploading file: {file.name}')
                    conn.storbinary(f'STOR {file.name}', f)

        files_to_remove = remote_files - local_files
        for file in files_to_remove:
            print(f'Deleting remote file: {file}')
            conn.delete(file)


def import_regions_if_required():
    try:
        with psycopg.connect(config.DATABASE_URL) as conn:
            with conn.cursor(row_factory=scalar_row) as cur:
                cur.execute('SELECT 1 FROM region').fetchone()
                return
    except psycopg.errors.UndefinedTable:
        pass

    qdlog(' > Region table not found, fetching and importing regions...')
    region_data_base_url = 'https://download.openplanetdata.com/boundaries/regions/{}/geojson/v2/{}-latest.boundary.geojson'
    regions = ['NL-DR', 'NL-FL', 'NL-FR', 'NL-GE', 'NL-GR', 'NL-LI', 'NL-NB', 'NL-NH', 'NL-OV', 'NL-UT', 'NL-ZE', 'NL-ZH']

    region_data = dict()
    for region in regions:
        r = requests.get(region_data_base_url.format(region, region))
        region_data[region] = r.json()['features'][0]

    with psycopg.connect(config.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS region (id TEXT PRIMARY KEY, name TEXT, geom GEOMETRY(Geometry, 3857))')

            for name, data in region_data.items():
                cur.execute(
                    'INSERT INTO region (id, name, geom) '
                    'VALUES (%s, %s, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), 3857))',
                    (name, data['properties']['name'], json.dumps(data['geometry']))
                )

    qdlog(' > Regions imported successfully.')


def do_update(with_upload_to_ftp: bool, force_processing: bool):
    import_regions_if_required()

    qdlog(' > Checking for updates')
    needs_processing = False
    new_dataset = download_latest_set()
    if new_dataset:
        reduced_dataset = reduce_dataset(new_dataset)
        if reduced_dataset:
            call_osm2pgsql(reduced_dataset)
            _set_current_db_set(new_dataset.name)
            needs_processing = True

    if needs_processing or force_processing:
        add_missing_data()
        process_database()

        qdlog(' > Running ways connection validation')
        from openrouteindex.route_validator import validate_ways_connections
        validate_ways_connections()

        qdlog(' > Generating HTML')
        output_dir = config.OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)
        for file in output_dir.iterdir():
            if file.is_file():
                file.unlink()

        from openrouteindex.generator import generate_html
        generate_html()

        if with_upload_to_ftp:
            upload_to_ftp()

        if config.HEALTHCHECK_URL:
            qdlog(' > Calling HealthCheck URL')
            try:
                requests.get(config.HEALTHCHECK_URL)
            except:
                pass


def update_loop(with_upload_to_ftp: bool):
    last_run = datetime.now() - timedelta(days=1)

    try:
        while True:
            now = datetime.now()
            since_last_run = now - last_run

            if since_last_run > timedelta(hours=6):
                global SCRIPT_START_TIME
                SCRIPT_START_TIME = now

                print(f"--- Time for a update run. Current wall time: {now.strftime('%H:%M:%S')}. ---")
                do_update(with_upload_to_ftp, False)
                last_run = now
                print(f"--- Update run done! Current wall time: {now.strftime('%H:%M:%S')}. ---")

            time.sleep(60)

    except KeyboardInterrupt:
        return


def main():
    parser = ArgumentParser()
    parser.add_argument('--loop', action='store_true',
                        help='Keep running the updater in a loop, updating once every 6 hours.')
    parser.add_argument('--process', action='store_true', help='Force post-processing.')
    parser.add_argument('--upload', action='store_true', help='Upload to FTP after generating pages.')
    args = parser.parse_args()

    force_processing = True if args.process else False
    with_upload_to_ftp = True if args.upload else False

    if args.loop:
        update_loop(with_upload_to_ftp)
    else:
        do_update(with_upload_to_ftp, force_processing)


if __name__ == "__main__":
    main()
