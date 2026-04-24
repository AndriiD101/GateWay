FROM nginx:alpine

# Install gettext for envsubst
RUN apk add --no-cache gettext

# Copy static files
COPY index.html        /usr/share/nginx/html/
COPY script.js         /usr/share/nginx/html/
COPY gateway_auth.js   /usr/share/nginx/html/
COPY styles/           /usr/share/nginx/html/styles/

# Copy nginx config as a TEMPLATE (envsubst fills in BACKEND_URL at startup)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy entrypoint that runs envsubst then starts nginx
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

CMD ["/docker-entrypoint.sh"]
