#!/bin/python3

import sys
sys.path.append(r'./modules')

from apicontroller import db

print("Purge Database Schemas")

db.drop_all()

print("Purge done")