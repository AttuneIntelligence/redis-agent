import sys
import json
import multiprocess
from termcolor import colored

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
        self.n_agent_actions = 3   ### AGENT ITERATION LIMIT
        self.n_final_agent_results = 8   ### LENGTH OF FINAL FUNCTION RESULTS
        self.agent_temperature = 0.4
        self.persona_temperature = 0.9

        ### REDIS CHAT HISTORY
        self.memory_token_len = 1800

        ### CLASS IMPORTS
        self.OpenAI = OpenAI(self)
        self.Utilities = Utilities(self)
        self.Agent_Queue = Agent_Queue(self)
        self.Toolkit = Toolkit(self)
        self.Memory = Memory(self)
        
    #####################
    ### AGENT WRAPPER ###
    #####################
    def server_execute(self,
                       user_json):
        timer = Timer()

        ### PULL CHAT HISTORY FROM REDIS
        chat_thread = self.Memory.egress_memory(user_json['user_id'])['chat_history']
        
        ### EXECUTE AGENT
        print(f"==> Executing agent...")
        chat_thread.append({'role': 'user', 'content': user_json['question']})
        agent_results, agent_metadata = self.invoke_gpt_agent(chat_thread)

        ### STREAM RESPONSE WITH PERSONA
        text_response = ""
        for chunk in self.server_persona_generation(
            user_json=user_json,
            chat_history=chat_thread,
            function_response=agent_results
        ):
            text_response += chunk
            yield chunk

        ### ADD CHAT HISTORY TO REDIS AFTER RESPONSE HAS BEEN STREAMED
        self.Memory.ingress_memory( 
            user_id=user_json['user_id'],
            message_thread=chat_thread,
            question=user_json['question'], 
            response=text_response
        )

    ### EXECUTE AGENT IN JUPYTER NOTEBOOK WITH METADATA COMILATION
    def notebook_execute(self,
                         user_json):
        timer = Timer()

        ### PULL CHAT HISTORY FROM REDIS
        chat_thread = self.Memory.egress_memory(user_json['user_id'])['chat_history']
        
        ### EXECUTE AGENT
        print(f"==> Executing agent...")
        chat_thread.append({'role': 'user', 'content': user_json['question']})
        agent_results, agent_metadata = self.invoke_gpt_agent(chat_thread)

        ### STREAM RESPONSE WITH PERSONA
        final_response, persona_metadata = self.notebook_persona_generation(
            user_json=user_json,
            chat_history=chat_thread,
            function_response=agent_results,
        )

        ### ADD CHAT HISTORY TO REDIS
        chat_summary_metadata = self.Memory.ingress_memory( 
            user_id=user_json['user_id'],
            message_thread=chat_thread,
            question=user_json['question'], 
            response=final_response
        )

        ### COMPILE FINAL AGENT METADATA
        time_taken = timer.get_elapsed_time()
        execution_metadata = {
            'time': time_taken,
            'cost': agent_metadata['cost'] + persona_metadata['cost'] + chat_summary_metadata.get('cost', 0),
            'time_to_first_token': persona_metadata['time_to_first_token'] + agent_metadata['time'],
            'tokens_per_second': persona_metadata['egress_tokens'] / time_taken,
            'n_agent_steps': agent_metadata['n_agent_steps'],
            'functions_executed': agent_metadata['functions_executed']
        }
        return final_response, execution_metadata

    ##################################################
    ### CHAIN OF THOUGHT REASONING FOR PREPLANNING ###
    ##################################################
    def generate_plan(self,
                      message_thread,
                      selected_tools):
        timer = Timer()

        ### GENERATE A PLAN WITH THE PRESELECTED SUBSET OF TOOLS
        CoT_template = self.Utilities.read_prompt_template(template_name="agential_planning_template")
        CoT_prompt = CoT_template.format(
            available_functions=json.dumps({item['name']: item['description'] for item in selected_tools}),
            available_function_names=', '.join([item['name'] for item in selected_tools]),
            n_agent_actions=self.n_agent_actions
        )
        CoT_messages = [{"role": "system", "content": CoT_prompt}]
        CoT_messages.extend(message_thread)
        structured_plan_response = self.OpenAI.client.chat.completions.create(
            model=self.OpenAI.primary_model,
            messages=CoT_messages,
            response_format={ "type": "json_object" },
            temperature=self.agent_temperature
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
                         user_message_thread):
        timer = Timer()
        messages = []
        functions_called = []
        total_cost = 0
        question = user_message_thread[-1]['content']

        #############################################
        ### 0 --> SELECT SUBSET OF RELEVANT TOOLS ###
        #############################################
        selected_tools = self.Toolkit.query_toolkit_db(user_message_thread[-1]['content'])
        tool_names = ', '.join([tool["name"] for tool in selected_tools])
        tool_names_message = {"role": "function_metadata", "content": tool_names}

        #############################
        ### 1 --> GENERATE A PLAN ###
        #############################
        generated_plan, planning_metadata = self.generate_plan(
            message_thread=user_message_thread, 
            selected_tools=selected_tools
        )
        total_cost += planning_metadata['cost']
                 
        #########################################################
        ### 2 --> EXECUTE STEP 1 OF THE PLAN IN REDIS WORKERS ###
        #########################################################
        n_function_calls = 0
        complete_function_responses = []
        step_01_actions = generated_plan['step_1']['actions']
        if step_01_actions and step_01_actions[0]["function"] != "return_answer":
            ### RESPONSE FUNCTION CALLS --> REDIS QUEUE CALLS
            function_queue = self.compile_agent_functions(step_01_actions)
            functions_called.extend(step_01_actions)
                    
            ### QUEUE FUNCTIONS TO REDIS WORKERS
            function_execution_response = self.Agent_Queue.queue_function_calls(function_queue)
    
            ### SORT BY RELEVANCE TO QUESTION BY COSINE SIMILARITY
            step_01_function_results = self.Agent_Queue.return_maximally_relevant(
                question=question,
                results=function_execution_response
            )
            n_function_calls += 1

        else:
            ### NO ACTION WAS NECESSARY
            step_01_function_results = []
        complete_function_responses.extend(step_01_function_results)
        
        ##################################################################
        ### 3 --> ENTER ITERATION LOOP FOR SUBSEQUENT CHAIN OF THOUGHT ###
        ##################################################################
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
                functions_called.extend(function_iteration_actions)
                total_cost += loop_iteration_metadata['cost']
    
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

        ### END OF FUNCTION CALLING LOOP --> FILTER UNIQUE AND RETURN MAXIMALLY RELEVANT FROM AGGREGATED SOURCES
        unique_results = self.Agent_Queue.filter_unique_results(complete_function_responses)
        best_function_responses = sorted(unique_results, key=lambda x: x['similarity'], reverse=True)[:self.n_final_agent_results]

        ### COMPILE METADATA AND RETURN
        time_taken = timer.get_elapsed_time()
        agent_metadata = {
            'time': time_taken,
            'cost': total_cost,
            'n_agent_steps': n_function_calls,
            'functions_executed': functions_called
        }
        print(f"==> Agent executed in {n_function_calls} steps for ${round(total_cost, 4)} ({time_taken} seconds).")
        return best_function_responses, agent_metadata

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
            response_format={ "type": "json_object" },
            temperature=self.agent_temperature
        )
        iterated_function_call = iterated_function_response.choices[0].message.content
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
                        'query': function_call['query'],
                        'n_results': self.Toolkit.n_function_responses   ### N RETURNED BY EACH FUNCTION
                    }
                })
            except:
                print(f"==> [Error] Invalid json returned by agent: {function_call}")
                continue
        return function_queue
        
    #######################################
    ### PERSONA GENERATION W/ STREAMING ###
    #######################################
    ### DIRECT RETURN OF STREAMED RESPONSE, NO SERVER
    def notebook_persona_generation(self,
                                    chat_history,
                                    function_response,
                                    user_json):
        timer = Timer()
        
        ### GENERATE AGENT MESSAGE THREAD
        agent_messages = self.format_agent_message_thread(         
            chat_history=chat_history,
            function_response=function_response,
            user_json=user_json
        )
                
        ### STREAM COMPLETION RESPONSE
        response_stream = self.OpenAI.client.chat.completions.create(
            messages=agent_messages,
            model=self.OpenAI.primary_model,
            temperature=self.persona_temperature,
            stream=True
        )
        if self.verbose:
            print(colored(f"{self.ai_name}:", 'blue'))

        ### RETURN TO JUPYTER CONSOLE
        text_response = ''
        first_response = True
        for chunk in response_stream:
            if first_response:
                time_to_first_token = timer.get_elapsed_time()
                first_response=False
            if chunk.choices[0].delta.content is not None:
                text_response += chunk.choices[0].delta.content
                if self.verbose:
                    print(colored(chunk.choices[0].delta.content, 'blue'), end="")
        if self.verbose:
            print("\n")

        ### COMPILE AGENT METADATA RESPONSE
        time_taken = timer.get_elapsed_time()
        persona_metadata = self.compile_agent_response_metadata(
            agent_messages=agent_messages,
            agent_response=text_response,
            time_elapsed=time_taken,
            time_to_first_token=time_to_first_token
        )
        return text_response, persona_metadata

    ### FLASK PERSONA GENERATION WITH STREAMING TO SERVER
    def server_persona_generation(self,
                                  chat_history,
                                  function_response,
                                  user_json):
        timer = Timer()
        
        ### GENERATE AGENT MESSAGE THREAD
        agent_messages = self.format_agent_message_thread(         
            chat_history=chat_history,
            function_response=function_response,
            user_json=user_json
        )
                
        ### STREAM COMPLETION RESPONSE
        response_stream = self.OpenAI.client.chat.completions.create(
            messages=agent_messages,
            model=self.OpenAI.primary_model,
            temperature=self.persona_temperature,
            stream=True
        )
        if self.verbose:
            print(colored(f"{self.ai_name}:", 'blue'))

        text_response = ''
        first_response = True
        time_to_first_token = 0
        for chunk in response_stream:
            if first_response:
                time_to_first_token = timer.get_elapsed_time()
                first_response = False
            if chunk.choices[0].delta.content is not None:
                text_response += chunk.choices[0].delta.content
                if self.verbose:
                    print(colored(chunk.choices[0].delta.content, 'blue'), end="")
                yield chunk.choices[0].delta.content
        if self.verbose:
            print("\n")
        yield "[DONE]"

    def format_agent_message_thread(self,         
                                    chat_history,
                                    function_response,
                                    user_json):
        all_messages = []
    
        ### ADD INDRA'S PERSONA TEMPLATE
        generation_prompt_template = self.Utilities.read_prompt_template(template_name="agential_persona_template")
        generation_prompt = generation_prompt_template.format(
            ai_name=self.ai_name,
            human_name=user_json.get('display_name', 'user')
        )
        all_messages.append({"role": "system", "content": generation_prompt})

        ### ADD CHAT HISTORY
        all_messages.extend(chat_history[:-1])   ### REMOVE QUESTION, REFERENCES COME FIRST FOR RELEVANCE ORDERING

        ### ADD COMPILED REFERENCE MATERIAL
        all_messages.append({"role": "user", "content": f"Compiled Reference Material: {json.dumps({'function_data': function_response})}"})
    
        ### THEN ADD QUESTION AS THE LAST MESSAGE
        input_message = {"role": "user", "content": user_json.get("question")}
        all_messages.append(input_message)
        if self.verbose:
            self.Utilities.pretty_print(all_messages)  
        return all_messages

    def compile_agent_response_metadata(self,
                                        agent_messages,
                                        agent_response,
                                        time_elapsed,
                                        time_to_first_token):
        ### PROCESS RESPONSE
        inference_cost, egress_tokens = self.OpenAI.cost_calculator(
            ingress=agent_messages,
            egress=agent_response,
            model=self.OpenAI.primary_model,
            return_egress_tokens=True
        )

        ### COMPILE METADATA
        metadata = {
            "cost": inference_cost,
            "time": time_elapsed,
            "time_to_first_token": round(time_to_first_token, 3),
            "egress_tokens": egress_tokens,
        }
        print(f"==> Persona response generated for ${round(inference_cost, 4)} ({time_elapsed} seconds).")
        return metadata


