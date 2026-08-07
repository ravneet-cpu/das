import React, { useState, useEffect } from 'react';
import { User, Plus, Edit2, Trash2, Shield, RefreshCw, Eye, EyeOff, Save, X, Mail } from 'lucide-react';

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showPasswords, setShowPasswords] = useState({});

  // Form state
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    role: 'validator'
  });

  // Fetch users
  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/users', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
	throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      setUsers(data.users || []);
      
    } catch (err) {
      setError(`Error loading: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle create user
  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!formData.username || !formData.password) {
      setError('Username and password required');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
	throw new Error(errorData.error || 'Error creating user');
      }

	setSuccess('User created successfully');
      setFormData({ username: '', password: '', email: '', role: 'validator' });
      setShowCreateForm(false);
      await fetchUsers();
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle update user
  const handleUpdateUser = async (userId, updates) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(updates)
      });

      if (!response.ok) {
        const errorData = await response.json();
	 throw new Error(errorData.error || 'Error updating user');
      }

      setSuccess('User updated successfully');
      setEditingUser(null);
      await fetchUsers();
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete user
  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`Are you sure you want to delete user "${username}" ?`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
	throw new Error(errorData.error || 'Error deleting user');
      }

	setSuccess('User deleted successfully');
      await fetchUsers();
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Toggle password visibility
  const togglePasswordVisibility = (userId) => {
    setShowPasswords(prev => ({
      ...prev,
      [userId]: !prev[userId]
    }));
  };

  // Send password by email
  const handleSendPassword = async (userId, username, email) => {
    if (!email) {
      setError('This user has no email configured');
      return;
    }

    if (!confirm(`Send new password to ${username} (${email})?`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/users/${userId}/send-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
	throw new Error(errorData.error || 'Error sending email');
      }

      const data = await response.json();
      setSuccess(data.message);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // Auto-clear messages
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const styles = {
    container: {
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto'
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '2rem'
    },
    title: {
      fontSize: '1.875rem',
      fontWeight: 'bold',
      margin: 0,
      color: '#1f2937'
    },
    button: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      padding: '0.75rem 1rem',
      border: 'none',
      borderRadius: '0.5rem',
      fontSize: '0.875rem',
      cursor: 'pointer',
      transition: 'background-color 0.2s'
    },
    buttonPrimary: {
      backgroundColor: '#3b82f6',
      color: 'white'
    },
    buttonSuccess: {
      backgroundColor: '#10b981',
      color: 'white'
    },
    buttonDanger: {
      backgroundColor: '#ef4444',
      color: 'white'
    },
    buttonSecondary: {
      backgroundColor: '#6b7280',
      color: 'white'
    },
    card: {
      backgroundColor: 'white',
      borderRadius: '0.5rem',
      padding: '1.5rem',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      marginBottom: '1rem'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse'
    },
    th: {
      padding: '0.75rem',
      textAlign: 'left',
      fontWeight: 'bold',
      borderBottom: '1px solid #e5e7eb',
      backgroundColor: '#f9fafb'
    },
    td: {
      padding: '0.75rem',
      borderBottom: '1px solid #e5e7eb'
    },
    input: {
      width: '100%',
      padding: '0.5rem',
      border: '1px solid #d1d5db',
      borderRadius: '0.375rem',
      fontSize: '0.875rem'
    },
    select: {
      width: '100%',
      padding: '0.5rem',
      border: '1px solid #d1d5db',
      borderRadius: '0.375rem',
      fontSize: '0.875rem',
      backgroundColor: 'white'
    },
    alert: {
      padding: '0.75rem 1rem',
      borderRadius: '0.375rem',
      marginBottom: '1rem',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem'
    },
    alertError: {
      backgroundColor: '#fef2f2',
      color: '#dc2626',
      border: '1px solid #fecaca'
    },
    alertSuccess: {
      backgroundColor: '#f0fdf4',
      color: '#16a34a',
      border: '1px solid #bbf7d0'
    },
    badge: {
      padding: '0.25rem 0.5rem',
      borderRadius: '9999px',
      fontSize: '0.75rem',
      fontWeight: '500'
    },
    badgeAdmin: {
      backgroundColor: '#faf5ff',
      color: '#7c3aed'
    },
    badgeValidator: {
      backgroundColor: '#f0fdf4',
      color: '#16a34a'
    },
    badgeUploader: {
      backgroundColor: '#eff6ff',
      color: '#2563eb'
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
	<h2 style={styles.title}>User Management</h2>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={fetchUsers}
            disabled={loading}
            style={{
              ...styles.button,
              ...styles.buttonSecondary,
              opacity: loading ? 0.5 : 1
            }}
          >
            <RefreshCw style={{ width: '1rem', height: '1rem' }} />
		Refresh
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            style={{
              ...styles.button,
              ...styles.buttonPrimary
            }}
          >
            <Plus style={{ width: '1rem', height: '1rem' }} />
		New User
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div style={{ ...styles.alert, ...styles.alertError }}>
          <X style={{ width: '1rem', height: '1rem' }} />
          {error}
        </div>
      )}
      
      {success && (
        <div style={{ ...styles.alert, ...styles.alertSuccess }}>
          <Save style={{ width: '1rem', height: '1rem' }} />
          {success}
        </div>
      )}

      {/* Create Form */}
      {showCreateForm && (
        <div style={styles.card}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: '600' }}>
		Create New User
          </h3>
          <form onSubmit={handleCreateUser}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  style={styles.input}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                  Email
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  style={styles.input}
                  placeholder="user@example.com"
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                  Password
                </label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  style={styles.input}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500' }}>
                  Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  style={styles.select}
                >
                  <option value="validator">Validator</option>
                  <option value="uploader">Uploader</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                type="submit"
                disabled={loading}
                style={{
                  ...styles.button,
                  ...styles.buttonSuccess,
                  opacity: loading ? 0.5 : 1
                }}
              >
                <Save style={{ width: '1rem', height: '1rem' }} />
		Create
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                style={{
                  ...styles.button,
                  ...styles.buttonSecondary
                }}
              >
                <X style={{ width: '1rem', height: '1rem' }} />
		Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div style={styles.card}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: '600' }}>
		 Users ({users.length})
        </h3>
        
        {loading && users.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
            Loading...
          </div>
        ) : users.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
		No users found
          </div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>User</th>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Password</th>
                <th style={styles.th}>Role</th>
                <th style={styles.th}>Validations</th>
                <th style={styles.th}>Created on</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td style={styles.td}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <User style={{ width: '1rem', height: '1rem', color: '#6b7280' }} />
                      {editingUser === user.id ? (
                        <input
                          type="text"
                          defaultValue={user.username}
                          style={{ ...styles.input, width: '150px' }}
                          onBlur={(e) => {
                            if (e.target.value !== user.username) {
                              handleUpdateUser(user.id, { username: e.target.value });
                            }
                          }}
                        />
                      ) : (
                        <span>{user.username}</span>
                      )}
                    </div>
                  </td>
                  <td style={styles.td}>
                    {editingUser === user.id ? (
                      <input
                        type="email"
                        defaultValue={user.email || ''}
                        placeholder="user@example.com"
                        style={{ ...styles.input, width: '200px' }}
                        onBlur={(e) => {
                          if (e.target.value !== (user.email || '')) {
                            handleUpdateUser(user.id, { email: e.target.value });
                          }
                        }}
                      />
                    ) : (
                      <span style={{ color: user.email ? '#374151' : '#9ca3af', fontStyle: user.email ? 'normal' : 'italic' }}>
                        {user.email || 'No email'}
                      </span>
                    )}
                  </td>
                  <td style={styles.td}>
                    {editingUser === user.id ? (
                      <select
                        defaultValue={user.role}
                        style={{ ...styles.select, width: '120px' }}
                        onChange={(e) => {
                          handleUpdateUser(user.id, { role: e.target.value });
                        }}
                      >
                        <option value="validator">Validator</option>
                        <option value="uploader">Uploader</option>
                        <option value="admin">Administrator</option>
                      </select>
                    ) : (
                      <span style={{
                        ...styles.badge,
                        ...(user.role === 'admin' ? styles.badgeAdmin :
                            user.role === 'validator' ? styles.badgeValidator :
                            styles.badgeUploader)
                      }}>
                        {user.role}
                      </span>
                    )}
                  </td>
                  <td style={styles.td}>
                    <span style={{ fontWeight: '600', color: '#059669' }}>
                      {user.validation_count || 0}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {user.created_at ? new Date(user.created_at).toLocaleDateString('fr-FR') : '-'}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {editingUser === user.id ? (
                        <button
                          onClick={() => setEditingUser(null)}
                          style={{
                            ...styles.button,
                            ...styles.buttonSuccess,
                            padding: '0.5rem'
                          }}
                        >
                          <Save style={{ width: '1rem', height: '1rem' }} />
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => setEditingUser(user.id)}
                            style={{
                              ...styles.button,
                              ...styles.buttonSecondary,
                              padding: '0.5rem'
                            }}
				title="Edit User"
                          >
                            <Edit2 style={{ width: '1rem', height: '1rem' }} />
                          </button>
                          <button
                            onClick={() => handleSendPassword(user.id, user.username, user.email)}
                            disabled={!user.email || loading}
                            style={{
                              ...styles.button,
                              ...styles.buttonPrimary,
                              padding: '0.5rem',
                              opacity: (!user.email || loading) ? 0.5 : 1
                            }}
				 title={user.email ? 'Send new password by email' : 'No email configured'}
                          >
                            <Mail style={{ width: '1rem', height: '1rem' }} />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => handleDeleteUser(user.id, user.username)}
                        style={{
                          ...styles.button,
                          ...styles.buttonDanger,
                          padding: '0.5rem'
                        }}
			 title="Delete User"
                      >
                        <Trash2 style={{ width: '1rem', height: '1rem' }} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UserManagement;
