import os
from dotenv import load_dotenv

def set_keys(MyAgent):
    ### LOOK FOR .ENV
    try:
        load_dotenv()
    except:
        pass

    ### SET KEYS
    MyAgent.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")