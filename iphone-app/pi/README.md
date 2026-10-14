# pi 폴더 파일 설명 (한 줄씩)

라즈베리 파이에 설치하는 파일 6개.
- 핫스팟 자동 접속 (파트 1): `hotspot-priority.sh`, `.service`, `.timer` → 설치: [../README.md 3번](../README.md#3-파이가-핫스팟에-자동-접속하게-라즈베리-파이에서-한-번만)
- GPIO 제어 서버 (파트 2): `gpio-server.py`, `gpio-server.service`, `make-cert.sh` → 설치: [../README.md 4번](../README.md#4-파이에-gpio-서버-설치-라즈베리-파이에서-한-번만), 설명: 아래 4·5·6번

| 파일 | 역할 | 설치 위치 |
|-----|-----|-----|
| `hotspot-priority.sh` | **실제 일을 하는 스크립트**: 핫스팟이 보이면 전환 | `/usr/local/bin/` |
| `hotspot-priority.service` | **무엇을** 실행할지 systemd에 알려 주는 설정 | `/etc/systemd/system/` |
| `hotspot-priority.timer` | **언제** 실행할지 (부팅 20초 후부터 30초마다) | `/etc/systemd/system/` |
| `gpio-server.py` | 웹앱의 요청을 받아 **GPIO를 켜고 끄고, 실제 상태를 알려 주는 작은 웹 서버** | `/usr/local/bin/` |
| `gpio-server.service` | GPIO 서버를 **부팅 때 켜고 계속 켜 두는** systemd 설정 | `/etc/systemd/system/` |
| `make-cert.sh` | 웹앱이 `https`로 접속할 수 있게 **인증서를 만드는** 스크립트 (처음 한 번 실행) | 복사 안 함, 결과는 `/etc/gpio-server/` |

동작 순서: 부팅 → **timer**가 30초마다 → **service**를 실행 → service가 **sh 스크립트**를 실행 → 핫스팟이 보이면 전환

- `systemd`: 라즈베리 파이 OS에서 프로그램을 자동으로 켜고 끄고 반복 실행해 주는 관리자
- `.service` / `.timer`는 프로그램이 아니라 systemd가 읽는 **설정 파일**. 같은 이름(`hotspot-priority`)끼리 짝이 됨

<br><br><br>

> 코드 바로 옆 `#` 뒤가 설명. 화면이 좁으면 코드 칸을 옆으로 밀어서 보기
> 여기 코드는 **읽기용** (설명을 붙여 둔 것). 설치할 때는 README의 `sudo cp ...` 명령으로 이 폴더의 원본 파일을 복사

<br>

## 1. `hotspot-priority.sh` (스크립트)

```bash
#!/bin/bash                          # 셔뱅: 이 파일을 bash(명령어 해석기)로 실행하라는 표시. 항상 첫 줄
# 아이폰 핫스팟이 보이면 ...          # '#'로 시작하는 줄 = 주석(메모). 실행 안 됨 (원본 2~4줄)

HOTSPOT="$1"                         # 실행할 때 준 첫 번째 값("iPhone")을 HOTSPOT 변수에 저장. $1 = 첫 번째 값
IFACE="${2:-wlan0}"                  # 두 번째 값이 없으면 기본값 wlan0(파이의 Wi-Fi 장치 이름)을 IFACE에 저장
[ -z "$HOTSPOT" ] && { echo "사용법: $0 \"핫스팟 이름\" [wlan0]"; exit 1; }
                                     # ↑ 핫스팟 이름이 비어 있으면(-z = 길이 0) 사용법을 출력하고 오류로 종료(exit 1)
                                     #   && = 앞이 참이면 뒤를 실행, $0 = 스크립트 자기 이름

current=$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null)
                                     # ↑ wlan0에 지금 연결된 Wi-Fi 이름을 current에 저장
                                     #   $( ... ) = 명령 결과를 값으로 받기, 2>/dev/null = 오류 메시지는 버림
[ "$current" = "$HOTSPOT" ] && exit 0
                                     # ↑ 이미 핫스팟(iPhone)에 연결돼 있으면 할 일이 없으니 정상 종료(exit 0)

if nmcli -g SSID device wifi list ifname "$IFACE" --rescan yes 2>/dev/null | grep -Fxq "$HOTSPOT"; then
                                     # ↑ 주변 Wi-Fi를 새로 검색(--rescan yes)해서 이름(SSID)만 한 줄씩 출력
                                     #   | (파이프) = 그 목록을 grep에 넘김
                                     #   grep -Fxq "iPhone" = 목록에 iPhone이 정확히 있는지 확인
                                     #   (-F 글자 그대로, -x 한 줄 전체 일치, -q 출력 없이 있다/없다만)
                                     #   if ...; then = 있으면 아래 두 줄 실행
    echo "핫스팟 '$HOTSPOT' 발견 → 전환"  # 로그에 남길 메시지 (journalctl -u hotspot-priority 로 봄)
    nmcli connection up id "$HOTSPOT" ifname "$IFACE"
                                     # ↑ 저장해 둔 iPhone 연결을 켜서 전환. 기존 Wi-Fi(iptime)는 자동으로 끊김
fi                                   # if 끝 (if를 거꾸로 쓴 것)
                                     # 핫스팟이 안 보이면 아무것도 안 하고 끝 → 기존 Wi-Fi 그대로
```

<br><br><br>

## 2. `hotspot-priority.service` (무엇을 실행할지)

```ini
[Unit]                               # 이 서비스의 기본 정보 구역 시작
Description=Prefer iPhone hotspot over other Wi-Fi
                                     # ↑ 서비스 설명. systemctl status, 로그에 보이는 이름표
After=NetworkManager.service         # 네트워크 관리자가 먼저 켜진 뒤에 실행 (nmcli가 NetworkManager를 쓰기 때문)

[Service]                            # 실행 방법 구역 시작
Type=oneshot                         # 계속 켜져 있는 프로그램이 아니라 한 번 실행하고 끝나는 작업. 반복은 timer가 담당
ExecStart=/usr/local/bin/hotspot-priority.sh "iPhone"
                                     # ↑ 실제로 실행할 명령. 1번 스크립트를 "iPhone"(핫스팟 이름)과 함께 실행
                                     #   → 스크립트 안에서 $1 = iPhone

                                     # [Install] 구역이 없는 이유: 혼자 켜지지 않고 timer가 불러서 실행되기 때문
                                     # (그래서 enable도 timer에만 함)
```

<br><br><br>

## 3. `hotspot-priority.timer` (언제 실행할지)

```ini
[Unit]                               # 기본 정보 구역
Description=Check for iPhone hotspot every 30 seconds
                                     # ↑ 타이머 설명 (systemctl list-timers 에 보임)

[Timer]                              # 실행 시각 구역. 같은 이름의 hotspot-priority.service를 실행함
OnBootSec=20                         # 부팅하고 20초 뒤 첫 실행 (Wi-Fi가 준비될 시간)
OnUnitActiveSec=30                   # 마지막 실행 뒤 30초마다 다시 실행. 60으로 바꾸면 1분 간격
AccuracySec=5                        # 실행 시각 오차 5초까지만 허용 (기본 1분이면 30초 간격이 들쭉날쭉)

[Install]                            # enable 할 때 쓰는 구역
WantedBy=timers.target               # enable 하면 부팅 때마다 이 타이머가 자동으로 켜짐
```

<br><br><br>

## 4. `gpio-server.py` (GPIO 제어 서버)

```python
#!/usr/bin/env python3               # 셔뱅: 이 파일을 python3로 실행하라는 표시
# 라즈베리 파이 GPIO 제어 서버 ...    # 주석(원본 2~7줄): 무슨 프로그램인지, 어떤 주소로 부르는지

import json                          # 결과를 {"pin": 17, "on": true} 같은 JSON 글자로 만드는 도구
import re                            # 정규식(글자 패턴 찾기) 도구. 주소에서 핀 번호·명령을 뽑을 때 사용
import ssl                           # https(암호화 연결) 도구
import subprocess                    # 다른 명령(pinctrl)을 실행하고 결과를 받는 도구
import threading                     # 두 서버(http·https)를 동시에 돌리는 도구
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
                                     # ↑ 파이썬 기본 웹 서버 도구 (추가 설치 불필요)
                                     #   ThreadingHTTPServer = 여러 요청을 동시에 처리

from gpiozero import OutputDevice    # GPIO 핀을 출력용(켜기/끄기)으로 쓰는 도구. Raspberry Pi OS 기본 포함, 파이 5 지원

HTTP_PORT = 8000                     # http 포트: 인증서 받기(/ca.crt)·테스트용
HTTPS_PORT = 8443                    # https 포트: 웹앱이 쓰는 주소 = user-root.local:8443
CERT_DIR = '/etc/gpio-server'        # make-cert.sh 가 인증서를 만드는 폴더
WEBAPP = 'https://cheul0518.github.io'   # 이 주소의 웹앱만 GPIO를 조작할 수 있음
ALLOWED = set(range(2, 28))          # 제어 허용 GPIO 2~27 (range(2, 28) = 2부터 27까지). GPIO0·1은 HAT 정보용이라 제외
pins = {}                            # 이 서버가 켜고 끈 핀을 기억하는 사전 {번호: 핀}
lock = threading.Lock()              # 두 요청이 동시에 같은 핀을 건드리지 않게 하는 자물쇠


def device(pin):                     # 핀 번호를 주면 그 핀을 돌려주는 함수
    if pin not in pins:              # 처음 쓰는 핀이면
        pins[pin] = OutputDevice(pin, initial_value=False)   # 꺼진 상태로 준비해서 저장
    return pins[pin]                 # 저장된 핀을 돌려줌


def read_all():                      # GPIO2~27 의 실제 상태를 읽는 함수
    state = {}
    try:
        out = subprocess.run(['pinctrl', 'get', '2-27'], capture_output=True, text=True, timeout=3).stdout
                                     # ↑ 파이 5 기본 명령 pinctrl 로 핀 상태를 읽음 (다른 프로그램이 바꾼 것도 보임)
                                     #   한 줄 예: " 17: op dh pd | hi // GPIO17 = output"
        for line in out.splitlines():    # 한 줄씩
            m = re.match(r'\s*(\d+):\s+(\S+).*\|\s*(hi|lo)', line)
                                     # ↑ 줄에서 핀 번호(17), 모드(op), 전압(hi/lo)을 뽑음
            if m and int(m.group(1)) in ALLOWED:
                mode = m.group(2)    # op = 출력, ip = 입력, no = 안 씀, a0~a8 = 다른 기능(I2C·SPI 등)
                state[m.group(1)] = {'mode': mode, 'on': mode == 'op' and m.group(3) == 'hi'}
                                     # ↑ "켜짐" = 출력(op)이면서 전압이 높음(hi)
    except (OSError, subprocess.SubprocessError):
        pass                         # pinctrl 실행이 실패하면 그냥 넘어감
    if not state:                    # pinctrl 결과가 없으면 이 서버가 기억하는 핀만 알려 줌
        state = {str(p): {'mode': 'op', 'on': bool(d.value)} for p, d in pins.items()}
    return state


class Handler(BaseHTTPRequestHandler):   # 요청이 올 때마다 무엇을 할지 정하는 부분
    def do_OPTIONS(self):            # 브라우저의 사전 확인 ("X-GPIO 표시를 붙여 보내도 돼?")
        if self.headers.get('Origin') != WEBAPP:   # 요청한 웹사이트가 우리 웹앱이 아니면
            return self.reply(403, {'error': '허용되지 않은 웹사이트'})   # 거절 → 브라우저가 본 요청을 아예 안 보냄
        self.send_response(204)      # 204 = 허락 (내용 없음)
        self.send_header('Access-Control-Allow-Origin', WEBAPP)   # 우리 웹앱에만
        self.send_header('Access-Control-Allow-Headers', 'X-GPIO')   # X-GPIO 표시를 붙여도 된다고 허락
        self.send_header('Access-Control-Allow-Private-Network', 'true')   # 크롬 계열 브라우저용 (사설 네트워크 접속 허락)
        self.send_header('Access-Control-Max-Age', '600')   # 이 허락을 600초 동안 기억
        self.end_headers()

    def do_GET(self):                # 주소를 여는 요청(GET)이 오면 실행
        path = self.path.split('?')[0].rstrip('/')    # 주소에서 ? 뒤와 끝의 / 를 지움 → 예: /gpio/17/on
        if path == '/ca.crt':        # 아이폰이 인증서를 받으러 오면
            try:
                body = open(f'{CERT_DIR}/ca.crt', 'rb').read()   # 인증서 파일을 읽음
            except OSError:          # 파일이 없으면 (make-cert.sh 안 함)
                return self.reply(404, {'error': '인증서가 없어요. make-cert.sh 를 먼저 실행하세요'})
            self.send_response(200)
            self.send_header('Content-Type', 'application/x-x509-ca-cert')   # "인증서 파일"이라고 알림 → 아이폰이 설치 화면을 띄움
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if path.startswith('/gpio/') and self.headers.get('X-GPIO') != '1':
            return self.reply(403, {'error': 'X-GPIO 머리말 없음'})
                                     # ↑ 켜고 끄는 요청에 X-GPIO 표시가 없으면 거절
                                     #   브라우저는 위 do_OPTIONS 허락을 받은 웹사이트(우리 웹앱)만 이 표시를 붙일 수 있음
                                     #   → 다른 웹사이트가 내 아이폰을 이용해 몰래 켜고 끄는 것을 막음
        m = re.fullmatch(r'/gpio/(\d+)/(on|off|toggle)', path)
                                     # ↑ 주소가 /gpio/숫자/on·off·toggle 모양인지 검사
        if m:                        # 모양이 맞으면
            pin, action = int(m.group(1)), m.group(2)   # 숫자 → 핀 번호, 명령 → action (예: 17, 'on')
            if pin not in ALLOWED:   # 2~27이 아니면 400(잘못된 요청)
                return self.reply(400, {'error': f'GPIO{pin}는 사용할 수 없어요 (2~27만 가능)'})
            with lock:               # 자물쇠를 잠그고
                try:
                    dev = device(pin)    # 그 핀 가져오기
                except Exception as e:   # 다른 프로그램이 이미 쓰는 핀이면 409(충돌)
                    return self.reply(409, {'error': f'GPIO{pin}을 쓸 수 없어요: {e}'})
                getattr(dev, action)()   # dev.on() 켜기 / dev.off() 끄기 / dev.toggle() 반대로
                on = bool(dev.value)     # 지금 켜져 있는지
            print(f'GPIO{pin} → {"ON" if on else "OFF"}', flush=True)
                                     # ↑ 로그에 "GPIO17 → ON" 출력 (journalctl -u gpio-server 로 봄)
            return self.reply(200, {'pin': pin, 'on': on})   # 200(성공)과 {"pin": 17, "on": true}
        if path == '/gpio/all/off':  # 웹앱의 "켜진 GPIO 모두 끄기"
            with lock:
                for dev in pins.values():
                    dev.off()        # 이 서버로 켠 핀을 전부 끔
            print('모든 GPIO → OFF', flush=True)
            return self.reply(200, {'all': 'off'})
        if path == '/gpio':          # 실제 상태 보기 (웹앱이 2초마다 부름)
            return self.reply(200, read_all())
        self.reply(404, {'error': 'not found'})   # 그 외 주소는 404(없음)

    def reply(self, code, data):     # 결과를 보내는 공통 함수
        body = json.dumps(data, ensure_ascii=False).encode()   # JSON 글자로 바꿈 (ensure_ascii=False = 한글 그대로)
        self.send_response(code)     # 상태 코드 (200 성공 / 400 잘못된 요청 / 404 없음 / 409 충돌)
        self.send_header('Content-Type', 'application/json; charset=utf-8')   # "내용은 JSON"이라고 알림
        self.send_header('Content-Length', str(len(body)))   # 내용 길이
        self.send_header('Access-Control-Allow-Origin', WEBAPP)
                                     # ↑ 우리 웹앱(GitHub 주소)만 결과를 읽을 수 있게 허용. 없으면 웹앱이 답을 못 읽음
        self.send_header('Cache-Control', 'no-store')   # 저장해 둔 옛날 답 말고 항상 새로 받게 함
        self.end_headers()           # 머리말 끝
        self.wfile.write(body)       # 내용 보내기

    def log_message(self, *args):    # 접속할 때마다 찍히는 기본 기록은 끔
        pass                         # (2초마다 상태 읽기가 로그를 채우지 않게. GPIO 변경만 남김)


def serve_https():                   # https 서버 (웹앱용)
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)   # https 설정 만들기
        ctx.load_cert_chain(f'{CERT_DIR}/server.crt', f'{CERT_DIR}/server.key')   # make-cert.sh 가 만든 인증서·키
    except OSError:                  # 인증서가 없으면 https 는 켜지 않음 (http 8000 은 계속 동작)
        print('https 꺼짐: 인증서가 없어요. make-cert.sh 를 먼저 실행하세요', flush=True)
        return
    httpd = ThreadingHTTPServer(('0.0.0.0', HTTPS_PORT), Handler)   # 8443번 포트로 같은 Handler 사용
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)   # 연결을 https 로 감쌈
    print(f'https 시작: 포트 {HTTPS_PORT}', flush=True)
    httpd.serve_forever()            # 끌 때까지 계속 요청을 기다림


if __name__ == '__main__':           # 이 파일을 직접 실행했을 때만 아래 실행 (파이썬 관례)
    threading.Thread(target=serve_https, daemon=True).start()   # https 서버를 옆에서 따로 실행
    print(f'GPIO 서버 시작: 포트 {HTTP_PORT}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', HTTP_PORT), Handler).serve_forever()
                                     # ↑ http 서버. 0.0.0.0 = 파이의 모든 네트워크(핫스팟·iptime)에서 받음
```

<br><br><br>

## 5. `gpio-server.service` (GPIO 서버 자동 실행)

```ini
[Unit]                               # 기본 정보 구역
Description=GPIO control server for the iPhone web app
                                     # ↑ 서비스 설명 (systemctl status gpio-server 에 보임)
After=network.target                 # 네트워크가 준비된 뒤에 시작

[Service]                            # 실행 방법 구역
ExecStart=/usr/bin/python3 /usr/local/bin/gpio-server.py
                                     # ↑ 실행할 명령: python3로 gpio-server.py 실행
                                     #   User= 가 없으니 관리자(root) 권한 → GPIO 권한 문제 없음
Restart=always                       # 서버가 어떤 이유로든 꺼지면 자동으로 다시 켬
RestartSec=3                         # 다시 켜기 전 3초 기다림

[Install]                            # enable 할 때 쓰는 구역
WantedBy=multi-user.target           # enable 하면 부팅 때마다 자동 시작 (multi-user.target = 부팅이 거의 끝난 단계)

                                     # 핫스팟용 .service(한 번 실행하고 끝 + timer)와 달리
                                     # 이 서버는 계속 켜져서 요청을 기다려야 하므로 Restart=always로 항상 켜 둠
```

<br><br><br>

## 6. `make-cert.sh` (https 인증서 만들기)

```bash
#!/bin/bash                          # 셔뱅: bash로 실행
# GPIO 서버용 https 인증서 만들기 ... # 주석(원본 2~6줄)

set -e                               # 중간에 오류가 나면 바로 멈춤
NAME=$(hostname)                     # 파이 이름을 NAME에 저장 (이 파이는 user-root)
DIR=/etc/gpio-server                 # 인증서를 둘 폴더
mkdir -p "$DIR"                      # 폴더 만들기 (-p = 이미 있으면 그냥 넘어감)
cd "$DIR"                            # 그 폴더로 이동

if [ ! -f ca.key ]; then             # ca.key 파일이 없을 때만 (= 처음 실행할 때만)
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout ca.key -out ca.crt -subj "/CN=$NAME GPIO CA" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign" \
        -addext "nameConstraints=critical,permitted;DNS:$NAME.local"
                                     # ↑ 직접 만든 "인증 기관"(ca.crt + 비밀 키 ca.key). 10년(3650일) 유효
                                     #   이름 = "user-root GPIO CA" (아이폰 설정에 이 이름으로 보임)
                                     #   CA:TRUE = 다른 인증서에 서명할 수 있는 인증서라는 뜻
                                     #   nameConstraints = user-root.local 주소에만 쓸 수 있게 제한
                                     #   (키가 새도 은행·포털 같은 다른 사이트를 흉내 낼 수 없음)
                                     #   다시 만들면 아이폰에 다시 설치해야 해서 한 번만 만듦
fi

openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/CN=$NAME.local"
                                     # ↑ 서버용 비밀 키(server.key)와 서명 요청서(server.csr) 만들기
printf "subjectAltName=DNS:%s.local\nbasicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n" "$NAME" > server.ext
                                     # ↑ 서버 인증서에 넣을 정보: 주소 user-root.local, 서버용(serverAuth)
                                     #   아이폰은 이 정보가 없으면 인증서를 받아 주지 않음
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days 825 -out server.crt -extfile server.ext
                                     # ↑ 인증 기관(ca)이 서버 인증서(server.crt)에 서명. 825일 = 아이폰이 허용하는 최대 기간
                                     #   825일(약 2년 3개월)이 지나면 이 스크립트를 다시 실행 → restart (아이폰은 다시 설치 안 해도 됨)
rm -f server.csr server.ext          # 다 쓴 임시 파일 지우기
chmod 600 ca.key server.key          # 비밀 키는 관리자만 읽을 수 있게

echo "완료: $DIR 에 인증서를 만들었어요 (주소: $NAME.local)"   # 끝 메시지
```

<br><br><br>

## 수정한 뒤에는
`/etc/systemd/system/`의 `.service`나 `.timer`를 고쳤다면:
```bash
sudo systemctl daemon-reload                     # 바뀐 설정 다시 읽기
sudo systemctl restart hotspot-priority.timer    # 핫스팟 타이머 다시 시작
sudo systemctl restart gpio-server               # GPIO 서버 다시 시작
```
- `/usr/local/bin/hotspot-priority.sh`를 고쳤다면 다음 실행(30초 이내)부터 바로 반영
- `/usr/local/bin/gpio-server.py`를 고쳤다면 `sudo systemctl restart gpio-server` 필요 (계속 켜져 있는 프로그램이라 다시 시작해야 반영)
- GitHub에서 새 버전을 받았다면: `cd ~/RaspberryPi && git pull` 후 위 설치 명령의 `sudo cp ...`를 다시 실행하고 restart
