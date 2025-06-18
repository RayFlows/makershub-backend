//init.js

db = db.getSiblingDB('makerhub');

// 创建应用专用用户（如果不存在）
var user = db.getUser("appuser");
if (!user) {
  db.createUser({
    user: "appuser",
    pwd: "apppassword", // 设置密码
    roles: [
      { role: "readWrite", db: "makerhub" },
      { role: "dbAdmin", db: "makerhub" }
    ]
  });
  print("Application user created");
} else {
  print("Application user already exists");
}