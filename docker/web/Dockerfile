# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS app
WORKDIR /src
COPY web/app/package.json web/app/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY web/app/ ./
RUN npm run build

FROM node:22-alpine AS admin
WORKDIR /src
COPY web/admin/package.json web/admin/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY web/admin/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=app /src/dist /usr/share/nginx/html/app
COPY --from=admin /src/dist /usr/share/nginx/html/admin
EXPOSE 8080 8081

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
