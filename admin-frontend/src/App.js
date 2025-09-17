import React, { useState, useEffect } from 'react';

// 样式定义
const styles = {
  container: {
    minHeight: '100vh',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  loginPage: {
    height: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  },
  loginCard: {
    background: 'white',
    borderRadius: '8px',
    padding: '40px',
    width: '400px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
  },
  loginTitle: {
    fontSize: '24px',
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: '30px',
    color: '#333',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    color: '#666',
    fontSize: '14px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d9d9d9',
    borderRadius: '4px',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%',
    padding: '10px',
    background: '#6366f1',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
  },
  buttonHover: {
    background: '#5558e3',
  },
  layout: {
    display: 'flex',
    minHeight: '100vh',
  },
  sidebar: {
    width: '250px',
    background: '#001529',
    color: 'white',
    transition: 'width 0.3s',
  },
  sidebarCollapsed: {
    width: '80px',
  },
  logo: {
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
  },
  menu: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  menuItem: {
    padding: '16px 24px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    transition: 'background 0.3s',
  },
  menuItemActive: {
    background: '#1890ff',
  },
  menuItemHover: {
    background: 'rgba(255,255,255,0.1)',
  },
  menuIcon: {
    marginRight: '12px',
    fontSize: '18px',
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    height: '64px',
    background: 'white',
    borderBottom: '1px solid #f0f0f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 24px',
  },
  content: {
    flex: 1,
    padding: '24px',
    background: '#f0f2f5',
  },
  card: {
    background: 'white',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  cardTitle: {
    fontSize: '20px',
    fontWeight: 'bold',
    marginBottom: '16px',
    color: '#333',
  },
  userInfo: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
  },
  avatar: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: '#6366f1',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    marginRight: '8px',
  },
  dropdown: {
    position: 'absolute',
    top: '64px',
    right: '24px',
    background: 'white',
    borderRadius: '4px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
    padding: '8px 0',
    minWidth: '120px',
  },
  dropdownItem: {
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '14px',
  },
  dropdownItemHover: {
    background: '#f5f5f5',
  },
};

// 模拟认证服务
const authService = {
  login: (username, password) => {
    const ADMIN_USERNAME = 'admin';
    const ADMIN_PASSWORD = 'MakerHub@2024';
    
    if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
      const token = btoa(`${username}:${Date.now()}`);
      localStorage.setItem('adminToken', token);
      localStorage.setItem('adminUser', username);
      return { success: true, token };
    }
    return { success: false, message: '用户名或密码错误' };
  },
  
  logout: () => {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminUser');
  },
  
  isAuthenticated: () => {
    return !!localStorage.getItem('adminToken');
  },
  
  getUser: () => {
    return localStorage.getItem('adminUser') || 'Admin';
  }
};

// 登录页组件
const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isHovered, setIsHovered] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    const result = authService.login(username, password);
    if (result.success) {
      onLogin();
    } else {
      setError(result.message);
    }
  };

  return (
    <div style={styles.loginPage}>
      <div style={styles.loginCard}>
        <h2 style={styles.loginTitle}>MakerHub 管理后台</h2>
        <div>
          <div style={styles.formGroup}>
            <label style={styles.label}>用户名</label>
            <input
              type="text"
              style={styles.input}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入管理员用户名"
            />
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>密码</label>
            <input
              type="password"
              style={styles.input}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入管理员密码"
            />
          </div>
          
          {error && (
            <div style={{ color: 'red', marginBottom: '16px', fontSize: '14px' }}>
              {error}
            </div>
          )}
          
          <button
            style={{
              ...styles.button,
              ...(isHovered ? styles.buttonHover : {})
            }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={handleSubmit}
          >
            登录
          </button>
        </div>
      </div>
    </div>
  );
};

// 主布局组件
const MainLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedMenu, setSelectedMenu] = useState('dashboard');
  const [showDropdown, setShowDropdown] = useState(false);
  const [hoveredMenu, setHoveredMenu] = useState(null);

  const menuItems = [
    { key: 'dashboard', icon: '📊', label: '仪表盘' },
    { key: 'stuff', icon: '📦', label: '物资管理' },
    { key: 'site', icon: '🏢', label: '场地管理' },
    { key: 'user', icon: '👥', label: '用户管理' },
  ];

  const handleLogout = () => {
    authService.logout();
    window.location.reload();
  };

  const renderContent = () => {
    const contents = {
      dashboard: (
        <div>
          <h2>欢迎使用 MakerHub 管理后台</h2>
          <p style={{ color: '#666', marginTop: '16px' }}>
            请从左侧菜单选择要管理的模块
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginTop: '30px' }}>
            <div style={{ ...styles.card, textAlign: 'center' }}>
              <div style={{ fontSize: '32px' }}>📦</div>
              <div style={{ marginTop: '8px', fontSize: '18px', fontWeight: 'bold' }}>物资总数</div>
              <div style={{ fontSize: '24px', color: '#6366f1', marginTop: '8px' }}>--</div>
            </div>
            <div style={{ ...styles.card, textAlign: 'center' }}>
              <div style={{ fontSize: '32px' }}>🏢</div>
              <div style={{ marginTop: '8px', fontSize: '18px', fontWeight: 'bold' }}>场地总数</div>
              <div style={{ fontSize: '24px', color: '#6366f1', marginTop: '8px' }}>--</div>
            </div>
            <div style={{ ...styles.card, textAlign: 'center' }}>
              <div style={{ fontSize: '32px' }}>👥</div>
              <div style={{ marginTop: '8px', fontSize: '18px', fontWeight: 'bold' }}>用户总数</div>
              <div style={{ fontSize: '24px', color: '#6366f1', marginTop: '8px' }}>--</div>
            </div>
          </div>
        </div>
      ),
      stuff: (
        <div>
          <h2>物资管理</h2>
          <p style={{ color: '#999', marginTop: '16px' }}>
            物资管理功能开发中...<br />
            将支持：查看所有物资、添加新物资、编辑物资信息、删除物资
          </p>
        </div>
      ),
      site: (
        <div>
          <h2>场地管理</h2>
          <p style={{ color: '#999', marginTop: '16px' }}>
            场地管理功能开发中...<br />
            将支持：查看所有场地、添加新场地、编辑场地信息、删除场地
          </p>
        </div>
      ),
      user: (
        <div>
          <h2>用户管理</h2>
          <p style={{ color: '#999', marginTop: '16px' }}>
            用户管理功能开发中...<br />
            将支持：查看所有用户、封禁/解封用户、修改用户角色
          </p>
        </div>
      ),
    };
    
    return contents[selectedMenu] || contents.dashboard;
  };

  return (
    <div style={styles.layout}>
      {/* 侧边栏 */}
      <div style={{
        ...styles.sidebar,
        ...(collapsed ? styles.sidebarCollapsed : {})
      }}>
        <div style={styles.logo}>
          <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
            {collapsed ? 'MH' : 'MakerHub'}
          </span>
        </div>
        <ul style={styles.menu}>
          {menuItems.map(item => (
            <li
              key={item.key}
              style={{
                ...styles.menuItem,
                ...(selectedMenu === item.key ? styles.menuItemActive : {}),
                ...(hoveredMenu === item.key && selectedMenu !== item.key ? styles.menuItemHover : {})
              }}
              onClick={() => setSelectedMenu(item.key)}
              onMouseEnter={() => setHoveredMenu(item.key)}
              onMouseLeave={() => setHoveredMenu(null)}
            >
              <span style={styles.menuIcon}>{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </li>
          ))}
        </ul>
      </div>
      
      {/* 主内容区 */}
      <div style={styles.mainContent}>
        {/* 头部 */}
        <div style={styles.header}>
          <button
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '8px',
            }}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? '☰' : '✕'}
          </button>
          
          <div style={styles.userInfo} onClick={() => setShowDropdown(!showDropdown)}>
            <div style={styles.avatar}>A</div>
            <span>{authService.getUser()}</span>
          </div>
          
          {showDropdown && (
            <div style={styles.dropdown}>
              <div
                style={styles.dropdownItem}
                onClick={handleLogout}
                onMouseEnter={(e) => e.target.style.background = '#f5f5f5'}
                onMouseLeave={(e) => e.target.style.background = 'white'}
              >
                退出登录
              </div>
            </div>
          )}
        </div>
        
        {/* 内容区 */}
        <div style={styles.content}>
          <div style={styles.card}>
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
};

// 主应用组件
export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(authService.isAuthenticated());
    setLoading(false);
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  if (loading) {
    return (
      <div style={{ 
        height: '100vh', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center' 
      }}>
        <div>加载中...</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {isAuthenticated ? <MainLayout /> : <LoginPage onLogin={handleLogin} />}
    </div>
  );
}