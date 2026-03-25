import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut, useAuth, useUser } from '@clerk/clerk-react';
import { useApi } from './hooks/useApi.js';
import { AnimatePresence } from 'framer-motion';

import Sidebar from './components/Sidebar.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import CallPage from './pages/CallPage.jsx';
import CallHistoryPage from './pages/CallHistoryPage.jsx';
import CallDetailPage from './pages/CallDetailPage.jsx';
import TeamDashboardPage from './pages/TeamDashboardPage.jsx';
import DevPage from './pages/DevPage.jsx';
import { CallProvider } from './context/CallContext.jsx';
import GlobalHeader from './components/GlobalHeader.jsx';

export default function App() {
    const { isSignedIn } = useAuth();
    const { user } = useUser();
    const { fetchWithAuth } = useApi();
    const [userRole, setUserRole] = useState('agent');
    const [userName, setUserName] = useState('');
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    useEffect(() => {
        if (isSignedIn && user) {
            const meta = user.publicMetadata || {};
            setUserRole(meta.role || 'agent');
            setUserName(user.firstName || user.fullName || 'User');

            fetchWithAuth('/api/me').catch(err =>
                console.warn('User sync failed:', err)
            );
        }
    }, [isSignedIn, user]);

    return (
        <>
            <SignedOut>
                <LoginPage />
            </SignedOut>
            <SignedIn>
                <CallProvider>
                    <div className="global-layout">
                        <GlobalHeader userRole={userRole} />
                        <div className={`app-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
                            <Sidebar
                                userRole={userRole}
                                collapsed={sidebarCollapsed}
                                onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
                            />
                            <main className="app-main">
                                <AnimatePresence mode="wait">
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
                                </AnimatePresence>
                            </main>
                        </div>
                    </div>
                </CallProvider>
            </SignedIn>
        </>
    );
}
