import React, { useState, useEffect } from 'react';
import adminApi from '../api/adminApi';

/**
 * 场地管理组件
 * 提供完整的场地CRUD操作界面，包含工位管理和借用状态查看
 */
const SiteManagement = () => {
  // ========== 状态管理 ==========
  const [sitesList, setSitesList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({});
  const [locations, setLocations] = useState([]);
  const [expandedSites, setExpandedSites] = useState({});
  
  // 筛选条件
  const [filters, setFilters] = useState({
    site: '',
    is_occupied: ''
  });
  
  // 弹窗控制
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [borrowHistory, setBorrowHistory] = useState([]);
  
  // 表单数据
  const [formData, setFormData] = useState({
    site: '',
    workstations: ''
  });
  
  const [editFormData, setEditFormData] = useState({
    new_name: '',
    add_workstations: '',
    remove_workstations: ''
  });

  // ========== API调用函数 ==========
  const API_BASE = `${process.env.REACT_APP_API_URL}/admin/api/site`;
  
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
   * 获取场地列表
   */
  const fetchSiteList = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.site) params.append('site', filters.site);
      if (filters.is_occupied !== '') params.append('is_occupied', filters.is_occupied);
      
      const response = await fetch(`${API_BASE}/list?${params}`, {
        headers: getAuthHeader()
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setSitesList(result.data.sites_list || []);
        setStats(result.data.stats || {});
        setLocations(result.data.available_locations || []);
      }
    } catch (error) {
      console.error('获取场地列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 创建场地
   */
  const handleCreate = async () => {
    try {
      const workstations = formData.workstations
        .split(',')
        .map(num => parseInt(num.trim()))
        .filter(num => !isNaN(num));
      
      if (workstations.length === 0) {
        alert('请输入有效的工位号');
        return;
      }
      
      const response = await fetch(`${API_BASE}/create`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: JSON.stringify({
          site: formData.site,
          workstations: workstations
        })
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setShowCreateModal(false);
        fetchSiteList();
        resetForm();
      } else {
        alert(result.message || '创建失败');
      }
    } catch (error) {
      console.error('创建场地失败:', error);
      alert('创建失败');
    }
  };

  /**
   * 更新场地
   */
  const handleUpdate = async () => {
    try {
      const updateData = {};
      
      if (editFormData.new_name) {
        updateData.new_name = editFormData.new_name;
      }
      
      if (editFormData.add_workstations) {
        updateData.add_workstations = editFormData.add_workstations
          .split(',')
          .map(num => parseInt(num.trim()))
          .filter(num => !isNaN(num));
      }
      
      if (editFormData.remove_workstations) {
        updateData.remove_workstations = editFormData.remove_workstations
          .split(',')
          .map(num => parseInt(num.trim()))
          .filter(num => !isNaN(num));
      }
      
      const response = await fetch(`${API_BASE}/update/${editingSite}`, {
        method: 'PUT',
        headers: getAuthHeader(),
        body: JSON.stringify(updateData)
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setShowEditModal(false);
        fetchSiteList();
        setEditingSite(null);
        resetEditForm();
      } else {
        alert(result.message || '更新失败');
      }
    } catch (error) {
      console.error('更新场地失败:', error);
      alert('更新失败');
    }
  };

  /**
   * 删除场地
   */
  const handleDelete = async (siteName) => {
    if (!window.confirm(`确定要删除场地 "${siteName}" 吗？`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE}/delete/${siteName}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });
      
      const result = await response.json();
      if (result.code === 200) {
        fetchSiteList();
      } else {
        alert(result.message || '删除失败');
      }
    } catch (error) {
      console.error('删除场地失败:', error);
      alert('删除失败');
    }
  };

  /**
   * 获取借用历史
   */
  const fetchBorrowHistory = async (siteName) => {
    try {
      const response = await fetch(`${API_BASE}/borrow-history/${siteName}`, {
        headers: getAuthHeader()
      });
      
      const result = await response.json();
      if (result.code === 200) {
        setBorrowHistory(result.data.borrow_history || []);
        setShowHistoryModal(true);
      }
    } catch (error) {
      console.error('获取借用历史失败:', error);
    }
  };

  /**
   * 重置表单
   */
  const resetForm = () => {
    setFormData({
      site: '',
      workstations: ''
    });
  };

  const resetEditForm = () => {
    setEditFormData({
      new_name: '',
      add_workstations: '',
      remove_workstations: ''
    });
  };

  /**
   * 展开/折叠场地详情
   */
  const toggleExpand = (siteName) => {
    setExpandedSites(prev => ({
      ...prev,
      [siteName]: !prev[siteName]
    }));
  };

  // ========== 生命周期 ==========
  useEffect(() => {
    fetchSiteList();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSiteList();
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
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: '16px',
      marginBottom: '20px'
    },
    statCard: {
      backgroundColor: 'white',
      padding: '16px',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
    },
    statLabel: {
      fontSize: '14px',
      color: '#666',
      marginBottom: '8px'
    },
    statValue: {
      fontSize: '24px',
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
      gridTemplateColumns: '1fr 1fr 1fr',
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
    select: {
      padding: '8px',
      border: '1px solid #ddd',
      borderRadius: '4px',
      fontSize: '14px',
      backgroundColor: 'white'
    },
    button: {
      padding: '8px 16px',
      borderRadius: '4px',
      border: 'none',
      fontSize: '14px',
      fontWeight: 'bold',
      cursor: 'pointer',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px'
    },
    primaryButton: {
      backgroundColor: '#6366f1',
      color: 'white'
    },
    secondaryButton: {
      backgroundColor: '#e5e7eb',
      color: '#374151'
    },
    dangerButton: {
      backgroundColor: '#fee2e2',
      color: '#991b1b'
    },
    siteCard: {
      backgroundColor: 'white',
      borderRadius: '8px',
      marginBottom: '16px',
      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      overflow: 'hidden'
    },
    siteHeader: {
      padding: '16px',
      borderBottom: '1px solid #f0f0f0',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      cursor: 'pointer'
    },
    siteName: {
      fontSize: '18px',
      fontWeight: 'bold',
      color: '#333'
    },
    siteStats: {
      display: 'flex',
      gap: '20px',
      fontSize: '14px',
      color: '#666'
    },
    workstationGrid: {
      padding: '16px',
      display: 'grid',
      gridTemplateColumns: 'repeat(6, 1fr)',
      gap: '12px'
    },
    workstation: {
      padding: '12px',
      borderRadius: '6px',
      textAlign: 'center',
      fontSize: '14px',
      fontWeight: '500'
    },
    availableWorkstation: {
      backgroundColor: '#d1fae5',
      color: '#065f46',
      border: '1px solid #a7f3d0'
    },
    occupiedWorkstation: {
      backgroundColor: '#fee2e2',
      color: '#991b1b',
      border: '1px solid #fecaca'
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
    modalFormGroup: {
      marginBottom: '16px'
    },
    modalLabel: {
      display: 'block',
      marginBottom: '6px',
      fontSize: '14px',
      fontWeight: '500',
      color: '#374151'
    },
    modalInput: {
      width: '100%',
      padding: '10px',
      border: '1px solid #d1d5db',
      borderRadius: '4px',
      fontSize: '14px'
    },
    modalFooter: {
      marginTop: '24px',
      display: 'flex',
      justifyContent: 'flex-end',
      gap: '12px'
    },
    badge: {
      padding: '2px 8px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: '500'
    },
    successBadge: {
      backgroundColor: '#d1fae5',
      color: '#065f46'
    },
    warningBadge: {
      backgroundColor: '#fed7aa',
      color: '#92400e'
    },
    dangerBadge: {
      backgroundColor: '#fee2e2',
      color: '#991b1b'
    }
  };

  // ========== 渲染组件 ==========
  return (
    <div style={styles.container}>
      {/* 页面标题和操作按钮 */}
      <div style={styles.header}>
        <h1 style={styles.title}>场地管理</h1>
        <button
          style={{...styles.button, ...styles.primaryButton}}
          onClick={() => setShowCreateModal(true)}
        >
          ➕ 新增场地
        </button>
      </div>

      {/* 统计卡片 */}
      <div style={styles.statsCards}>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>场地总数</div>
          <div style={styles.statValue}>{stats.total_sites || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>工位总数</div>
          <div style={styles.statValue}>{stats.total_workstations || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>已占用</div>
          <div style={styles.statValue}>{stats.total_occupied || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>占用率</div>
          <div style={styles.statValue}>{stats.occupancy_rate || 0}%</div>
        </div>
      </div>

      {/* 筛选区域 */}
      <div style={styles.filterSection}>
        <div style={styles.filterGrid}>
          <div style={styles.formGroup}>
            <label style={styles.label}>场地位置</label>
            <select
              style={styles.select}
              value={filters.site}
              onChange={(e) => setFilters({...filters, site: e.target.value})}
            >
              <option value="">全部场地</option>
              {locations.map(loc => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>占用状态</label>
            <select
              style={styles.select}
              value={filters.is_occupied}
              onChange={(e) => setFilters({...filters, is_occupied: e.target.value})}
            >
              <option value="">全部状态</option>
              <option value="false">空闲</option>
              <option value="true">已占用</option>
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>&nbsp;</label>
            <button
              style={{...styles.button, ...styles.secondaryButton}}
              onClick={() => setFilters({site: '', is_occupied: ''})}
            >
              🔄 重置筛选
            </button>
          </div>
        </div>
      </div>

      {/* 场地列表 */}
      {loading ? (
        <div style={{textAlign: 'center', padding: '40px', color: '#666'}}>
          加载中...
        </div>
      ) : sitesList.length === 0 ? (
        <div style={{textAlign: 'center', padding: '40px', color: '#666'}}>
          暂无数据
        </div>
      ) : (
        sitesList.map(site => (
          <div key={site.site} style={styles.siteCard}>
            <div
              style={styles.siteHeader}
              onClick={() => toggleExpand(site.site)}
            >
              <div>
                <div style={styles.siteName}>{site.site}</div>
                <div style={styles.siteStats}>
                  <span>工位总数: {site.total_count}</span>
                  <span style={{color: '#065f46'}}>空闲: {site.available_count}</span>
                  <span style={{color: '#991b1b'}}>占用: {site.occupied_count}</span>
                </div>
              </div>
              
              <div style={{display: 'flex', gap: '8px'}}>
                <button
                  style={{...styles.button, ...styles.secondaryButton, padding: '6px 12px'}}
                  onClick={(e) => {
                    e.stopPropagation();
                    fetchBorrowHistory(site.site);
                  }}
                >
                  📋 借用历史
                </button>
                <button
                  style={{...styles.button, ...styles.secondaryButton, padding: '6px 12px'}}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingSite(site.site);
                    setShowEditModal(true);
                  }}
                >
                  ✏️ 编辑
                </button>
                <button
                  style={{
                    ...styles.button,
                    ...styles.dangerButton,
                    padding: '6px 12px',
                    opacity: site.occupied_count > 0 ? 0.5 : 1,
                    cursor: site.occupied_count > 0 ? 'not-allowed' : 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (site.occupied_count === 0) {
                      handleDelete(site.site);
                    }
                  }}
                  disabled={site.occupied_count > 0}
                  title={site.occupied_count > 0 ? '有工位被占用，不能删除' : '删除场地'}
                >
                  🗑️ 删除
                </button>
              </div>
            </div>
            
            {expandedSites[site.site] && (
              <div style={styles.workstationGrid}>
                {site.details.map(detail => (
                  <div
                    key={detail.number}
                    style={{
                      ...styles.workstation,
                      ...(detail.is_occupied ? styles.occupiedWorkstation : styles.availableWorkstation)
                    }}
                    title={detail.borrow_info ? 
                      `借用人: ${detail.borrow_info.borrower}\n用途: ${detail.borrow_info.purpose}` : 
                      '空闲'}
                  >
                    工位 {detail.number}
                    {detail.borrow_info && (
                      <div style={{fontSize: '10px', marginTop: '4px'}}>
                        {detail.borrow_info.borrower}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))
      )}

      {/* 创建场地弹窗 */}
      {showCreateModal && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2 style={styles.modalHeader}>新增场地</h2>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>场地名称 *</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="例如：二基楼B208+"
                value={formData.site}
                onChange={(e) => setFormData({...formData, site: e.target.value})}
              />
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>工位号列表 *</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="输入工位号，用逗号分隔，如：1,2,3,4,5"
                value={formData.workstations}
                onChange={(e) => setFormData({...formData, workstations: e.target.value})}
              />
              <div style={{fontSize: '12px', color: '#666', marginTop: '4px'}}>
                例如输入：1,2,3,4,5 将创建5个工位
              </div>
            </div>
            
            <div style={styles.modalFooter}>
              <button
                style={{...styles.button, ...styles.secondaryButton}}
                onClick={() => {
                  setShowCreateModal(false);
                  resetForm();
                }}
              >
                取消
              </button>
              <button
                style={{...styles.button, ...styles.primaryButton}}
                onClick={handleCreate}
              >
                确认创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑场地弹窗 */}
      {showEditModal && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2 style={styles.modalHeader}>编辑场地: {editingSite}</h2>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>新场地名称（选填）</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="留空则不修改名称"
                value={editFormData.new_name}
                onChange={(e) => setEditFormData({...editFormData, new_name: e.target.value})}
              />
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>新增工位（选填）</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="输入要新增的工位号，用逗号分隔"
                value={editFormData.add_workstations}
                onChange={(e) => setEditFormData({...editFormData, add_workstations: e.target.value})}
              />
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>删除工位（选填）</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="输入要删除的工位号，用逗号分隔"
                value={editFormData.remove_workstations}
                onChange={(e) => setEditFormData({...editFormData, remove_workstations: e.target.value})}
              />
              <div style={{fontSize: '12px', color: '#ff4d4f', marginTop: '4px'}}>
                注意：只有未被占用的工位才能删除
              </div>
            </div>
            
            <div style={styles.modalFooter}>
              <button
                style={{...styles.button, ...styles.secondaryButton}}
                onClick={() => {
                  setShowEditModal(false);
                  setEditingSite(null);
                  resetEditForm();
                }}
              >
                取消
              </button>
              <button
                style={{...styles.button, ...styles.primaryButton}}
                onClick={handleUpdate}
              >
                保存修改
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 借用历史弹窗 */}
      {showHistoryModal && (
        <div style={styles.modal}>
          <div style={{...styles.modalContent, width: '700px'}}>
            <h2 style={styles.modalHeader}>借用历史</h2>
            
            {borrowHistory.length === 0 ? (
              <div style={{textAlign: 'center', padding: '20px', color: '#666'}}>
                暂无借用记录
              </div>
            ) : (
              <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                {borrowHistory.map((record, index) => (
                  <div
                    key={record.apply_id}
                    style={{
                      padding: '12px',
                      borderBottom: index < borrowHistory.length - 1 ? '1px solid #f0f0f0' : 'none'
                    }}
                  >
                    <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '8px'}}>
                      <div>
                        <strong>{record.borrower}</strong> (工位 {record.workstation})
                      </div>
                      <span
                        style={{
                          ...styles.badge,
                          ...(record.state === 0 ? styles.warningBadge :
                              record.state === 1 ? styles.dangerBadge :
                              record.state === 2 ? styles.warningBadge :
                              styles.successBadge)
                        }}
                      >
                        {record.state_text}
                      </span>
                    </div>
                    <div style={{fontSize: '14px', color: '#666'}}>
                      <div>用途: {record.purpose}</div>
                      <div>时间: {record.start_time} 至 {record.end_time}</div>
                      {record.review && <div>审核意见: {record.review}</div>}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div style={styles.modalFooter}>
              <button
                style={{...styles.button, ...styles.secondaryButton}}
                onClick={() => {
                  setShowHistoryModal(false);
                  setBorrowHistory([]);
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

export default SiteManagement;