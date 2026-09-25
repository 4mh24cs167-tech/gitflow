import { API_URL } from '../config';
import { useEffect, useState } from 'react';
import { GitCommit, ArrowUpRight } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

export default function Dashboard() {
  const [repos, setRepos] = useState<any[]>([]);
  const [history, setHistory] = useState<{ commit: string; score: number; date: string; scoreDelta: number | null }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const res = await axios.get(`${API_URL}/repositories/`, {
          withCredentials: true
        });
        setRepos(res.data);
        
        if (res.data.length > 0) {
           const historyRes = await axios.get(`${API_URL}/repositories/${res.data[0].id}/risk-history`, {
             withCredentials: true
           });
           const chartData = historyRes.data.map((h: any) => ({
             commit: h.short_sha,
             score: h.risk_score,
             date: new Date(h.scanned_at).toLocaleDateString(),
             scoreDelta: h.score_delta
           }));
           setHistory(chartData);
        }
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRepos();
  }, []);

  const stats = [
    { title: 'Total Repositories', value: repos.length, change: '', trend: 'neutral' },
    { title: 'Average Risk Score', value: history.length > 0 ? history[history.length - 1].score : 'N/A', change: history.length > 0 ? (history[history.length - 1].scoreDelta === null ? 'Baseline scan' : `Latest Δ ${history[history.length - 1].scoreDelta! >= 0 ? '+' : ''}${history[history.length - 1].scoreDelta}`) : 'Connect a repo', trend: 'neutral' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
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
          {loading ? "Loading history..." : 
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
          ) : repos.length === 0 ? (
            <div className="p-6 text-center text-slate-500">No repositories connected. Go to Onboarding.</div>
          ) : (
            repos.map((repo: any) => (
              <div key={repo.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                    <GitCommit className="w-5 h-5 text-slate-500" />
                  </div>
                  <div>
                    <h4 className="font-medium">{repo.name}</h4>
                    <p className="text-sm text-slate-500">{repo.url}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-8">
                  <ArrowUpRight className="w-5 h-5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
