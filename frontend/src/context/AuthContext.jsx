import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('learnable_token') || '');
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('learnable_token')));

  const refreshUser = useCallback(async () => {
    const stored = localStorage.getItem('learnable_token');
    if (!stored) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const { data } = await api.get('/auth/me');
      setUser(data.user);
      return data.user;
    } catch {
      localStorage.removeItem('learnable_token');
      setToken('');
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const register = async ({ full_name, email, password, confirm_password }) => {
    const { data } = await api.post('/auth/register', {
      full_name,
      email,
      password,
      confirm_password,
    });
    localStorage.setItem('learnable_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const login = async ({ email, password }) => {
    const { data } = await api.post('/auth/login', { email, password });
    localStorage.setItem('learnable_token', data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      if (token) {
        await api.post('/auth/logout');
      }
    } catch {
      // Ignore network errors during logout cleanup
    } finally {
      localStorage.removeItem('learnable_token');
      setToken('');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: Boolean(user && token),
        register,
        login,
        logout,
        refreshUser,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
