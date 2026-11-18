ARG NODE_IMAGE=node:24-alpine
ARG NGINX_IMAGE=nginx:stable-alpine
FROM ${NODE_IMAGE} AS build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund --fetch-timeout=60000 --fetch-retries=1
COPY frontend/ ./
ARG STOREFRONT_BASE_URL=https://blissbiz.biz
ARG ADMIN_BASE_URL=https://admin.blissbiz.biz
ENV VITE_STOREFRONT_BASE_URL=${STOREFRONT_BASE_URL} VITE_ADMIN_BASE_URL=${ADMIN_BASE_URL}
RUN npm run build

FROM ${NGINX_IMAGE}
COPY --from=build /build/dist /opt/blissbiz/current/frontend/dist
COPY deploy/nginx/vps.conf /etc/nginx/conf.d/default.conf
COPY deploy/nginx/vps-proxy.conf /etc/nginx/blissbiz-proxy.conf
