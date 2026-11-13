# syntax=docker/dockerfile:1.7
# The public app (web/app) and the admin app (web/admin) as static files behind nginx.
# Build from the repo root:  docker build -f docker/web/Dockerfile .
#
#   :8080  public app
#   :8081  admin app
#
# Both call /api/v1 on their own origin; the host's nginx routes /api/ to the API container
# (deploy/nginx/currency-rates.conf), so the browser never makes a cross-origin call.

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
