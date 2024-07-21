import os
import re
import sys
import importlib
import subprocess
import json
import requests
import inspect
from termcolor import colored
from serpapi import GoogleSearch
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

sys.path.append('/workspace/indra/src')
from bin.utilities import *

class Toolkit:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.tools_json = f"{self.MyAgent.home}src/agent/tools.json"
        self.n_function_responses = 3   ### FOR EACH INDIVIDUAL TOOL CALL
        self.n_available_tools = 6   ### N AVAILABLE TOOLS FOR EACH AGENT CALL

        ### DEFINE THE TOOLSET VECTOR DATABASE IN MEMORY
        self.all_tools = self.load_tools()
        self.tool_definitions = self.load_tool_metadata()
        self.toolkit_db = self.create_toolkit_db()
            
    def read_tools(self):
        with open(self.tools_json, 'r') as file:
            return json.load(file)

    def load_tool_metadata(self):
        ### RETURN FUNCTION DEFINITIONS
        tools = self.read_tools()
        definitions = []
        for tool in tools:
            ### ONLY INCLUDE SERPAPI / PUBMED FUNCTIONS IF AUTH IS PROVIDED
            if tool["type"] == "serpapi" and 'SERPAPI_API_KEY' not in os.environ:
                continue
            elif tool["type"] == "pubmed" and 'PUBMED_API_KEY' not in os.environ:
                continue
            else:
                definitions.append(tool["function"])
        return definitions
    
    def load_tools(self):
        tools = self.read_tools()

        ### RETURN DEFAULT AVAILABLE TOOLS AS A LIST OF DICTIONARIES
        all_tools =  {
            tool["function"]["name"]: importlib.import_module(f"agent.functions.{tool['function']['name']}").__dict__[tool["function"]["name"]]
            for tool in tools if tool["type"] == "function"
        }
        
        ### ADD PUBMED TOOL IF AVAILABLE, AS STATIC METHODS
        if 'PUBMED_API_KEY' in os.environ:
            all_tools.update({
                tool["function"]["name"]: importlib.import_module(f"agent.functions.{tool['function']['name']}").__dict__[tool["function"]["name"]]
            for tool in tools if tool["type"] == "pubmed"
        })
            
        ### ADD SERPAPI TOOLS IF AVAILABLE, ALL AS STATIC METHODS
        if 'SERPAPI_API_KEY' in os.environ:
            all_tools.update({
                tool["function"]["name"]: importlib.import_module(f"agent.functions.serpapi_tools").__dict__[tool["function"]["name"]]
            for tool in tools if tool["type"] == "serpapi"
        })
        return all_tools
            
    ### STATIC METHOD FOR TOOL EXECUTION, OFFLOADED TO REDIS WORKERS
    @staticmethod
    def execute_function_call(function_json,
                              all_tools):
        ### LOAD INPUTS AND TOOLS
        func_name = function_json.get("name")
        func_arguments = function_json.get("arguments", {})

        ### FUNCTION PARAMETERS
        if func_name not in all_tools:
            print(f"Error: function {func_name} does not exist")
            return None
        func = all_tools[func_name]
        expected_params = set(inspect.signature(func).parameters)

        ### CALL THE FUNCTION
        if set(func_arguments) <= expected_params:
            try:
                ### RETURN OUTPUT
                return func(**func_arguments)
            except TypeError as e:
                print(f"Error: Incorrect arguments provided. {e}")
                return None
        else:
            print(f"Error: Incorrect argument keys. Expected: {', '.join(expected_params)}")
            return None

    ### DEFINE A CHROMA EPHEMERAL VECTOR DATABASE FOR TOOL SELECTION
    def create_toolkit_db(self):
        timer = Timer()
        ### DEFINE THE DATABASE
        chroma_client = chromadb.EphemeralClient()
        embedding_function = OpenAIEmbeddingFunction(api_key=self.MyAgent.OPENAI_API_KEY, model_name="text-embedding-3-small")
        db = chroma_client.create_collection(name='toolset_vectorstore', embedding_function=embedding_function)
        db.add(
            documents=[tool['description'] for tool in self.tool_definitions],
            ids=[tool['name'] for tool in self.tool_definitions]
        )
        time_taken = timer.get_elapsed_time()
        print(f'==> Toolkit vector db created in {time_taken} seconds.')
        return db

    ### SELECT RELEVANT TOOLS FROM ALL AVAILABLE FOR EACH FUNCTION CALL
    def query_toolkit_db(self,
                         query):
        selected_tool_ids = self.toolkit_db.query(query_texts=query, include=['documents', 'distances'], n_results=self.n_available_tools)['ids'][0]
        return [tool for tool in self.tool_definitions if tool['name'] in selected_tool_ids]

