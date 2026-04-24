#!/bin/sh

# Set default values if environment variables are not provided
BACKEND_API_URL="${BACKEND_API_URL:-http://localhost:8000}"

# Substitute environment variables in nginx config
envsubst '${BACKEND_API_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Start nginx
nginx -g 'daemon off;'
