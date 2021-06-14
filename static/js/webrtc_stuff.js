var pc = null;
var dc = null;
var _pcid = -1;


function dc_onmessage(evt) {

    window._evt = evt;
    try {
        var msg = JSON.parse(evt.data);
        parse_message(msg);
    } catch (e) {
        console.log('not a JSON message on WebRTC datachannel', e);
        console.log(evt.data);
    }
}


function negotiate() {
    console.log(' *** this is negotiate()');

    var _answer = null;

    // #########################
    // ### GET offer from server:
    // #########################
    fetch('/offer')
    .then((response) => response.json())
    .then((offer) => {
        console.log("Offer:", offer);
        _pcid = offer.pcid;
        return pc.setRemoteDescription(offer);
    })
    .then(() => pc.createAnswer())
    .then((answer) => {
        _answer = answer;
        console.log("Answer:", answer);
        return pc.setLocalDescription(answer);
    }).then(() => {
        // #########################
        // ### POST answer to server:
        // #########################
        return fetch('/answer', {
            method: 'POST',
            body: JSON.stringify({
                sdp: _answer.sdp,
                type: _answer.type,
                pcid: _pcid
            }),
            headers: {
                'Content-Type': 'application/json'
            },
        });
    });
}


function start_webrtc() {
    var config = {
        //sdpSemantics: 'unified-plan',
        iceServers: [{urls: ['stun:stun.l.google.com:19302']}]
    };


    pc = new RTCPeerConnection(config);
    pc.addTransceiver('video', {direction: 'recvonly'});

    pc.addEventListener('datachannel', function (evt) {
        console.log(' **** this is on datachannel');
        dc = evt.channel;
        dc.addEventListener('message', dc_onmessage);
    });

    pc.addEventListener('icecandidate', function (evt) {
        console.log(' **** this is on icecandidate');
        console.log(evt);
        fetch('/ice_candidate', {
            method: 'POST',
            body: JSON.stringify({
                candidate: evt.candidate,
                pcid: _pcid
            }),
            headers: {
                'Content-Type': 'application/json'
            },
        });
    });

    // connect audio / video
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video') {
            console.log(' ontrack, video');
            document.getElementById('stream1').srcObject = evt.streams[0];
        } else {
            console.log(' ontrack, audio');
            //document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    negotiate();
}


