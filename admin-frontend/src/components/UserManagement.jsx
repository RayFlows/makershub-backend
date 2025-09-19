// admin-frontend/src/components/UserManagement.jsx
import React, { useState, useEffect } from 'react';
import adminApi from '../api/adminApi';

/**
 * 用户管理组件
 * 提供完整的用户管理界面，包括查看、修改权限、封禁等功能
 */
const UserManagement = () => {
  // ========== 状态管理 ==========
  const [usersList, setUsersList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({});
  const [departmentStats, setDepartmentStats] = useState({});
  
  // 筛选条件
  const [filters, setFilters] = useState({
    role: '',
    state: '',
    department: '',
    search: ''
  });
  
  // 弹窗控制
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // 编辑状态
  const [editingUser, setEditingUser] = useState(null);
  const [editData, setEditData] = useState({});

  // ========== API调用函数 ==========
  const API_BASE = 'http://localhost:8000/admin/api/user';
  
  const getAuthHeader = () => {
    const token = localStorage.getItem('adminToken');
    if (!token) {
      console.error('No admin token found');
      window.location.href = '/login';
      return {};
    }
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  /**
   * 获取用户列表
   */
  const fetchUserList = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.role !== '') params.append('role', filters.role);
      if (filters.state !== '') params.append('state', filters.state);
      if (filters.department !== '') params.append('department', filters.department);
      if (filters.search) params.append('search', filters.search);
      
      const response = await fetch(`${API_BASE}/list?${params}`, {
        headers: getAuthHeader()
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setUsersList(result.data.users_list || []);
        setStats(result.data.stats || {});
        setDepartmentStats(result.data.department_stats || {});
      }
    } catch (error) {
      console.error('获取用户列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 更新用户角色
   */
  const handleUpdateRole = async (userid, newRole) => {
    try {
      const response = await fetch(`${API_BASE}/role/${userid}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify({ role: parseInt(newRole) })
      });
      
      const result = await response.json();
      if (result.code === 200) {
        fetchUserList();
      } else {
        alert(result.message || '更新失败');
      }
    } catch (error) {
      console.error('更新用户角色失败:', error);
      alert('更新失败');
    }
  };

  /**
   * 更新用户状态（封禁/解封）
   */
  const handleUpdateState = async (userid, newState) => {
    const action = newState === 0 ? '封禁' : '解封';
    if (!window.confirm(`确定要${action}该用户吗？`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/state/${userid}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify({ state: newState })
      });
      
      const result = await response.json();
      if (result.code === 200) {
        fetchUserList();
      } else {
        alert(result.message || '操作失败');
      }
    } catch (error) {
      console.error('更新用户状态失败:', error);
      alert('操作失败');
    }
  };

  /**
   * 查看用户详情
   */
  const fetchUserDetail = async (userid) => {
    try {
      const response = await fetch(`${API_BASE}/detail/${userid}`, {
        headers: getAuthHeader()
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setSelectedUser(result.data);
        setShowDetailModal(true);
      }
    } catch (error) {
      console.error('获取用户详情失败:', error);
    }
  };

  /**
   * 保存用户信息编辑
   */
  const handleSaveEdit = async () => {
    try {
      const response = await fetch(`${API_BASE}/update/${editingUser}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify(editData)
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setEditingUser(null);
        setEditData({});
        fetchUserList();
      } else {
        alert(result.message || '保存失败');
      }
    } catch (error) {
      console.error('保存用户信息失败:', error);
      alert('保存失败');
    }
  };

  // ========== 生命周期 ==========
  useEffect(() => {
    fetchUserList();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUserList();
    }, 300);
    return () => clearTimeout(timer);
  }, [filters]);

  // ========== 样式定义 ==========
  const styles = {
    container: {
      padding: '20px',
      backgroundColor: '#f5f5f5',
      minHeight: '100vh'
    },
    header: {
      marginBottom: '20px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    },
    title: {
      fontSize: '24px',
      fontWeight: 'bold',
      color: '#333'
    },
    statsCards: {
      display: 'grid',
      gridTemplateColumns: 'repeat(6, 1fr)',
      gap: '16px',
      marginBottom: '20px'
    },
    statCard: {
      backgroundColor: 'white',
      padding: '16px',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      textAlign: 'center'
    },
    statLabel: {
      fontSize: '12px',
      color: '#666',
      marginBottom: '8px'
    },
    statValue: {
      fontSize: '20px',
      fontWeight: 'bold',
      color: '#6366f1'
    },
    filterSection: {
      backgroundColor: 'white',
      padding: '16px',
      borderRadius: '8px',
      marginBottom: '20px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    },
    filterGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: '12px'
    },
    formGroup: {
      display: 'flex',
      flexDirection: 'column'
    },
    label: {
      fontSize: '12px',
      color: '#666',
      marginBottom: '4px'
    },
    input: {
      padding: '8px',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '14px'
    },
    select: {
      padding: '8px',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '14px',
      backgroundColor: 'white'
    },
    table: {
      width: '100%',
      backgroundColor: 'white',
      borderRadius: '8px',
      overflow: 'hidden',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    },
    tableHeader: {
      backgroundColor: '#f9fafb',
      borderBottom: '1px solid #e5e7eb'
    },
    th: {
      padding: '12px',
      textAlign: 'left',
      fontSize: '12px',
      fontWeight: 'bold',
      color: '#6b7280'
    },
    td: {
      padding: '12px',
      fontSize: '14px',
      borderBottom: '1px solid #f3f4f6'
    },
    avatar: {
      width: '32px',
      height: '32px',
      borderRadius: '50%',
      marginRight: '8px'
    },
    userInfo: {
      display: 'flex',
      alignItems: 'center'
    },
    badge: {
      padding: '2px 8px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: '500'
    },
    roleBadge: {
      backgroundColor: '#e0e7ff',
      color: '#3730a3'
    },
    stateBadge: {
      backgroundColor: '#d1fae5',
      color: '#065f46'
    },
    bannedBadge: {
      backgroundColor: '#fee2e2',
      color: '#991b1b'
    },
    button: {
      padding: '6px 12px',
      borderRadius: '4px',
      border: 'none',
      fontSize: '12px',
      fontWeight: '500',
      cursor: 'pointer',
      marginLeft: '4px'
    },
    primaryButton: {
      backgroundColor: '#6366f1',
      color: 'white'
    },
    dangerButton: {
      backgroundColor: '#ef4444',
      color: 'white'
    },
    successButton: {
      backgroundColor: '#10b981',
      color: 'white'
    },
    modal: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    },
    modalContent: {
      backgroundColor: 'white',
      borderRadius: '8px',
      padding: '24px',
      width: '500px',
      maxHeight: '80vh',
      overflow: 'auto'
    },
    modalHeader: {
      fontSize: '20px',
      fontWeight: 'bold',
      marginBottom: '20px',
      color: '#333'
    },
    detailRow: {
      display: 'flex',
      marginBottom: '12px',
      paddingBottom: '12px',
      borderBottom: '1px solid #f0f0f0'
    },
    detailLabel: {
      width: '120px',
      fontWeight: '500',
      color: '#666'
    },
    detailValue: {
      flex: 1,
      color: '#333'
    }
  };

  // 部门映射
  const departmentMap = {
    0: "基地管理部",
    1: "宣传部",
    2: "运维部",
    3: "项目部",
    4: "副会长",
    5: "会长",
    999: "未分配"
  };

  // ========== 渲染组件 ==========
  return (
    <div style={styles.container}>
      {/* 页面标题 */}
      <div style={styles.header}>
        <h1 style={styles.title}>用户管理</h1>
      </div>

      {/* 统计卡片 */}
      <div style={styles.statsCards}>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>总用户数</div>
          <div style={styles.statValue}>{stats.total_users || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>正常用户</div>
          <div style={styles.statValue}>{stats.active_users || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>封禁用户</div>
          <div style={styles.statValue}>{stats.banned_users || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>普通用户</div>
          <div style={styles.statValue}>{stats.normal_users || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>干事</div>
          <div style={styles.statValue}>{stats.staff_users || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>部长及以上</div>
          <div style={styles.statValue}>{stats.manager_users || 0}</div>
        </div>
      </div>

      {/* 筛选区域 */}
      <div style={styles.filterSection}>
        <div style={styles.filterGrid}>
          <div style={styles.formGroup}>
            <label style={styles.label}>用户角色</label>
            <select
              style={styles.select}
              value={filters.role}
              onChange={(e) => setFilters({...filters, role: e.target.value})}
            >
              <option value="">全部角色</option>
              <option value="0">普通用户</option>
              <option value="1">干事</option>
              <option value="2">部长及以上</option>
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>用户状态</label>
            <select
              style={styles.select}
              value={filters.state}
              onChange={(e) => setFilters({...filters, state: e.target.value})}
            >
              <option value="">全部状态</option>
              <option value="1">正常</option>
              <option value="0">封禁</option>
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>所属部门</label>
            <select
              style={styles.select}
              value={filters.department}
              onChange={(e) => setFilters({...filters, department: e.target.value})}
            >
              <option value="">全部部门</option>
              {Object.entries(departmentMap).map(([key, value]) => (
                <option key={key} value={key}>{value}</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>搜索用户</label>
            <input
              style={styles.input}
              type="text"
              placeholder="姓名或手机号"
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
            />
          </div>
        </div>
      </div>

      {/* 用户列表表格 */}
      <table style={styles.table}>
        <thead style={styles.tableHeader}>
          <tr>
            <th style={styles.th}>用户信息</th>
            <th style={styles.th}>协会ID</th>
            <th style={styles.th}>手机号</th>
            <th style={styles.th}>角色</th>
            <th style={styles.th}>部门</th>
            <th style={styles.th}>状态</th>
            <th style={styles.th}>积分</th>
            <th style={styles.th}>值班时长</th>
            <th style={styles.th}>操作</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan="9" style={{...styles.td, textAlign: 'center', padding: '40px'}}>
                加载中...
              </td>
            </tr>
          ) : usersList.length === 0 ? (
            <tr>
              <td colSpan="9" style={{...styles.td, textAlign: 'center', padding: '40px'}}>
                暂无数据
              </td>
            </tr>
          ) : (
            usersList.map(user => (
              <tr key={user.userid}>
                <td style={styles.td}>
                  <div style={styles.userInfo}>
                    {user.profile_photo ? (
                      <img src={user.profile_photo} alt="" style={styles.avatar} />
                    ) : (
                      <div style={{...styles.avatar, backgroundColor: '#e5e7eb'}} />
                    )}
                    <div>
                      <div style={{fontWeight: 'bold'}}>{user.real_name}</div>
                      <div style={{fontSize: '12px', color: '#666'}}>{user.userid.substring(0, 10)}...</div>
                    </div>
                  </div>
                </td>
                <td style={styles.td}>{user.maker_id || '-'}</td>
                <td style={styles.td}>{user.phone_num || '-'}</td>
                <td style={styles.td}>
                  {editingUser === user.userid ? (
                    <select
                      style={{...styles.select, width: '120px'}}
                      value={editData.role || user.role}
                      onChange={(e) => setEditData({...editData, role: parseInt(e.target.value)})}
                    >
                      <option value="0">普通用户</option>
                      <option value="1">干事</option>
                      <option value="2">部长及以上</option>
                    </select>
                  ) : (
                    <span style={{...styles.badge, ...styles.roleBadge}}>
                      {user.role_text}
                    </span>
                  )}
                </td>
                <td style={styles.td}>
                  {editingUser === user.userid ? (
                    <select
                      style={{...styles.select, width: '120px'}}
                      value={editData.department !== undefined ? editData.department : user.department}
                      onChange={(e) => setEditData({...editData, department: parseInt(e.target.value)})}
                    >
                      {Object.entries(departmentMap).map(([key, value]) => (
                        <option key={key} value={key}>{value}</option>
                      ))}
                    </select>
                  ) : (
                    user.department_text
                  )}
                </td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.badge,
                    ...(user.state === 1 ? styles.stateBadge : styles.bannedBadge)
                  }}>
                    {user.state_text}
                  </span>
                </td>
                <td style={styles.td}>{user.score}</td>
                <td style={styles.td}>{user.total_dutytime} 分钟</td>
                <td style={styles.td}>
                  {editingUser === user.userid ? (
                    <>
                      <button
                        style={{...styles.button, ...styles.successButton}}
                        onClick={handleSaveEdit}
                      >
                        保存
                      </button>
                      <button
                        style={{...styles.button, backgroundColor: '#6b7280', color: 'white'}}
                        onClick={() => {
                          setEditingUser(null);
                          setEditData({});
                        }}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        style={{...styles.button, ...styles.primaryButton}}
                        onClick={() => fetchUserDetail(user.userid)}
                      >
                        详情
                      </button>
                      <button
                        style={{...styles.button, backgroundColor: '#f59e0b', color: 'white'}}
                        onClick={() => {
                          setEditingUser(user.userid);
                          setEditData({role: user.role, department: user.department});
                        }}
                      >
                        编辑
                      </button>
                      {user.state === 1 ? (
                        <button
                          style={{...styles.button, ...styles.dangerButton}}
                          onClick={() => handleUpdateState(user.userid, 0)}
                        >
                          封禁
                        </button>
                      ) : (
                        <button
                          style={{...styles.button, ...styles.successButton}}
                          onClick={() => handleUpdateState(user.userid, 1)}
                        >
                          解封
                        </button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* 用户详情弹窗 */}
      {showDetailModal && selectedUser && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2 style={styles.modalHeader}>用户详情</h2>
            
            {selectedUser.profile_photo && (
              <div style={{textAlign: 'center', marginBottom: '20px'}}>
                <img 
                  src={selectedUser.profile_photo} 
                  alt="头像" 
                  style={{width: '80px', height: '80px', borderRadius: '50%'}}
                />
              </div>
            )}
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>用户ID:</div>
              <div style={styles.detailValue}>{selectedUser.userid}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>协会ID:</div>
              <div style={styles.detailValue}>{selectedUser.maker_id || '未设置'}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>真实姓名:</div>
              <div style={styles.detailValue}>{selectedUser.real_name}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>手机号:</div>
              <div style={styles.detailValue}>{selectedUser.phone_num || '未设置'}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>用户角色:</div>
              <div style={styles.detailValue}>{selectedUser.role_text}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>所属部门:</div>
              <div style={styles.detailValue}>{selectedUser.department_text}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>账号状态:</div>
              <div style={styles.detailValue}>
                <span style={{
                  ...styles.badge,
                  ...(selectedUser.state === 1 ? styles.stateBadge : styles.bannedBadge)
                }}>
                  {selectedUser.state_text}
                </span>
              </div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>个性签名:</div>
              <div style={styles.detailValue}>{selectedUser.motto || '这个人很懒，什么都没写~'}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>积分:</div>
              <div style={styles.detailValue}>{selectedUser.score}</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>总值班时长:</div>
              <div style={styles.detailValue}>{selectedUser.total_dutytime} 分钟</div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>注册时间:</div>
              <div style={styles.detailValue}>
                {selectedUser.created_at ? new Date(selectedUser.created_at).toLocaleString() : '-'}
              </div>
            </div>
            
            <div style={styles.detailRow}>
              <div style={styles.detailLabel}>最后更新:</div>
              <div style={styles.detailValue}>
                {selectedUser.updated_at ? new Date(selectedUser.updated_at).toLocaleString() : '-'}
              </div>
            </div>
            
            <div style={{marginTop: '24px', textAlign: 'right'}}>
              <button
                style={{...styles.button, backgroundColor: '#6b7280', color: 'white', padding: '8px 16px'}}
                onClick={() => {
                  setShowDetailModal(false);
                  setSelectedUser(null);
                }}
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;