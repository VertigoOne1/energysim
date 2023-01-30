#!/bin/python3

import sys, os
from envyaml import EnvYAML
from modules.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

print("Check for existing database, create if not")

from sqlalchemy_utils import create_database, database_exists

try:
    if not database_exists(config["sqlalchemy"]["db_url"]):
        create_database(config["sqlalchemy"]["db_url"],"utf8mb4")
except:
    print("Error creating database!")

print("Setup database and schema")

from modules.database import init_db
init_db()

print("Setup database complete")