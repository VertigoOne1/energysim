#!/bin/python3

import sys
from envyaml import EnvYAML

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