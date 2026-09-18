FROM node:25-alpine AS builder

ARG VITE_API_URL=http://localhost:8000
ARG VITE_API_KEY=""
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_KEY=$VITE_API_KEY

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serve the built app with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Route all requests to index.html (for SPA routing)
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
