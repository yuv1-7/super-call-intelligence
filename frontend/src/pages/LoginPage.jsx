import React from 'react';
import { SignIn } from '@clerk/clerk-react';
import { dark } from '@clerk/themes';
import { Sparkles, Activity, ShieldCheck, Zap } from 'lucide-react';
import '../index.css';

export default function LoginPage() {
    return (
        <div className="login-container">
            {/* Animated Background Elements */}
            <div className="blob blob-1"></div>
            <div className="blob blob-2"></div>
            <div className="blob blob-3"></div>

            <main className="login-content">
                {/* Left side: Branding & Value Props */}
                <div className="login-branding">
                    <div className="brand-header">
                        <img src="/logo.png" alt="Extremum Analytics Logo" className="login-logo" />
                        <h1 className="login-title">
                            Super Call Intelligence
                            <span className="login-badge"><Sparkles size={16} /> AI Powered</span>
                        </h1>
                        <p className="login-subtitle">
                            Empowering your support teams with superhuman analytics and real-time coaching.
                        </p>
                    </div>

                    <div className="value-props">
                        <div className="value-prop">
                            <div className="vp-icon"><Activity size={24} /></div>
                            <div className="vp-text">
                                <h3>Real-time Transcripts</h3>
                                <p>Capture every word with sub-second latency.</p>
                            </div>
                        </div>
                        <div className="value-prop">
                            <div className="vp-icon"><Zap size={24} /></div>
                            <div className="vp-text">
                                <h3>Instant Insights</h3>
                                <p>Contextual suggestions powered by semantic search.</p>
                            </div>
                        </div>
                        <div className="value-prop">
                            <div className="vp-icon"><ShieldCheck size={24} /></div>
                            <div className="vp-text">
                                <h3>Live Compliance</h3>
                                <p>Ensure agent adherence to QA guidelines dynamically.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right side: Authentication Card */}
                <div className="login-auth-card">
                    {/* Right side: Authentication Card */}
                    <div className="login-auth-card">
                        <SignIn
                            appearance={{
                                baseTheme: dark,
                                variables: {
                                    colorPrimary: '#3b82f6', // Professional blue
                                    colorBackground: '#1e293b', // Solid slate background, no transparency
                                    colorInputBackground: '#0f172a',
                                    colorInputText: '#fff',
                                    colorText: '#f8fafc',
                                    colorTextSecondary: '#94a3b8',
                                    borderRadius: '16px', // Less round, more professional
                                },
                                elements: {
                                    cardBox: "clerk-pro-card",
                                    socialButtonsBlockButton: "clerk-social-button",
                                    formButtonPrimary: "clerk-primary-button",
                                    formFieldInput: "clerk-input",
                                },
                            }}
                        />
                    </div>
                </div>
            </main>
        </div>
    );
}
