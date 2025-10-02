# Stage 1: Build the React application
FROM node:18-alpine as builder

WORKDIR /app

COPY webui/package.json webui/yarn.lock ./
RUN yarn install

COPY webui/ .

RUN yarn build

# Stage 2: Serve the static files with Nginx
FROM nginx:1.21-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the Nginx configuration file
COPY webui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
