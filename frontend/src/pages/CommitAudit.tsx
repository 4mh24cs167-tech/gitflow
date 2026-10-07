import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, FileText, Zap, CheckCircle, Activity, ChevronDown, ChevronRight, FileCode } from 'lucide-react';
import { apiClient } from '../config';

export default function CommitAudit() {
  const { repositoryId, scanId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});

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

  if (loading) return <div className="p-8 text-center text-slate-500 flex flex-col items-center"><Activity className="w-8 h-8 animate-spin mb-4" />Loading audit data...</div>;
  if (!repositoryId || !scanId) return null;
  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!data) return <div className="p-8 text-center text-slate-500">No data found.</div>;

  const currentScore = data.risk_score;
  const prevCommit = data.previous_commit;
  
  const newFindings = data.findings?.filter((f: any) => f.status === 'NEW' || f.status === 'BASELINE') || [];
  const unchangedFindings = data.findings?.filter((f: any) => f.status === 'UNCHANGED') || [];
  const resolvedFindings = data.findings?.filter((f: any) => f.status === 'RESOLVED') || [];
  
  const toggleFile = (filePath: string) => {
    setExpandedFiles(prev => ({...prev, [filePath]: !prev[filePath]}));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row gap-6 items-start justify-between">
        <div className="flex-1">
          <Link to={`/`} className="text-sm text-brand-500 hover:underline mb-4 inline-block">&larr; Back to Dashboard</Link>
          <div className="flex items-center space-x-3 mb-2">
            <h1 className="text-3xl font-bold font-mono">Commit {data.commit_sha?.substring(0, 7) || scanId}</h1>
            <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
              {data.status}
            </span>
          </div>
          <p className="text-slate-800 dark:text-slate-200 text-lg font-medium">"{data.message || 'No commit message'}"</p>
          <div className="text-sm text-slate-600 dark:text-slate-400 mt-2">
            <span>{data.author || 'Unknown'}</span> &bull; <span>{data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown time'}</span>
          </div>
        </div>

        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft flex items-center justify-between min-w-[280px]">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Security Score</div>
            <div className="flex items-end space-x-3">
              <span className="text-4xl font-bold text-slate-900 dark:text-white leading-none">{currentScore !== null ? currentScore : "N/A"}</span>
              {prevCommit && data.score_delta !== null && (
                <span className={`flex items-center px-2 py-1 rounded text-sm font-bold ${data.score_delta > 0 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30' : data.score_delta < 0 ? 'bg-red-100 text-red-700 dark:bg-red-900/30' : 'bg-slate-100 text-slate-600 dark:bg-slate-800'}`}>
                  {data.score_delta > 0 ? '+' : ''}{data.score_delta}
                </span>
              )}
            </div>
            {prevCommit ? (
              <div className="text-xs text-slate-500 mt-2">Previous ({prevCommit.short_sha}): <span className="font-semibold text-slate-700 dark:text-slate-300">{prevCommit.score}</span></div>
            ) : (
              <div className="text-xs text-slate-500 mt-2 font-semibold">BASELINE SCAN</div>
            )}
          </div>
          
          <div className="flex flex-col space-y-2 text-right border-l border-border-light dark:border-border-dark pl-4">
             <div className="text-xs">
               <span className="text-red-500 font-bold">{newFindings.length}</span> <span className="text-slate-500">New</span>
             </div>
             <div className="text-xs">
               <span className="text-emerald-500 font-bold">{resolvedFindings.length}</span> <span className="text-slate-500">Resolved</span>
             </div>
          </div>
        </div>
      </div>

      {/* COMMIT SUMMARY */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
          <Activity className="w-4 h-4 mr-2" />
          Commit Summary
        </h2>
        <div className="text-slate-700 dark:text-slate-300 whitespace-pre-line leading-relaxed">
          {data.human_summary || "No summary available."}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* WHAT CHANGED */}
        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
            <FileText className="w-4 h-4 mr-2" />
            What Changed
          </h2>
          <div className="space-y-3">
            {data.changes?.length > 0 ? (
              data.changes.map((c: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                  <div className="flex items-center truncate mr-4">
                    <span className={`w-2 h-2 rounded-full mr-3 shrink-0 ${c.status === 'A' || c.status === 'added' ? 'bg-emerald-500' : c.status === 'D' || c.status === 'deleted' ? 'bg-red-500' : c.status.startsWith('R') || c.status === 'renamed' ? 'bg-amber-500' : 'bg-brand-500'}`} />
                    <span className="font-mono text-sm text-slate-700 dark:text-slate-300 truncate" title={c.file}>{c.file}</span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs font-mono shrink-0">
                    <span className="text-emerald-600 dark:text-emerald-400">+{c.additions}</span>
                    <span className="text-red-600 dark:text-red-400">-{c.deletions}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No file changes recorded.</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* WHY THE SCORE CHANGED */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
              <Zap className="w-4 h-4 mr-2" />
              Why the Score Changed
            </h2>
            <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
              {data.score_explanation || "No explanation provided by analysis engine."}
            </p>
          </div>

          {/* ACTIONS DETECTED */}
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center">
              <CheckCircle className="w-4 h-4 mr-2" />
              Actions Detected
            </h2>
            {data.actions_detected && data.actions_detected.length > 0 ? (
              <ul className="space-y-2">
                {data.actions_detected.map((action: string, i: number) => (
                  <li key={i} className="flex items-start text-sm text-slate-700 dark:text-slate-300">
                    <span className="text-brand-500 mr-2 mt-0.5">+</span> {action}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No specific high-level actions identified.</p>
            )}
          </div>
        </div>
      </div>

      {/* ISSUES */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-6 flex items-center">
          <ShieldAlert className="w-4 h-4 mr-2" />
          Issues ({data.findings?.length || 0})
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* NEW ISSUES */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase mb-3 border-b border-slate-100 dark:border-slate-800 pb-2">New Issues ({newFindings.length})</h3>
            <div className="space-y-3">
              {newFindings.length === 0 ? <p className="text-sm text-slate-500 italic">No new issues.</p> : 
                newFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-red-50 dark:bg-red-900/10 p-3 rounded-lg border border-red-100 dark:border-red-900/30">
                    <div className="font-semibold text-red-700 dark:text-red-400 text-xs mb-1">{f.severity}</div>
                    <div className="text-slate-800 dark:text-slate-200 text-sm font-medium mb-1">{f.title}</div>
                    <div className="font-mono text-xs text-slate-500 truncate" title={f.file_path}>{f.file_path}{f.line_number ? `:${f.line_number}` : ''}</div>
                  </div>
                ))
              }
            </div>
          </div>
          
          {/* RESOLVED ISSUES */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase mb-3 border-b border-slate-100 dark:border-slate-800 pb-2">Resolved ({resolvedFindings.length})</h3>
            <div className="space-y-3">
              {resolvedFindings.length === 0 ? <p className="text-sm text-slate-500 italic">No resolved issues.</p> : 
                resolvedFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-emerald-50 dark:bg-emerald-900/10 p-3 rounded-lg border border-emerald-100 dark:border-emerald-900/30 opacity-75">
                    <div className="font-semibold text-emerald-700 dark:text-emerald-400 text-xs mb-1">{f.severity}</div>
                    <div className="text-slate-800 dark:text-slate-200 text-sm font-medium line-through mb-1">{f.title}</div>
                    <div className="font-mono text-xs text-slate-500 truncate" title={f.file_path}>{f.file_path}</div>
                  </div>
                ))
              }
            </div>
          </div>

          {/* UNCHANGED ISSUES */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase mb-3 border-b border-slate-100 dark:border-slate-800 pb-2">Unchanged ({unchangedFindings.length})</h3>
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
              {unchangedFindings.length === 0 ? <p className="text-sm text-slate-500 italic">No unchanged issues.</p> : 
                unchangedFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-800 opacity-75">
                    <div className="font-semibold text-slate-600 dark:text-slate-400 text-xs mb-1">{f.severity}</div>
                    <div className="text-slate-700 dark:text-slate-300 text-sm font-medium mb-1">{f.title}</div>
                    <div className="font-mono text-xs text-slate-500 truncate" title={f.file_path}>{f.file_path}{f.line_number ? `:${f.line_number}` : ''}</div>
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      </div>

      {/* FILE / LINE DETAILS (Diff Viewer) */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-6 flex items-center">
          <FileCode className="w-4 h-4 mr-2" />
          File / Line Details
        </h2>
        
        <div className="space-y-4">
          {data.changes?.length > 0 ? (
            data.changes.map((c: any, i: number) => {
              const fileFindings = data.findings?.filter((f: any) => f.file_path === c.file) || [];
              const hasIssues = fileFindings.length > 0;
              const isExpanded = expandedFiles[c.file];
              
              return (
                <div key={i} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                  <div 
                    className={`flex items-center justify-between p-3 cursor-pointer select-none transition-colors ${hasIssues ? 'bg-red-50/50 dark:bg-red-900/10 hover:bg-red-50 dark:hover:bg-red-900/20' : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700'}`}
                    onClick={() => toggleFile(c.file)}
                  >
                    <div className="flex items-center space-x-3 truncate">
                      {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                      <span className="font-mono text-sm font-medium text-slate-700 dark:text-slate-300">{c.file}</span>
                      {hasIssues && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400">{fileFindings.length} issue(s)</span>}
                    </div>
                    <div className="flex items-center space-x-4 text-xs font-mono shrink-0">
                      <span className="text-emerald-600 dark:text-emerald-400">+{c.additions}</span>
                      <span className="text-red-600 dark:text-red-400">-{c.deletions}</span>
                    </div>
                  </div>
                  
                  {isExpanded && (
                    <div className="p-0 border-t border-slate-200 dark:border-slate-700 bg-background-light dark:bg-background-dark">
                      {/* Show Findings for this file */}
                      {hasIssues && (
                        <div className="p-4 bg-red-50 dark:bg-red-900/10 border-b border-red-100 dark:border-red-900/30 space-y-3">
                          {fileFindings.map((f: any, idx: number) => (
                            <div key={idx} className="text-sm">
                              <div className="flex items-center space-x-2 font-semibold text-red-700 dark:text-red-400 mb-1">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                <span>{f.severity} - {f.title}</span>
                                {f.line_number && <span className="bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200 px-1.5 py-0.5 rounded text-xs ml-2">Line {f.line_number}</span>}
                              </div>
                              <p className="text-slate-700 dark:text-slate-300 pl-5">{f.description}</p>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {/* Diff Viewer */}
                      {c.patch ? (
                        <div className="overflow-x-auto p-4 custom-scrollbar">
                          <pre className="text-xs font-mono text-slate-700 dark:text-slate-300">
                            {c.patch.split('\n').map((line: string, lIdx: number) => {
                               let lineClass = "px-2 py-0.5 ";
                               if (line.startsWith('+') && !line.startsWith('+++')) lineClass += "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400";
                               else if (line.startsWith('-') && !line.startsWith('---')) lineClass += "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400";
                               else if (line.startsWith('@@')) lineClass += "bg-slate-100 dark:bg-slate-800 text-slate-500 font-bold";
                               
                               return (
                                 <div key={lIdx} className={lineClass} style={{ minWidth: 'max-content' }}>
                                   {line}
                                 </div>
                               );
                            })}
                          </pre>
                        </div>
                      ) : (
                        <div className="p-4 text-center text-sm text-slate-500 italic">No diff content available.</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <p className="text-sm text-slate-500">No file details available.</p>
          )}
        </div>
      </div>
      
    </div>
  );
}
