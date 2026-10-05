import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { GitCommit, ShieldAlert, AlertTriangle, FileText, ArrowUpRight, ArrowDownRight, MessageSquare, Shield, Activity, Zap } from 'lucide-react';
import { apiClient } from '../config';

export default function CommitAudit() {
  const { repositoryId, scanId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [promptMsg, setPromptMsg] = useState('');
  const [chatLog, setChatLog] = useState<{role: string, text: string}[]>([]);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    if (!repositoryId || !scanId) {
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        const res = await apiClient.get(`/repositories/${repositoryId}/scans/${scanId}`);
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load audit data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [repositoryId, scanId]);

  const handleAsk = async (question: string) => {
    if (!question.trim()) return;
    setChatLog(prev => [...prev, { role: 'user', text: question }]);
    setPromptMsg('');
    setAsking(true);
    try {
      const res = await apiClient.post(`/repositories/${repositoryId}/scans/${scanId}/ask`, { question });
      setChatLog(prev => [...prev, { role: 'ai', text: res.data.answer }]);
    } catch (err) {
      setChatLog(prev => [...prev, { role: 'ai', text: 'Error fetching explanation.' }]);
    } finally {
      setAsking(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Loading audit data...</div>;

  if (!repositoryId || !scanId) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center h-full">
        <ShieldAlert className="w-16 h-16 text-slate-300 dark:text-slate-700 mb-4" />
        <h2 className="text-xl font-bold mb-2">No Scan Selected</h2>
        <p className="text-slate-500 max-w-sm">
          Please select a completed scan from your repository dashboard to view its detailed audit.
        </p>
      </div>
    );
  }

  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!data) return <div className="p-8 text-center text-slate-500">No data found.</div>;

  const currentScore = data.risk_score;
  const prevScore = data.previous_score;
  const delta = data.score_delta;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center mb-2">
            <GitCommit className="w-8 h-8 mr-3 text-slate-400" />
            Commit {data.commit_sha || data.short_sha || scanId}
          </h1>
          <p className="text-slate-700 dark:text-slate-300 text-lg">{data.message || 'No commit message'}</p>
          <div className="text-sm text-slate-500 mt-2 flex items-center space-x-4">
            <span>by <span className="font-medium text-slate-700 dark:text-slate-300">{data.author || 'Unknown'}</span></span>
            <span>•</span>
            <span>{data.repository || 'Repository'}</span>
            <span>•</span>
            <span>{data.timestamp ? new Date(data.timestamp).toLocaleString() : (data.scanned_at ? new Date(data.scanned_at).toLocaleString() : 'Prior to tracking')}</span>
          </div>
        </div>
        
        {/* Risk Score Card */}
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft flex items-center space-x-8 min-w-[250px]">
          <div>
            <div className="text-sm text-slate-500 uppercase tracking-wider mb-1">Risk Score</div>
            <div className="flex items-center">
              <span className="text-4xl font-bold text-slate-800 dark:text-white">{currentScore !== null ? currentScore : "N/A"}</span>
              <div className={`ml-3 flex items-center text-sm font-medium ${delta < 0 ? 'text-red-500' : delta > 0 ? 'text-emerald-500' : 'text-slate-500'}`}>
                {delta !== null && delta < 0 ? <ArrowUpRight className="w-4 h-4 mr-1" /> : delta !== null && delta > 0 ? <ArrowDownRight className="w-4 h-4 mr-1" /> : null}
                {delta !== null && delta !== 0 ? Math.abs(delta) : delta === 0 ? 'No change' : ''}
              </div>
            </div>
          </div>
          {delta !== 0 && (
            <div className="text-xs text-slate-500">
              Prev: {prevScore}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">

          {/* Executive Summary */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-brand-500" />
              Executive Summary
            </h2>
            <div className="text-slate-600 dark:text-slate-400 leading-relaxed text-sm space-y-4">
              <p>
                This commit introduced <strong>{data.changes?.length || 0} file change(s)</strong>.
                {data.findings && data.findings.length > 0 ? (
                  <> During static analysis, <strong>{data.findings.length} security finding(s)</strong> were identified.</>
                ) : (
                  <> No security risks were identified in the source code.</>
                )}
              </p>
              {data.findings && data.findings.length > 0 && (
                <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-lg mt-4 border border-slate-200 dark:border-slate-700">
                  <h4 className="font-semibold text-slate-800 dark:text-slate-200 mb-2">Detailed Report</h4>
                  <ul className="list-disc pl-5 space-y-2">
                    {data.findings.map((f: any, i: number) => (
                      <li key={i}>
                        <span className={`font-semibold ${f.severity === 'Critical' || f.severity === 'High' ? 'text-red-500' : f.severity === 'Medium' ? 'text-amber-500' : 'text-blue-500'}`}>
                          [{f.severity}] {f.title}:
                        </span>{' '}
                        {f.description}
                        {f.file_path && <span className="block text-xs font-mono mt-1 text-slate-500">Path: {f.file_path}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
          
          {/* Alerts */}
          {data.alerts && data.alerts.length > 0 && (
            <div className="rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/10 p-6">
              <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-4 flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2" />
                Alerts Detected
              </h2>
              <ul className="space-y-2">
                {data.alerts.map((alert: string, i: number) => (
                  <li key={i} className="text-red-600 dark:text-red-300 text-sm flex items-start">
                    <span className="mr-2">•</span> {alert}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* What Changed */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-slate-400" />
              What Changed
            </h2>
            {data.changes && data.changes.length > 0 ? (
              <div className="divide-y divide-border-light dark:divide-border-dark">
                {data.changes.map((change: any, i: number) => (
                  <div key={i} className="py-3 flex items-center justify-between">
                    <div className="flex items-center">
                      <span className={`w-2 h-2 rounded-full mr-3 ${change.type === 'added' ? 'bg-emerald-500' : change.type === 'deleted' ? 'bg-red-500' : 'bg-amber-500'}`} />
                      <span className="font-mono text-sm text-slate-700 dark:text-slate-300">{change.file}</span>
                    </div>
                    {(change.linesAdded !== undefined || change.linesRemoved !== undefined) && (
                      <div className="text-sm font-mono flex space-x-4">
                        {change.linesAdded !== undefined && <span className="text-emerald-500">+{change.linesAdded}</span>}
                        {change.linesRemoved !== undefined && <span className="text-red-500">-{change.linesRemoved}</span>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-500 text-sm">No structural changes detailed.</p>
            )}
          </div>

          {/* Actions Detected */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-slate-400" />
              Actions Detected
            </h2>
            {data.actions && data.actions.length > 0 ? (
              <ul className="space-y-3">
                {data.actions.map((action: string, i: number) => (
                  <li key={i} className="flex items-center text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                    <Zap className="w-4 h-4 mr-3 text-brand-500" />
                    {action}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-slate-500 text-sm">No high-level actions identified.</p>
            )}
          </div>

        </div>

        <div className="space-y-6">
          
          {/* Impact */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Shield className="w-5 h-5 mr-2 text-slate-400" />
              Impact
            </h2>
            {data.impact ? (
              <div className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-slate-700 dark:text-slate-300">Directly Changed</h4>
                  <p className="text-slate-600 dark:text-slate-400 mt-1">{data.impact.directly_changed || 'None'}</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-700 dark:text-slate-300">Potentially Affected</h4>
                  <p className="text-slate-600 dark:text-slate-400 mt-1">{data.impact.potentially_affected || 'None'}</p>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-700 dark:text-slate-300">Reason</h4>
                  <p className="text-slate-600 dark:text-slate-400 mt-1">{data.impact.reason || 'Not specified'}</p>
                </div>
              </div>
            ) : (
              <p className="text-slate-500 text-sm">Impact analysis not available.</p>
            )}
          </div>

          {/* Ask About This Commit */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft flex flex-col h-[500px]">
            <div className="p-4 border-b border-border-light dark:border-border-dark">
              <h2 className="font-semibold flex items-center text-brand-600 dark:text-brand-400">
                <MessageSquare className="w-4 h-4 mr-2" />
                Ask About This Commit
              </h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {chatLog.length === 0 ? (
                <div className="text-sm text-slate-500">
                  <p className="mb-4">Suggested questions:</p>
                  <div className="space-y-2">
                    {["What changed?", "Why did risk change?", "Are there any hardcoded secrets?"].map(q => (
                      <button 
                        key={q} 
                        onClick={() => handleAsk(q)}
                        className="block w-full text-left p-2 rounded-lg bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-brand-600 dark:text-brand-400"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatLog.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-lg p-3 text-sm ${
                      msg.role === 'user' 
                        ? 'bg-brand-500 text-white' 
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200'
                    }`}>
                      {msg.text}
                    </div>
                  </div>
                ))
              )}
              {asking && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-lg p-3 text-sm animate-pulse">
                    Thinking...
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-border-light dark:border-border-dark">
              <form 
                onSubmit={(e) => { e.preventDefault(); handleAsk(promptMsg); }}
                className="flex space-x-2"
              >
                <input 
                  type="text" 
                  value={promptMsg}
                  onChange={e => setPromptMsg(e.target.value)}
                  placeholder="Ask a question..."
                  className="flex-1 px-3 py-2 rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/50"
                  disabled={asking}
                />
                <button 
                  type="submit"
                  disabled={asking || !promptMsg.trim()}
                  className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-50 transition-colors"
                >
                  Ask
                </button>
              </form>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
