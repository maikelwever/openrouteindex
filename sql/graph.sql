CREATE INDEX IF NOT EXISTS planet_osm_rels_members_idx ON planet_osm_rels USING gin (members);
CREATE INDEX IF NOT EXISTS planet_osm_ways_id_idx ON planet_osm_ways(id);
CREATE INDEX IF NOT EXISTS planet_osm_nodes_id_idx ON planet_osm_nodes(id);
CREATE UNIQUE INDEX IF NOT EXISTS region_id_idx ON region(id);

BEGIN;
SET max_parallel_workers_per_gather = 8;

DROP TABLE IF EXISTS rels_region;
DROP TABLE IF EXISTS rels_geom;
DROP TABLE IF EXISTS rels_ways;


-- Table that contains a many-to-many style mapping between relations and ways.
CREATE TABLE rels_ways AS
    WITH RECURSIVE rel_members AS (
        SELECT
            r.id AS root_id,
            r.id AS rel_id,
            m.member AS member,
            ARRAY[r.id] AS path
        FROM planet_osm_rels r
        CROSS JOIN LATERAL jsonb_array_elements(r.members) AS m(member)

        UNION ALL

        SELECT
            rm.root_id as root_id,
            child.id AS rel_id,
            m.member,
            rm.path || child.id
        FROM rel_members rm
             JOIN planet_osm_rels child ON (rm.member->>'type') = 'R' AND (rm.member->>'ref')::bigint = child.id
        CROSS JOIN LATERAL jsonb_array_elements(child.members) AS m(member)
        WHERE NOT child.id = ANY(rm.path)
    )
    SELECT DISTINCT
        root_id AS rel_id,
        (member->>'ref')::bigint AS way_id
    FROM rel_members
    WHERE (member->>'type') = 'W';

CREATE INDEX ON rels_ways(rel_id);
CREATE INDEX ON rels_ways(way_id);

ALTER TABLE rels_ways ADD CONSTRAINT fk_rels_ways__rel_id FOREIGN KEY (rel_id) REFERENCES planet_osm_rels(id);

-- Table that contains the merged way geometry and the centroid of the relation's route.
CREATE TABLE rels_geom AS
    SELECT
        rw.rel_id AS id,
        ST_LineMerge(ST_Union(l.way)) AS geom,
        ST_PointOnSurface(ST_Union(l.way)) AS point
    FROM rels_ways rw
        LEFT JOIN planet_osm_line l ON osm_id = rw.way_id
    GROUP BY rw.rel_id;


CREATE INDEX ON rels_geom(id);
ALTER TABLE rels_geom ADD CONSTRAINT fk_rels_geom__id FOREIGN KEY (id) REFERENCES planet_osm_rels(id);

-- Table that calculates the region the relation is in.
CREATE TABLE rels_region AS
    SELECT
        r.id AS id,
        reg.id AS region_id
    FROM rels_geom r
        INNER JOIN region reg ON ST_Within(r.point, reg.geom);

CREATE INDEX ON rels_region(id);
CREATE INDEX ON rels_region(region_id);
ALTER TABLE rels_region ADD CONSTRAINT fk_rels_region__id FOREIGN KEY (id) REFERENCES planet_osm_rels(id);
ALTER TABLE rels_region ADD CONSTRAINT fk_rels_region__region_id FOREIGN KEY (region_id) REFERENCES region(id);

COMMIT;
