import { Outlet, Link, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, GitBranch, Moon, Sun, Settings, LogOut, Bell } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../config';

export default function Layout() {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Repositories', href: '/onboarding', icon: GitBranch },
    { name: 'Security Passport', href: '/passport', icon: Shield },
  ];

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await apiClient.get(`/notifications`);
        setNotifications(res.data);
      } catch (e) {
        console.error("Failed to fetch notifications", e);
      }
    };
    fetchNotifications();
    
    const interval = setInterval(fetchNotifications, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const markAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.put(`/notifications/${id}/read`, {});
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (e) {
      console.error("Failed to mark as read", e);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="flex h-screen bg-background-light dark:bg-background-dark">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border-light dark:border-border-dark bg-surface-light dark:bg-surface-dark flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-border-light dark:border-border-dark">
          <img src="/gitflow-logo.jpg" alt="GitFlow Logo" className="w-8 h-8 rounded mr-3 shadow-sm border border-slate-700/50" />
          <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-500 to-brand-400 tracking-tight">
            GitFlow
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
        <header className="h-16 border-b border-border-light dark:border-border-dark bg-surface-light/50 dark:bg-surface-dark/50 backdrop-blur-sm flex items-center justify-between px-8 z-10">
          <h1 className="text-xl font-semibold">
            {navigation.find(n => location.pathname.startsWith(n.href))?.name || 'Overview'}
          </h1>
          <div className="flex items-center space-x-4">
            
            <div className="relative" ref={notifRef}>
              <button 
                onClick={() => setShowNotifications(!showNotifications)}
                className="p-2 relative text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white dark:border-slate-900"></span>
                )}
              </button>

              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-border-light dark:border-border-dark rounded-xl shadow-xl overflow-hidden z-50">
                  <div className="p-4 border-b border-border-light dark:border-border-dark flex justify-between items-center">
                    <h3 className="font-semibold text-sm">Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="text-xs bg-brand-100 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400 px-2 py-0.5 rounded-full font-medium">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  <div className="max-h-[400px] overflow-y-auto">
                    {notifications.length === 0 ? (
                      <div className="p-4 text-center text-sm text-slate-500">No notifications</div>
                    ) : (
                      notifications.map((n, i) => (
                        <div key={i} className={`p-4 border-b border-border-light dark:border-border-dark last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ${!n.is_read ? 'bg-slate-50/50 dark:bg-slate-800/20' : ''}`}>
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-sm font-medium pr-4">{n.title || n.message}</span>
                            {!n.is_read && (
                              <button 
                                onClick={(e) => markAsRead(n.id, e)}
                                className="text-xs text-brand-500 hover:text-brand-600 whitespace-nowrap"
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-1">{new Date(n.created_at || Date.now()).toLocaleString()}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            <button onClick={() => alert("Settings configuration coming soon.")} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <Settings className="w-5 h-5" />
            </button>
            <div onClick={() => alert("Profile management coming soon.")} className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-500 to-purple-500 flex items-center justify-center text-white font-medium text-sm cursor-pointer hover:opacity-90 transition-opacity">
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
