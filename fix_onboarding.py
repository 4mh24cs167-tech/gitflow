with open("frontend/src/pages/Onboarding.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Introduce scanId state
content = content.replace(
    'const [scannedSha, setScannedSha] = useState<string | null>(null);',
    'const [scannedSha, setScannedSha] = useState<string | null>(null);\n  const [scanId, setScanId] = useState<number | null>(null);'
)

# Update fetchScanStatus to return status
old_fetch = '''const fetchScanStatus = async (repository_id: number, currentScanId: number) => {
    try {
      const res = await apiClient.get(`/repositories/${repository_id}/scans/${currentScanId}`);
      consecutiveErrorsRef.current = 0;
      
      const status = res.data.status;
      setScanStatus(status);
      if (res.data.commit_sha && res.data.commit_sha !== "HEAD") {
          setScannedSha(res.data.commit_sha.substring(0, 7));
      }

      if (status === 'COMPLETED' || status === 'FAILED') {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setScanning(false);
      }
    } catch (err) {
      console.error("Failed to poll scan status", err);
      consecutiveErrorsRef.current += 1;
      
      if (consecutiveErrorsRef.current >= 5) {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setScanning(false);
        setScanStatus('POLLING_ERROR');
        setErrorMsg("Unable to retrieve scan status. The scan may still be running.");
      }
    }
  };'''

new_fetch = '''const fetchScanStatus = async (repository_id: number, currentScanId: number) => {
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
  };'''
content = content.replace(old_fetch, new_fetch)

# Update pollScanStatus to fix race condition
old_poll = '''const pollScanStatus = (repository_id: number, currentScanId: number) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    
    consecutiveErrorsRef.current = 0;
    startPollingTimeRef.current = Date.now();
    
    // Initial fetch
    fetchScanStatus(repository_id, currentScanId);
    
    pollingRef.current = setInterval(() => {
      // 10 minutes timeout
      if (Date.now() - startPollingTimeRef.current > 10 * 60 * 1000) {
        clearInterval(pollingRef.current);
        setScanning(false);
        setScanStatus('TIMEOUT');
        setErrorMsg("Scan is taking longer than expected.");
        return;
      }
      
      fetchScanStatus(repository_id, currentScanId);
    }, 1500);
  };'''

new_poll = '''const pollScanStatus = async (repository_id: number, currentScanId: number) => {
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
  };'''
content = content.replace(old_poll, new_poll)

# Save scanId in handleSelect
content = content.replace(
    'const newScanId = scanRes.data.scan_id;\n      \n      // 3. Poll for status',
    'const newScanId = scanRes.data.scan_id;\n      setScanId(newScanId);\n      \n      // 3. Poll for status'
)

# Rename handleRetry to handleRetryScan and add handleRetryStatus
old_retry = '''const handleRetry = async () => {
    if (!repoId) return;
    setScanning(true);
    setScanStatus('QUEUED');
    setErrorMsg(null);
    setScannedSha(null);
    
    try {
      const scanRes = await apiClient.post(`/repositories/${repoId}/scan`, { commit_sha: "HEAD" });
      const newScanId = scanRes.data.scan_id;
      pollScanStatus(repoId, newScanId);
    } catch(e: any) {
      console.error("Failed to retry scan", e);
      setScanning(false);
      setScanStatus('FAILED');
      setErrorMsg(e?.response?.data?.detail || "An error occurred while communicating with the server.");
    }
  };'''

new_retry = '''const handleRetryScan = async () => {
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
  };'''
content = content.replace(old_retry, new_retry)

# Replace handleRetry in UI buttons
content = content.replace(
    '<button \n                    onClick={handleRetry}\n                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"\n                  >\n                    Retry Scan\n                  </button>',
    '<button \n                    onClick={handleRetryScan}\n                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"\n                  >\n                    Retry Scan\n                  </button>'
)

content = content.replace(
    '<button \n                    onClick={handleRetry}\n                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"\n                  >\n                    Retry Status\n                  </button>',
    '<button \n                    onClick={handleRetryStatus}\n                    className="px-6 py-3 bg-brand-500 text-white font-medium rounded-lg hover:bg-brand-600 transition-colors shadow-lg shadow-brand-500/25"\n                  >\n                    Retry Status\n                  </button>'
)

content = content.replace(
    '<button \n                    onClick={handleRetry}\n                    className="px-6 py-3 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"\n                  >\n                    Check Again\n                  </button>',
    '<button \n                    onClick={handleRetryStatus}\n                    className="px-6 py-3 bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-medium rounded-lg hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"\n                  >\n                    Check Again\n                  </button>'
)

with open("frontend/src/pages/Onboarding.tsx", "w", encoding="utf-8") as f:
    f.write(content)
