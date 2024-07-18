import time
import os
import json
from termcolor import colored
import tiktoken
from datetime import datetime

class Utilities:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent

    def get_timestamp(self):
        return datetime.now().isoformat(timespec='minutes')
    
    ### PRINT MESSAGE THREADS TO THE CONSOLE
    def pretty_print(self,
                     messages):
        role_to_color = {
            "system": "red",
            "user": "green",
            "assistant": "blue",
            "function": "magenta",
            "function_metadata": "magenta",
        }
        def print_message(message):
            if message["role"] == "system":
                print(colored(f"{self.MyAgent.ai_name} <sys>:\n{message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "user":
                print(colored(f"Human:\n{message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "function":
                print(colored(f"function ({message['name']}; '{message['name']}'): {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "function_metadata":
                print(colored(f"available functions: {message['content']}\n", role_to_color[message["role"]]))
            elif message["role"] == "assistant":
                print(colored(f"{self.MyAgent.ai_name}:\n{message['content']}\n", role_to_color[message["role"]]))
                
        if isinstance(messages, list):
            for message in messages:
                print_message(message)
        else:
            print_message(messages)

    def read_prompt_template(self,
                             template_name):
        with open(f"{self.MyAgent.prompt_templates}{template_name}.txt", 'r') as file:
            prompt_template = file.read()
        return prompt_template

    def create_message_thread(self,
                              question,
                              system_prompt=None,
                              verbose=False):
        ### SYSTEM PROMPT
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            system_prompt = self.read_prompt_template(template_name="instruct_template")
            messages.append({"role": "system", "content": system_prompt})

        ### RETURN WITH QUESTION
        question = question.replace("'", "").replace('"', "")
        messages.append({"role": "user", "content": question})

        ### PRINT IF VERBOSE
        if verbose and self.MyAgent.verbose:
            self.MyAgent.Utilities.pretty_print(messages)
        return messages

    def create_response_thread(self,
                               messages,
                               text_response,
                               verbose=False):
        response_message = {
            "role": "assistant",
            "content": text_response
        }
        messages.append(response_message)
        if verbose and self.MyAgent.verbose:
            self.MyAgent.Utilities.pretty_print(response_message)
        return messages
        
#######################
### UNIVERSAL TIMER ###
#######################
class Timer:
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_elapsed_time(self):
        end = time.time()
        return round(end - self.start, 1)
