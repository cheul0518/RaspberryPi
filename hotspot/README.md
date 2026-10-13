# 아이폰 연동 - 핫스팟 (파트 1)

아이폰에서 앱처럼 실행되는 **버튼 1개짜리 웹앱**으로 아이폰의 **개인용 핫스팟을 켜고 끄기**.
라즈베리 파이를 휴대폰과 연결하기 위한 첫 단계 (파이가 아이폰 핫스팟에 자동 접속 → 이후 파트에서 파이 제어).

- 웹앱 주소: https://cheul0518.github.io/RaspberryPi/hotspot/
- 동작: 버튼을 누르면 눌린 채로 **ON** + 핫스팟 켜짐, 다시 누르면 원위치 **OFF** + 핫스팟 꺼짐
- 확인 환경: iPhone 17 (iOS 26), 홈 화면 웹앱 → 단축어 실행 → 웹앱으로 자동 복귀 동작 확인 (2026-10-13)

| OFF | ON |
|-----|-----|
| <img src="../images/hotspot_off.png" width="220"> | <img src="../images/hotspot_on.png" width="220"> |

<br><br><br>

## 구조
```
[홈 화면 아이콘(웹앱)] --버튼--> [단축어 앱: 핫스팟 켜기/끄기] --왼쪽 위 ◀ 로 복귀--> [같은 웹앱 화면: ON/OFF 표시]
```
- **웹앱**: HTML + CSS + JavaScript 한 파일(`index.html`). GitHub Pages로 무료 호스팅
- **단축어(Shortcuts)**: 아이폰 기본 앱. "개인용 핫스팟 설정" 동작으로 실제 핫스팟을 켜고 끔
- 단축어 실행 후 `webapp://` 주소(iOS 26)로 홈 화면 웹앱에 자동 복귀. 안 되면 왼쪽 위 **◀** 로 복귀 (새 탭은 생기지 않음)
- 파이가 아니라 인터넷(GitHub Pages)에 올린 이유: 핫스팟이 꺼진 상태에서도 페이지가 열려야 하기 때문

<br><br><br>

## 왜 단축어를 거쳐야 할까?
- iOS는 보안상 **웹페이지뿐 아니라 일반 앱(App Store 앱, Xcode로 만든 앱 포함)도 핫스팟을 직접 켜고 끄지 못하게** 막아 둠 (공개 API 없음)
- 대신 단축어 앱의 "개인용 핫스팟 설정" 동작은 허용됨 (iOS 16 이상)
- 그래서 웹앱은 URL 스킴 `shortcuts://`로 단축어를 실행하고, 끝나면 다시 웹앱으로 돌아오게 함
- 결론: Mac + Xcode로 네이티브 앱을 만들어도 단축어는 여전히 필요

<br><br><br>

## 설정 방법 (아이폰, 한 번만)

### 1. 단축어 2개 만들기
1. 단축어 앱 → 오른쪽 위 `+` → **동작 추가** → `핫스팟` 검색 → **"개인용 핫스팟 설정"** → "켜기" 그대로 → 이름 **`핫스팟 켜기`**
2. 만든 단축어를 길게 눌러 **복제** → 동작의 "켜기"를 **"끄기"**로 변경 → 이름 **`핫스팟 끄기`**
- 이름은 띄어쓰기까지 정확히 같아야 함 (코드의 `SHORTCUT_ON`, `SHORTCUT_OFF`와 일치)
- 단축어는 파일로 자동 설치 불가: iOS는 Apple 서명된 단축어 파일만 가져올 수 있고, 서명은 Mac에서만 가능

### 2. 홈 화면에 추가 (앱처럼 독립 창으로)
1. Safari에서 https://cheul0518.github.io/RaspberryPi/hotspot/ 열기
2. 공유 버튼 → **홈 화면에 추가** → **"웹 앱으로 열기" 켜기** → 이름 `핫스팟` → 추가
3. 이후엔 홈 화면 아이콘으로만 실행 (주소창 없는 독립 창, 실행할 때마다 Safari 탭이 생기지 않음)
4. 처음 누를 때 "단축어에서 열겠습니까?" 확인이 뜨면 열기
- 예전에 추가한 아이콘이 Safari 탭으로 열리면: 그 아이콘 삭제 → Safari 탭 정리 → 위 순서로 다시 추가

### 3. 파이가 핫스팟에 자동 접속하게 (라즈베리 파이에서 한 번만)
목표: **1순위 아이폰 핫스팟, 2순위 지금 쓰는 Wi-Fi**. 핫스팟이 켜지면 30초 안에 자동으로 넘어가고, 꺼지면 원래 Wi-Fi로 돌아감.

아이폰: 설정 → 개인용 핫스팟 → **"호환성 최대화"** 켜기 (연결 안정). 핫스팟 이름은 설정 → 일반 → 정보 → 이름.

**① 핫스팟 저장 + 우선순위 지정** (아이폰 핫스팟을 켜 둔 상태에서)
```bash
sudo nmcli dev wifi connect "핫스팟 이름" password "비밀번호"
nmcli -f NAME,TYPE,AUTOCONNECT-PRIORITY connection show   # 저장된 Wi-Fi 이름 확인

sudo nmcli connection modify "핫스팟 이름" connection.autoconnect-priority 10   # 1순위
sudo nmcli connection modify "지금 Wi-Fi 이름" connection.autoconnect-priority 5  # 2순위
```
- 우선순위 숫자가 클수록 먼저 접속 (부팅할 때 둘 다 보이면 핫스팟 선택)
- 핫스팟이 꺼지면 NetworkManager가 자동으로 2순위 Wi-Fi에 다시 접속

**② 이미 다른 Wi-Fi에 붙어 있을 때도 핫스팟으로 넘어가게**

NetworkManager는 이미 연결된 상태에서는 더 높은 순위 Wi-Fi가 나타나도 스스로 갈아타지 않음 (①의 순위는 부팅·재접속할 때만 적용). 그래서 30초마다 핫스팟이 보이는지 확인해서 전환하는 스크립트를 등록 ([pi/](./pi/)).

```bash
# 1) 파일 받기 (이미 받았다면 cd 후 git pull)
cd ~
git clone https://github.com/cheul0518/RaspberryPi.git
cd ~/RaspberryPi/hotspot/pi

# 2) 설치
sudo cp hotspot-priority.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/hotspot-priority.sh
sudo cp hotspot-priority.service hotspot-priority.timer /etc/systemd/system/

# 3) "핫스팟 이름"을 실제 이름으로 바꾸기 (①에서 저장한 이름과 똑같이)
sudo sed -i 's/핫스팟 이름/여기에 실제 핫스팟 이름/' /etc/systemd/system/hotspot-priority.service
grep ExecStart /etc/systemd/system/hotspot-priority.service   # 바뀌었는지 확인

# 4) 켜기
sudo systemctl daemon-reload
sudo systemctl enable --now hotspot-priority.timer

# 확인
systemctl list-timers hotspot-priority.timer     # 다음 실행 시각이 보이면 정상
journalctl -u hotspot-priority -n 20             # "핫스팟 발견 → 전환" 로그
nmcli -g GENERAL.CONNECTION device show wlan0    # 지금 연결된 Wi-Fi
```

주의할 점
- 스크립트는 **연결 이름 = 핫스팟 이름(SSID)** 이라고 가정. ①처럼 `nmcli dev wifi connect`로 저장하면 자동으로 같아짐. `nmcli connection show`에 보이는 이름을 그대로 쓰기
- 아이폰 핫스팟은 연결된 기기가 없으면 잠시 뒤 신호를 멈추거나 꺼짐 → 파이가 못 찾으면 아이폰에서 **설정 → 개인용 핫스팟 화면을 열어 둔 채** 30초 정도 기다리기
- 30초마다 주변 Wi-Fi를 검색하므로 그 순간 Wi-Fi가 아주 잠깐 느려질 수 있음 (간격은 `.timer`의 `OnUnitActiveSec`로 조절)
- 핫스팟을 끄면 NetworkManager가 자동으로 ②순위 Wi-Fi에 다시 접속 (스크립트는 핫스팟으로 "넘어가는" 일만 함)
- 끄려면: `sudo systemctl disable --now hotspot-priority.timer`

<br><br><br>

## 코드 핵심 (`index.html`)
```js
const SHORTCUT_ON = '핫스팟 켜기';
const SHORTCUT_OFF = '핫스팟 끄기';

// 버튼을 누르면: 화면을 먼저 ON/OFF로 바꾸고 단축어 실행
const back = encodeURIComponent('webapp://' + location.host + location.pathname);  // 홈 화면 웹앱 주소
const url = 'shortcuts://x-callback-url/run-shortcut?name=' + encodeURIComponent(이름)
  + '&x-success=' + back + '&x-cancel=' + back + '&x-error=' + back;
location.href = url;
```
- 버튼 상태는 단축어를 부르기 **전에** `localStorage`에 저장 → 단축어 실행 후 왼쪽 위 **◀** 로 돌아오면 같은 탭, 같은 화면
- 자동 복귀는 `x-callback-url`의 `x-success`에 `webapp://도메인/경로` 사용 (iOS 26부터 홈 화면 웹앱을 여는 주소). `https://`로 돌아오게 하면 Safari **새 탭**이 생김
- `webapp://`은 경로·파라미터를 무시하고 앱만 열어서, 상태는 단축어 실행 **전에** 저장. 일부 iOS 버전에서는 "주소가 유효하지 않음" 오류가 난다는 보고도 있음 → 그때는 **◀** 로 복귀
- 공백은 반드시 `%20`으로 인코딩 (`URLSearchParams`는 공백을 `+`로 바꿔 단축어 이름이 안 맞음)
- 눌린 버튼 효과: CSS에서 `transform: scale(.92)` + 안쪽 그림자(`inset box-shadow`)

<br><br><br>

## 문제 해결
| 증상 | 원인 / 해결 |
|-----|-----|
| "'핫스팟 끄기' 단축어를 찾을 수 없습니다" | 단축어가 없거나 이름이 다름 → 위 1번대로 이름 정확히 만들기 |
| 버튼 표시와 실제 핫스팟 상태가 다름 | 웹앱은 실제 상태를 읽을 수 없음 (제어센터에서 따로 바꾼 경우) → 한 번 더 누르면 맞춰짐 |
| 실행할 때마다 Safari 새 탭이 생김 | 홈 화면 아이콘이 Safari 탭으로 열리는 상태. 아이콘 삭제 → 탭 정리 → **"웹 앱으로 열기" 켜고** 다시 추가 (2번 참고) |
| 단축어 실행 후 단축어 앱에 머묾 / "주소가 유효하지 않음" | 이 iOS에서 `webapp://` 복귀가 안 되는 경우. 핫스팟은 이미 바뀌었으니 왼쪽 위 **◀** 로 돌아가기 |
| 단축어 실행에 실패했는데 버튼은 바뀜 | 버튼을 한 번 더 눌러 맞추기 (단축어 이름 확인) |
| 파이가 핫스팟에 안 붙음 | "호환성 최대화" 켜기, 핫스팟 설정 화면을 열어 둔 채 기다리기, `journalctl -u hotspot-priority`로 로그 확인 |
| 파이가 핫스팟으로 안 넘어감 | 서비스 파일의 핫스팟 이름이 `nmcli connection show`의 이름과 정확히 같은지 확인 |

<br><br><br>

## 공개 범위
- GitHub Pages는 저장소별 설정 → 이 저장소만 웹 주소가 생기고, 다른 저장소는 영향 없음
- 주소를 아는 사람은 페이지를 열 수 있지만, 버튼은 **누른 사람 폰의 단축어**만 실행 → 남이 내 핫스팟을 조작할 수 없음
- 개인정보·비밀번호 없음

<br><br><br>

## 다음 파트 예정
- 파트 2: 핫스팟으로 연결된 라즈베리 파이 제어 (LED 등, 파이에서 FastAPI 서버 + 웹앱)
