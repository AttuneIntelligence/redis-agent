import os
import sys
import redis
from rq import Worker, Queue, Connection
from multiprocessing import Process

sys.path.append('/workspace/redis-agent/src')
from my_agent import MyAgent

########################################################
### PROCESS TO BE RUN IN A SEPERATE SERVER CONTAINER ###
## LAUNCHES WORKER NODES FOR PROCESSING AGENT REQUESTS #
########################################################

### INITIALIZE THE AGENT
WorkerAgent = MyAgent()

### DEFINE QUERIES TO LOOK FOR
listen = ['high', 'default', 'low']
conn = redis.from_url(f'redis://{WorkerAgent.redis_host}:{WorkerAgent.redis_port}')

def start_worker():
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()

if __name__ == '__main__':
    num_workers = WorkerAgent.n_redis_workers
    processes = []

    for _ in range(num_workers):
        p = Process(target=start_worker)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
