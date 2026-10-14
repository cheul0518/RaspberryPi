#!/usr/bin/env python3
# 라즈베리 파이 GPIO 제어 서버 (웹앱 2번 탭이 단축어 없이 직접 연결)
# 추가 설치 없이 동작: 파이썬 기본 웹 서버 + Raspberry Pi OS에 기본으로 있는 gpiozero, pinctrl
# https://user-root.local:8443/gpio/17/on   (on / off / toggle)  ← 웹앱이 쓰는 주소
# https://user-root.local:8443/gpio/all/off  (이 서버가 켠 핀 모두 끄기)
# https://user-root.local:8443/gpio          (GPIO2~27 실제 상태)
# http://user-root.local:8000/ca.crt         (아이폰에 설치할 인증서 받기, 처음 한 번)

import json
import re
import ssl
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gpiozero import OutputDevice

HTTP_PORT = 8000                     # 인증서 받기·테스트용 (http)
HTTPS_PORT = 8443                    # 웹앱용 (https)
CERT_DIR = '/etc/gpio-server'        # make-cert.sh 가 인증서를 만드는 곳
WEBAPP = 'https://cheul0518.github.io'   # 이 주소의 웹앱만 GPIO를 조작할 수 있음
ALLOWED = set(range(2, 28))          # GPIO2~27 (GPIO0·1은 HAT 정보용 핀이라 제외)
pins = {}                            # 이 서버가 켜고 끈 핀: {번호: OutputDevice}
lock = threading.Lock()


def device(pin):
    if pin not in pins:
        pins[pin] = OutputDevice(pin, initial_value=False)
    return pins[pin]


def read_all():
    # pinctrl 로 GPIO2~27의 실제 상태를 읽음 (다른 프로그램이 바꾼 것도 보임)
    # 줄 예: " 17: op dh pd | hi // GPIO17 = output"  → 모드 op(출력), 전압 hi(켜짐)
    state = {}
    try:
        out = subprocess.run(['pinctrl', 'get', '2-27'], capture_output=True, text=True, timeout=3).stdout
        for line in out.splitlines():
            m = re.match(r'\s*(\d+):\s+(\S+).*\|\s*(hi|lo)', line)
            if m and int(m.group(1)) in ALLOWED:
                mode = m.group(2)    # op = 출력, ip = 입력, no = 안 씀, a0~a8 = 다른 기능(I2C·SPI 등)
                state[m.group(1)] = {'mode': mode, 'on': mode == 'op' and m.group(3) == 'hi'}
    except (OSError, subprocess.SubprocessError):
        pass
    if not state:                    # pinctrl 이 없으면 이 서버가 기억하는 핀만
        state = {str(p): {'mode': 'op', 'on': bool(d.value)} for p, d in pins.items()}
    return state


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # 브라우저의 사전 확인: "X-GPIO 머리말을 붙여 보내도 돼?" → 우리 웹앱 주소에만 허락
        if self.headers.get('Origin') != WEBAPP:
            return self.reply(403, {'error': '허용되지 않은 웹사이트'})
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', WEBAPP)
        self.send_header('Access-Control-Allow-Headers', 'X-GPIO')
        self.send_header('Access-Control-Allow-Private-Network', 'true')   # 크롬 계열 브라우저용 (사설 네트워크 접속 허락)
        self.send_header('Access-Control-Max-Age', '600')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/')
        if path == '/ca.crt':        # 아이폰에 설치할 인증서 파일
            try:
                body = open(f'{CERT_DIR}/ca.crt', 'rb').read()
            except OSError:
                return self.reply(404, {'error': '인증서가 없어요. make-cert.sh 를 먼저 실행하세요'})
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-x509-ca-cert')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if path.startswith('/gpio/') and self.headers.get('X-GPIO') != '1':
            # 다른 웹사이트가 몰래 켜고 끄는 것 방지: 브라우저는 우리 웹앱에서만 이 머리말을 붙일 수 있음
            return self.reply(403, {'error': 'X-GPIO 머리말 없음'})
        m = re.fullmatch(r'/gpio/(\d+)/(on|off|toggle)', path)
        if m:
            pin, action = int(m.group(1)), m.group(2)
            if pin not in ALLOWED:
                return self.reply(400, {'error': f'GPIO{pin}는 사용할 수 없어요 (2~27만 가능)'})
            with lock:
                try:
                    dev = device(pin)
                except Exception as e:   # 다른 프로그램이 이미 쓰는 핀 등
                    return self.reply(409, {'error': f'GPIO{pin}을 쓸 수 없어요: {e}'})
                getattr(dev, action)()   # dev.on() / dev.off() / dev.toggle()
                on = bool(dev.value)
            print(f'GPIO{pin} → {"ON" if on else "OFF"}', flush=True)
            return self.reply(200, {'pin': pin, 'on': on})
        if path == '/gpio/all/off':
            with lock:
                for dev in pins.values():
                    dev.off()
            print('모든 GPIO → OFF', flush=True)
            return self.reply(200, {'all': 'off'})
        if path == '/gpio':
            return self.reply(200, read_all())
        self.reply(404, {'error': 'not found'})

    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', WEBAPP)   # 우리 웹앱만 결과를 읽을 수 있게 허용
        self.send_header('Cache-Control', 'no-store')          # 항상 최신 상태
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):    # 접속 기록은 생략 (GPIO 변경만 출력)
        pass


def serve_https():
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(f'{CERT_DIR}/server.crt', f'{CERT_DIR}/server.key')
    except OSError:
        print('https 꺼짐: 인증서가 없어요. make-cert.sh 를 먼저 실행하세요', flush=True)
        return
    httpd = ThreadingHTTPServer(('0.0.0.0', HTTPS_PORT), Handler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f'https 시작: 포트 {HTTPS_PORT}', flush=True)
    httpd.serve_forever()


if __name__ == '__main__':
    threading.Thread(target=serve_https, daemon=True).start()
    print(f'GPIO 서버 시작: 포트 {HTTP_PORT}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', HTTP_PORT), Handler).serve_forever()
