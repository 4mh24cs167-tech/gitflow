import { Link } from 'react-router-dom';
import { Shield, ChevronRight, GitBranch } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Landing() {
  useTheme();

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Background gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-500/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/20 blur-[120px] rounded-full pointer-events-none" />

      {/* Navbar */}
      <nav className="border-b border-border-light dark:border-border-dark bg-surface-light/50 dark:bg-surface-dark/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="w-7 h-7 text-brand-500" />
            <span className="text-xl font-bold tracking-tight">Risk Passport</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link to="/login" className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors">
              Sign In
            </Link>
            <Link to="/register" className="text-sm font-medium px-4 py-2 rounded-md bg-brand-500 hover:bg-brand-600 text-white transition-colors shadow-lg shadow-brand-500/25">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20 z-10">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-sm font-medium border border-brand-100 dark:border-brand-800/50 mb-4">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-500"></span>
            </span>
            <span>Now in public beta</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.1]">
            Secure your software <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-purple-500">
              supply chain.
            </span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            Comprehensive risk analysis, vulnerability scanning, and compliance tracking for modern engineering teams. Generate your Software Risk Passport in minutes.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4 pt-4">
            <Link to="/register" className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 rounded-lg bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-medium hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors shadow-xl shadow-slate-900/10 dark:shadow-white/10">
              Connect GitBranch <GitBranch className="ml-2 w-4 h-4" />
            </Link>
            <Link to="/login" className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 rounded-lg bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark text-slate-900 dark:text-white font-medium hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors">
              View Dashboard <ChevronRight className="ml-1 w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* Dashboard Preview */}
        <div className="w-full max-w-5xl mx-auto mt-20 relative">
          <div className="absolute inset-0 bg-gradient-to-t from-background-light dark:from-background-dark to-transparent z-10 bottom-0 h-1/3 mt-auto pointer-events-none" />
          <div className="rounded-xl border border-border-light dark:border-border-dark bg-surface-light/80 dark:bg-surface-dark/80 backdrop-blur-xl shadow-2xl overflow-hidden p-2">
             <div className="rounded-lg border border-border-light/50 dark:border-border-dark/50 bg-background-light dark:bg-background-dark p-6">
                <div className="flex items-center justify-between mb-8">
                  <div className="space-y-1">
                    <h3 className="text-lg font-semibold">Security Posture</h3>
                    <p className="text-sm text-slate-500">Real-time risk assessment</p>
                  </div>
                  <div className="flex space-x-2">
                    <div className="w-3 h-3 rounded-full bg-severity-critical" />
                    <div className="w-3 h-3 rounded-full bg-severity-high" />
                    <div className="w-3 h-3 rounded-full bg-severity-medium" />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-32 rounded-lg bg-slate-100 dark:bg-slate-800/50 animate-pulse" />
                  ))}
                </div>
             </div>
          </div>
        </div>
      </main>
    </div>
  );
}
