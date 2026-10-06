import { useEffect, useRef, useState } from 'react';
import { GitCommit, CheckCircle2, Activity } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../config';

export default function Dashboard() {
  const [repos, setRepos] = useState<any[]>([]);
  const [activeRepoId, setActiveRepoId] = useState<string | null>(localStorage.getItem('gitflow_active_repo') || null);
  const [history, setHistory] = useState<{ commit: string; score: number | null; date: string; scoreDelta: number | null; findingsCount?: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [repoError, setRepoError] = useState('');
  const activeRepoIdRef = useRef(activeRepoId);
  const historyLoadedRef = useRef(false);
  
  const handleRepoChange = (e: any) => {
    const newId = e.target.value;
    activeRepoIdRef.current = newId;
    historyLoadedRef.current = false;
    setActiveRepoId(newId);
    localStorage.setItem('gitflow_active_repo', newId);
  };

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    const fetchRepos = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const reposRes = await apiClient.get(`/repositories/`);
        if (cancelled) return;
        setRepoError('');
        setRepos(reposRes.data);
        
        if (reposRes.data.length === 0) {
            setLoading(false);
            return;
        }
        
        let targetId = activeRepoIdRef.current;
        if (!targetId || !reposRes.data.find((r: any) => r.id.toString() === targetId)) {
            targetId = reposRes.data[0].id.toString();
            activeRepoIdRef.current = targetId;
            setActiveRepoId(targetId);
            localStorage.setItem('gitflow_active_repo', targetId as string);
        }
      } catch (err) {
        console.error("Failed to fetch repos", err);
        if (!cancelled) setRepoError('Could not load repositories. Check your connection and try again.');
      } finally {
        inFlight = false;
        if (!cancelled) setLoading(false);
      }
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') fetchRepos();
    };
    fetchRepos();
    const interval = window.setInterval(refreshWhenVisible, 30000);
    window.addEventListener('focus', refreshWhenVisible);
    document.addEventListener('visibilitychange', refreshWhenVisible);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener('focus', refreshWhenVisible);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
    };
  }, []);

  useEffect(() => {
    if (!activeRepoId) return;
    let cancelled = false;
    let inFlight = false;
    const fetchHistory = async () => {
      if (inFlight) return;
      inFlight = true;
      if (!historyLoadedRef.current) setHistoryLoading(true);
      try {
           const historyRes = await apiClient.get(`/repositories/${activeRepoId}/risk-history`);
           if (cancelled) return;
           const latestHistory = historyRes.data.slice(-50);
           const chartData = latestHistory.map((h: any) => ({
             scanId: h.id,
             findingsCount: h.findings_count,
             repoId: activeRepoId,
             commit: h.short_sha,
             score: h.risk_score,
             date: new Date(h.scanned_at).toLocaleDateString(),
             scoreDelta: h.score_delta,
             alerts: h.alerts
           }));
           setHistory(chartData);
      } catch (err) {
        console.error("Failed to fetch history", err);
      } finally {
        inFlight = false;
        if (!cancelled) {
          historyLoadedRef.current = true;
          setHistoryLoading(false);
        }
      }
    };
    fetchHistory();
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') fetchHistory();
    };
    const interval = window.setInterval(refreshWhenVisible, 30000);
    window.addEventListener('focus', refreshWhenVisible);
    document.addEventListener('visibilitychange', refreshWhenVisible);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener('focus', refreshWhenVisible);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
    };
  }, [activeRepoId]);

  const stats = [
    { title: 'Total Repositories', value: repos.length, change: '', trend: 'neutral' },
    { title: 'Current Security Score', value: history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : 'Unavailable') : 'NO COMPLETED SCAN', change: history.length > 0 ? (history[history.length - 1].scoreDelta === null ? 'Baseline scan' : `Latest: ${history[history.length - 1].scoreDelta! > 0 ? '+' : ''}${history[history.length - 1].scoreDelta}`) : 'Connect a repo', trend: 'neutral' },
  ];

  

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-between items-center mb-6 pt-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button onClick={() => window.location.href = '/onboarding'} className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors shadow-sm font-medium">
           + Add Repository
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="p-6 rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark">
            <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">{stat.title}</h3>
            <div className="flex items-baseline justify-between">
              <span className="text-3xl font-bold">{stat.value}</span>
              <span className={`text-sm font-medium text-slate-500`}>{stat.change}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden p-6">
        <h2 className="text-lg font-semibold mb-6">Repository Risk History</h2>
        <div className="h-72 w-full flex items-center justify-center text-slate-500">
          {historyLoading ? (
            <div className="animate-pulse w-full h-full flex flex-col justify-end space-y-2">
               <div className="h-full w-full bg-slate-200 dark:bg-slate-800 rounded opacity-50"></div>
            </div>
          ) : 
           history.length === 0 ? "No risk history yet. Push a commit or run your first scan to start tracking risk." :
           (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} vertical={false} />
                <XAxis dataKey="commit" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                  itemStyle={{ color: '#8b5cf6' }}
                />
                <Line type="monotone" dataKey="score" stroke="#8b5cf6" strokeWidth={3} dot={{ r: 4, fill: '#8b5cf6', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
           )}
        </div>
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
          <h2 className="text-lg font-semibold">Active Repositories</h2>
        </div>
        <div className="divide-y divide-border-light dark:divide-border-dark">
          {loading ? (
            <div className="p-6 text-center text-slate-500">Loading repositories...</div>
          ) : repoError ? (
            <div role="alert" className="p-6 text-center text-red-600 dark:text-red-400">{repoError}</div>
          ) : repos.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No repositories connected. Go to Onboarding.</div>
          ) : (
            repos.map((repo: any) => (
              <div key={repo.id} className={`px-6 py-6 flex flex-col space-y-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer ${activeRepoId === repo.id.toString() ? 'border-l-4 border-brand-500 bg-slate-50/50 dark:bg-slate-800/30' : ''}`} onClick={() => handleRepoChange({target: {value: repo.id.toString()}})}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                      <GitCommit className="w-5 h-5 text-slate-500" />
                    </div>
                    <div>
                      <h4 className="font-medium text-lg cursor-pointer hover:text-brand-500 transition-colors" onClick={() => {}}>{repo.name}</h4>
                      <p className="text-sm text-slate-500">{repo.url}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          await apiClient.post(`/repositories/${repo.id}/scan`, { commit_sha: "HEAD" });
                          alert('Scan initiated for HEAD');
                        } catch (err) {
                          console.error(err);
                          alert('Failed to initiate scan');
                        }
                      }}
                      className="px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-sm font-medium rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors"
                    >
                      Manual Scan Now
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-4 border-t border-border-light dark:border-border-dark">
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Monitoring Status</p>
                    <div className="flex items-center space-x-2">
                      <div className="relative flex h-3 w-3">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${repo.last_poll_error ? 'bg-red-400' : 'bg-emerald-400'}`}></span>
                        <span className={`relative inline-flex rounded-full h-3 w-3 ${repo.last_poll_error ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
                      </div>
                      <p className={`font-medium ${repo.last_poll_error ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        {repo.last_poll_error ? 'POLLING FAILED' : (repo.monitoring_status ? repo.monitoring_status.replace('_', ' ') : 'NOT CONFIGURED')}
                      </p>
                    </div>
                    {repo.last_poll_error && (
                      <p className="text-xs text-red-500 mt-1 truncate" title={repo.last_poll_error}>{repo.last_poll_error}</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Last Polled</p>
                    <p className="font-medium text-sm">
                      {repo.last_polled_at ? new Date(repo.last_polled_at).toLocaleString() : 'Never'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Success: {repo.last_successful_poll_at ? new Date(repo.last_successful_poll_at).toLocaleTimeString() : 'Never'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Sync Status</p>
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-700 dark:text-slate-300">
                        {repo.last_processed_sha ? repo.last_processed_sha.substring(0, 7) : 'None'}
                      </span>
                      <span className="text-slate-400">&rarr;</span>
                      <span className="font-mono text-sm bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-700 dark:text-slate-300">
                        {repo.last_seen_sha ? repo.last_seen_sha.substring(0, 7) : 'None'}
                      </span>
                    </div>
                    {repo.last_processed_sha && repo.last_seen_sha && repo.last_processed_sha === repo.last_seen_sha && (
                       <p className="text-xs text-emerald-500 mt-1 flex items-center"><CheckCircle2 className="w-3 h-3 mr-1" /> Fully Synced</p>
                    )}
                    {repo.last_processed_sha && repo.last_seen_sha && repo.last_processed_sha !== repo.last_seen_sha && (
                       <p className="text-xs text-amber-500 mt-1 flex items-center"><Activity className="w-3 h-3 mr-1" /> Processing backlog...</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Current Security Score</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">
                      {activeRepoId === repo.id.toString() && history.length > 0 ? (history[history.length - 1].score !== null ? history[history.length - 1].score : 'N/A') : '--'}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft dark:shadow-soft-dark overflow-hidden">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent Commit Intelligence</h2>
        </div>
        <div className="divide-y divide-border-light dark:divide-border-dark">
          {historyLoading ? (
            <div className="p-6 space-y-4">
               <div className="h-6 w-1/3 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
               <div className="h-6 w-1/2 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
               <div className="h-6 w-1/4 bg-slate-200 dark:bg-slate-800 animate-pulse rounded"></div>
            </div>
          ) : history.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No commits analyzed yet.</div>
          ) : (
            history.slice().reverse().slice(0, 5).map((h: any, idx) => (
              <div key={idx} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group cursor-pointer" onClick={() => window.location.href=`/repositories/${h.repoId}/scans/${h.scanId}/audit`}>
                <div>
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="font-mono text-sm font-semibold text-slate-700 dark:text-slate-300">{h.commit}</span>
                    <span className="text-xs text-slate-500">{h.date}</span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm">
                      {h.scoreDelta === null ? (
                        <>Baseline Score: <span className="font-semibold">{h.score}</span></>
                      ) : (
                        <>Security Score: <span className="font-semibold">{h.score - h.scoreDelta}</span> &rarr; <span className="font-semibold">{h.score}</span></>
                      )}
                    </div>
                    {h.alerts && h.alerts.length > 0 && (
                      <div className="flex items-center space-x-2">
                        {h.alerts.map((alert: string, i: number) => (
                          <span key={i} className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium">
                            {alert}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-brand-500 opacity-0 group-hover:opacity-100 transition-opacity">
                  View Details &rarr;
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
