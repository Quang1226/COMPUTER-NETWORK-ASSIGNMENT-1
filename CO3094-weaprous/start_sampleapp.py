#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

app = WeApRous()

active_peers = []

@app.route('/submit-info', methods=['POST'])
def handle_submit_info(headers, body):
    global active_peers
    print(f"[Tracker] Received /submit-info, body: {body}")
    
    try:
        # 1. Parse body 
        peer_data = json.loads(body)
        username = peer_data.get('username')
        ip = peer_data.get('ip')
        port = peer_data.get('port')

        if not username or not ip or not port:
            raise ValueError("'username', 'ip', and 'port' are required")

        new_peer = {'username': username, 'ip': ip, 'port': int(port)}

        # 2. Check and update (Tracker update)
        found = False
        for i, peer in enumerate(active_peers):
            if peer['username'] == username:
                active_peers[i] = new_peer
                found = True
                break
        if not found:
            active_peers.append(new_peer) 

        print(f"[Tracker] Peer registered/updated: {new_peer}")
        print(f"[Tracker] Current active peers: {active_peers}")
        
        # 3. Return response (status, body_string)
        response_body = json.dumps({"status": "success", "message": f"{username} registered"})
        return '200 OK', response_body

    except Exception as e:
        print(f"[Tracker] Error /submit-info: {e}")
        response_body = json.dumps({"status": "error", "message": str(e)})
        return '400 Bad Request', response_body

@app.route('/get-list', methods=['GET'])
def handle_get_list(headers, body):
    global active_peers
    print(f"[Tracker] Request /get-list. Returning {len(active_peers)} peers.")
    
    try:
        # Return peer list as JSON
        response_body = json.dumps({"status": "success", "peers": active_peers})
        
        # Return response (status, body_string)
        return '200 OK', response_body
    except Exception as e:
        print(f"[Tracker] Error /get-list: {e}")
        response_body = json.dumps({"status": "error", "message": str(e)})
        return '500 Internal Server Error', response_body

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()