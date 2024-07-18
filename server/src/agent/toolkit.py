import os
import re
import sys
import importlib
import subprocess
import json
import requests
import inspect
from termcolor import colored

class Toolkit:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.tools_json = f"{self.MyAgent.home}src/agent/tools.json"
        self.all_tools = self.load_tools()
        self.tool_definitions = self.load_tool_metadata()

    def read_tools(self):
        with open(self.tools_json, 'r') as file:
            return json.load(file)

    def load_tool_metadata(self):
        ### RETURN FUNCTION DEFINITIONS
        tools = self.read_tools()
        definitions = []
        for tool in tools:
            definitions.append(tool["function"])
        return definitions
    
    def load_tools(self):
        tools = self.read_tools()

        ### RETURN AVAILABLE TOOLS AS A LIST OF DICTIONARIES
        return {
            tool["function"]["name"]: importlib.import_module(f"agent.functions.{tool['function']['name']}").__dict__[tool["function"]["name"]]
            for tool in tools if tool["type"] == "function"
        }

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

