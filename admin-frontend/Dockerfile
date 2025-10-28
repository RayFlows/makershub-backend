# admin-frontend/Dockerfile
# 管理员前端Docker镜像构建文件

# FROM node:16-alpine as builder
# WORKDIR /app
# COPY package*.json ./
# RUN npm install
# COPY . .
# RUN npm run build

# # 直接使用nginx提供静态文件
# FROM nginx:alpine
# COPY --from=builder /app/build /usr/share/nginx/html
# EXPOSE 80
# CMD ["nginx", "-g", "daemon off;"]

# 开发阶段镜像，不做 build，只起 dev-server
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install          # 这一步必须有
COPY . .
EXPOSE 3000
CMD ["npm", "start"]