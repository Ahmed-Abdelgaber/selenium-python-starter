FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8080
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

# Copy nginx configuration template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built application
COPY --from=build /app/dist /usr/share/nginx/html

ENV NGINX_PORT=80
ENV API_BASE_URL=3.230.1.49:8000

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget -qO- http://127.0.0.1:${NGINX_PORT}/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
