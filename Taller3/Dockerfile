# Build stage
FROM node:18 as build

WORKDIR /app

# Copy package files for better caching
COPY package*.json ./
# Use npm install instead of npm ci since package-lock.json might not exist
RUN npm install

# Copy the rest of the application
COPY . .

# Build the app
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Configure Nginx to handle React routing
RUN echo 'server { \
  listen 8080; \
  root /usr/share/nginx/html; \
  index index.html; \
  location / { \
    try_files $uri $uri/ /index.html; \
  } \
}' > /etc/nginx/conf.d/default.conf

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]