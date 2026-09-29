import { useState, useEffect, useRef } from 'react';
import { GitBranch, CheckCircle2, Loader2, Shield, AlertCircle } from 'lucide-react';
import { apiClient } from '../config';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState<string | null>(null);
  const [scannedSha, setScannedSha] = useState<string | null>(null);
  const [scanId, setScanId] = useState<number | null>(null);
  
  const [repoUrl, setRepoUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
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

  const handleAddRepository = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    
    setIsSubmitting(true);
    setErrorMsg(null);
    
    try {
      // 1. Create/Add Repository
      const repoRes = await apiClient.post('/repositories/', { name: 'repo', url: repoUrl });
      const newRepoId = repoRes.data.id;
      setRepoId(newRepoId);
      
      // 2. Start initial scan
      const scanRes = await apiClient.post(`/repositories/${newRepoId}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      setScanId(newScanId);
      
      // 3. Poll for status
      setStep(2);
      setScanning(true);
      pollScanStatus(newRepoId, newScanId);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.response?.data?.detail || "Failed to add repository. Please check the URL and try again.");
    } finally {
      setIsSubmitting(false);
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
    setScanStatus(null);
    setErrorMsg(null);
    pollScanStatus(repoId, scanId);
  };

  const steps = [
    { num: 1, title: 'Add Repository' },
    { num: 2, title: 'Initial Scan' }
  ];

  return (
    <div className="min-h-[calc(100vh-73px)] bg-background-light dark:bg-background-dark text-slate-900 dark:text-white pt-24">
      <div className="max-w-3xl mx-auto py-8">
        {/* Stepper */}
        <div className="mb-12">
          <div className="flex items-center justify-center space-x-8">
            {steps.map((s, i) => (
              <div key={s.num} className="flex flex-col items-center relative">
                {i !== 0 && (
                  <div className={`absolute top-5 -left-12 w-16 h-[2px] -translate-x-1/2 ${
                    step >= s.num ? 'bg-brand-500' : 'bg-border-light dark:bg-border-dark'
                  }`} />
                )}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg border-2 z-10 transition-colors ${
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

        <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl shadow-soft dark:shadow-soft-dark overflow-hidden">
          {step === 1 && (
            <div className="p-12">
              <div className="flex flex-col items-center text-center mb-10">
                <div className="w-20 h-20 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-6">
                  <GitBranch className="w-10 h-10 text-slate-700 dark:text-slate-300" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Connect a Public Repository</h2>
                <p className="text-slate-500 dark:text-slate-400 max-w-md">
                  Enter the URL of a public GitHub repository to generate its Risk Passport and monitor future commits.
                </p>
              </div>

              {errorMsg && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg mb-6 flex items-center text-left">
                  <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
                  <p>{errorMsg}</p>
                </div>
              )}

              <form onSubmit={handleAddRepository} className="max-w-lg mx-auto">
                <div className="mb-6">
                  <label htmlFor="repoUrl" className="block text-sm font-medium mb-2 text-left text-slate-700 dark:text-slate-300">
                    GitHub Repository URL
                  </label>
                  <input
                    id="repoUrl"
                    type="url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    className="w-full px-4 py-3 rounded-lg bg-background-light dark:bg-background-dark border border-border-light dark:border-border-dark outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
                    required
                  />
                </div>
                <button 
                  type="submit"
                  disabled={isSubmitting || !repoUrl}
                  className="w-full py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isSubmitting ? (
                    <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Adding Repository...</>
                  ) : "Add Repository"}
                </button>
              </form>
            </div>
          )}

          {step === 2 && (
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
                    <div className="h-full bg-gradient-to-r from-brand-500 to-purple-500 w-full animate-pulse" />
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
                      onClick={() => { setStep(1); setScanning(false); setScanStatus(null); }}
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
                      onClick={() => { setStep(1); setScanning(false); setScanStatus(null); }}
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
    </div>
  );
}
