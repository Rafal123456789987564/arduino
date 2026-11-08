#!/usr/bin/env python3
"""Launch CYD Studio and open browser only after verified HTTP readiness.

Uses an available loopback port instead of showing a dead 127.0.0.1:8765 tab.
Keeps server attached to the console: close the console to stop the server.
"""
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def port_is_available(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def find_port():
    for port in range(8765, 8800):
        if port_is_available(port):
            return port
    raise RuntimeError('Brak wolnego portu HTTP 8765-8799.')

def server_ready(port):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=0.5)
    try:
        conn.request('GET', '/api/status')
        res = conn.getresponse()
        data = res.read(8192)
        return res.status == 200 and json.loads(data).get('online') is True
    except (OSError, ValueError, TimeoutError):
        return False
    finally:
        conn.close()

def main():
    if not (ROOT/'studio_server.py').is_file() or not (ROOT/'index.html').is_file():
        print('BLAD: Rozpakuj caly folder CYD Studio z ZIP (index.html i studio_server.py).', flush=True)
        return 1
    try:
        port=find_port()
    except RuntimeError as exc:
        print('BLAD:', exc, flush=True)
        return 1
    env=os.environ.copy()
    env['CYD_STUDIO_PORT']=str(port)
    env['CYD_STUDIO_NO_BROWSER']='1'
    url=f'http://127.0.0.1:{port}/'
    print('CYD STUDIO - uruchamianie...', flush=True)
    print('Serwer:',url, flush=True)
    process=subprocess.Popen([sys.executable,'-u',str(ROOT/'studio_server.py')], cwd=str(ROOT),env=env)
    try:
        for _ in range(60):
            if process.poll() is not None:
                print('BLAD: Serwer zakonczyl prace. Kod:', process.returncode, flush=True)
                return 1
            if server_ready(port):
                print('SERWER GOTOWY. Otwieram przegladarke:',url, flush=True)
                if os.environ.get('CYD_STUDIO_NO_BROWSER') != '1':
                    if not webbrowser.open(url):
                        print('Otworz recznie:',url, flush=True)
                print('Nie zamykaj tego okna, gdy korzystasz z CYD Studio.',flush=True)
                return process.wait()
            time.sleep(0.15)
        print('BLAD: Serwer nie odpowiedzial na /api/status. Sprawdz komunikaty powyzej.', flush=True)
        return 1
    except KeyboardInterrupt:
        print('Zatrzymywanie CYD Studio...', flush=True)
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired: process.kill()

if __name__=='__main__':
    raise SystemExit(main())