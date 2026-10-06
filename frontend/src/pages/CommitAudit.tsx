import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, FileText, Shield, Zap, CheckCircle, Activity } from 'lucide-react';
import { apiClient } from '../config';

function securityGuidance(category: string) {
  switch (category?.toLowerCase()) {
    case 'secret':
      return 'Security: if this is a real credential, revoke or rotate it and remove it from the repository history.';
    case 'vulnerability':
      return 'Security: review the affected dependency and update to a patched version.';
    case 'dependencyscan':
      return 'Security: dependency results are incomplete. Install or restore the dependency scanner and run this scan again.';
    default:
      return 'Review this finding and its file location to decide whether it needs a change.';
  }
}

export default function CommitAudit() {
  const { repositoryId, scanId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!repositoryId || !scanId) {
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

  if (!repositoryId || !scanId) return <div role="alert" className="p-8 text-center text-slate-500">This audit link is missing its repository or scan ID.</div>;
  if (loading) return <div className="p-8 text-center text-slate-500">Loading audit data...</div>;

  if (error) return <div className="p-8 text-center text-red-500">{error}</div>;
  if (!data) return <div className="p-8 text-center text-slate-500">No data found.</div>;

  const currentScore = data.risk_score;
  const prevCommit = data.previous_commit;
  
  // Group findings
  const newFindings = data.findings?.filter((f: any) => f.status === 'NEW' || f.status === 'BASELINE') || [];
  const unchangedFindings = data.findings?.filter((f: any) => f.status === 'UNCHANGED') || [];
  const resolvedFindings = data.findings?.filter((f: any) => f.status === 'RESOLVED') || [];
  
  const addedFiles = data.changes?.filter((c: any) => c.status === 'A' || c.status?.startsWith('C')) || [];
  const modifiedFiles = data.changes?.filter((c: any) => ['M', 'T', 'U', 'X', 'B'].includes(c.status)) || [];
  const removedFiles = data.changes?.filter((c: any) => c.status === 'D') || [];
  const renamedFiles = data.changes?.filter((c: any) => c.status?.startsWith('R')) || [];

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* COMMIT */}
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft">
          <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">COMMIT</h2>
          <div className="font-mono text-xl text-brand-600 dark:text-brand-400 mb-2">{data.commit_sha?.substring(0, 7)}</div>
          <p className="text-slate-800 dark:text-slate-200 font-medium mb-4">"{data.message || 'No commit message'}"</p>
          <div className="text-sm text-slate-600 dark:text-slate-400">
            <p>Author: {data.author || 'Unknown'}</p>
            <p>Timestamp: {data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown time'}</p>
          </div>
        </div>

        {/* PREVIOUS COMMIT / SCORE */}
        <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-4">PREVIOUS COMMIT</h2>
            {prevCommit ? (
              <>
                <div className="font-mono text-lg text-slate-600 dark:text-slate-400 mb-1">{prevCommit.short_sha}</div>
                <p className="text-slate-700 dark:text-slate-300 text-sm italic mb-2">"{prevCommit.message}"</p>
                <div className="text-xs text-slate-500">
                  <p>{prevCommit.author} | {new Date(prevCommit.timestamp).toLocaleString()}</p>
                  <p className="mt-1">Previous Score: <strong className="text-slate-700 dark:text-slate-300">{prevCommit.score}</strong></p>
                </div>
              </>
            ) : (
              <div className="text-slate-600 dark:text-slate-400 text-sm">
                <p className="font-medium mb-1">BASELINE COMMIT</p>
                <p>This is the first tracked commit for this repository. No previous score is available.</p>
              </div>
            )}
          </div>
          
          <div className="mt-4 pt-4 border-t border-border-light dark:border-border-dark flex items-center justify-between">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Current Security Score</span>
            <div className="flex items-center space-x-3">
              <span className="text-3xl font-bold text-slate-800 dark:text-white">{currentScore !== null ? currentScore : "N/A"}</span>
              {prevCommit && data.score_delta !== null && (
                <span className={`px-2 py-1 rounded text-sm font-bold ${data.score_delta > 0 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30' : data.score_delta < 0 ? 'bg-red-100 text-red-700 dark:bg-red-900/30' : 'bg-slate-100 text-slate-600 dark:bg-slate-800'}`}>
                  {data.score_delta > 0 ? '+' : ''}{data.score_delta}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {data.status === 'FAILED' && (
        <div role="alert" className="rounded-xl border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 p-5 text-red-700 dark:text-red-300">
          <h2 className="font-semibold">This scan did not complete</h2>
          <p className="mt-1 text-sm">{data.error_message || 'The scan failed without an additional message. You can retry it from the dashboard.'}</p>
          <p className="mt-2 text-xs">Scan ID: {data.id} · Commit: {data.commit_sha?.substring(0, 7)}</p>
        </div>
      )}

      {/* WHY THE SCORE CHANGED */}
      {prevCommit && (
        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-brand-500" />
            Why the Score Changed
          </h2>
          <div className="text-slate-600 dark:text-slate-400 text-sm mb-4">
            Security Score {data.score_delta > 0 ? `improved by ${data.score_delta} points.` : data.score_delta < 0 ? `decreased by ${Math.abs(data.score_delta)} points of deduction.` : 'remained unchanged.'}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {resolvedFindings.length > 0 && (
              <div className="bg-emerald-50 dark:bg-emerald-900/10 p-4 rounded-lg border border-emerald-100 dark:border-emerald-900/30">
                <h4 className="font-semibold text-emerald-700 dark:text-emerald-400 mb-2 flex items-center"><CheckCircle className="w-4 h-4 mr-2"/> Resolved</h4>
                <ul className="text-sm space-y-1 text-emerald-600 dark:text-emerald-500">
                  {resolvedFindings.map((f: any, i: number) => <li key={i}>+ {f.title} fixed</li>)}
                </ul>
              </div>
            )}
            {newFindings.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/10 p-4 rounded-lg border border-red-100 dark:border-red-900/30">
                <h4 className="font-semibold text-red-700 dark:text-red-400 mb-2 flex items-center"><AlertTriangle className="w-4 h-4 mr-2"/> New Deductions</h4>
                <ul className="text-sm space-y-1 text-red-600 dark:text-red-500">
                  {newFindings.map((f: any, i: number) => <li key={i}>- {f.title}</li>)}
                </ul>
              </div>
            )}
            {newFindings.length === 0 && resolvedFindings.length === 0 && (
               <div className="text-sm text-slate-500 p-4">No point deductions were added or removed in this commit.</div>
            )}
          </div>
        </div>
      )}

      {/* WHAT CHANGED */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <FileText className="w-5 h-5 mr-2 text-slate-400" />
          What Changed
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">{data.changes?.length || 0} files changed.</p>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
          {addedFiles.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-emerald-500 mb-2">Added ({addedFiles.length})</h4>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1 font-mono text-xs overflow-hidden">
                {addedFiles.map((c: any, i: number) => <li key={i} className="break-all" title={c.file}>+ {c.file}</li>)}
              </ul>
            </div>
          )}
          {modifiedFiles.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-brand-500 mb-2">Modified ({modifiedFiles.length})</h4>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1 font-mono text-xs overflow-hidden">
                {modifiedFiles.map((c: any, i: number) => <li key={i} className="break-all" title={c.file}>~ {c.file}</li>)}
              </ul>
            </div>
          )}
          {removedFiles.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-red-500 mb-2">Removed ({removedFiles.length})</h4>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1 font-mono text-xs overflow-hidden">
                {removedFiles.map((c: any, i: number) => <li key={i} className="break-all" title={c.file}>- {c.file}</li>)}
              </ul>
            </div>
          )}
          {renamedFiles.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-amber-500 mb-2">Renamed ({renamedFiles.length})</h4>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-1 font-mono text-xs overflow-hidden">
                {renamedFiles.map((c: any, i: number) => <li key={i} className="break-all" title={c.file}>→ {c.file}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* ISSUES FOUND */}
      <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
        <h2 className="text-xl font-semibold mb-6 flex items-center">
          <ShieldAlert className="w-5 h-5 mr-2 text-slate-400" />
          Issues Found
        </h2>
        
        <div className="space-y-6">
          {newFindings.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold uppercase text-slate-500 mb-3">{prevCommit ? 'NEW ISSUES' : 'BASELINE ISSUES'}</h3>
              <div className="space-y-3">
                {newFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-red-50 dark:bg-red-900/10 p-3 rounded-lg border border-red-100 dark:border-red-900/30 text-sm">
                    <div className="flex items-center mb-1">
                      <span className="w-2 h-2 rounded-full bg-red-500 mr-2"/>
                      <span className="font-semibold text-red-700 dark:text-red-400">{f.severity}</span>
                      <span className="mx-2 text-slate-300">|</span>
                      <span className="text-slate-700 dark:text-slate-300 font-medium">{f.title}</span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400 pl-4">
                      <p>{f.description || `Potential ${f.title.toLowerCase()} detected.`} Location: <span className="font-mono text-xs">{f.file_path || 'repository'}</span>{f.line_number ? `, line ${f.line_number}` : ', file-level finding (no single line)' }.</p>
                      <p className="mt-2 text-xs font-medium">{securityGuidance(f.title)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resolvedFindings.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold uppercase text-slate-500 mb-3">RESOLVED ISSUES</h3>
              <div className="space-y-3">
                {resolvedFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-emerald-50 dark:bg-emerald-900/10 p-3 rounded-lg border border-emerald-100 dark:border-emerald-900/30 text-sm">
                    <div className="flex items-center mb-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"/>
                      <span className="font-semibold text-emerald-700 dark:text-emerald-400">{f.severity}</span>
                      <span className="mx-2 text-slate-300">|</span>
                      <span className="text-slate-700 dark:text-slate-300 font-medium">{f.title}</span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400 pl-4 font-mono text-xs">
                      {f.file_path}{f.line_number ? ` (line ${f.line_number})` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {unchangedFindings.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold uppercase text-slate-500 mb-3">UNCHANGED ISSUES</h3>
              <div className="space-y-3">
                {unchangedFindings.map((f: any, i: number) => (
                  <div key={i} className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-200 dark:border-slate-700 text-sm opacity-80">
                    <div className="flex items-center mb-1">
                      <span className={`w-2 h-2 rounded-full mr-2 ${f.severity==='Critical'?'bg-red-500':f.severity==='High'?'bg-orange-500':f.severity==='Medium'?'bg-amber-500':'bg-blue-500'}`}/>
                      <span className="font-semibold text-slate-700 dark:text-slate-400">{f.severity}</span>
                      <span className="mx-2 text-slate-300">|</span>
                      <span className="text-slate-700 dark:text-slate-300 font-medium">{f.title}</span>
                    </div>
                    <div className="text-slate-500 dark:text-slate-400 pl-4 font-mono text-xs">
                      {f.file_path}{f.line_number ? ` (line ${f.line_number})` : ''}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.findings?.length === 0 && (
            <p className="text-sm text-slate-500">No issues found.</p>
          )}
        </div>
      </div>

      {/* ACTION SUMMARY & IMPACT */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Zap className="w-5 h-5 mr-2 text-brand-500" />
            Action Summary
          </h2>
          {data.actions_detected && data.actions_detected.length > 0 ? (
            <ul className="space-y-3">
              {data.actions_detected.map((action: string, i: number) => (
                <li key={i} className="flex items-center text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/50 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                  <CheckCircle className="w-4 h-4 mr-3 text-brand-500" />
                  {action}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No high-level actions identified.</p>
          )}
        </div>

        <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Shield className="w-5 h-5 mr-2 text-slate-400" />
            Impact
          </h2>
          {data.impact && Object.keys(data.impact).length > 0 ? (
            <div className="space-y-4 text-sm max-h-[250px] overflow-y-auto pr-2 custom-scrollbar">
              {Object.entries(data.impact).map(([affected, causes]: [string, any], i) => (
                <div key={i} className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded border border-slate-100 dark:border-slate-700">
                    <span className="font-mono text-xs text-brand-600 dark:text-brand-400 truncate block">{affected}</span> 
                    <span className="text-xs text-slate-500 mt-1 block">is affected by changes in:</span>
                    <ul className="list-disc pl-5 mt-1 text-slate-500 space-y-1">
                      {causes.map((c: any, j: number) => (
                        <li key={j}>
                          <span className="font-mono text-xs truncate inline-block max-w-[150px] align-bottom">{c.changed_file}</span>
                          <span className={`ml-2 text-[10px] uppercase px-1.5 py-0.5 rounded ${c.review_priority === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-slate-200 text-slate-600'}`}>{c.review_priority}</span>
                        </li>
                      ))}
                    </ul>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-sm">No cross-file dependencies were detected as impacted by this change.</p>
          )}
        </div>
      </div>
    </div>
  );
}
