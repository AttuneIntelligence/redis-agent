import sys
import json
import multiprocess

sys.path.append('/workspace/redis-agent')
from src import *
from bin.utilities import *

class MyAgent:
    def __init__(self):
        
        ### INITIALIZATION
        set_keys(self)
        self.cpu_count = multiprocess.cpu_count()
        self.ai_name = "Asclepius"
        self.home = "/workspace/redis-agent/"
        self.prompt_templates = f"{self.home}assets/prompt-templates/"
        self.verbose = True   ### ALLOW FOR GLOBAL OVERWRITE OF VERBOSITY

        ### REDIS TOOLKIT WORKER PARAMETERS
        self.n_redis_workers = 4
        self.redis_host = 'redis'
        self.redis_port = 6379

        ### AGENTIAL Q&A
        self.n_agent_actions = 3

        ### CLASS IMPORTS
        self.OpenAI = OpenAI(self)
        self.Utilities = Utilities(self)
        self.Agent_Queue = Agent_Queue(self)
        self.Toolkit = Toolkit(self)
        
    ##################################################
    ### CHAIN OF THOUGHT REASONING FOR PREPLANNING ###
    ##################################################
    def generate_plan(self,
                      question,
                      selected_tools):
        timer = Timer()

        ### GENERATE A PLAN WITH THE PRESELECTED SUBSET OF TOOLS
        CoT_template = self.Utilities.read_prompt_template(template_name="agential_planning_template")
        CoT_prompt = CoT_template.format(
            available_functions=json.dumps({item['name']: item['description'] for item in selected_tools}),
            available_function_names=', '.join([item['name'] for item in selected_tools]),
            n_agent_actions=self.n_agent_actions
        )
        CoT_messages = [{"role": "system", "content": CoT_prompt}, {"role": "user", "content": question}]
        structured_plan_response = self.OpenAI.client.chat.completions.create(
          model=self.OpenAI.primary_model,
          messages=CoT_messages,
          response_format={ "type": "json_object" }
        )
        structured_plan = structured_plan_response.choices[0].message.content
        planning_cost = self.OpenAI.cost_calculator(
            ingress=CoT_messages,
            egress=structured_plan,
            model=self.OpenAI.primary_model,
            return_egress_tokens=False
        )

        ### RETURN JSON PLAN
        time_elapsed = timer.get_elapsed_time()
        planning_metadata = {
            'time': time_elapsed,
            'cost': planning_cost
        }
        # print(f"==> Plan generated in {time_elapsed} seconds (${round(planning_cost, 4)}).")
        return json.loads(structured_plan), planning_metadata

    #######################
    ### AGENT EXECUTION ###
    #######################
    def invoke_gpt_agent(self,
                         question):
        timer = Timer()
        messages = []
        functions_called = []
        total_cost = 0

        #############################################
        ### 0 --> SELECT SUBSET OF RELEVANT TOOLS ###
        #############################################
        selected_tools = self.Toolkit.query_toolkit_db(question)
        tool_names = ', '.join([tool["name"] for tool in selected_tools])
        tool_names_message = {"role": "function_metadata", "content": tool_names}

        #############################
        ### 1 --> GENERATE A PLAN ###
        #############################
        generated_plan, planning_metadata = self.generate_plan(
            question=question, 
            selected_tools=selected_tools
        )
         
        #########################################################
        ### 2 --> EXECUTE STEP 1 OF THE PLAN IN REDIS WORKERS ###
        #########################################################
        complete_function_responses = []
        step_01_actions = generated_plan['step_1']['actions']
        if step_01_actions:
            ### RESPONSE FUNCTION CALLS --> REDIS QUEUE CALLS
            function_queue = self.compile_agent_functions(step_01_actions)
                    
            ### QUEUE FUNCTIONS TO REDIS WORKERS
            function_execution_response = self.Agent_Queue.queue_function_calls(function_queue)
    
            ### SORT BY RELEVANCE TO QUESTION BY COSINE SIMILARITY
            step_01_function_results = self.Agent_Queue.return_maximally_relevant(
                question=question,
                results=function_execution_response
            )

        else:
            ### NO ACTION WAS NECESSARY
            step_01_function_results = []
        complete_function_responses.extend(step_01_function_results)
        
        ##################################################################
        ### 3 --> ENTER ITERATION LOOP FOR SUBSEQUENT CHAIN OF THOUGHT ###
        ##################################################################
        n_function_calls = 1   ### ALREADY EXECUTED STEP 1
        while n_function_calls < self.n_agent_actions:
            if not step_01_actions:
                ### BYPASS AGENT LOOP IF NO ACTIONS TO TAKE
                break
            else:
                ### GENERATE LOOP ITERATION FUNCTION CALL
                function_iteration_results, loop_iteration_metadata = self.agential_loop_execution(
                    question=question,
                    selected_tools=selected_tools,
                    prepared_plan=generated_plan,
                    function_results=complete_function_responses,
                    current_step=n_function_calls+1
                )
                function_iteration_actions = function_iteration_results['actions']
    
                ### BREAK AGENT LOOP IF STOP SEQUENCE IS RETURNED
                if function_iteration_actions[0]["function"] == "return_answer":
                    break
    
                ### EXECUTE FUNCTION CALLS CONCURRENTLY IN REDIS WORKERS
                function_queue = self.compile_agent_functions(function_iteration_actions)
                function_execution_response = self.Agent_Queue.queue_function_calls(function_queue)
        
                ### SORT BY RELEVANCE TO QUESTION BY COSINE SIMILARITY
                relevant_function_results = self.Agent_Queue.return_maximally_relevant(
                    question=question,
                    results=function_execution_response
                )
    
                ### TRACK FUNCTION RESULTS AND RE-ITERATE
                complete_function_responses.extend(relevant_function_results)
                n_function_calls += 1

        # print(f"==> Agent Execution completed in {n_function_calls} steps.")
        return complete_function_responses

    def agential_loop_execution(self,
                                question,
                                selected_tools,
                                prepared_plan,
                                function_results,
                                current_step):
        timer = Timer()

        ### REVIEW TOOL RESPONSE AND PREPARE A SUBSEQUENT FUNCTION EXECUTION
        agent_loop_template = self.Utilities.read_prompt_template(template_name="agential_loop_template")
        agent_loop_prompt = agent_loop_template.format(
            available_functions=json.dumps({item['name']: item['description'] for item in selected_tools}),
            available_function_names=', '.join([item['name'] for item in selected_tools]),
            current_step=current_step
        )
        agent_iteration_messages = [
            {"role": "system", "content": agent_loop_prompt}, 
            {"role": "user", "content": f"User's Question: {question}"},
            {"role": "user", "content": f"Original Plan: {json.dumps(prepared_plan)}"},
            {"role": "user", "content": f"Function Results: {json.dumps(function_results)}"}
        ]
        iterated_function_response = self.OpenAI.client.chat.completions.create(
          model=self.OpenAI.primary_model,
          messages=agent_iteration_messages,
          response_format={ "type": "json_object" }
        )
        iterated_function_call = iterated_function_response.choices[0].message.content
        print(json.loads(iterated_function_call))
        funtion_iteration_cost = self.OpenAI.cost_calculator(
            ingress=agent_iteration_messages,
            egress=iterated_function_call,
            model=self.OpenAI.primary_model,
            return_egress_tokens=False
        )

        ### RETURN JSON PLAN
        time_elapsed = timer.get_elapsed_time()
        funtion_iteration_metadata = {
            'time': time_elapsed,
            'cost': funtion_iteration_cost
        }
        # print(f"==> Agent iteration completed in {time_elapsed} seconds (${round(funtion_iteration_cost, 4)}).")
        return json.loads(iterated_function_call), funtion_iteration_metadata

    ### ORGANIZE AGENT RESPONSE TO FUNCTION CALLS
    def compile_agent_functions(self,
                                step_actions):
        function_queue = []
        for function_call in step_actions:
            try:
                function_queue.append({
                    'name': function_call['function'],
                    'arguments': {
                        'query': function_call['query']
                    }
                })
            except:
                print(f"==> [Error] Invalid json returned by agent: {function_call}")
                continue
        return function_queue




