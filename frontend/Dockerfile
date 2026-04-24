FROM node:18-alpine AS builder
WORKDIR /app
# Optional: If you want to build your frontend with a build tool in the future

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh
COPY gateway_auth.js /usr/share/nginx/html/gateway_auth.js
COPY gateway_auth_old.js /usr/share/nginx/html/gateway_auth_old.js
COPY script.js /usr/share/nginx/html/script.js
COPY index.html /usr/share/nginx/html/index.html
COPY styles /usr/share/nginx/html/styles

RUN chmod +x /entrypoint.sh && \
    apk add --no-cache gettext

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
