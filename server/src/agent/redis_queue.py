import sys
from random import choice
import requests
import redis
from rq import Queue, Worker
from rq.job import Job
import time

sys.path.append('/workspace/redis-agent')
from bin.utilities import *

class Agent_Queue:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.redis_connection = redis.Redis(host=MyAgent.redis_host, port=MyAgent.redis_port)

    ### WRAP QUEUE AND FETCH INTO SINGLE FUNCTION
    def queue_function_calls(self,
                             query_list):
        timer = Timer()
        if not Worker.all(connection=self.redis_connection):
            print(f"==> [Error] No Redis workers found to be available.")
            return None
        job_ids = self.enqueue_tasks(query_list)
        results = self.fetch_results(job_ids)
        time_taken = timer.get_elapsed_time()
        print(f'Agent execution complete in {time_taken} seconds.')
        return results
    
    ### CREATE QUEUE OF FUNCTION CALLS IN REDIS WORKER\
    def enqueue_tasks(self,
                      query_list):
        q = Queue(connection=self.redis_connection)
        job_ids = []
        for function_call in query_list:
            function_call['n_results'] = self.MyAgent.Toolkit.n_function_responses   ### PASS CLASS LIMIT TO STATIC METHODS
            job = q.enqueue(self.MyAgent.Toolkit.execute_function_call, function_call, self.MyAgent.Toolkit.all_tools)
            job_ids.append(job.id)
        return job_ids

    ### FETCH THE COMPLETED JOBS FROM REDIS WHEN RUN
    def fetch_results(self,
                      job_ids):
        results = []
        for job_id in job_ids:
            job = Job.fetch(job_id, connection=self.redis_connection)
            while job.result is None:
                time.sleep(1)
                job.refresh()
            results.extend(job.result)
        return results
