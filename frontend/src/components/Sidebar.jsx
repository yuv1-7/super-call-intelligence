// components/Sidebar.jsx — Premium redesigned sidebar with smooth collapse

import { useLocation, useNavigate } from 'react-router-dom';
import { UserButton } from '@clerk/clerk-react';
import {
    LayoutDashboard, Phone, History, Users, Shield, Settings,
    ChevronLeft, ChevronRight
} from 'lucide-react';

const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export default function Sidebar({ userRole, collapsed, onToggle }) {
    const location = useLocation();
    const navigate = useNavigate();

    const navItems = [
        { path: '/', icon: LayoutDashboard, label: 'Dashboard', roles: ['agent', 'team_lead', 'manager'] },
        { path: '/call', icon: Phone, label: 'Active Call', roles: ['agent', 'team_lead', 'manager'] },
        { path: '/history', icon: History, label: 'Call History', roles: ['agent', 'team_lead', 'manager'] },
        { path: '/team', icon: Users, label: 'Team', roles: ['team_lead', 'manager'] },
    ];

    if (DEV_MODE) {
        navItems.push({ path: '/dev', icon: Settings, label: 'Dev Tools', roles: ['agent', 'team_lead', 'manager'] });
    }

    const filteredItems = navItems.filter(item => item.roles.includes(userRole || 'agent'));

    const roleLabel = (userRole || 'agent').replace('_', ' ');
    const roleIcon = userRole === 'manager' ? '👔' : userRole === 'team_lead' ? '👥' : '🎧';

    return (
        <nav className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            {/* Brand */}
            <div className="sidebar-brand" onClick={() => navigate('/')}>
                <img src="/logo.png" alt="CallIQ" className="sidebar-logo" />
                <div className="sidebar-brand-text">
                    <span className="sidebar-title">CallIQ</span>
                    <span className="sidebar-subtitle">Intelligence</span>
                </div>
            </div>

            {/* Toggle */}
            <button
                className="sidebar-collapse-btn"
                onClick={onToggle}
                title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
                {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {/* Navigation */}
            <div className="sidebar-nav">
                {filteredItems.map(item => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path ||
                        (item.path !== '/' && location.pathname.startsWith(item.path));
                    return (
                        <button
                            key={item.path}
                            className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                            onClick={() => navigate(item.path)}
                            title={item.label}
                        >
                            <div className="sidebar-nav-icon">
                                <Icon size={18} />
                            </div>
                            <span className="sidebar-nav-label">{item.label}</span>
                            {isActive && <div className="sidebar-active-indicator" />}
                        </button>
                    );
                })}
            </div>

            {/* Footer */}
            <div className="sidebar-footer">
                <div className="sidebar-role-badge" title={roleLabel}>
                    <span className="sidebar-role-icon">{roleIcon}</span>
                    <span className="sidebar-role-text">{roleLabel}</span>
                </div>
                <div className="sidebar-user-btn">
                    <UserButton />
                </div>
            </div>
        </nav>
    );
}
