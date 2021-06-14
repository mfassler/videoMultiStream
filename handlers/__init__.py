"""
Copyright 2021 Mark Fassler
Licensed under the GPLv3.
"""

import os
import pprint
from aiohttp import web

from .WebRTCs import WebRTCs

ROOT = os.path.join(os.path.dirname(__file__), '../')


async def get_index(request):
    content = open(os.path.join(ROOT, 'static', "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)

