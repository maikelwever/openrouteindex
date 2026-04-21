import os
from pathlib import Path


def path_from_env(key, default):
    val = os.environ.get(key)
    if val:
        return Path(val)
    return default

def env_bool(key, default):
    val = os.environ.get(key)

    if val and val.strip().lower() in ('true', 't', '1', 'on', 'yes'):
        return True
    elif val and val.strip().lower() in ('false', 'f', '0', 'off', 'no'):
        return False

    return default


DEBUG = env_bool('DEBUG', False)
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql:///openrouteindex_0')
FTP_URL = os.environ.get('FTP_URL', '')
HEALTHCHECK_URL = os.environ.get('HEALTHCHECK_URL', '')

PROJECT_DIR = Path(__file__).absolute().parent.parent
SQL_DIR = PROJECT_DIR / 'sql'
STATIC_DIR = PROJECT_DIR / 'static'

OUTPUT_DIR = path_from_env('OUTPUT_DIR', PROJECT_DIR / 'out')
GEO_DIR = path_from_env('GEO_DIR', PROJECT_DIR / 'geofabrik')
