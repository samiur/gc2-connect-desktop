#!/usr/bin/env python3
"""Mock GSPro server for testing without GSPro."""

import json
import socket
import argparse
from datetime import datetime


def run_server(host: str = "0.0.0.0", port: int = 921):
    """Run a mock GSPro server."""
    print(f"Starting Mock GSPro Server on {host}:{port}")
    print("=" * 50)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        
        print("Waiting for connection...")
        
        while True:
            try:
                conn, addr = server.accept()
                print(f"\nClient connected from {addr}")
                
                with conn:
                    conn.settimeout(30.0)
                    
                    while True:
                        try:
                            data = conn.recv(4096)
                            
                            if not data:
                                print("Client disconnected")
                                break
                            
                            try:
                                message = json.loads(data.decode('utf-8'))
                                
                                # Pretty print the received shot
                                timestamp = datetime.now().strftime("%H:%M:%S")
                                shot_num = message.get('ShotNumber', '?')
                                
                                print(f"\n[{timestamp}] Shot #{shot_num} received:")
                                
                                ball_data = message.get('BallData', {})
                                print(f"  Ball Speed: {ball_data.get('Speed', 0):.1f} mph")
                                print(f"  Launch: {ball_data.get('VLA', 0):.1f}° / {ball_data.get('HLA', 0):.1f}°")
                                print(f"  Total Spin: {ball_data.get('TotalSpin', 0):.0f} RPM")
                                print(f"  Spin Axis: {ball_data.get('SpinAxis', 0):.1f}°")
                                
                                club_data = message.get('ClubData', {})
                                if message.get('ShotDataOptions', {}).get('ContainsClubData'):
                                    print(f"  Club Speed: {club_data.get('Speed', 0):.1f} mph")
                                    print(f"  Path: {club_data.get('Path', 0):.1f}°")
                                    print(f"  Face: {club_data.get('FaceToTarget', 0):.1f}°")
                                
                                # Send success response
                                response = {
                                    "Code": 200,
                                    "Message": "Shot received successfully",
                                    "Player": {
                                        "Handed": "RH",
                                        "Club": "DR"
                                    }
                                }
                                
                            except json.JSONDecodeError:
                                print(f"Invalid JSON received: {data}")
                                response = {
                                    "Code": 500,
                                    "Message": "Invalid JSON"
                                }
                            
                            conn.sendall(json.dumps(response).encode('utf-8'))
                            
                        except socket.timeout:
                            continue
                        except ConnectionResetError:
                            print("Client connection reset")
                            break
                            
            except KeyboardInterrupt:
                print("\nShutting down...")
                break


def main():
    parser = argparse.ArgumentParser(description='Mock GSPro Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=921, help='Port to listen on')
    args = parser.parse_args()
    
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
