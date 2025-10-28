import React, { useState, useEffect } from 'react';
import adminApi from '../api/adminApi';
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons';

/**
 * 物资管理组件
 * 提供完整的物资CRUD操作界面，包含筛选、搜索、批量操作等功能
 */
const StuffManagement = () => {
  // ========== 状态管理 ==========
  const [stuffList, setStuffList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({});
  const [typeStats, setTypeStats] = useState({});
  const [locations, setLocations] = useState(['i创街', '101', '208+']);
  const [cabinets, setCabinets] = useState([]);
  
  // 筛选条件
  const [filters, setFilters] = useState({
    type: '',
    location: '',
    cabinet: '',
    layer: '',
    search: ''
  });
  
  // 弹窗控制
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingStuff, setEditingStuff] = useState(null);
  
  // 表单数据
  const [formData, setFormData] = useState({
    type: '',
    stuff_name: '',
    number_total: 0,
    number_remain: 0,
    description: '',
    location: '',
    cabinet: '',
    layer: 1
  });

  // ========== API调用函数 ==========
  
  /**
   * 获取物资列表
   */
  const fetchStuffList = async () => {
    setLoading(true);
    try {
      const result = await adminApi.getStuffList(filters);
      
      if (result && result.code === 200) {
        setStuffList(result.data.stuff_list || []);
        setStats(result.data.stats || {});
        setTypeStats(result.data.type_stats || {});
        setLocations(result.data.available_locations || ['i创街', '101', '208+']);
        setCabinets(result.data.available_cabinets || []);
      }
    } catch (error) {
      console.error('获取物资列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 创建物资
   */
  const handleCreate = async () => {
    try {
      const result = await adminApi.createStuff(formData);
      
      if (result && result.code === 200) {
        setShowCreateModal(false);
        fetchStuffList();
        resetForm();
      } else {
        alert(result?.message || '创建失败');
      }
    } catch (error) {
      console.error('创建物资失败:', error);
      alert('创建失败');
    }
  };

  /**
   * 更新物资
   */
  const handleUpdate = async () => {
    try {
      const result = await adminApi.updateStuff(editingStuff.stuff_id, formData);
      
      if (result && result.code === 200) {
        setShowEditModal(false);
        fetchStuffList();
        setEditingStuff(null);
        resetForm();
      } else {
        alert(result?.message || '更新失败');
      }
    } catch (error) {
      console.error('更新物资失败:', error);
      alert('更新失败');
    }
  };

  /**
   * 删除物资
   */
  const handleDelete = async (stuffId, stuffName) => {
    if (!window.confirm(`确定要删除物资 "${stuffName}" 吗？`)) {
      return;
    }
    
    try {
      const result = await adminApi.deleteStuff(stuffId);
      
      if (result && result.code === 200) {
        fetchStuffList();
      } else {
        alert(result?.message || '删除失败');
      }
    } catch (error) {
      console.error('删除物资失败:', error);
      alert('删除失败');
    }
  };

  /**
   * 重置表单
   */
  const resetForm = () => {
    setFormData({
      type: '',
      stuff_name: '',
      number_total: 0,
      number_remain: 0,
      description: '',
      location: '',
      cabinet: '',
      layer: 1
    });
  };

  /**
   * 打开编辑弹窗
   */
  const openEditModal = (stuff) => {
    setEditingStuff(stuff);
    setFormData({
      type: stuff.type,
      stuff_name: stuff.stuff_name,
      number_total: stuff.number_total,
      number_remain: stuff.number_remain,
      description: stuff.description,
      location: stuff.location || '',
      cabinet: stuff.cabinet || '',
      layer: stuff.layer || 1
    });
    setShowEditModal(true);
  };

  // ========== 生命周期 ==========
  useEffect(() => {
    fetchStuffList();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStuffList();
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
      gridTemplateColumns: 'repeat(5, 1fr)',
      gap: '12px',
      alignItems: 'end'
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
    modalSelect: {
      width: '100%',
      padding: '10px',
      border: '1px solid #d1d5db',
      borderRadius: '4px',
      fontSize: '14px',
      backgroundColor: 'white'
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
        <h1 style={styles.title}>物资管理</h1>
        <button
          style={{...styles.button, ...styles.primaryButton}}
          onClick={() => setShowCreateModal(true)}
        >
          <PlusOutlined /> 新增物资
        </button>
      </div>

      {/* 统计卡片 */}
      <div style={styles.statsCards}>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>物资总数</div>
          <div style={styles.statValue}>{stats.total_count || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>物品总量</div>
          <div style={styles.statValue}>{stats.total_items || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>剩余数量</div>
          <div style={styles.statValue}>{stats.total_remain || 0}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>借出数量</div>
          <div style={styles.statValue}>{stats.total_borrowed || 0}</div>
        </div>
      </div>

      {/* 筛选区域 */}
      <div style={styles.filterSection}>
        <div style={styles.filterGrid}>
          <div style={styles.formGroup}>
            <label style={styles.label}>物资类型</label>
            <select
              style={styles.select}
              value={filters.type}
              onChange={(e) => setFilters({...filters, type: e.target.value})}
            >
              <option value="">全部类型</option>
              {Object.keys(typeStats).map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>所在场地</label>
            <select
              style={styles.select}
              value={filters.location}
              onChange={(e) => setFilters({...filters, location: e.target.value})}
            >
              <option value="">全部场地</option>
              {locations.map(loc => (
                <option key={loc} value={loc}>{loc}</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>展柜位置</label>
            <select
              style={styles.select}
              value={filters.cabinet}
              onChange={(e) => setFilters({...filters, cabinet: e.target.value})}
            >
              <option value="">全部展柜</option>
              {cabinets.slice(0, 26).map(cab => (
                <option key={cab} value={cab}>{cab}</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>所在层数</label>
            <select
              style={styles.select}
              value={filters.layer}
              onChange={(e) => setFilters({...filters, layer: e.target.value})}
            >
              <option value="">全部层数</option>
              {[1,2,3,4,5,6].map(layer => (
                <option key={layer} value={layer}>第{layer}层</option>
              ))}
            </select>
          </div>
          
          <div style={styles.formGroup}>
            <label style={styles.label}>搜索物资</label>
            <input
              style={styles.input}
              type="text"
              placeholder="输入物资名称..."
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
            />
          </div>
        </div>
      </div>

      {/* 物资列表表格 */}
      <table style={styles.table}>
        <thead style={styles.tableHeader}>
          <tr>
            <th style={styles.th}>物资名称</th>
            <th style={styles.th}>类型</th>
            <th style={styles.th}>位置信息</th>
            <th style={styles.th}>总量</th>
            <th style={styles.th}>剩余</th>
            <th style={styles.th}>借出</th>
            <th style={styles.th}>借出率</th>
            <th style={styles.th}>描述</th>
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
          ) : stuffList.length === 0 ? (
            <tr>
              <td colSpan="9" style={{...styles.td, textAlign: 'center', padding: '40px'}}>
                暂无数据
              </td>
            </tr>
          ) : (
            stuffList.map(stuff => (
              <tr key={stuff.stuff_id}>
                <td style={styles.td}>
                  <strong>{stuff.stuff_name}</strong>
                </td>
                <td style={styles.td}>{stuff.type}</td>
                <td style={styles.td}>
                  {stuff.location && stuff.cabinet ? 
                    `${stuff.location}-${stuff.cabinet}-${stuff.layer}层` : 
                    '-'}
                </td>
                <td style={styles.td}>{stuff.number_total}</td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.badge,
                    ...(stuff.number_remain > 0 ? styles.successBadge : styles.dangerBadge)
                  }}>
                    {stuff.number_remain}
                  </span>
                </td>
                <td style={styles.td}>{stuff.number_borrowed}</td>
                <td style={styles.td}>
                  <span style={{
                    ...styles.badge,
                    ...(stuff.borrow_rate < 50 ? styles.successBadge : 
                        stuff.borrow_rate < 80 ? styles.warningBadge : 
                        styles.dangerBadge)
                  }}>
                    {stuff.borrow_rate}%
                  </span>
                </td>
                <td style={styles.td}>
                  <div style={{maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                    {stuff.description}
                  </div>
                </td>
                <td style={styles.td}>
                  <div style={{display: 'flex', gap: '8px'}}>
                    <button
                      style={{...styles.button, ...styles.secondaryButton, padding: '4px 8px'}}
                      onClick={() => openEditModal(stuff)}
                      title="编辑"
                    >
                      <EditOutlined />
                    </button>
                    <button
                      style={{
                        ...styles.button, 
                        backgroundColor: '#fee2e2',
                        color: '#991b1b',
                        padding: '4px 8px'
                      }}
                      onClick={() => handleDelete(stuff.stuff_id, stuff.stuff_name)}
                      title="删除"
                      disabled={stuff.number_borrowed > 0}
                    >
                      <DeleteOutlined />
                    </button>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {/* 创建物资弹窗 */}
      {showCreateModal && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2 style={styles.modalHeader}>新增物资</h2>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>物资类型 *</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="例如：开发板、传感器、工具等"
                value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value})}
              />
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>物资名称 *</label>
              <input
                style={styles.modalInput}
                type="text"
                placeholder="请输入物资名称"
                value={formData.stuff_name}
                onChange={(e) => setFormData({...formData, stuff_name: e.target.value})}
              />
            </div>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px'}}>
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>总数量 *</label>
                <input
                  style={styles.modalInput}
                  type="number"
                  min="0"
                  value={formData.number_total}
                  onChange={(e) => setFormData({...formData, number_total: parseInt(e.target.value) || 0})}
                />
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>剩余数量 *</label>
                <input
                  style={styles.modalInput}
                  type="number"
                  min="0"
                  max={formData.number_total}
                  value={formData.number_remain}
                  onChange={(e) => setFormData({...formData, number_remain: parseInt(e.target.value) || 0})}
                />
              </div>
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>描述信息</label>
              <textarea
                style={{...styles.modalInput, minHeight: '80px', resize: 'vertical'}}
                placeholder="请输入物资描述..."
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </div>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px'}}>
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>所在场地</label>
                <select
                  style={styles.modalSelect}
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                >
                  <option value="">请选择</option>
                  {locations.map(loc => (
                    <option key={loc} value={loc}>{loc}</option>
                  ))}
                </select>
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>展柜位置</label>
                <select
                  style={styles.modalSelect}
                  value={formData.cabinet}
                  onChange={(e) => setFormData({...formData, cabinet: e.target.value})}
                >
                  <option value="">请选择</option>
                  {cabinets.slice(0, 26).map(cab => (
                    <option key={cab} value={cab}>{cab}</option>
                  ))}
                </select>
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>所在层数</label>
                <select
                  style={styles.modalSelect}
                  value={formData.layer}
                  onChange={(e) => setFormData({...formData, layer: parseInt(e.target.value)})}
                >
                  {[1,2,3,4,5,6].map(layer => (
                    <option key={layer} value={layer}>第{layer}层</option>
                  ))}
                </select>
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

      {/* 编辑物资弹窗 */}
      {showEditModal && (
        <div style={styles.modal}>
          <div style={styles.modalContent}>
            <h2 style={styles.modalHeader}>编辑物资</h2>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>物资类型</label>
              <input
                style={styles.modalInput}
                type="text"
                value={formData.type}
                onChange={(e) => setFormData({...formData, type: e.target.value})}
              />
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>物资名称</label>
              <input
                style={styles.modalInput}
                type="text"
                value={formData.stuff_name}
                onChange={(e) => setFormData({...formData, stuff_name: e.target.value})}
              />
            </div>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px'}}>
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>总数量</label>
                <input
                  style={styles.modalInput}
                  type="number"
                  min="0"
                  value={formData.number_total}
                  onChange={(e) => setFormData({...formData, number_total: parseInt(e.target.value) || 0})}
                />
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>剩余数量</label>
                <input
                  style={styles.modalInput}
                  type="number"
                  min="0"
                  max={formData.number_total}
                  value={formData.number_remain}
                  onChange={(e) => setFormData({...formData, number_remain: parseInt(e.target.value) || 0})}
                />
              </div>
            </div>
            
            <div style={styles.modalFormGroup}>
              <label style={styles.modalLabel}>描述信息</label>
              <textarea
                style={{...styles.modalInput, minHeight: '80px', resize: 'vertical'}}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </div>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px'}}>
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>所在场地</label>
                <select
                  style={styles.modalSelect}
                  value={formData.location}
                  onChange={(e) => setFormData({...formData, location: e.target.value})}
                >
                  <option value="">请选择</option>
                  {locations.map(loc => (
                    <option key={loc} value={loc}>{loc}</option>
                  ))}
                </select>
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>展柜位置</label>
                <select
                  style={styles.modalSelect}
                  value={formData.cabinet}
                  onChange={(e) => setFormData({...formData, cabinet: e.target.value})}
                >
                  <option value="">请选择</option>
                  {cabinets.slice(0, 26).map(cab => (
                    <option key={cab} value={cab}>{cab}</option>
                  ))}
                </select>
              </div>
              
              <div style={styles.modalFormGroup}>
                <label style={styles.modalLabel}>所在层数</label>
                <select
                  style={styles.modalSelect}
                  value={formData.layer}
                  onChange={(e) => setFormData({...formData, layer: parseInt(e.target.value)})}
                >
                  {[1,2,3,4,5,6].map(layer => (
                    <option key={layer} value={layer}>第{layer}层</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div style={styles.modalFooter}>
              <button
                style={{...styles.button, ...styles.secondaryButton}}
                onClick={() => {
                  setShowEditModal(false);
                  setEditingStuff(null);
                  resetForm();
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
    </div>
  );
};

export default StuffManagement;