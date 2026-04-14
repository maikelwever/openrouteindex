-- Current tables from our project
DROP TABLE IF EXISTS rels_validity;
DROP TABLE IF EXISTS rels_region;
DROP TABLE IF EXISTS rels_geom;
DROP TABLE IF EXISTS rels_ways;

-- Tables from Osm2pgsql
DROP TABLE IF EXISTS planet_osm_roads;
DROP TABLE IF EXISTS planet_osm_polygon;
DROP TABLE IF EXISTS planet_osm_line;
DROP TABLE IF EXISTS planet_osm_point;
DROP TABLE IF EXISTS planet_osm_rels;
DROP TABLE IF EXISTS planet_osm_nodes;
DROP TABLE IF EXISTS planet_osm_ways;
DROP TABLE IF EXISTS planet_osm_users;
DROP TABLE IF EXISTS osm2pgsql_properties;

-- Table we use to track which Geofabrik dump has been imported
DROP TABLE IF EXISTS import_state;
