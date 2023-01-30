#!/bin/python3

import json, os
from flask import Flask, Blueprint
from envyaml import EnvYAML

if "CONFIG_FILE" in os.environ:
    print("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    print("Loading Development Config")
    config = EnvYAML('config.yml')

APP_NAME = config['general']['app_name']

health_bp = Blueprint('health_bp', __name__)

@health_bp.route("/" + APP_NAME + '/api/v1/actuator/health')
def health_act():
    d = {}
    d["status"] = "UP"
    return json.dumps(d)