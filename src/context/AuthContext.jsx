// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Try to load user from localStorage on app startup
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (token && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        if (parsedUser && parsedUser.username && parsedUser.role) {
          // Validate the token by fetching user info
          fetchUserInfo(token);
        } else {
          console.log('Invalid saved user data, clearing localStorage');
          logout();
        }
      } catch (err) {
        console.error('Error parsing saved user or validating token:', err);
        logout();
      }
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUserInfo = async (token) => {
    try {
      const response = await fetch('/api/auth/user-info', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const userData = await response.json();
        if (userData && userData.username && userData.role) {
          setUser({
            username: userData.username,
            role: userData.role,
            token
          });
          localStorage.setItem('user', JSON.stringify({
            username: userData.username,
            role: userData.role
          }));
        } else {
          console.error('Invalid user data received:', userData);
          logout();
        }
      } else {
        console.log('Token validation failed:', response.status);
        // Token is invalid or expired
        logout();
      }
    } catch (err) {
      console.error('Error fetching user info:', err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password, twofa_code = '') => {
    setLoading(true);
    setError(null);
    
    try {
      const requestBody = { username, password };
      if (twofa_code) {
        requestBody.twofa_code = twofa_code;
      }
      
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        const userData = {
          username: data.username,
          role: data.role,
          token: data.token
        };
        
        setUser(userData);
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify({
          username: data.username,
          role: data.role
        }));
        
        return true;
      } else {
	setError(data.error || 'Connection failed');
        return false;
      }
    } catch (err) {
	setError('Server connection error');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
