import { useState, useEffect, useRef } from 'react';
import { GitBranch, CheckCircle2, ChevronRight, Loader2, GitFork, Shield, Search, AlertCircle, Lock, Globe } from 'lucide-react';
import { apiClient } from '../config';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [scannedSha, setScannedSha] = useState<string | null>(null);
  const [scanId, setScanId] = useState<number | null>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [repoId, setRepoId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  
  const pollingRef = useRef<any>(null);
  const consecutiveErrorsRef = useRef(0);
  const startPollingTimeRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  const fetchScanStatus = async (repository_id: number, currentScanId: number) => {
    try {
      const res = await apiClient.get(`/repositories/${repository_id}/scans/${currentScanId}`);
      consecutiveErrorsRef.current = 0;
      
      const status = res.data.status;
      setScanStatus(status);
      if (res.data.commit_sha && res.data.commit_sha !== "HEAD") {
          setScannedSha(res.data.commit_sha.substring(0, 7));
      }

      return status;
    } catch (err) {
      console.error("Failed to poll scan status", err);
      consecutiveErrorsRef.current += 1;
      
      if (consecutiveErrorsRef.current >= 5) {
        setScanning(false);
        setScanStatus('POLLING_ERROR');
        setErrorMsg("Unable to retrieve scan status. The scan may still be running.");
        return 'POLLING_ERROR';
      }
      return null;
    }
  };

  const pollScanStatus = async (repository_id: number, currentScanId: number) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    consecutiveErrorsRef.current = 0;
    startPollingTimeRef.current = Date.now();
    
    // Initial fetch
    const initialStatus = await fetchScanStatus(repository_id, currentScanId);
    
    if (initialStatus === 'COMPLETED' || initialStatus === 'FAILED' || initialStatus === 'POLLING_ERROR') {
      if (initialStatus === 'COMPLETED' || initialStatus === 'FAILED') {
        setScanning(false);
      }
      return; // Do not create an interval
    }
    
    pollingRef.current = setInterval(async () => {
      if (Date.now() - startPollingTimeRef.current > 10 * 60 * 1000) {
        clearInterval(pollingRef.current);
        setScanning(false);
        setScanStatus('TIMEOUT');
        setErrorMsg("Scan is taking longer than expected.");
        return;
      }
      
      const status = await fetchScanStatus(repository_id, currentScanId);
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'POLLING_ERROR') {
        clearInterval(pollingRef.current);
        if (status === 'COMPLETED' || status === 'FAILED') {
          setScanning(false);
        }
      }
    }, 1500);
  };

  const handleConnect = async () => {
    setStep(2);
    setLoadingRepos(true);
    setErrorMsg(null);
    setSearchQuery('');
    try {
      const res = await apiClient.get(`/repositories/github`);
      setRepos(res.data);
    } catch (e: any) {
      console.error(e);
      setRepos([]);
      if (e?.response?.status === 409 || e?.response?.status === 401) {
          setErrorMsg("GitHub authentication required. Please ensure your account is linked.");
      } else {
          setErrorMsg("Failed to load GitHub repositories.");
      }
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleSelect = async (repo: any) => {
    setStep(3);
    setScanning(true);
    setScanStatus('QUEUED');
    setErrorMsg(null);
    setScannedSha(null);
    
    try {
      // 1. Create repo in DB (deduplicates by owner and url automatically in backend)
      const createRes = await apiClient.post(`/repositories/`, {
        name: repo.name,
        url: repo.url
      });
      
      const repository_id = createRes.data.id;
      setRepoId(repository_id);
      localStorage.setItem('gitflow_active_repo', repository_id.toString());
      
      // 2. Trigger initial scan
      const scanRes = await apiClient.post(`/repositories/${repository_id}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      setScanId(newScanId);
      
      // 3. Poll for status
      pollScanStatus(repository_id, newScanId);
      
    } catch(e: any) {
      console.error("Failed to connect repo and scan", e);
      setScanning(false);
      setScanStatus('FAILED');
      setErrorMsg(e?.response?.data?.detail || "An error occurred while communicating with the server.");
    }
  };

  const handleRetryScan = async () => {
    if (!repoId) return;
    setScanning(true);
    setScanStatus('QUEUED');
    setErrorMsg(null);
    setScannedSha(null);
    
    try {
      const scanRes = await apiClient.post(`/repositories/${repoId}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      setScanId(newScanId);
      pollScanStatus(repoId, newScanId);
    } catch(e: any) {
      console.error("Failed to retry scan", e);
      setScanning(false);
      setScanStatus('FAILED');
      setErrorMsg(e?.response?.data?.detail || "An error occurred while communicating with the server.");
    }
  };

  const handleRetryStatus = () => {
    if (!repoId || !scanId) return;
    setScanning(true);
    setScanStatus('QUEUED'); // Resets UI to loading while we fetch
    setErrorMsg(null);
    pollScanStatus(repoId, scanId);
  };

  const filteredRepos = repos.filter(repo => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      repo.name?.toLowerCase().includes(q) ||
      repo.language?.toLowerCase().includes(q)
    );
  });

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
              className="flex items-center px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-medium rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors"
            >
              Load GitHub Repositories
              <ChevronRight className="w-4 h-4 ml-2" />
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="p-8">
            <h2 className="text-xl font-bold mb-6">Select a Repository</h2>
            {errorMsg ? (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg mb-6 flex items-center">
                <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                <p>{errorMsg}</p>
              </div>
            ) : null}
            <div className="mb-6 relative">
              <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search repositories..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-900 border border-border-light dark:border-border-dark rounded-lg pl-10 pr-4 py-2 outline-none focus:border-brand-500 transition-colors"
              />
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
              {loadingRepos ? (
                <div className="py-12 flex flex-col items-center justify-center text-slate-500">
                  <Loader2 className="w-8 h-8 text-brand-500 animate-spin mb-4" />
                  <p>Loading repositories from GitHub...</p>
                </div>
              ) : repos.length === 0 && !errorMsg ? (
                <div className="py-12 text-center text-slate-500 dark:text-slate-400">
                  <p>No repositories found.</p>
                </div>
              ) : filteredRepos.length === 0 && repos.length > 0 ? (
                <div className="py-12 text-center text-slate-500 dark:text-slate-400">
                  <p>No repositories match your search.</p>
                </div>
              ) : (
                filteredRepos.map((repo: any) => (
                  <div 
                    key={repo.id}
                    onClick={() => handleSelect(repo)}
                    className="flex items-center p-4 rounded-xl border border-border-light dark:border-border-dark hover:border-brand-500 dark:hover:border-brand-500 cursor-pointer transition-colors group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center mr-4 group-hover:bg-brand-50 dark:group-hover:bg-brand-900/20">
                      <GitFork className="w-5 h-5 text-slate-600 dark:text-slate-400 group-hover:text-brand-500" />
                    </div>
                    <div className="flex-1 text-left">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold text-slate-900 dark:text-white">{repo.name}</h3>
                        {repo.private ? <Lock className="w-3 h-3 text-slate-400" /> : <Globe className="w-3 h-3 text-slate-400" />}
                      </div>
                      <div className="flex items-center space-x-3 mt-1">
                        {repo.language && (
                          <span className="text-xs font-medium px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-full">
                            {repo.language}
                          </span>
                        )}
                        <span className="text-xs text-slate-500">
                          {repo.default_branch && `Branch: ${repo.default_branch}`}
                        </span>
                        <span className="text-xs text-slate-500">
                          {repo.updated_at ? `Updated: ${new Date(repo.updated_at).toLocaleDateString()}` : "Updated date unavailable"}
                        </span>
                      </div>
                    </div>
                    <div className="w-8 h-8 rounded-full border border-border-light dark:border-border-dark flex items-center justify-center group-hover:border-brand-500 group-hover:bg-brand-500 group-hover:text-white transition-colors">
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
                ))
              )}
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
                {scannedSha ? (
                   <h2 className="text-2xl font-bold mb-2">Analyzing commit {scannedSha}</h2>
                ) : (
                   <h2 className="text-2xl font-bold mb-2">Scanning latest commit</h2>
                )}
                <p className="text-slate-500 dark:text-slate-400 mb-6">
                  {scanStatus === 'QUEUED' && "Scan queued. Waiting for worker..."}
                  {scanStatus === 'RUNNING' && "Analyzing repository..."}
                  {!scanStatus && "Connecting..."}
                </p>
                <div className="w-full max-w-md h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-brand-500 to-purple-500 w-full animate-pulse"
                  />
                </div>
              </>
            ) : scanStatus === 'FAILED' ? (
              <>
                <div className="w-24 h-24 rounded-full bg-red-100 dark:bg-red-900/30 text-red-500 flex items-center justify-center mb-6">
                  <AlertCircle className="w-12 h-12" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Scan failed</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-8">{errorMsg || "The background worker encountered an error while scanning the repository."}</p>
                <div className="flex space-x-4">
                  <button 
                    onClick={() => { setStep(2); setScanning(false); setScanStatus(null); }}
                    className="px-6 py-3 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
                  >
                    Return to Repository
                  </button>
                  <button 
                    onClick={handleRetryScan}
                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"
                  >
                    Retry Scan
                  </button>
                </div>
              </>
            ) : scanStatus === 'POLLING_ERROR' ? (
              <>
                <div className="w-24 h-24 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-500 flex items-center justify-center mb-6">
                  <AlertCircle className="w-12 h-12" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Connection Lost</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-8">{errorMsg}</p>
                <div className="flex space-x-4">
                  <button 
                    onClick={() => { setStep(2); setScanning(false); setScanStatus(null); }}
                    className="px-6 py-3 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
                  >
                    Return to Repository
                  </button>
                  <button 
                    onClick={handleRetryStatus}
                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"
                  >
                    Retry Status
                  </button>
                </div>
              </>
            ) : scanStatus === 'TIMEOUT' ? (
              <>
                <div className="w-24 h-24 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-500 flex items-center justify-center mb-6">
                  <AlertCircle className="w-12 h-12" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Scan Timeout</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-8">{errorMsg}</p>
                <div className="flex space-x-4">
                  <button 
                    onClick={handleRetryStatus}
                    className="px-6 py-3 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
                  >
                    Check Again
                  </button>
                  <button 
                    onClick={() => window.location.href = '/dashboard'}
                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"
                  >
                    Go to Dashboard
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="w-24 h-24 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-500 flex items-center justify-center mb-6">
                  <CheckCircle2 className="w-12 h-12" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Scan completed</h2>
                <p className="text-slate-500 dark:text-slate-400 mb-8">The initial analysis has been finalized successfully.</p>
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
