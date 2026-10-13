# pi 폴더 파일 설명 (한 줄씩)

라즈베리 파이가 **아이폰 핫스팟을 1순위로 자동 접속**하게 만드는 파일 3개.
설치 방법은 [../README.md 3번](../README.md#3-파이가-핫스팟에-자동-접속하게-라즈베리-파이에서-한-번만) 참고.

| 파일 | 역할 | 설치 위치 |
|-----|-----|-----|
| `hotspot-priority.sh` | **실제 일을 하는 스크립트**: 핫스팟이 보이면 전환 | `/usr/local/bin/` |
| `hotspot-priority.service` | **무엇을** 실행할지 systemd에 알려 주는 설정 | `/etc/systemd/system/` |
| `hotspot-priority.timer` | **언제** 실행할지 (부팅 20초 후부터 30초마다) | `/etc/systemd/system/` |

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

## 수정한 뒤에는
`/etc/systemd/system/`의 `.service`나 `.timer`를 고쳤다면:
```bash
sudo systemctl daemon-reload                     # 바뀐 설정 다시 읽기
sudo systemctl restart hotspot-priority.timer    # 타이머 다시 시작
```
`/usr/local/bin/hotspot-priority.sh`를 고쳤다면 다음 실행(30초 이내)부터 바로 반영.
