import os, time, json, sys
sys.path.append(r'./modules')
from flask import jsonify, request, Flask
from envyaml import EnvYAML
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from datetime import datetime, timezone
from prometheus_client import make_wsgi_app
from pprint import pformat
from threading import Thread
import logic
import modules.bpm as bpm
from modules.defroutes import health_bp
from modules.database import db_session
from modules.logger import setup_custom_logger
import models, metrics

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

APP_NAME = config['general']['app_name']
TOPIC_PREFIX = config['kafka']['kafka_topic_prefix']

app = Flask(__name__)
app.register_blueprint(health_bp)

# @app.teardown_appcontext
# def shutdown_session(exception=None):
#     db_session.remove()

#Prometheus Exporter
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    f"/metrics": make_wsgi_app()
})

@app.route("/" + APP_NAME + '/requeue', methods=['POST'])
def msg_requeue():
    response = {}
    response["status"] = ""
    db_id = request.json.get('id', '')
    if db_id:
        if logic.requeue_message(db_id):
            response["status"] = "success"
            return json.dumps(response)
        else:
            response["status"] = "failed_likely_bad_id"
            return json.dumps(response)
    else:
        response["status"] = "failed_bad_json"
        return json.dumps(response)

class FlaskThread(Thread):
    def run(self):
        app.run(
            host='0.0.0.0',
            port=config['flask']['default_port'],
            debug=config['flask']['debug_enabled'],
            use_debugger=config['flask']['debug_enabled'],
            use_reloader=False)