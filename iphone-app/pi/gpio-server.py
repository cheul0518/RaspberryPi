#!/usr/bin/env python3
# 라즈베리 파이 GPIO 제어 서버 (웹앱 2번 탭 → 아이폰 단축어 "GPIO 제어" → 이 서버)
# 추가 설치 없이 동작: 파이썬 기본 웹 서버 + Raspberry Pi OS에 기본으로 있는 gpiozero
# 주소 예: http://user-root.local:8000/gpio/17/on   (on / off / toggle)
#          http://user-root.local:8000/gpio/all/off  (쓴 핀 모두 끄기)
#          http://user-root.local:8000/gpio          (지금 켜진 핀 목록)

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gpiozero import OutputDevice

PORT = 8000
ALLOWED = set(range(2, 28))  # GPIO2~27 (GPIO0·1은 HAT 정보용 핀이라 제외)
pins = {}                    # 한 번이라도 쓴 핀: {번호: OutputDevice}


def device(pin):
    if pin not in pins:
        pins[pin] = OutputDevice(pin, initial_value=False)
    return pins[pin]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/')
        m = re.fullmatch(r'/gpio/(\d+)/(on|off|toggle)', path)
        if m:
            pin, action = int(m.group(1)), m.group(2)
            if pin not in ALLOWED:
                return self.reply(400, {'error': f'GPIO{pin}는 사용할 수 없어요 (2~27만 가능)'})
            dev = device(pin)
            if action == 'on':
                dev.on()
            elif action == 'off':
                dev.off()
            else:
                dev.toggle()
            print(f'GPIO{pin} → {"ON" if dev.value else "OFF"}', flush=True)
            return self.reply(200, {'pin': pin, 'on': bool(dev.value)})
        if path == '/gpio/all/off':
            for dev in pins.values():
                dev.off()
            print('모든 GPIO → OFF', flush=True)
            return self.reply(200, {'all': 'off'})
        if path == '/gpio':
            return self.reply(200, {str(p): bool(d.value) for p, d in sorted(pins.items())})
        self.reply(404, {'error': 'not found'})

    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # 접속 기록은 생략 (GPIO 변경만 출력)
        pass


if __name__ == '__main__':
    print(f'GPIO 서버 시작: 포트 {PORT}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
