// components/Sidebar.jsx — Role-based navigation sidebar

import { useLocation, useNavigate } from 'react-router-dom';
import { UserButton } from '@clerk/clerk-react';
import {
    LayoutDashboard, Phone, History, Users, Shield, Settings, ChevronLeft, ChevronRight
} from 'lucide-react';
import { useState } from 'react';

const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export default function Sidebar({ userRole }) {
    const location = useLocation();
    const navigate = useNavigate();
    const [collapsed, setCollapsed] = useState(false);

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

    return (
        <nav className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-brand" onClick={() => navigate('/')}>
                    <img src="/logo.png" alt="CallIQ" className="sidebar-logo" />
                    {!collapsed && <span className="sidebar-title">CallIQ</span>}
                </div>
                <button
                    className="sidebar-toggle"
                    onClick={() => setCollapsed(!collapsed)}
                    title={collapsed ? 'Expand' : 'Collapse'}
                >
                    {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
                </button>
            </div>

            <div className="sidebar-nav">
                {filteredItems.map(item => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path ||
                        (item.path !== '/' && location.pathname.startsWith(item.path));
                    return (
                        <button
                            key={item.path}
                            className={`sidebar-item ${isActive ? 'active' : ''}`}
                            onClick={() => navigate(item.path)}
                            title={item.label}
                        >
                            <Icon size={20} />
                            {!collapsed && <span>{item.label}</span>}
                        </button>
                    );
                })}
            </div>

            <div className="sidebar-footer">
                {!collapsed && (
                    <div className="sidebar-role-badge">
                        <Shield size={14} />
                        <span>{(userRole || 'agent').replace('_', ' ')}</span>
                    </div>
                )}
                <UserButton />
            </div>
        </nav>
    );
}
