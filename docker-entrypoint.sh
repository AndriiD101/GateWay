#!/bin/sh
# Substitute BACKEND_URL into the nginx config template at startup.
# On Azure App Service, set the BACKEND_URL app setting to your backend URL,
# e.g. https://gateway-backend.azurewebsites.net

: "${BACKEND_URL:=gateway-backend-beh3grbfanheb4fc.austriaeast-01.azurewebsites.net}"

echo "Starting frontend – proxying API calls to: $BACKEND_URL"

# Replace placeholder in the nginx config template
envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# Hand off to the official nginx entrypoint
exec nginx -g "daemon off;"
