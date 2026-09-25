import { useParams } from 'react-router-dom';
import { GitCommit, ArrowUpRight, ArrowDownRight, FileText, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function CommitAudit() {
  const { id } = useParams();

  const commitData = {
    sha: "a1b2c3d4",
    message: "feat: Implement new authentication flow",
    author: "Alice Developer",
    date: "2026-09-25T10:00:00Z",
    riskScore: 78,
    scoreDelta: -5,
    whatChanged: [
      { file: "src/auth/login.ts", type: "modified", linesAdded: 45, linesRemoved: 12 },
      { file: "src/auth/oauth.ts", type: "added", linesAdded: 120, linesRemoved: 0 }
    ],
    findings: [
      { id: "F-001", title: "Hardcoded secret in oauth.ts", severity: "Critical", status: "new" },
      { id: "F-002", title: "Insecure random number generator", severity: "Medium", status: "resolved" }
    ],
    changeImpact: "High impact on authentication modules. Increased risk due to new secrets."
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center mb-2">
            <GitCommit className="w-8 h-8 mr-3 text-slate-400" />
            Commit {commitData.sha}
          </h1>
          <p className="text-slate-500 text-lg">{commitData.message}</p>
          <p className="text-sm text-slate-400 mt-1">by {commitData.author} on {new Date(commitData.date).toLocaleString()}</p>
        </div>
        <div className="flex flex-col items-end">
          <div className="text-sm text-slate-500 uppercase tracking-wider mb-1">Risk Score</div>
          <div className="flex items-center">
            <span className="text-4xl font-bold text-amber-500">{commitData.riskScore}</span>
            <div className={`ml-3 flex items-center text-sm font-medium ${commitData.scoreDelta < 0 ? 'text-red-500' : 'text-emerald-500'}`}>
              {commitData.scoreDelta < 0 ? <ArrowUpRight className="w-4 h-4 mr-1" /> : <ArrowDownRight className="w-4 h-4 mr-1" />}
              {Math.abs(commitData.scoreDelta)}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-slate-400" />
              What Changed
            </h2>
            <div className="divide-y divide-border-light dark:divide-border-dark">
              {commitData.whatChanged.map((change, i) => (
                <div key={i} className="py-3 flex items-center justify-between">
                  <div className="flex items-center">
                    <span className={`w-2 h-2 rounded-full mr-3 ${change.type === 'added' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <span className="font-mono text-sm">{change.file}</span>
                  </div>
                  <div className="text-sm font-mono flex space-x-4">
                    <span className="text-emerald-500">+{change.linesAdded}</span>
                    <span className="text-red-500">-{change.linesRemoved}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <AlertTriangle className="w-5 h-5 mr-2 text-slate-400" />
              Findings
            </h2>
            <div className="space-y-3">
              {commitData.findings.map((finding) => (
                <div key={finding.id} className="p-4 rounded-lg border border-border-light dark:border-border-dark flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-3 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded-md ${
                        finding.severity === 'Critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                        finding.severity === 'High' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                        finding.severity === 'Medium' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                        'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                      }`}>
                        {finding.severity}
                      </span>
                      <span className={`text-xs uppercase tracking-wider font-semibold ${
                        finding.status === 'new' ? 'text-red-500' : 'text-emerald-500'
                      }`}>
                        {finding.status}
                      </span>
                    </div>
                    <p className="font-medium">{finding.title}</p>
                  </div>
                  <button className="text-sm text-brand-500 hover:text-brand-600 font-medium">View Details</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark shadow-soft p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <ShieldAlert className="w-5 h-5 mr-2 text-slate-400" />
              Change Impact
            </h2>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              {commitData.changeImpact}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
