#!/bin/bash

# Force install MySQL connector first
pip install mysql-connector-python

# Then install everything else from requirements.txt
pip install -r requirements.txt
