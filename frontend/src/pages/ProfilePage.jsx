import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, Save, User } from 'lucide-react';
import api, { getErrorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (fullName.trim().length < 2) {
      setError('Full name must be at least 2 characters.');
      return;
    }

    setSaving(true);
    try {
      const { data } = await api.put('/auth/profile', { full_name: fullName.trim() });
      setUser(data.user);
      setSuccess('Profile details updated.');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not update profile.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Student Profile</h1>
          <p className="page-subtitle">Manage your personal account details.</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="alert alert-success" role="status">
          <CheckCircle2 size={18} />
          <span>{success}</span>
        </div>
      )}

      <div className="card" style={{ maxWidth: '540px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div className="brand-mark" aria-hidden="true">
            <User size={18} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.08rem' }}>{user?.full_name}</div>
            <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>{user?.email}</div>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <div className="form-group">
            <label className="form-label" htmlFor="profile-name">Full Name</label>
            <input
              id="profile-name"
              type="text"
              className="form-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="profile-email">Email Address</label>
            <input
              id="profile-email"
              type="email"
              className="form-input"
              value={user?.email || ''}
              disabled
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            <Save size={16} />
            <span>{saving ? 'Saving...' : 'Save Profile'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
