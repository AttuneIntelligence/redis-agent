from datetime import datetime
import subprocess
import re
import time
import tiktoken
import json
import redis
import sys

sys.path.append('/workspace/redis-agent')
from bin.utilities import *

class Memory:
    def __init__(self,
                 MyAgent):
        self.MyAgent = MyAgent
        self.redis_connection = redis.Redis(host=MyAgent.redis_host, port=MyAgent.redis_port)

    def ingress_memory(self, 
                       user_id,
                       message_thread,
                       question, 
                       response):
        timer = Timer()
        
        ### COMPRESS CHAT HISTORY IF NECESSARY BEFORE INGRESS
        context_token_len = len(self.MyAgent.OpenAI.tokenizer.encode(str([message["content"] for message in message_thread])))
        if context_token_len > self.MyAgent.memory_token_len:
            print(f"==> Summarizing chat history before Redis ingress...")
            compressed_messages, summary_metadata = self.summarize_message_thread(message_thread)
            curated_chat_thread = [{"role": "assistant", "content": compressed_messages[0]["content"]}]
        else:
            curated_chat_thread = message_thread
            summary_metadata = {}
        
        ### ADD MOST RECENT INTERACTION TO REDIS INGRESS
        # curated_chat_thread.append({'role': 'user', 'content': question})   ### ADDED BY AGENT EXECUTION
        curated_chat_thread.append({'role': 'assistant', 'content': response})
    
        ### UPDATE DATABASE
        json_chat = {'chat_history': curated_chat_thread}

        ### UPDATE CHAT HISTORY IN REDIS
        self.redis_connection.set(
            user_id,
            json.dumps(json_chat).encode('utf-8'),
        )

        ### RETURN SUMMARY COMPILATION METADATA
        time_taken = timer.get_elapsed_time()
        summary_cost = summary_metadata.get('cost', None)
        if summary_cost:
            print(f"==> Conversation thread summarized for ${round(summary_cost, 3)} ({time_taken} seconds).")
        return summary_metadata
    
    def egress_memory(self, 
                      user_id):

        ### PULL CHAT THREAD FROM REDIS
        egress_thread = self.redis_connection.get(user_id)

        ### CHECK CONTENT AND RETURN
        if not egress_thread:
            egress_thread = {'chat_history': [{"role": "system", "content": "This is the beginning of your conversation."}]}
        else:
            egress_thread = json.loads(egress_thread)
        return egress_thread
            
    def summarize_message_thread(self,
                                 conversation_messages):
        ### KEEP MESSAGE THREAD SMALL BY SUMMARIZING CONTEXT WITH SECONDARY MODEL
        summarization_template = self.MyAgent.Utilities.read_prompt_template(template_name="summarize_conversation_template")
        summarized_conversation_thread, summary_metadata = self.MyAgent.OpenAI.invoke_gpt(
            question=str(conversation_messages),
            system_prompt=summarization_template,
            secondary_model=True
        )
        
        ### COMPILE NEW MESSAGES
        new_system_message = {
            "role": "assistant",
            "content": f"### Current Conversation Summary\n{summarized_conversation_thread[-1]['content']}", 
        }
        return [new_system_message], summary_metadata



