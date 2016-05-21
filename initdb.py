#!/usr/bin/env python
# coding: utf-8
import sys
import os
from config import db


if __name__ == '__main__':
    schema = open(os.path.join(os.path.dirname(sys.argv[0]), 'schema.sql')).read().split(';')
    for st in schema:
        db.query(st)
