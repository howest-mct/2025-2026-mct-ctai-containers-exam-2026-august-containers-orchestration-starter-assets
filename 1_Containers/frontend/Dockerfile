FROM node:16-alpine AS builder

WORKDIR /app

COPY . .
RUN npm ci
RUN npm run build

FROM

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
