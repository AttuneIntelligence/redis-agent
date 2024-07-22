import os
import sys
from gevent import monkey
monkey.patch_all()
from flask import Flask, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from flask import Flask, request, Response
import time
from flask_socketio import SocketIO
from gunicorn.app.base import BaseApplication
import json
from concurrent.futures import ThreadPoolExecutor
import logging

sys.path.append('/workspace/redis-agent/src')
from my_agent import MyAgent

##########################
### REDIS AGENT SERVER ###
##########################

### SET LOGGING
logging.basicConfig(level=logging.ERROR)
print_logger = logging.getLogger('print')
print_logger.setLevel(logging.INFO)

def print(*args, **kwargs):
    print_logger.info(' '.join(map(str, args)))

### DEFINE EXECUTION
executor = ThreadPoolExecutor()
app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
CORS(app, resources={r"/chat": {"origins": "http://localhost:3000"}})
socketio = SocketIO(app, cors_allowed_origins="http://localhost:3000")
app.secret_key = os.urandom(24)

### INITIALIZATION
MyAgent = MyAgent()

### PRIMARY CHAT ENDPOINT
@app.route('/chat', methods=['OPTIONS'])
def chat_options():
    response = app.make_default_options_response()
    headers = response.headers

    headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    headers['Access-Control-Allow-Headers'] = 'Content-Type'

    return response

@app.route('/chat', methods=['POST'])
def chat():
    global MyAgent
    client_request = request.get_json()

    def generate():
        for chunk in MyAgent.server_execute(user_json=client_request):
            yield chunk

    return Response(generate(), content_type='text/plain')


@app.errorhandler(HTTPException)
def handle_exception(e):
    response = e.get_response()
    
    response.data = json.dumps({
        "status": e.code,
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"

    return response

class FlaskApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(FlaskApplication, self).__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

def run_gunicorn_server():
    options = {
        'bind': '0.0.0.0:5000',
        'workers': 1,
        'threads': 1,
        'timeout': 600,
        'worker_class': 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker',
        'proc_name': 'indra-server'
    }
    FlaskApplication(app, options).run()


if __name__ == "__main__":
    os.environ['FLASK_ENV'] = 'production'
    run_gunicorn_server()