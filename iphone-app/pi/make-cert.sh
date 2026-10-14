#!/bin/bash
# GPIO 서버용 https 인증서 만들기 (처음 한 번만)
# 사용: sudo bash make-cert.sh
# 만드는 파일 (/etc/gpio-server/):
#   ca.crt, ca.key         = 직접 만든 "인증 기관" (아이폰에 ca.crt 를 설치하고 신뢰)
#   server.crt, server.key = 이 파이 주소(user-root.local)의 인증서 (ca 가 서명)

set -e                                   # 중간에 오류가 나면 바로 멈춤
NAME=$(hostname)                         # 파이 이름 (예: user-root)
DIR=/etc/gpio-server
mkdir -p "$DIR"
cd "$DIR"

if [ ! -f ca.key ]; then                 # 인증 기관은 처음 한 번만 만듦 (다시 만들면 아이폰에 다시 설치해야 함)
    openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
        -keyout ca.key -out ca.crt -subj "/CN=$NAME GPIO CA" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"
fi

openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "/CN=$NAME.local"
printf "subjectAltName=DNS:%s.local\nbasicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n" "$NAME" > server.ext
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days 825 -out server.crt -extfile server.ext   # 825일 = 아이폰이 허용하는 최대 기간
rm -f server.csr server.ext
chmod 600 ca.key server.key              # 비밀 키는 관리자만 읽기

echo "완료: $DIR 에 인증서를 만들었어요 (주소: $NAME.local)"
