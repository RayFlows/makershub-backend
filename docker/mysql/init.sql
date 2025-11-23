-- docker/mysql/init.sql

-- 1. 创建数据库 (名称必须与 .env 中的 MYSQL_DATABASE 一致)
-- 注意：这里改成了 makershub (加了s)
CREATE DATABASE IF NOT EXISTS makershub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. 创建应用用户 (如果不存在) 并授予权限
-- 注意：这里改成了 GRANT ... ON makershub.*
CREATE USER IF NOT EXISTS 'appuser'@'%' IDENTIFIED BY 'apppassword';
GRANT ALL PRIVILEGES ON makershub.* TO 'appuser'@'%';

-- 3. 刷新权限
FLUSH PRIVILEGES;