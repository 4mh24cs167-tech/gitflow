import { useState, useEffect } from 'react';
import { apiClient } from '../config';
import { Shield, GitCommit, CheckCircle, ShieldAlert, Activity } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';


export default function RiskPassport() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [repo, setRepo] = useState<any>(null);
  const [repos, setRepos] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [latestScan, setLatestScan] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // 1. Get repos
        const repoRes = await apiClient.get(`/repositories/`);
        if (repoRes.data.length === 0) {
          setLoading(false);
          return;
        }
        
        let targetId = localStorage.getItem('gitflow_active_repo');
        let activeRepo = repoRes.data.find((r: any) => r.id.toString() === targetId);
        if (!activeRepo) {
            activeRepo = repoRes.data[0];
            localStorage.setItem('gitflow_active_repo', activeRepo.id.toString());
        }
        setRepo(activeRepo);
        setRepos(repoRes.data);

        // 2. Get history
        const histRes = await apiClient.get(`/repositories/${activeRepo.id}/risk-history`);
        setHistory(histRes.data);

        // 3. Get latest scan if exists
        if (histRes.data.length > 0) {
          const latest = histRes.data[histRes.data.length - 1];
          const scanRes = await apiClient.get(`/repositories/${activeRepo.id}/scans/${latest.id}`);
          setLatestScan(scanRes.data);
        }
        setLoading(false);
      } catch (err: any) {
        console.error(err);
        setError('Failed to load risk passport data.');
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Risk Passport...</div>;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;

  if (!repo || history.length === 0 || !latestScan) {
    return (
      <div className="max-w-6xl mx-auto text-center py-12">
        <Shield className="w-16 h-16 mx-auto text-slate-300 dark:text-slate-700 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Software Risk Passport</h1>
        <p className="text-slate-500 dark:text-slate-400">Connect a repository and complete a scan to generate its risk passport.</p>
      </div>
    );
  }

  const { risk_score, score_delta, findings, impact, actions_detected, commit_sha, message, author, time, status } = latestScan;
  
  const countSeverity = (sev: string) => findings.filter((f: any) => f.severity === sev).length;
  const countCategory = (cat: string) => findings.filter((f: any) => f.title === cat).length;
  
  const chartData = history.map((h: any) => ({
    name: h.short_sha,
    score: h.risk_score
  }));

  const handleRepoChange = (e: any) => {
    localStorage.setItem('gitflow_active_repo', e.target.value);
    window.location.reload();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex justify-end mb-2">
        {repos.length > 1 && (
          <select 
            className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-md px-3 py-1.5 text-sm outline-none"
            value={repo.id.toString()}
            onChange={handleRepoChange}
          >
            {repos.map((r: any) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        )}
      </div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 dark:text-white flex items-center">
            <Shield className="w-8 h-8 mr-3 text-brand-500" />
            Software Risk Passport
          </h1>
          <p className="text-slate-500 mt-1 flex items-center">
            <GitCommit className="w-4 h-4 mr-1" />
            {repo.name} &mdash; {repo.url}
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-500 uppercase tracking-wider mb-1">Scan Status</div>
          <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle className="w-4 h-4 mr-2" />
            {status}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Current Risk</h3>
          <div className="flex items-end space-x-4">
            <span className="text-6xl font-bold text-slate-800 dark:text-white">{status === 'FAILED' ? 'SCAN FAILED' : risk_score !== null ? risk_score : 'UNAVAILABLE'}</span>
            <div className="pb-2">
              <span className="text-sm text-slate-500 block">out of 100</span>
              {score_delta !== null && (
                <span className={`text-sm font-medium ${score_delta < 0 ? 'text-emerald-500' : score_delta > 0 ? 'text-red-500' : 'text-slate-500'}`}>
                  {score_delta > 0 ? '+' : ''}{score_delta} from previous
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Findings Summary</h3>
          <div className="flex items-center space-x-6">
            <div>
              <div className="text-3xl font-bold text-slate-800 dark:text-white">{findings.length}</div>
              <div className="text-xs text-slate-500">Total</div>
            </div>
            <div className="flex-1 grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between items-center bg-red-50 dark:bg-red-900/10 px-2 py-1 rounded text-red-700 dark:text-red-400">
                <span>Critical</span> <span className="font-bold">{countSeverity('Critical')}</span>
              </div>
              <div className="flex justify-between items-center bg-orange-50 dark:bg-orange-900/10 px-2 py-1 rounded text-orange-700 dark:text-orange-400">
                <span>High</span> <span className="font-bold">{countSeverity('High')}</span>
              </div>
              <div className="flex justify-between items-center bg-amber-50 dark:bg-amber-900/10 px-2 py-1 rounded text-amber-700 dark:text-amber-400">
                <span>Medium</span> <span className="font-bold">{countSeverity('Medium')}</span>
              </div>
              <div className="flex justify-between items-center bg-blue-50 dark:bg-blue-900/10 px-2 py-1 rounded text-blue-700 dark:text-blue-400">
                <span>Low</span> <span className="font-bold">{countSeverity('Low')}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">Latest Commit</h3>
          <div className="space-y-2">
            <div className="font-mono text-sm text-slate-800 dark:text-slate-200 truncate">{commit_sha}</div>
            <div className="text-sm text-slate-600 dark:text-slate-400 truncate">{message || 'No message'}</div>
            <div className="text-xs text-slate-500 flex items-center justify-between mt-4">
              <span>{author || 'Unknown'}</span>
              <span>{time ? new Date(time).toLocaleString() : 'Unknown time'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
        <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-6">Risk History</h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f8fafc' }}
                itemStyle={{ color: '#10b981' }}
              />
              <Area type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorScore)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <Activity className="w-4 h-4 mr-2" /> Change Intelligence
          </h3>
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Actions Detected</h4>
              {actions_detected && actions_detected.length > 0 ? (
                <ul className="space-y-2">
                  {actions_detected.map((action: string, i: number) => (
                    <li key={i} className="text-sm flex items-center text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800 p-2 rounded">
                      <div className="w-1.5 h-1.5 rounded-full bg-brand-500 mr-2" />
                      {action}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No high-level actions identified.</p>
              )}
            </div>
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase mb-2">Impact Analysis</h4>
              {impact && Object.keys(impact).length > 0 ? (
                <div className="text-sm space-y-2 bg-slate-50 dark:bg-slate-800 p-3 rounded">
                  <div><span className="font-semibold">Directly Changed:</span> {impact.directly_changed || 'None'}</div>
                  <div><span className="font-semibold">Potentially Affected:</span> {impact.potentially_affected || 'None'}</div>
                  <div className="text-slate-500 italic mt-1">{impact.reason || 'No specific reason provided.'}</div>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Impact analysis not available.</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <ShieldAlert className="w-4 h-4 mr-2" /> Category Breakdown
          </h3>
          <div className="space-y-4">
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Security</span>
               <span className="font-semibold">{countCategory('Vulnerability') + countCategory('Secret')}</span>
             </div>
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Dependencies</span>
               <span className="font-semibold">{countCategory('DependencyScan')}</span>
             </div>
             <div className="flex items-center justify-between text-sm border-b border-slate-100 dark:border-slate-800 pb-2">
               <span className="text-slate-600 dark:text-slate-400">Licenses</span>
               <span className="font-semibold">{countCategory('License')}</span>
             </div>
             <div className="flex items-center justify-between text-sm">
               <span className="text-slate-600 dark:text-slate-400">Quality / Architecture</span>
               <span className="font-semibold">{countCategory('Quality') + countCategory('Architecture')}</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
