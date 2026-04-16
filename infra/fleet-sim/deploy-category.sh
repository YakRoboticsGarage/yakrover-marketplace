#!/bin/bash
# Deploy a category fleet simulator to Fly.io.
# Usage: ./deploy-category.sh <category>
# Example: ./deploy-category.sh ground-gpr
#
# Handles the fly launch overwrite issue by writing fly.toml AFTER app creation.

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <category>"
  echo "Categories: aerial-lidar aerial-photo aerial-thermal ground-gpr skydio fixedwing ground-lidar confined fakerover"
  exit 1
fi

CAT="$1"
APP_NAME="yakrover-${CAT}"
CAT_ENV=$(echo "$CAT" | tr '-' '_')
DIR="$(dirname "$0")/${CAT}"

# Ensure directory exists with required files
mkdir -p "$DIR"
cp "$(dirname "$0")/category_server.py" "$DIR/category_server.py"
cp "$(dirname "$0")/requirements.txt" "$DIR/requirements.txt"
cp "$(dirname "$0")/Dockerfile.category" "$DIR/Dockerfile"

cd "$DIR"

# Create app if it doesn't exist (fly launch overwrites fly.toml — that's OK)
if ! fly apps list 2>/dev/null | grep -q "$APP_NAME"; then
  echo "Creating app $APP_NAME..."
  fly launch --no-deploy --name "$APP_NAME" --region ord --yes 2>&1 | tail -3
fi

# ALWAYS overwrite fly.toml after fly launch (fly launch clobbers it)
cat > fly.toml << EOF
app = '${APP_NAME}'
primary_region = 'ord'

[build]

[env]
  CATEGORY = '${CAT_ENV}'

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = 'off'
  auto_start_machines = true
  min_machines_running = 1
  processes = ['app']

[[vm]]
  memory = '256mb'
  cpu_kind = 'shared'
  cpus = 1

[deploy]
  strategy = 'immediate'
EOF

echo "Deploying $APP_NAME (CATEGORY=$CAT_ENV)..."
fly deploy 2>&1 | tail -3
echo "Done: https://${APP_NAME}.fly.dev/mcp"
