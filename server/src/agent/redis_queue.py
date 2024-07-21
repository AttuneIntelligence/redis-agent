import sys
from random import choice
import requests
import redis
from rq import Queue, Worker
from rq.job import Job
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

sys.path.append('/workspace/redis-agent')
from bin.utilities import *

class Agent_Queue:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.redis_connection = redis.Redis(host=MyAgent.redis_host, port=MyAgent.redis_port)
        self.relevance_embedding_model = 'text-embedding-3-small'
        self.relevance_embedding_dimensions = 512
        self.n_relevant_results = 4
        self.relevance_threshold = 0.25

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
        # print(f'==> Agent execution complete in {time_taken} seconds.')
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
                time.sleep(0.5)
                job.refresh()
            if job.result != "NA":
                results.extend(job.result)
            
        ### ENSURE UNIQUE RESULTS
        seen_titles = set()
        def add_unique_result(result):
            if not result:
                return False
            title = result.get('title', None)
            if not title:
                title = result.get('name', None)
            if title and title not in seen_titles:
                seen_titles.add(title)
                return True
            return False
        unique_results = [result for result in results if add_unique_result(result)]
        return unique_results

    ### SORT QUEUE RESPONSES BY RELEVANCE
    def return_maximally_relevant(self,
                                  question,
                                  results,
                                  n_results=None):
        timer = Timer()
        if not n_results:
            n_results=self.n_relevant_results
        
        ### COMPUTE COSINE SIMILARITY
        def compute_similarity(result, encoded_question):
            encoded_result = self.MyAgent.OpenAI.client.embeddings.create(
                input=json.dumps(result), 
                model=self.relevance_embedding_model,
                dimensions=self.relevance_embedding_dimensions
            ).data[0].embedding
            vector_dot_product = np.dot(encoded_question, encoded_result)
            magnitude_encoded_question = np.linalg.norm(encoded_question)
            magnitude_encoded_result = np.linalg.norm(encoded_result)
            cosine_similarity = vector_dot_product / (magnitude_encoded_question * magnitude_encoded_result)
            result['similarity'] = cosine_similarity
            return result
        
        ### ENCODE THE QUESTION
        encoded_question = self.MyAgent.OpenAI.client.embeddings.create(
            input=question, 
            model=self.relevance_embedding_model,
            dimensions=self.relevance_embedding_dimensions
        ).data[0].embedding
        
        ### COMPUTE SIMILARITIES IN PARALLEL
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(compute_similarity, result, encoded_question) for result in results]
            scored_results = [future.result() for future in futures]

        ### FILTER OUT RESULTS WITH SIMILARITY < 0.3
        filtered_results = [result for result in scored_results if result['similarity'] >= self.relevance_threshold]
        
        ### SORT BY SIMMILARITY SCORE AND RETURN
        sorted_results = sorted(filtered_results, key=lambda x: x['similarity'], reverse=True)
        time_taken = timer.get_elapsed_time()
        # print(f"==> Sorted queue results by cosine similarity in {time_taken} seconds.")
        return sorted_results[:n_results]

