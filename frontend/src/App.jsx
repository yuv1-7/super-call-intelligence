// App.jsx — Router shell with role-based navigation

import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, useAuth, useUser } from '@clerk/clerk-react';
import { useApi } from './hooks/useApi.js';

import Sidebar from './components/Sidebar.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import CallPage from './pages/CallPage.jsx';
import CallHistoryPage from './pages/CallHistoryPage.jsx';
import CallDetailPage from './pages/CallDetailPage.jsx';
import TeamDashboardPage from './pages/TeamDashboardPage.jsx';
import DevPage from './pages/DevPage.jsx';

export default function App() {
    const { isSignedIn } = useAuth();
    const { user } = useUser();
    const { fetchWithAuth } = useApi();
    const [userRole, setUserRole] = useState('agent');
    const [userName, setUserName] = useState('');

    useEffect(() => {
        if (isSignedIn && user) {
            // Get role from Clerk publicMetadata
            const meta = user.publicMetadata || {};
            setUserRole(meta.role || 'agent');
            setUserName(user.firstName || user.fullName || 'User');

            // Sync user to backend DB
            fetchWithAuth('/api/me').catch(err =>
                console.warn('User sync failed (backend may not have DB):', err)
            );
        }
    }, [isSignedIn, user]);

    return (
        <>
            <SignedOut>
                <LoginPage />
            </SignedOut>
            <SignedIn>
                <div className="app-shell">
                    <Sidebar userRole={userRole} />
                    <div className="app-main">
                        {/* Header */}
                        <header className="app-header compact">
                            <div className="header-brand">
                                <h1>
                                    <span className="brand-title">CallIQ</span>
                                    <span className="brand-subtitle">Dashboard</span>
                                </h1>
                            </div>
                        </header>

                        {/* Routes */}
                        <div className="app-content">
                            <Routes>
                                <Route path="/" element={
                                    <DashboardPage userRole={userRole} userName={userName} />
                                } />
                                <Route path="/call" element={<CallPage />} />
                                <Route path="/history" element={
                                    <CallHistoryPage userRole={userRole} />
                                } />
                                <Route path="/history/:id" element={<CallDetailPage />} />
                                <Route path="/team" element={
                                    userRole === 'agent'
                                        ? <Navigate to="/" replace />
                                        : <TeamDashboardPage userRole={userRole} />
                                } />
                                <Route path="/dev" element={<DevPage />} />
                                <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                        </div>
                    </div>
                </div>
            </SignedIn>
        </>
    );
}
