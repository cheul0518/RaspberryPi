#!/bin/bash
# 아이폰 핫스팟이 보이면 핫스팟으로 전환 (1순위).
# 핫스팟이 없으면 아무것도 안 함 → NetworkManager가 기존 Wi-Fi(2순위)를 유지/재접속.
# 사용: hotspot-priority.sh "iPhone"   (따옴표 안은 아이폰 핫스팟 이름, systemd 타이머가 30초마다 실행)

HOTSPOT="$1"
IFACE="${2:-wlan0}"
[ -z "$HOTSPOT" ] && { echo "사용법: $0 \"핫스팟 이름\" [wlan0]"; exit 1; }

# 이미 핫스팟에 연결돼 있으면 끝
current=$(nmcli -g GENERAL.CONNECTION device show "$IFACE" 2>/dev/null)
[ "$current" = "$HOTSPOT" ] && exit 0

# 주변 Wi-Fi를 다시 검색해서 핫스팟이 보이면 전환
if nmcli -g SSID device wifi list ifname "$IFACE" --rescan yes 2>/dev/null | grep -Fxq "$HOTSPOT"; then
    echo "핫스팟 '$HOTSPOT' 발견 → 전환"
    nmcli connection up id "$HOTSPOT" ifname "$IFACE"
fi
