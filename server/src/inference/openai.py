import json
import time
import requests
import sys
import os
import subprocess
from openai import OpenAI as Open_AI
from openai import AsyncOpenAI
import tiktoken
from termcolor import colored

sys.path.append('/workspace/indra/src')
from bin.utilities import *

class OpenAI:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        
        ### MODEL SELECTION
        # self.primary_model = "gpt-4o-2024-05-13"
        self.primary_model = "gpt-4-turbo-2024-04-09"
        # self.secondary_model = "gpt-4o-2024-05-13"
        self.secondary_model = "gpt-3.5-turbo-1106"

        ### CLASS IMPORTS
        self.client = Open_AI()
        self.async_client = AsyncOpenAI()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = 4096
        
    def invoke_gpt(self, 
                   question,
                   system_prompt=None,
                   temperature=0.7,
                   verbose=False,
                   stream_response=False,
                   secondary_model=False):
        timer = Timer()

        ### CREATE SYSTEM INPUT WITH MESSAGE THREAD
        messages = self.MyAgent.Utilities.create_message_thread(
            question=question,
            system_prompt=system_prompt,
            verbose=verbose
        )

        ### DEFINE GPT MODEL TO USE
        if not secondary_model:
            model_to_use = self.primary_model
        else:
            model_to_use = self.secondary_model


        ### STREAM COMPLETION RESPONSE...
        if stream_response:
            text_response = ""
            response_stream = self.client.chat.completions.create(
                messages=messages,
                model=model_to_use,
                temperature=temperature,
                stream=True
            )
            if verbose and self.MyAgent.verbose:
                print(colored(f"{self.MyAgent.ai_name}:", 'blue'))
            for chunk in response_stream:
                if chunk.choices[0].delta.content is not None:
                    text_response += chunk.choices[0].delta.content
                if verbose and self.MyAgent.verbose:
                        print(colored(chunk.choices[0].delta.content, 'blue'), end="")
            if verbose and self.MyAgent.verbose:
                print("\n")
            response_messages = self.MyAgent.Utilities.create_response_thread(
                messages=messages,
                text_response=text_response,
                verbose=False   ### ALREADY STREAMED RESPONSE TO CONSOLE
            )
            
        ### ...OR EXECUTE COMPLETEION WITHOUT STREAMING
        else:
            response = self.client.chat.completions.create(
                messages=messages,
                model=model_to_use,
                temperature=temperature,
                stream=False
            )
            text_response = response.choices[0].message.content
            response_messages = self.MyAgent.Utilities.create_response_thread(
                messages=messages,
                text_response=text_response,
                verbose=verbose
            )

        ### COMPILE METADATA
        inference_cost, egress_tokens = self.cost_calculator(
            ingress=messages,
            egress=text_response,
            model=model_to_use,
            return_egress_tokens=True
        )
        time_elapsed = timer.get_elapsed_time()
        tps = egress_tokens / time_elapsed
        
        ### COMPILE METADATA
        metadata = {
            "cost": inference_cost,
            "time": time_elapsed,
            "tokens_per_second": tps
        }
        if verbose:
            print(f"==> Cost: ${inference_cost:0.4f}")
            print(f"==> Time: {time_elapsed:0.1f} seconds")
            print(f"==> TPS: {tps:0.1f} tokens / second")
        return response_messages, metadata

    async def openai_async(self, 
                           prompt,
                           model,
                           system_prompt=None,
                           temperature=0.3):
        timer = Timer()
        if system_prompt:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=temperature,
            )
            text_response = response.choices[0].message.content.strip().replace("'", "")
            compiled_prompt = f"{system_prompt} /n/n {prompt}"
        else:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            text_response = response.choices[0].message.content.strip().replace("'", "")
            compiled_prompt = prompt

        ### GET METADATA FOR SINGLE REQUEST
        time_taken = timer.get_elapsed_time()
        metadata = self.MyAgent.Utilities.compile_openai_metadata(
            ingress=compiled_prompt,
            egress=text_response, 
            time_taken=time_taken, 
            model_name=model
        )
        return text_response, metadata


    def cost_calculator(self,
                        ingress,
                        egress,
                        model,
                        return_egress_tokens=False):
        
        ### INGRESS IS MESSAGE LIST / EGRESS IS RESPONSE STRING
        if isinstance(ingress, list):
            ingress_tokens = sum([len(self.tokenizer.encode(message["content"])) for message in ingress])
        elif isinstance(ingress, str):
            ingress_tokens = len(self.tokenizer.encode(ingress))
        elif isinstance(ingress, int):
            ingress_tokens = ingress
        if isinstance(egress, int):
            egress_tokens = egress
        else:
            egress_tokens = len(self.tokenizer.encode(egress))
                            
        if model in ["gpt-4-0125-preview", "gpt-4-1106-preview", "gpt-4-vision-preview"]:
            prompt_cost = (ingress_tokens / 1000)*0.01
            response_cost = (egress_tokens / 1000)*0.03

        elif model in ["gpt-4o-2024-05-13"]:
            prompt_cost = (ingress_tokens / 1000000)*5.00
            response_cost = (egress_tokens / 1000000)*15.00

        elif model in ["gpt-4-turbo-2024-04-09"]:
            prompt_cost = (ingress_tokens / 1000000)*10.00
            response_cost = (egress_tokens / 1000000)*30.00

        elif model in ["gpt-4"]:
            prompt_cost = (egress_tokens / 1000)*0.03
            response_cost = (egress_tokens / 1000)*0.06
        elif model in ["gpt-4"]:
            prompt_cost = (egress_tokens / 1000)*0.03
            response_cost = (egress_tokens / 1000)*0.06

        elif model in ["gpt-4-32k"]:
            prompt_cost = (egress_tokens / 1000)*0.06
            response_cost = (egress_tokens / 1000)*0.12

        elif model in ["gpt-3.5-turbo-1106", "gpt-3.5-turbo-0125"]:
            prompt_cost = (egress_tokens / 1000)*0.0010
            response_cost = (egress_tokens / 1000)*0.0020

        elif model in ["gpt-3.5-turbo-instruct"]:
            prompt_cost = (egress_tokens / 1000)*0.0015
            response_cost = (egress_tokens / 1000)*0.0020

        if not return_egress_tokens:
            return prompt_cost+response_cost     
        else:
            return prompt_cost+response_cost, egress_tokens



