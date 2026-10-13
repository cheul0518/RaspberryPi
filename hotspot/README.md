# 아이폰 연동 - 핫스팟 (파트 1)

아이폰에서 앱처럼 실행되는 **버튼 1개짜리 웹앱**으로 아이폰의 **개인용 핫스팟을 켜고 끄기**.
라즈베리 파이를 휴대폰과 연결하기 위한 첫 단계 (파이가 아이폰 핫스팟에 자동 접속 → 이후 파트에서 파이 제어).

- 웹앱 주소: https://cheul0518.github.io/RaspberryPi/hotspot/
- 동작: 버튼을 누르면 눌린 채로 **ON** + 핫스팟 켜짐, 다시 누르면 원위치 **OFF** + 핫스팟 꺼짐

| OFF | ON |
|-----|-----|
| <img src="../images/hotspot_off.png" width="220"> | <img src="../images/hotspot_on.png" width="220"> |

<br><br><br>

## 구조
```
[홈 화면 아이콘(웹앱)] --버튼--> [단축어 앱: 핫스팟 켜기/끄기] --실행 후 복귀--> [웹앱: ON/OFF 표시]
```
- **웹앱**: HTML + CSS + JavaScript 한 파일(`index.html`). GitHub Pages로 무료 호스팅
- **단축어(Shortcuts)**: 아이폰 기본 앱. "개인용 핫스팟 설정" 동작으로 실제 핫스팟을 켜고 끔
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

### 2. 홈 화면에 추가
1. Safari에서 https://cheul0518.github.io/RaspberryPi/hotspot/ 열기
2. 공유 버튼 → **홈 화면에 추가** → 이름 `핫스팟`
3. 처음 누를 때 단축어 실행 허용 확인이 뜨면 허용

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

NetworkManager는 연결된 상태에서는 더 높은 순위 Wi-Fi가 나타나도 스스로 바꾸지 않음. 그래서 30초마다 핫스팟이 보이는지 확인해서 전환하는 스크립트를 등록 ([pi/](./pi/)).
```bash
# 저장소의 hotspot/pi 폴더에서
sudo cp hotspot-priority.sh /usr/local/bin/
sudo cp hotspot-priority.service hotspot-priority.timer /etc/systemd/system/
sudo nano /etc/systemd/system/hotspot-priority.service   # "핫스팟 이름"을 실제 이름으로 수정
sudo systemctl daemon-reload
sudo systemctl enable --now hotspot-priority.timer

# 확인
systemctl list-timers hotspot-priority.timer
journalctl -u hotspot-priority -n 20     # "핫스팟 발견 → 전환" 로그
nmcli -g GENERAL.CONNECTION device show wlan0   # 지금 연결된 Wi-Fi
```
- 핫스팟을 30초마다 검색할 때 Wi-Fi가 아주 잠깐 느려질 수 있음 (간격은 `.timer`의 `OnUnitActiveSec`로 조절)
- 끄려면: `sudo systemctl disable --now hotspot-priority.timer`

<br><br><br>

## 코드 핵심 (`index.html`)
```js
const SHORTCUT_ON = '핫스팟 켜기';
const SHORTCUT_OFF = '핫스팟 끄기';

// 버튼을 누르면: 화면을 먼저 ON/OFF로 바꾸고 단축어 실행
const url = 'shortcuts://x-callback-url/run-shortcut?name=' + encodeURIComponent(이름)
  + '&x-success=' + encodeURIComponent(이 페이지 + '?s=on')   // 성공 → 이 페이지로 복귀
  + '&x-cancel='  + encodeURIComponent(이 페이지 + '?s=off')  // 취소/실패 → 원래 상태로
  + '&x-error='   + encodeURIComponent(이 페이지 + '?s=off');
location.href = url;
```
- **x-callback-url**: 단축어 실행 후 `x-success` 주소로 돌아오게 하는 iOS 규칙
- 돌아온 주소의 `?s=on / ?s=off`를 읽어 버튼 상태 결정, `localStorage`에 저장해서 다시 열어도 유지
- 공백은 반드시 `%20`으로 인코딩 (`URLSearchParams`는 공백을 `+`로 바꿔 단축어 이름이 안 맞음)
- 눌린 버튼 효과: CSS에서 `transform: scale(.92)` + 안쪽 그림자(`inset box-shadow`)

<br><br><br>

## 문제 해결
| 증상 | 원인 / 해결 |
|-----|-----|
| "'핫스팟 끄기' 단축어를 찾을 수 없습니다" | 단축어가 없거나 이름이 다름 → 위 1번대로 이름 정확히 만들기 |
| 버튼 표시와 실제 핫스팟 상태가 다름 | 웹앱은 실제 상태를 읽을 수 없음 (제어센터에서 따로 바꾼 경우) → 한 번 더 누르면 맞춰짐 |
| 단축어 실행 후 Safari 탭으로 열림 | 정상. 홈 화면 아이콘을 Safari로 열리게 하려면 추가할 때 "웹 앱으로 열기" 끄기 |
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
