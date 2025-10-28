-- docker/mysql/init.sql

-- 创建数据库 (如果不存在)
CREATE DATABASE IF NOT EXISTS makerhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建应用用户 (如果不存在) 并授予权限
CREATE USER 'appuser'@'%' IDENTIFIED BY 'apppassword';
GRANT ALL PRIVILEGES ON makerhub.* TO 'appuser'@'%';

-- 刷新权限
FLUSH PRIVILEGES;