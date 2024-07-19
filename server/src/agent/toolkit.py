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

class Toolkit:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.tools_json = f"{self.MyAgent.home}src/agent/tools.json"
        self.all_tools = self.load_tools()
        self.tool_definitions = self.load_tool_metadata()
        self.n_function_responses = 3
        
        ### LIMIT TOOLSET IF SERPAPI IS UNAVAILABLE
        if self.MyAgent.SERPAPI_API_KEY is not None:
            self.serpapi_available = True
        else:
            self.serpapi_available = False
            
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
        default_tools =  {
            tool["function"]["name"]: importlib.import_module(f"agent.functions.{tool['function']['name']}").__dict__[tool["function"]["name"]]
            for tool in tools if tool["type"] == "function"
        }

        return default_tools
            

    ### STATIC METHOD FOR TOOL EXECUTION, OFFLOADED TO REDIS WORKERS
    @staticmethod
    def execute_function_call(function_json,
                              all_tools):
        ### LOAD INPUTS AND TOOLS
        func_name = function_json.get("name")
        func_arguments = function_json.get("arguments", {})

        ### LIMIT FUNCTION RESPONSES
        function_json['n_results'] = self.n_function_responses

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
            
    ####################################
    ### ADDITIONAL SERPAPI FUNCTIONS ###
    ####################################
    def web_search(self, 
                   query,
                   site=None,
                   engine="duckduckgo"):
        ### DEFINE INPUT QUERY
        input_query = f"{query} site:{site}"
        
        ### UTILIZE SERPAPI FOR SEARCH
        params = {
            "q": input_query,
            "engine": engine,
            "api_key": self.MyAgent.SERPAPI_API_KEY
        }
        search = GoogleSearch(params)
        search_results = search.get_dict()
        # return search_results

        ### PARSE RESULTS TO STRING
        final_results = []
        try:
            if len(search_results['organic_results']) != 0:
                for i in search_results['organic_results'][:self.n_function_responses]:
                    response = {
                        'title': i.get('title', ''),
                        'url': i.get('link', ''),
                        'description': i.get('snippet', ''),
                        'source': i.get('source', ''),
                    }
                    final_results.append(response)
            return final_results
        except:
            return None


    ### DEFINE SEARCH OF SPECIFIC WEBSITES ###
    ##########################################
    def twitter(self, query):
        return self.web_search(query, site="twitter.com")
        
    def neurips(self, query):
        return self.web_search(query, site="proceedings.neurips.cc")
        
    # def youtube(self, query):
    #     return self.web_search(query, site="site:youtube.com")
        
    def github(self, query):
        github_query = f"{query} repository"
        return self.web_search(query, site="github.com")

    ### US PATENT AND TRADEMARK OFFICE ###
    def uspto(self,
              query):
        ### UTILIZE SERPAPI FOR SEARCH OF USPTO
        params = {
            "q": query,
            "engine": "google_patents",
            "api_key": self.MyAgent.SERPAPI_API_KEY
        }
        search = GoogleSearch(params)
        search_results = search.get_dict()

        ### PARSE RESULTS TO STRING
        final_results = []
        try:
            if len(search_results['organic_results']) != 0:
                for i in search_results['organic_results'][:self.n_function_responses]:
                    response = {
                        'title': i.get('title', ''),
                        'url': i.get('pdf', ''),
                        'description': i.get('snippet', ''),
                        'patent_number': i.get('publication_number', ''),
                        'inventor': i.get('inventor', ''),
                        'date_filed': i.get('filing_date', '')
                    }
                    final_results.append(response)
            return final_results
        except:
            return None

    ### SEARCH GOOGLE SCHOLAR
    def scholar_authors(self, 
                        query):
        ### DEFINE DISTINCT ENGINE FOR GOOGLE SCHOLAR
        params = {
            "q": query,
            "engine": "google_scholar",
            "api_key": self.MyAgent.SERPAPI_API_KEY,
            "num": self.n_function_responses
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        # return results

        ### EXTRACT SCHOLARLY DATA
        try:
            data = []
            if not results.get('profiles', {}).get('authors'):
                return None
            else:
                for i in results['profiles']['authors'][:self.n_function_responses]:
                    response = {
                        'name': i.get('name', ''),
                        'affiliation': i.get('affiliations', ''),
                        'cited_by': i.get('cited_by', ''),
                        'url': i.get('link', ''),
                        'scholar_id': i.get('author_id', ''),
                    }
                    data.append(response)
            return response
        except Exception as e:
            print(f"Error! {e}")
            return None
        



