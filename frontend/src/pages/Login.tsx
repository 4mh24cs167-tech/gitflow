import { API_URL } from '../config';
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, GitBranch } from 'lucide-react';
import axios from 'axios';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const res = await axios.post(${API_URL}/auth/login, formData);
      localStorage.setItem('access_token', res.data.access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden bg-background-light dark:bg-background-dark">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-500/10 blur-[100px] rounded-full pointer-events-none" />
      
      <div className="w-full max-w-md p-8 rounded-2xl bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark shadow-xl shadow-black/5 dark:shadow-black/20 z-10">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center mb-4">
            <Shield className="w-6 h-6 text-brand-500" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight mb-1">Welcome back</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">Sign in to your account to continue</p>
        </div>

        <a href={${API_URL}/auth/github/login} className="w-full mb-6 flex items-center justify-center px-4 py-2.5 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors font-medium text-sm">
          <GitBranch className="w-5 h-5 mr-2" />
          Continue with GitHub
        </a>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border-light dark:border-border-dark"></div>
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="px-2 bg-surface-light dark:bg-surface-dark text-slate-500">Or sign in with username</span>
          </div>
        </div>
        
        {error && <div className="mb-4 text-red-500 text-sm text-center">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5 text-slate-700 dark:text-slate-300">Username</label>
            <input 
              type="text" 
              required
              value={username}
              onChange={(e: any) => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50 transition-shadow"
              placeholder="you"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Password</label>
              <a href="#" className="text-xs text-brand-600 dark:text-brand-400 hover:underline">Forgot password?</a>
            </div>
            <input 
              type="password" 
              required
              value={password}
              onChange={(e: any) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50 transition-shadow"
              placeholder="••••••••"
            />
          </div>
          <button type="submit" className="w-full py-2.5 rounded-lg bg-brand-500 hover:bg-brand-600 text-white font-medium transition-colors mt-2 shadow-lg shadow-brand-500/25">
            Sign In
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-500">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
