import { API_URL } from '../config';
import { useState, useEffect } from 'react';
import { GitBranch, CheckCircle2, ChevronRight, Loader2, GitFork, Shield, Search } from 'lucide-react';
import axios from 'axios';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [repos, setRepos] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(false);

  useEffect(() => {
    if (scanning) {
      const interval = setInterval(() => {
        setScanProgress(prev => {
          if (prev >= 100) {
            clearInterval(interval);
            setScanning(false);
            return 100;
          }
          return prev + 5;
        });
      }, 200);
      return () => clearInterval(interval);
    }
  }, [scanning]);

  const handleConnect = async () => {
    setStep(2);
    setLoadingRepos(true);
    try {
      const res = await axios.get(`${API_URL}/repositories/github`, {
        withCredentials: true
      });
      setRepos(res.data);
    } catch (e) {
      console.error(e);
      // In case of error (e.g. no token), we stay on step 2 but show empty
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleSelect = async (repo: any) => {
    setStep(3);
    setScanning(false);
    
    try {
      // 1. Create repo in DB
      const createRes = await axios.post(`${API_URL}/repositories/`, {
        name: repo.name,
        url: repo.url
      }, {
        withCredentials: true
      });
      
      void createRes.data;
      
      // Initial scans are only started from an immutable Git SHA, never a moving branch name.
      setScanning(false);
    } catch(e) {
      console.error("Failed to connect repo and scan", e);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8">
      {/* Stepper */}
      <div className="mb-12">
        <div className="flex items-center justify-between relative">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-border-light dark:bg-border-dark -z-10" />
          {[
            { num: 1, title: 'Connect' },
            { num: 2, title: 'Select Repository' },
            { num: 3, title: 'Initial Scan' }
          ].map((s) => (
            <div key={s.num} className="flex flex-col items-center bg-background-light dark:bg-background-dark px-4">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-colors ${
                step > s.num ? 'bg-brand-500 border-brand-500 text-white' :
                step === s.num ? 'bg-background-light dark:bg-background-dark border-brand-500 text-brand-500' :
                'bg-surface-light dark:bg-surface-dark border-border-light dark:border-border-dark text-slate-400'
              }`}>
                {step > s.num ? <CheckCircle2 className="w-5 h-5" /> : s.num}
              </div>
              <span className={`mt-2 text-sm font-medium ${step >= s.num ? 'text-slate-900 dark:text-white' : 'text-slate-400'}`}>
                {s.title}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="bg-surface-light dark:bg-surface-dark rounded-2xl border border-border-light dark:border-border-dark shadow-soft dark:shadow-soft-dark overflow-hidden">
        {step === 1 && (
          <div className="p-12 text-center flex flex-col items-center">
            <div className="w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-6">
              <GitBranch className="w-10 h-10 text-slate-700 dark:text-slate-300" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Connect your Provider</h2>
            <p className="text-slate-500 dark:text-slate-400 mb-8 max-w-sm">
              Link your GitHub account to allow Risk Passport to scan your repositories for vulnerabilities and secrets.
            </p>
            <button 
              onClick={handleConnect}
              className="px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-medium rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors flex items-center shadow-lg shadow-slate-900/10 dark:shadow-white/10"
            >
              <GitBranch className="w-5 h-5 mr-2" />
              Load GitHub Repositories
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col h-[500px]">
            <div className="p-6 border-b border-border-light dark:border-border-dark">
              <h2 className="text-xl font-bold mb-4">Select a Repository</h2>
              <div className="relative">
                <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input 
                  type="text" 
                  placeholder="Search repositories..." 
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {loadingRepos ? (
                <div className="p-12 flex justify-center"><Loader2 className="w-8 h-8 text-brand-500 animate-spin" /></div>
              ) : repos.length === 0 ? (
                <div className="p-12 text-center text-slate-500">No repositories found or not connected to GitHub.</div>
              ) : repos.map((repo: any) => (
                <div key={repo.name} className="flex items-center justify-between p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg cursor-pointer group" onClick={() => handleSelect(repo)}>
                  <div className="flex items-center space-x-3">
                    <GitFork className="w-5 h-5 text-slate-400" />
                    <div>
                      <h3 className="font-medium">{repo.name}</h3>
                      <p className="text-xs text-slate-500">{repo.language || 'Unknown language'}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight className="w-5 h-5 text-slate-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
            {scanning ? (
              <>
                <div className="relative mb-8">
                  <div className="w-24 h-24 rounded-full border-4 border-slate-100 dark:border-slate-800 flex items-center justify-center">
                    <Loader2 className="w-10 h-10 text-brand-500 animate-spin" />
                  </div>
                  <div className="absolute top-0 right-0 w-6 h-6 bg-brand-500 rounded-full flex items-center justify-center animate-pulse shadow-lg shadow-brand-500/50">
                    <Shield className="w-3 h-3 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold mb-2">Scanning Repository</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-6">Analyzing code quality, secrets, and dependencies...</p>
                <div className="w-full max-w-md h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-brand-500 to-purple-500 transition-all duration-300"
                    style={{ width: `${scanProgress}%` }}
                  />
                </div>
                <p className="text-sm font-medium mt-3 text-slate-500">{scanProgress}%</p>
              </>
            ) : (
              <>
                <div className="w-24 h-24 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 flex items-center justify-center mb-6">
                  <CheckCircle2 className="w-12 h-12" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Repository Connected</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-8">An initial scan will begin when an immutable commit SHA is selected.</p>
                <button 
                  onClick={() => window.location.href = '/dashboard'}
                  className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"
                >
                  Return to Dashboard
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
