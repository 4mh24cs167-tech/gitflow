import { Outlet, Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, FileCode, GitBranch, Moon, Sun, Settings, LogOut } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function Layout() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Repositories', href: '/onboarding', icon: GitBranch },
    { name: 'Risk Passport', href: '/passport', icon: Shield },
    { name: 'Audit', href: '/audit', icon: FileCode },
  ];

  return (
    <div className="flex h-screen bg-background-light dark:bg-background-dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border-light dark:border-border-dark">
          <Shield className="w-8 h-8 text-brand-500 mr-3" />
          <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-500 to-brand-400">
            Risk Passport
          </span>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400 font-medium' 
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                }`}
              >
                <item.icon className={`w-5 h-5 mr-3 ${isActive ? 'text-brand-600 dark:text-brand-400' : 'text-slate-400'}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border-light dark:border-border-dark space-y-2">
          <button 
            onClick={toggleTheme}
            className="flex items-center w-full px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 mr-3" /> : <Moon className="w-4 h-4 mr-3" />}
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button 
            onClick={() => {
              localStorage.removeItem('access_token');
              window.location.href = '/';
            }}
            className="flex items-center w-full px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors">
            <LogOut className="w-4 h-4 mr-3" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 border-b border-border-light dark:border-border-dark bg-surface-light/50 dark:bg-surface-dark/50 backdrop-blur-sm flex items-center justify-between px-8">
          <h1 className="text-xl font-semibold">
            {navigation.find(n => location.pathname.startsWith(n.href))?.name || 'Overview'}
          </h1>
          <div className="flex items-center space-x-4">
            <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <Settings className="w-5 h-5" />
            </button>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-500 to-purple-500 flex items-center justify-center text-white font-medium text-sm">
              JD
            </div>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
