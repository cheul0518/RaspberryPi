# pi 폴더 파일 설명 (한 줄씩)

라즈베리 파이에 설치하는 파일 5개.
- 핫스팟 자동 접속 (파트 1): `hotspot-priority.sh`, `.service`, `.timer` → 설치: [../README.md 3번](../README.md#3-파이가-핫스팟에-자동-접속하게-라즈베리-파이에서-한-번만)
- GPIO 제어 서버 (파트 2): `gpio-server.py`, `gpio-server.service` → 설치: [../README.md 5번](../README.md#5-파이에-gpio-서버-설치-라즈베리-파이에서-한-번만), 설명: [아래 4·5번](#4-gpio-serverpy-gpio-제어-서버)

| 파일 | 역할 | 설치 위치 |
|-----|-----|-----|
| `hotspot-priority.sh` | **실제 일을 하는 스크립트**: 핫스팟이 보이면 전환 | `/usr/local/bin/` |
| `hotspot-priority.service` | **무엇을** 실행할지 systemd에 알려 주는 설정 | `/etc/systemd/system/` |
| `hotspot-priority.timer` | **언제** 실행할지 (부팅 20초 후부터 30초마다) | `/etc/systemd/system/` |
| `gpio-server.py` | 아이폰 단축어의 요청을 받아 **GPIO를 켜고 끄는 작은 웹 서버** | `/usr/local/bin/` |
| `gpio-server.service` | GPIO 서버를 **부팅 때 켜고 계속 켜 두는** systemd 설정 | `/etc/systemd/system/` |

동작 순서: 부팅 → **timer**가 30초마다 → **service**를 실행 → service가 **sh 스크립트**를 실행 → 핫스팟이 보이면 전환

- `systemd`: 라즈베리 파이 OS에서 프로그램을 자동으로 켜고 끄고 반복 실행해 주는 관리자
- `.service` / `.timer`는 프로그램이 아니라 systemd가 읽는 **설정 파일**. 같은 이름(`hotspot-priority`)끼리 짝이 됨

<br><br><br>

## 1. `hotspot-priority.sh` (스크립트)

```bash
1  #!/bin/bash
2  # 아이폰 핫스팟이 보이면 핫스팟으로 전환 (1순위).
3  # 핫스팟이 없으면 아무것도 안 함 → NetworkManager가 기존 Wi-Fi(2순위)를 유지/재접속.
4  # 사용: hotspot-priority.sh "iPhone"   (따옴표 안은 아이폰 핫스팟 이름, systemd 타이머가 30초마다 실행)
5
6  HOTSPOT="$1"
7  IFACE="${2:-wlan0}"
8  [ -z "$HOTSPOT" ] && { echo "사용법: $0 \"핫스팟 이름\" [wlan0]"; exit 1; }
9
10 # 이미 핫스팟에 연결돼 있으면 끝
11 current=$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null)
12 [ "$current" = "$HOTSPOT" ] && exit 0
13
14 # 주변 Wi-Fi를 다시 검색해서 핫스팟이 보이면 전환
15 if nmcli -g SSID device wifi list ifname "$IFACE" --rescan yes 2>/dev/null | grep -Fxq "$HOTSPOT"; then
16     echo "핫스팟 '$HOTSPOT' 발견 → 전환"
17     nmcli connection up id "$HOTSPOT" ifname "$IFACE"
18 fi
```

| 줄 | 설명 |
|-----|-----|
| 1 | **셔뱅(shebang)**. 이 파일을 `bash`(리눅스 명령어 해석기)로 실행하라는 표시. 항상 첫 줄에 있어야 함 |
| 2~4 | `#`로 시작하는 줄은 **주석**(설명 메모). 실행되지 않음 |
| 5 | 빈 줄 (읽기 쉽게 띄움) |
| 6 | `HOTSPOT="$1"`: 실행할 때 넘겨준 **첫 번째 값**(`"iPhone"`)을 `HOTSPOT`이라는 변수에 저장. `$1` = 첫 번째 인자 |
| 7 | `IFACE="${2:-wlan0}"`: 두 번째 값이 있으면 그걸, 없으면 기본값 `wlan0`(파이의 Wi-Fi 장치 이름)을 `IFACE`에 저장. `${값:-기본값}` 문법 |
| 8 | `[ -z "$HOTSPOT" ]`: 핫스팟 이름이 **비어 있으면**(`-z` = 길이 0) 사용법을 출력(`echo`)하고 `exit 1`(오류로 종료). `&&` = 앞이 참이면 뒤를 실행. `$0` = 스크립트 자기 이름 |
| 10 | 주석 |
| 11 | `nmcli -g GENERAL.CONNECTION device show wlan0`: wlan0에 **지금 연결된 Wi-Fi 이름**을 가져옴. `$( ... )` = 명령 결과를 값으로 받기 → `current`에 저장. `2>/dev/null` = 오류 메시지는 버림 |
| 12 | 지금 연결된 이름이 핫스팟 이름과 **같으면**(`=`) 할 일이 없으니 `exit 0`(정상 종료) |
| 14 | 주석 |
| 15 | `nmcli -g SSID device wifi list ifname wlan0 --rescan yes`: 주변 Wi-Fi를 **새로 검색**(`--rescan yes`)해서 이름(SSID)만 한 줄씩 출력 → `\|`(파이프)로 넘겨서 `grep -Fxq "iPhone"`이 그 목록에 핫스팟 이름이 **정확히** 있는지 확인. `-F` 글자 그대로 비교, `-x` 한 줄 전체가 일치, `-q` 출력 없이 결과(있다/없다)만. `if ...; then` = 있으면 아래 실행 |
| 16 | 로그에 남길 메시지 출력 (`journalctl -u hotspot-priority`로 볼 수 있음) |
| 17 | `nmcli connection up id "iPhone" ifname wlan0`: 저장해 둔 `iPhone` 연결을 wlan0으로 **켜서 전환**. 기존 Wi-Fi(iptime)는 자동으로 끊김 |
| 18 | `fi`: `if` 끝 (if를 거꾸로 쓴 것) |

핫스팟이 안 보이면 15번 줄에서 조건이 거짓 → 아무것도 안 하고 끝 → 기존 Wi-Fi 그대로 유지.

<br><br><br>

## 2. `hotspot-priority.service` (무엇을 실행할지)

```ini
1  [Unit]
2  Description=Prefer iPhone hotspot over other Wi-Fi
3  After=NetworkManager.service
4
5  [Service]
6  Type=oneshot
7  # 따옴표 안은 아이폰 핫스팟 이름 (설정 → 일반 → 정보 → 이름)
8  ExecStart=/usr/local/bin/hotspot-priority.sh "iPhone"
```

| 줄 | 설명 |
|-----|-----|
| 1 | `[Unit]`: 이 서비스의 **기본 정보** 구역 시작 |
| 2 | `Description=`: 서비스 설명. `systemctl status`, 로그 등에 표시되는 이름표 |
| 3 | `After=NetworkManager.service`: 네트워크 관리자(NetworkManager)가 **먼저 켜진 뒤에** 실행. nmcli가 NetworkManager를 쓰기 때문 |
| 4 | 빈 줄 |
| 5 | `[Service]`: **실행 방법** 구역 시작 |
| 6 | `Type=oneshot`: 계속 켜져 있는 프로그램이 아니라 **한 번 실행하고 끝나는** 작업이라는 뜻. 반복은 timer가 담당 |
| 7 | 주석 |
| 8 | `ExecStart=`: 실제로 실행할 명령. 1번 스크립트를 `"iPhone"`(핫스팟 이름)과 함께 실행 → 스크립트의 `$1`이 됨 |

`[Install]` 구역이 없는 이유: 이 서비스는 혼자 켜지지 않고 **timer가 불러서** 실행되기 때문 (그래서 `enable`도 timer에만 함).

<br><br><br>

## 3. `hotspot-priority.timer` (언제 실행할지)

```ini
1  [Unit]
2  Description=Check for iPhone hotspot every 30 seconds
3
4  [Timer]
5  OnBootSec=20
6  OnUnitActiveSec=30
7  AccuracySec=5
8
9  [Install]
10 WantedBy=timers.target
```

| 줄 | 설명 |
|-----|-----|
| 1 | `[Unit]`: 기본 정보 구역 |
| 2 | `Description=`: 타이머 설명 (`systemctl list-timers`에 표시) |
| 3 | 빈 줄 |
| 4 | `[Timer]`: **실행 시각** 구역. 같은 이름의 `hotspot-priority.service`를 실행함 |
| 5 | `OnBootSec=20`: 부팅하고 **20초 뒤** 첫 실행 (Wi-Fi가 준비될 시간) |
| 6 | `OnUnitActiveSec=30`: 서비스가 마지막으로 실행된 뒤 **30초마다** 다시 실행. 숫자를 바꾸면 간격 조절 (예: 60 = 1분) |
| 7 | `AccuracySec=5`: 실행 시각 오차 허용 범위 5초. 기본값(1분)이면 30초 간격이 들쭉날쭉해지므로 좁혀 둠 |
| 8 | 빈 줄 |
| 9 | `[Install]`: `enable` 할 때 쓰는 구역 |
| 10 | `WantedBy=timers.target`: `systemctl enable` 하면 **부팅 때마다 자동으로 타이머가 켜지도록** 등록 (`timers.target` = 부팅 시 모든 타이머를 켜는 단계) |

<br><br><br>

## 4. `gpio-server.py` (GPIO 제어 서버)

```python
1  #!/usr/bin/env python3
2  # 라즈베리 파이 GPIO 제어 서버 (웹앱 2번 탭 → 아이폰 단축어 "GPIO 제어" → 이 서버)
3  # 추가 설치 없이 동작: 파이썬 기본 웹 서버 + Raspberry Pi OS에 기본으로 있는 gpiozero
4  # 주소 예: http://raspberrypi.local:8000/gpio/17/on   (on / off / toggle)
5  #          http://raspberrypi.local:8000/gpio/all/off  (쓴 핀 모두 끄기)
6  #          http://raspberrypi.local:8000/gpio          (지금 켜진 핀 목록)
7  
8  import json
9  import re
10 from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
11 
12 from gpiozero import OutputDevice
13 
14 PORT = 8000
15 ALLOWED = set(range(2, 28))  # GPIO2~27 (GPIO0·1은 HAT 정보용 핀이라 제외)
16 pins = {}                    # 한 번이라도 쓴 핀: {번호: OutputDevice}
17 
18 
19 def device(pin):
20     if pin not in pins:
21         pins[pin] = OutputDevice(pin, initial_value=False)
22     return pins[pin]
23 
24 
25 class Handler(BaseHTTPRequestHandler):
26     def do_GET(self):
27         path = self.path.split('?')[0].rstrip('/')
28         m = re.fullmatch(r'/gpio/(\d+)/(on|off|toggle)', path)
29         if m:
30             pin, action = int(m.group(1)), m.group(2)
31             if pin not in ALLOWED:
32                 return self.reply(400, {'error': f'GPIO{pin}는 사용할 수 없어요 (2~27만 가능)'})
33             dev = device(pin)
34             if action == 'on':
35                 dev.on()
36             elif action == 'off':
37                 dev.off()
38             else:
39                 dev.toggle()
40             print(f'GPIO{pin} → {"ON" if dev.value else "OFF"}', flush=True)
41             return self.reply(200, {'pin': pin, 'on': bool(dev.value)})
42         if path == '/gpio/all/off':
43             for dev in pins.values():
44                 dev.off()
45             print('모든 GPIO → OFF', flush=True)
46             return self.reply(200, {'all': 'off'})
47         if path == '/gpio':
48             return self.reply(200, {str(p): bool(d.value) for p, d in sorted(pins.items())})
49         self.reply(404, {'error': 'not found'})
50 
51     def reply(self, code, data):
52         body = json.dumps(data, ensure_ascii=False).encode()
53         self.send_response(code)
54         self.send_header('Content-Type', 'application/json; charset=utf-8')
55         self.send_header('Content-Length', str(len(body)))
56         self.end_headers()
57         self.wfile.write(body)
58 
59     def log_message(self, *args):  # 접속 기록은 생략 (GPIO 변경만 출력)
60         pass
61 
62 
63 if __name__ == '__main__':
64     print(f'GPIO 서버 시작: 포트 {PORT}', flush=True)
65     ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
```

| 줄 | 설명 |
|-----|-----|
| 1 | 셔뱅. 이 파일을 `python3`로 실행하라는 표시 (`/usr/bin/env`가 python3 위치를 찾아 줌) |
| 2~6 | 주석. 무슨 프로그램인지, 어떤 주소로 부르는지 |
| 8 | `import json`: 결과를 `{"pin": 17, "on": true}` 같은 JSON 글자로 만드는 도구 |
| 9 | `import re`: 정규식(글자 패턴 찾기) 도구. 주소에서 핀 번호·명령을 뽑을 때 사용 |
| 10 | 파이썬에 기본으로 들어 있는 **웹 서버** 도구 (추가 설치 불필요). `ThreadingHTTPServer` = 여러 요청을 동시에 처리 |
| 12 | `gpiozero`의 `OutputDevice`: GPIO 핀을 **출력용**(켜기/끄기)으로 쓰는 도구. Raspberry Pi OS 기본 포함, 파이 5 지원 |
| 14 | `PORT = 8000`: 서버가 받을 포트 번호. 주소 뒤의 `:8000` |
| 15 | `ALLOWED`: 제어를 허용할 GPIO 번호 2~27. `range(2, 28)` = 2부터 27까지. GPIO0·1은 HAT 정보용이라 제외 |
| 16 | `pins = {}`: 한 번이라도 쓴 핀을 기억하는 사전(번호 → 핀 객체) |
| 19~22 | `device(pin)`: 처음 쓰는 핀이면 `OutputDevice(pin, initial_value=False)`로 **꺼진 상태로** 준비해서 저장, 이미 있으면 그걸 돌려줌 |
| 25 | `class Handler`: 요청이 올 때마다 무엇을 할지 정하는 부분 |
| 26 | `do_GET`: 주소를 여는 요청(GET)이 오면 실행. 단축어의 "URL 콘텐츠 가져오기"가 GET 요청 |
| 27 | 주소에서 `?` 뒤를 버리고, 끝의 `/`도 지움 → 예: `/gpio/17/on` |
| 28 | 주소가 `/gpio/숫자/on·off·toggle` 형태인지 검사. `(\d+)` = 숫자 부분, `(on\|off\|toggle)` = 명령 부분 |
| 29~30 | 형태가 맞으면 숫자를 핀 번호(`int`), 명령을 `action`에 저장 |
| 31~32 | 허용 범위(2~27)가 아니면 400(잘못된 요청)과 오류 메시지를 돌려주고 끝 |
| 33 | 그 핀의 객체 가져오기 (19~22줄) |
| 34~39 | 명령대로 `on()` 켜기 / `off()` 끄기 / `toggle()` 반대로 |
| 40 | 서버 로그에 `GPIO17 → ON` 같은 줄 출력 (`journalctl -u gpio-server`로 봄). `flush=True` = 바로 기록 |
| 41 | 200(성공)과 `{"pin": 17, "on": true}` 를 돌려줌 |
| 42~46 | 주소가 `/gpio/all/off`면 쓴 핀을 전부 끄고 `{"all": "off"}` (웹앱의 "켜진 GPIO 모두 끄기") |
| 47~48 | 주소가 `/gpio`면 지금까지 쓴 핀들의 상태를 돌려줌 (예: `{"17": true}`) |
| 49 | 그 외 주소는 404(없음) |
| 51~57 | `reply`: 결과를 JSON 글자로 바꿔(`ensure_ascii=False` = 한글 그대로) 상태 코드·헤더와 함께 보내는 공통 함수 |
| 59~60 | 접속할 때마다 찍히는 기본 기록은 끔 (로그에는 GPIO 변경만 남김) |
| 63 | 이 파일을 직접 실행했을 때만 아래를 실행 (파이썬 관례) |
| 64 | 시작 메시지 출력 |
| 65 | `0.0.0.0` = 파이의 **모든 네트워크(핫스팟·iptime)** 에서 8000번 포트로 요청을 받고, `serve_forever()` = 끄기 전까지 계속 대기 |

<br><br><br>

## 5. `gpio-server.service` (GPIO 서버 자동 실행)

```ini
1  [Unit]
2  Description=GPIO control server for the iPhone web app
3  After=network.target
4  
5  [Service]
6  ExecStart=/usr/bin/python3 /usr/local/bin/gpio-server.py
7  Restart=always
8  RestartSec=3
9  
10 [Install]
11 WantedBy=multi-user.target
```

| 줄 | 설명 |
|-----|-----|
| 1 | `[Unit]`: 기본 정보 구역 |
| 2 | `Description=`: 서비스 설명 (`systemctl status gpio-server`에 표시) |
| 3 | `After=network.target`: 네트워크가 준비된 뒤에 시작 |
| 5 | `[Service]`: 실행 방법 구역 |
| 6 | `ExecStart=`: 실행할 명령. `python3`로 `/usr/local/bin/gpio-server.py` 실행. `User=`가 없으니 관리자(root) 권한으로 실행 → GPIO 접근 권한 문제 없음 |
| 7 | `Restart=always`: 서버가 어떤 이유로든 꺼지면 **자동으로 다시 켬** |
| 8 | `RestartSec=3`: 다시 켜기 전 3초 기다림 |
| 10 | `[Install]`: `enable` 할 때 쓰는 구역 |
| 11 | `WantedBy=multi-user.target`: `enable` 하면 **부팅 때마다 자동 시작** (`multi-user.target` = 부팅이 거의 끝난 일반 동작 단계) |

핫스팟용 `.service`(한 번 실행하고 끝, `Type=oneshot` + timer)와 달리, 이 서버는 **계속 켜져서 요청을 기다려야** 하므로 timer 없이 `Restart=always`로 항상 켜 둠.

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
