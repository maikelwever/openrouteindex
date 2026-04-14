#!/usr/bin/env python3
# This is like 1000000x faster than having postgres deal with this.
import multiprocessing as mp

import psycopg
from psycopg.rows import dict_row
from tqdm import tqdm

from openrouteindex import config


query = '''
SELECT
    w.rel_id,
    json_agg(json_build_object(
        'id', w.way_id,
        'nodes', p.nodes
    )) as data
FROM rels_ways w JOIN planet_osm_ways p ON p.id = w.way_id
GROUP BY w.rel_id;
'''


def check_network_connectivity(ways):
    parent = {}
    # Iterative find with path compression
    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while x != root:
            next_node = parent[x]
            parent[x] = root
            x = next_node
        return root

    # Union function
    def union(x, y):
        root_x = find(x)
        root_y = find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    # Initialize each node as its own parent
    for way in ways:
        for node in way["nodes"]:
            if node not in parent:
                parent[node] = node

    # Union all nodes in each way
    for way in ways:
        nodes = way["nodes"]
        for i in range(1, len(nodes)):
            union(nodes[0], nodes[i])

    # Determine main network root (the root of the first node in the first way)
    all_nodes = [node for way in ways for node in way["nodes"]]
    main_root = find(all_nodes[0])

    # Find unconnected ways
    unconnected_way_ids = []
    for way in ways:
        way_root = find(way["nodes"][0])
        if way_root != main_root:
            unconnected_way_ids.append(way["id"])

    # Network is fully connected if no unconnected ways
    is_connected = len(unconnected_way_ids) == 0
    return is_connected, unconnected_way_ids


insert_queue = mp.Queue()

def db_insert_worker():
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            with cur.copy("COPY rels_validity (id, connected, unconnected_ways) FROM STDIN") as copy:
                while True:
                    data = insert_queue.get()
                    if data is None:
                        return

                    copy.write_row(data)


def worker(queue):
    while True:
        dataset = queue.get()
        if dataset is None:  # Sentinel to signal termination
            break
        try:
            connected, unconnected_ways = check_network_connectivity(dataset['data'])
            insert_queue.put((dataset['rel_id'], connected, unconnected_ways))
        except Exception as e:
            print(f"Error processing relation {dataset['rel_id']}: {e}")


# Producer-consumer manager
def validate_ways_connections(num_workers=mp.cpu_count() - 1, max_queue_size=500):
    print('Validating connections between ways in all routes')
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('DROP TABLE IF EXISTS rels_validity')
            cur.execute('CREATE TABLE rels_validity (id BIGINT REFERENCES planet_osm_rels(id), connected BOOLEAN, unconnected_ways BIGINT[])')

        queue = mp.Queue(maxsize=max_queue_size)

        # Spawn worker processes
        processes = []
        for _ in range(num_workers):
            p = mp.Process(target=worker, args=(queue,))
            p.start()
            processes.append(p)

        # Spawn db insert process
        ip = mp.Process(target=db_insert_worker)
        ip.start()

        counter = 0
        with conn.cursor(row_factory=dict_row) as cur:
            num_relations = cur.execute('select count(*) as count from planet_osm_rels').fetchone()
            cur.execute(query)

            with tqdm(total=num_relations['count'], unit_scale=True) as progress_bar:
                while True:
                    records = cur.fetchmany(max_queue_size)
                    if not records:
                        break

                    len_records = len(records)

                    for row in records:
                        queue.put(row)  # Blocks automatically if queue is full

                    progress_bar.update(len_records)

        # Send sentinel values to tell workers to exit
        for _ in range(num_workers):
            queue.put(None)

        # Wait for workers to finish
        for p in processes:
            p.join()

        insert_queue.put(None)
        ip.join()


# Run the manager
if __name__ == "__main__":
    validate_ways_connections()
