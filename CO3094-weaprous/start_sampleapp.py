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

peer_list = []

app = WeApRous()

@app.route('/register', methods=['POST'])
def register_peer(headers, body):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    print(f"[Tracker] Received registration request, body: {body}")
    try:
        peer_info = json.loads(body)
        if 'ip' not in peer_info or 'port' not in peer_info:
             return {"error": "Invalid peer info. 'ip' and 'port' are required."}
             
        if peer_info not in peer_list:
            peer_list.append(peer_info)
            print(f"[Tracker] Registered new peer: {peer_info}")
        else:
            print(f"[Tracker] Peer already registered: {peer_info}")
            
        return {"status": "registered", "peers": peer_list}
        
    except json.JSONDecodeError:
        print("[Tracker] Invalid JSON received for registration.")
        return {"error": "Invalid JSON body"}
    except Exception as e:
        print(f"[Tracker] Error processing registration: {e}")
        return {"error": str(e)}

@app.route('/get-list', methods=['GET'])
def get_peer_list(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print(f"[Tracker] Peer list requested. Sending {len(peer_list)} peers.")
    return peer_list

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(
        prog='TrackerApp', 
        description='Tracker Server for P2P Chat', 
        epilog='WeApRous daemon'
    )
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    print(f"[Tracker] Starting Tracker server on {ip}:{port}")
    app.prepare_address(ip, port)
    app.run()