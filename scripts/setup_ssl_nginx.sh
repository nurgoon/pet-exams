#!/usr/bin/env sh
set -e

DOMAIN=${1:-}
EMAIL=${2:-}
APP_PORT=${3:-18080}

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
  echo "Usage: setup_ssl_nginx.sh <domain> <email> [app_port]" >&2
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "This script must run as root (required for nginx/certbot)." >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y nginx certbot python3-certbot-nginx
else
  echo "Unsupported OS: apt-get not found. Install nginx+certbot manually." >&2
  exit 1
fi

cat > "/etc/nginx/sites-available/$DOMAIN" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email --redirect --non-interactive
systemctl reload nginx
