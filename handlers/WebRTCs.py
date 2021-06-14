"""
Copyright 2021 Mark Fassler
Licensed under the GPLv3.
"""

import sys
import time
import pprint
import json
import struct
import socket
import select
import asyncio
from aiohttp import web

import aiortc
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay

import handlers


def dc_on_close():
    print('this is dc_on_close')


class WebRTCs:
    def __init__(self):
        self.pcs = {}
        self.dcs = {}
        self._connection_counter = 0

        # open media source
        self._open_local_webcam()


    def _open_local_webcam(self):
        options = {"framerate": "30", "video_size": "640x480"}
        self._media_source_0 = MediaPlayer("/dev/video0", format="v4l2", options=options)


    def send_to_all(self, msg, dumbHack=False):
        to_delete = set()
        for dc in self.dcs:
            # AFAICT, the DataChannel doesn't like to do more than 5 messages per second.
            # so if the buffer is filling up, then we skip.
            #   see:  https://github.com/aiortc/aiortc/issues/462
            #print('dc:', dc.bufferedAmount)
            if dumbHack and dc.bufferedAmount > 50:
                pass
            else:
                try:
                    dc.send(msg)
                except Exception as ee:
                    pass

                    #print('failed to send msg:', ee)
                    #print('msg:', msg)
                    #print('dc.readyState:', dc.readyState)
                    #if dc.readyState in ["closing", "closed"]:
                    #    print('removing datachannel...')
                    #    to_delete.add(dc)

        if len(to_delete):
            for dc in to_delete:
                # hmm... how to make this work:
                #pc = self.dcs[dc]
                #pc.close()
                del self.dcs[dc]
            print('There are %d active datachannel(s)' % len(self.dcs))
            print('There are %d active peerconnections(s)' % len(self.pcs))


    async def get_offer(self, request):
        pc = RTCPeerConnection()
        pcid = self._connection_counter
        self._connection_counter += 1
        self.pcs[pcid] = pc

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print("ICE connection state is %s" % pc.iceConnectionState)
            if pc.iceConnectionState == "failed":
                print(' .... CLOSING PEER CONNECTION:')
                await pc.close()
                del self.pcs[pcid]

        @pc.on("close")
        async def on_pc_close():
            print('this is pc.on close')

        dc = pc.createDataChannel('myDataChannel')
        self.dcs[dc] = pc  # reverse-mapping to find my connection

        @dc.on('message')
        async def dc_on_message(message):
            print('dc, rx message:', message)
            sys.stdout.flush()
            if isinstance(message, str) and message.startswith("ping"):
                dc.send("pong" + message[4:])

        dc.on('close', dc_on_close)

        relay = MediaRelay()
        video = relay.subscribe(self._media_source_0.video)
        t = pc.addTransceiver('video', direction='sendonly')
        pc.addTrack(video)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        offerDict = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, 'pcid': pcid}

        #print(' TX offer:')
        #pprint.pprint(offerDict)
        print('\n  TX SDP offer:')
        print('-----------------------------------------------------------')
        print(pc.localDescription.sdp)
        print('-----------------------------------------------------------')
        sys.stdout.flush()

        return web.json_response(offerDict)


    async def post_answer(self, request):
        params = await request.json()
        #print(' RX answer:')
        #pprint.pprint(params)
        answer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        print('\n  RX SDP answer:')
        print('-----------------------------------------------------------')
        print(answer.sdp)
        print('-----------------------------------------------------------')
        sys.stdout.flush()

        pc = self.pcs[params['pcid']]

        await pc.setRemoteDescription(answer)
        return web.json_response({})


    async def post_ice_candidate(self, request):
        params = await request.json()
        print('  RX Ice Candidate:')
        pprint.pprint(params)
        sys.stdout.flush()

        pc = self.pcs[params['pcid']]
        try:
            candidate = aiortc.sdp.candidate_from_sdp(params['candidate']['candidate'])
            candidate.sdpMLineIndex = params['candidate']['sdpMLineIndex']
            candidate.sdpMid = params['candidate']['sdpMid']
        except:
            print('...failed to parse ice candidate')

        else:
            await pc.addIceCandidate(candidate)

        return web.json_response({})


    async def on_shutdown(self, app):
        print(" This is on_shutdown")
        # close peer connections
        coros = [pc.close() for pc in self.pcs.values()]
        await asyncio.gather(*coros)
        self.pcs.clear()


