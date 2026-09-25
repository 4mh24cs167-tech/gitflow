import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { GitCommit, ShieldAlert, AlertTriangle, FileText } from 'lucide-react';
import axios from 'axios';
import { API_URL } from '../config';

export default function CommitAudit() {
  const { repositoryId, scanId } = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!repositoryId || !scanId) {
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_URL}/repositories/${repositoryId}/scans/${scanId}`);
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load audit data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [repositoryId, scanId]);

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

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center mb-2">
            <GitCommit className="w-8 h-8 mr-3 text-brand-500" />
            Commit Audit
          </h1>
          <p className="text-slate-500">
            Real production analysis for scan ID {scanId}.
          </p>
        </div>
      </div>
      
      <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft dark:shadow-soft-dark">
        <h3 className="text-lg font-semibold mb-4">Risk Findings</h3>
        {data.findings && data.findings.length > 0 ? (
          <div className="space-y-4">
            {data.findings.map((finding: any, i: number) => (
              <div key={i} className="flex items-start p-4 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 mr-3 shrink-0" />
                <div>
                  <h4 className="font-medium">{finding.title}</h4>
                  <p className="text-sm text-slate-500 mt-1">{finding.description}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-slate-500 text-sm">No critical findings in this scan.</p>
        )}
      </div>
      
      <div className="bg-surface-light dark:bg-surface-dark rounded-xl border border-border-light dark:border-border-dark p-6 shadow-soft dark:shadow-soft-dark">
        <h3 className="text-lg font-semibold mb-4">What Changed</h3>
        {data.changes && data.changes.length > 0 ? (
           <div className="space-y-2">
             {data.changes.map((change: any, i: number) => (
               <div key={i} className="flex items-center text-sm font-mono text-slate-600 dark:text-slate-300">
                 <FileText className="w-4 h-4 mr-2 text-slate-400" />
                 {change.file}
               </div>
             ))}
           </div>
        ) : (
           <p className="text-slate-500 text-sm">No structural changes detected.</p>
        )}
      </div>
    </div>
  );
}
