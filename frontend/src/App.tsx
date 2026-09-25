import React, { Suspense, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import './config'; // Ensures axios interceptor is loaded

const Landing = React.lazy(() => import('./pages/Landing'));
const Login = React.lazy(() => import('./pages/Login'));
const Register = React.lazy(() => import('./pages/Register'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Onboarding = React.lazy(() => import('./pages/Onboarding'));
const RiskPassport = React.lazy(() => import('./pages/RiskPassport'));
const CommitAudit = React.lazy(() => import('./pages/CommitAudit'));

function TokenExtractor() {
  const location = useLocation();
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes('token=')) {
      const params = new URLSearchParams(hash.substring(1));
      const token = params.get('token');
      if (token) {
        localStorage.setItem('access_token', token);
        // Remove token from visible URL without triggering reload
        window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
      }
    }
  }, [location]);
  return null;
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <TokenExtractor />
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-background-light dark:bg-background-dark text-slate-500">Loading...</div>}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/passport" element={<RiskPassport />} />
              <Route path="/repositories/:repositoryId/scans/:scanId/audit" element={<CommitAudit />} />
            </Route>
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
