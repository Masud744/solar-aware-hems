import React, { useState, useEffect, useCallback } from 'react';
import { getAdminUsersApi, approveUserApi, rejectUserApi, setUserRoleApi } from '../../api/client';
import { useAuth } from '../../hooks/useAuth';
import type { UserProfile, UserStatus } from '../../types';

export function AdminPage() {
  const { user: currentAdmin } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await getAdminUsersApi('all');
      setUsers(res.users || []);
    } catch (err: any) {
      setMessage({ text: err?.message || 'Failed to fetch user list.', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleApprove = async (targetUser: UserProfile) => {
    setActionLoading(targetUser.id);
    setMessage(null);
    try {
      await approveUserApi(targetUser.id);
      setMessage({ text: `User ${targetUser.email} has been approved successfully!`, type: 'success' });
      await loadUsers();
    } catch (err: any) {
      setMessage({ text: err?.message || 'Failed to approve user.', type: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (targetUser: UserProfile) => {
    if (targetUser.id === currentAdmin?.id) {
      alert('You cannot reject your own administrator account.');
      return;
    }
    if (!confirm(`Are you sure you want to reject access for ${targetUser.email}?`)) return;

    setActionLoading(targetUser.id);
    setMessage(null);
    try {
      await rejectUserApi(targetUser.id);
      setMessage({ text: `User ${targetUser.email} access has been rejected.`, type: 'success' });
      await loadUsers();
    } catch (err: any) {
      setMessage({ text: err?.message || 'Failed to reject user.', type: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleRole = async (targetUser: UserProfile) => {
    if (targetUser.id === currentAdmin?.id) {
      alert('You cannot modify your own administrator role here.');
      return;
    }
    const newRole = targetUser.role === 'admin' ? 'user' : 'admin';
    if (!confirm(`Change role for ${targetUser.email} to '${newRole}'?`)) return;

    setActionLoading(targetUser.id);
    setMessage(null);
    try {
      await setUserRoleApi(targetUser.id, newRole);
      setMessage({ text: `Role for ${targetUser.email} updated to ${newRole}.`, type: 'success' });
      await loadUsers();
    } catch (err: any) {
      setMessage({ text: err?.message || 'Failed to change user role.', type: 'error' });
    } finally {
      setActionLoading(null);
    }
  };

  const pendingCount = users.filter((u) => u.status === 'pending').length;
  const approvedCount = users.filter((u) => u.status === 'approved').length;
  const rejectedCount = users.filter((u) => u.status === 'rejected').length;

  const filteredUsers = users.filter((u) => {
    if (activeTab === 'all') return true;
    return u.status === activeTab;
  });

  return (
    <div className="page admin-page" style={{ maxWidth: '1080px', margin: '0 auto' }}>
      {/* 1. Header */}
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.6875rem', fontWeight: 800, letterSpacing: '0.12em', color: 'var(--text-3)', marginBottom: '4px' }}>
              ADMINISTRATION & ACCESS CONTROL
            </div>
            <h1 className="t-display" style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>User Approval Management</span>
              <span className="badge-online" style={{ fontSize: '0.75rem', padding: '3px 8px', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', fontWeight: 600 }}>
                🛡️ Admin Area
              </span>
            </h1>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', marginTop: '4px' }}>
              Review pending registrations, approve user access to the SolarMate dashboard, and manage system roles.
            </p>
          </div>

          <button
            className="btn-secondary"
            onClick={loadUsers}
            disabled={loading}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', padding: '8px 14px' }}
          >
            <span>🔄</span>
            <span>Refresh Users</span>
          </button>
        </div>
      </div>

      {/* 2. Notification Message */}
      {message && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--r-md, 10px)',
            background: message.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${message.type === 'success' ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'}`,
            color: message.type === 'success' ? '#34d399' : '#f87171',
            fontSize: '0.875rem',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>{message.type === 'success' ? '✅' : '⚠️'} {message.text}</span>
          <button
            onClick={() => setMessage(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. Summary Stats Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '12px',
          marginBottom: '24px',
        }}
      >
        <div className="card glass" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontWeight: 700 }}>PENDING APPROVAL</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fbbf24', marginTop: '4px' }}>
            {pendingCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-2)', marginTop: '2px' }}>Awaiting admin review</div>
        </div>

        <div className="card glass" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontWeight: 700 }}>APPROVED USERS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>
            {approvedCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-2)', marginTop: '2px' }}>Active dashboard access</div>
        </div>

        <div className="card glass" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontWeight: 700 }}>REJECTED USERS</div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f87171', marginTop: '4px' }}>
            {rejectedCount}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-2)', marginTop: '2px' }}>Access blocked</div>
        </div>
      </div>

      {/* 4. Filter Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--border)',
          marginBottom: '16px',
          paddingBottom: '8px',
        }}
      >
        {(
          [
            { key: 'pending', label: 'Pending Review', count: pendingCount },
            { key: 'approved', label: 'Approved Users', count: approvedCount },
            { key: 'rejected', label: 'Rejected', count: rejectedCount },
            { key: 'all', label: 'All Registered Users', count: users.length },
          ] as const
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              background: activeTab === tab.key ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
              border: `1px solid ${activeTab === tab.key ? 'rgba(245, 158, 11, 0.4)' : 'transparent'}`,
              borderRadius: '8px',
              padding: '6px 14px',
              color: activeTab === tab.key ? '#fff' : 'var(--text-2)',
              fontWeight: activeTab === tab.key ? 700 : 500,
              fontSize: '0.85rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s ease',
            }}
          >
            <span>{tab.label}</span>
            <span
              style={{
                fontSize: '0.75rem',
                padding: '1px 6px',
                borderRadius: '10px',
                background: activeTab === tab.key ? 'var(--solar, #f59e0b)' : 'rgba(255, 255, 255, 0.08)',
                color: activeTab === tab.key ? '#111827' : 'inherit',
                fontWeight: 700,
              }}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* 5. User Table Container */}
      <div className="card glass" style={{ padding: '0', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-3)' }}>
            <span className="spinner" style={{ width: '24px', height: '24px', marginBottom: '8px' }} />
            <div>Loading registered users...</div>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-3)' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>📂</div>
            <div style={{ fontSize: '0.9375rem', fontWeight: 600 }}>No users found in this category.</div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ background: 'rgba(255, 255, 255, 0.03)', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-3)', fontSize: '0.75rem', textTransform: 'uppercase' }}>User / Email</th>
                  <th style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-3)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Registered</th>
                  <th style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-3)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Role</th>
                  <th style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-3)', fontSize: '0.75rem', textTransform: 'uppercase' }}>Approval Status</th>
                  <th style={{ padding: '12px 16px', fontWeight: 700, color: 'var(--text-3)', fontSize: '0.75rem', textTransform: 'uppercase', textAlign: 'right' }}>Admin Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isCurrent = u.id === currentAdmin?.id;
                  const isBusy = actionLoading === u.id;

                  return (
                    <tr
                      key={u.id}
                      style={{
                        borderBottom: '1px solid var(--border)',
                        background: u.status === 'pending' ? 'rgba(245, 158, 11, 0.03)' : 'transparent',
                      }}
                    >
                      {/* Name / Email */}
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ fontWeight: 600, color: '#fff' }}>
                          {u.full_name || 'No Name Provided'}
                          {isCurrent && (
                            <span style={{ marginLeft: '6px', fontSize: '0.7rem', color: 'var(--solar)', fontWeight: 700 }}>
                              (You)
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-3)' }}>{u.email}</div>
                      </td>

                      {/* Registered Date */}
                      <td style={{ padding: '14px 16px', color: 'var(--text-2)', fontSize: '0.8125rem' }}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : 'Unknown'}
                      </td>

                      {/* Role */}
                      <td style={{ padding: '14px 16px' }}>
                        <span
                          style={{
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: '6px',
                            background: u.role === 'admin' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                            color: u.role === 'admin' ? '#c084fc' : 'var(--text-2)',
                            border: `1px solid ${u.role === 'admin' ? 'rgba(168, 85, 247, 0.3)' : 'transparent'}`,
                          }}
                        >
                          {u.role === 'admin' ? '👑 Admin' : 'User'}
                        </span>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '14px 16px' }}>
                        {u.status === 'approved' && (
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                            ✅ Approved
                          </span>
                        )}
                        {u.status === 'pending' && (
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px', background: 'rgba(245, 158, 11, 0.18)', color: '#fbbf24' }}>
                            ⏳ Pending
                          </span>
                        )}
                        {u.status === 'rejected' && (
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '3px 8px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171' }}>
                            🚫 Rejected
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                          {u.status !== 'approved' && (
                            <button
                              onClick={() => handleApprove(u)}
                              disabled={isBusy}
                              style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                background: '#10b981',
                                color: '#fff',
                                fontWeight: 700,
                                fontSize: '0.75rem',
                                border: 'none',
                                cursor: isBusy ? 'not-allowed' : 'pointer',
                              }}
                            >
                              {isBusy ? '...' : 'Approve'}
                            </button>
                          )}

                          {u.status !== 'rejected' && !isCurrent && (
                            <button
                              onClick={() => handleReject(u)}
                              disabled={isBusy}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                color: '#f87171',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                cursor: isBusy ? 'not-allowed' : 'pointer',
                              }}
                            >
                              Reject
                            </button>
                          )}

                          {!isCurrent && u.status === 'approved' && (
                            <button
                              onClick={() => handleToggleRole(u)}
                              disabled={isBusy}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                background: 'rgba(255, 255, 255, 0.06)',
                                color: 'var(--text-2)',
                                border: '1px solid var(--border)',
                                fontSize: '0.75rem',
                                cursor: isBusy ? 'not-allowed' : 'pointer',
                              }}
                              title={u.role === 'admin' ? 'Demote to normal user' : 'Promote to administrator'}
                            >
                              {u.role === 'admin' ? 'Demote' : 'Make Admin'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
