// admin-frontend/src/api/adminApi.js
/**
 * 管理员API服务
 * 处理所有与后端管理员API的通信
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class AdminApiService {
  /**
   * 管理员登录
   * @param {string} username - 用户名
   * @param {string} password - 密码
   * @returns {Promise} 登录结果
   */
  async login(username, password) {
    try {
      const response = await fetch(`${API_BASE}/admin/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();
      
      if (response.ok && data.code === 200) {
        // 保存token到localStorage
        const token = data.data.token;
        localStorage.setItem('adminToken', token);
        localStorage.setItem('adminUser', username);
        console.log('Login successful, token saved');
        return {
          success: true,
          token: token,
          username: username
        };
      } else {
        console.error('Login failed:', data.message);
        return {
          success: false,
          message: data.message || '登录失败'
        };
      }
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        message: '网络错误，请检查后端服务是否运行'
      };
    }
  }

  /**
   * 登出
   */
  logout() {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminUser');
  }

  /**
   * 验证token是否有效
   * @returns {Promise<boolean>}
   */
  async verifyToken() {
    const token = this.getToken();
    if (!token) {
      return false;
    }

    try {
      const response = await fetch(`${API_BASE}/admin/api/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Token verification error:', error);
      return false;
    }
  }

  /**
   * 检查是否已认证
   * @returns {boolean}
   */
  isAuthenticated() {
    return !!this.getToken();
  }

  /**
   * 获取当前用户名
   * @returns {string}
   */
  getUser() {
    return localStorage.getItem('adminUser') || 'Admin';
  }

  /**
   * 获取token
   * @returns {string|null}
   */
  getToken() {
    return localStorage.getItem('adminToken');
  }

  /**
   * 获取带认证的请求头
   * @returns {Object}
   */
  getAuthHeaders() {
    const token = this.getToken();
    if (!token) {
      console.warn('No token found');
      return {
        'Content-Type': 'application/json',
      };
    }
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // ========== 物资管理API ==========

  /**
   * 获取物资列表
   * @param {Object} filters - 筛选条件
   * @returns {Promise}
   */
  async getStuffList(filters = {}) {
    const params = new URLSearchParams();
    if (filters.type) params.append('type', filters.type);
    if (filters.location) params.append('location', filters.location);
    if (filters.cabinet) params.append('cabinet', filters.cabinet);
    if (filters.layer) params.append('layer', filters.layer.toString());  // 确保是字符串
    if (filters.search) params.append('search', filters.search);

    try {
      const response = await fetch(`${API_BASE}/admin/api/stuff/list?${params}`, {
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.error('Unauthorized, redirecting to login');
          this.logout();
          window.location.href = '/login';
          return null;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get stuff list error:', error);
      throw error;
    }
  }

  /**
   * 创建物资
   * @param {Object} stuffData - 物资数据
   * @returns {Promise}
   */
  async createStuff(stuffData) {
    try {
      const response = await fetch(`${API_BASE}/admin/api/stuff/create`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(stuffData),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
          window.location.href = '/login';
          return null;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Create stuff error:', error);
      throw error;
    }
  }

  /**
   * 更新物资
   * @param {string} stuffId - 物资ID
   * @param {Object} updateData - 更新数据
   * @returns {Promise}
   */
  async updateStuff(stuffId, updateData) {
    try {
      const response = await fetch(`${API_BASE}/admin/api/stuff/update/${stuffId}`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
          window.location.href = '/login';
          return null;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Update stuff error:', error);
      throw error;
    }
  }

  /**
   * 删除物资
   * @param {string} stuffId - 物资ID
   * @returns {Promise}
   */
  async deleteStuff(stuffId) {
    try {
      const response = await fetch(`${API_BASE}/admin/api/stuff/delete/${stuffId}`, {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
          window.location.href = '/login';
          return null;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Delete stuff error:', error);
      throw error;
    }
  }

  /**
   * 获取统计信息
   * @returns {Promise}
   */
  async getStats() {
    try {
      const response = await fetch(`${API_BASE}/admin/api/stats/overview`, {
        headers: this.getAuthHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          this.logout();
          window.location.href = '/login';
          return null;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get stats error:', error);
      throw error;
    }
  }
}

// 导出单例
const adminApi = new AdminApiService();
export default adminApi;