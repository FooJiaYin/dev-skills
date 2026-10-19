#!/bin/zsh
# Usage: cfapi.sh METHOD PATH [JSON_BODY]   — calls the CF API with the wrangler OAuth token, refreshing it when <10 min left.
export PATH="$HOME/.nvm/versions/node/v24.12.0/bin:/opt/homebrew/bin:$PATH"
CFG=~/Library/Preferences/.wrangler/config/default.toml
exp=$(grep -E '^expiration_time' $CFG | sed -E 's/.*"(.*)"/\1/')
if [ $(( $(date -j -u -f "%Y-%m-%dT%H:%M:%S" "${exp%.*}" +%s) - $(date -u +%s) )) -lt 600 ]; then
  (cd "${TMPDIR:-/tmp}" && npx -y wrangler@4 whoami >/dev/null 2>&1)
fi
T=$(grep -E '^oauth_token' $CFG | sed -E 's/^oauth_token *= *"(.*)"/\1/')
if [ -n "$3" ]; then
  curl -s -X "$1" -H "Authorization: Bearer $T" -H "Content-Type: application/json" "https://api.cloudflare.com/client/v4$2" -d "$3"
else
  curl -s -X "$1" -H "Authorization: Bearer $T" "https://api.cloudflare.com/client/v4$2"
fi
