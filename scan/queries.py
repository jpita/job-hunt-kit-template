#!/usr/bin/env python3
"""Print the JavaScript line that gives harvest-google.js your queries.

  python3 scan/queries.py

Inject the output into the Google tab before harvest-google.js.
"""
import json

import config

print("window._GROUPS = " + json.dumps(config.GOOGLE_QUERIES) + ";")
