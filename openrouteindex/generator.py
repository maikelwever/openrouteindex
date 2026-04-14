from threading import Thread
from queue import Queue
from multiprocessing import cpu_count

from openrouteindex.config import OUTPUT_DIR
from openrouteindex.db.core import engine
from openrouteindex.environment import build_environment


def output_worker(queue, global_context):
    with engine.connect() as conn:
        while True:
            item = queue.get()
            if item is None:  # Sentinel to signal termination
                break

            filename = item.get_filename()
            output_file = OUTPUT_DIR / filename
            print(f'Generating page: {output_file}')

            try:
                with conn.begin() as tx:
                    content = item.render(conn, global_context)

                mode = 'w'
                if type(content) is bytes:
                    mode = 'wb'

                with open(output_file, mode) as f:
                    f.write(content)
            except Exception as e:
                print(f"Error rendering page {filename}: {e}")


def generate_html():
    with engine.connect() as conn:
        pages, global_context = build_environment(conn)

    OUTPUT_DIR.mkdir(exist_ok=True)

    num_workers = cpu_count() - 1
    queue = Queue(maxsize=num_workers * 2)
    processes = []

    for _ in range(num_workers):
        p = Thread(target=output_worker, args=(queue, global_context.copy()))
        p.start()
        processes.append(p)

    for item in pages:
        queue.put(item)

    for _ in range(num_workers):
        queue.put(None)

    for p in processes:
        p.join()



if __name__ == '__main__':
    generate_html()