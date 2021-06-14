#!/usr/bin/env python3
"""
Using a single webcam, broadcast video to multiple web-browsers using WebRTC.

Copyright 2021 Mark Fassler
Licensed under the GPLv3.
"""

import logging
import ssl
import asyncio
from aiohttp import web
import handlers

try:
    import config
except:
    config = {}

# One object to manage all WebRTC connections:
webrtcs = handlers.WebRTCs()


if __name__ == "__main__":

    if hasattr(config, 'LOGLEVEL'):
        logging.basicConfig(level=config.LOGLEVEL)


    app = web.Application()


    # Static web pages:
    app.router.add_get("/", handlers.get_index)
    app.router.add_static('/static/', path='static')

    # This is to create the WebRTC channel:
    app.router.add_get("/offer", webrtcs.get_offer)
    app.router.add_post("/answer", webrtcs.post_answer)
    app.router.add_post("/ice_candidate", webrtcs.post_ice_candidate)
    app.on_shutdown.append(webrtcs.on_shutdown)

    print('http://localhost:3000/')
    web.run_app(app, port=3000)

