import sys
import multiprocess
from random import choice
import requests

sys.path.append('/workspace/redis-agent')
from src import *

class MyAgent:
    def __init__(self):
        
        ### INITIALIZATION
        set_keys(self)
        self.cpu_count = multiprocess.cpu_count()
        self.ai_name = "Asclepius"
        self.home = "/workspace/redis-agent/"
        self.prompt_templates = f"{self.home}assets/prompt-templates/"
        self.verbose = True   ### ALLOW FOR GLOBAL OVERWRITE OF VERBOSITY

        ### REDIS AGENT PARAMETERS
        self.n_redis_workers = 4
        self.redis_host = 'redis'
        self.redis_port = 6379

        ### CLASS IMPORTS
        self.OpenAI = OpenAI(self)
        self.Utilities = Utilities(self)
        self.Agent_Queue = Agent_Queue(self)
        self.Toolkit = Toolkit(self)


        