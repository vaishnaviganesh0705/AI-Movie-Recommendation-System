import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Sparkles, ShieldCheck, Zap, Film, Tv, Headphones, Award } from 'lucide-react';
import api from '../services/api';

const Subscription = () => {
    const navigate = useNavigate();
    const [plans, setPlans] = useState([]);
    const [currentSub, setCurrentSub] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadSubscriptionData = async () => {
            setLoading(true);
            try {
                // 1) Load available plans
                const plansRes = await api.get('/subscription/plans');
                if (Array.isArray(plansRes.data)) {
                    setPlans(plansRes.data);
                }

                // 2) Load user's current subscription status if logged in
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (token) {
                    try {
                        const statusRes = await api.get('/subscription/status');
                        setCurrentSub(statusRes.data);
                    } catch (e) {
                        console.warn("Could not load current subscription", e);
                    }
                }
            } catch (err) {
                console.error("Error loading plans", err);
            } finally {
                setLoading(false);
            }
        };

        loadSubscriptionData();
    }, []);

    const handleSelectPlan = (plan) => {
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        if (!token) {
            alert('Please sign in to choose a subscription plan.');
            return navigate('/login');
        }

        if (plan.price === 0) {
            // Free plan
            alert("You are already on the Free tier.");
            return;
        }

        navigate(`/payment?planId=${plan.id}`);
    };

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Loading subscription plans...
            </div>
        );
    }

    // Default fallback plans if database was empty
    const displayPlans = plans.length > 0 ? plans : [
        { id: 1, name: 'Free', price: 0.0, duration_days: 30, features: 'Standard definition (480p), Ad-supported, 1 screen' },
        { id: 2, name: 'Standard', price: 9.99, duration_days: 30, features: 'Full HD (1080p), Ad-free movies & TV, 2 screens simultaneously' },
        { id: 3, name: 'Premium', price: 19.99, duration_days: 30, features: 'Ultra HD 4K + HDR, Spatial audio, 4 screens, Full Music library, AI agent priority' }
    ];

    const currentPlanId = currentSub?.status === 'active' ? currentSub.plan_id : (plans.find(p => p.price === 0)?.id || 1);

    return (
        <div style={{ padding: '100px 4% 80px', color: 'var(--text-primary)', maxWidth: '1140px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '50px' }}>
                <span style={{
                    background: 'rgba(229, 9, 20, 0.15)',
                    color: 'var(--accent-hover)',
                    padding: '6px 14px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: 700,
                    letterSpacing: '1px',
                    textTransform: 'uppercase',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginBottom: '16px'
                }}>
                    <Sparkles size={14} /> StreamHub Unlimited
                </span>
                <h1 style={{ fontSize: '40px', margin: '0 0 16px', fontWeight: 800, letterSpacing: '-0.5px' }}>
                    Choose the plan that's right for you
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '16px', maxWidth: '600px', margin: '0 auto' }}>
                    Stream all movies, series, and high-fidelity music tracks with zero interruptions. Cancel or switch anytime.
                </p>
            </div>

            {/* Plans Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: '28px',
                marginBottom: '60px'
            }}>
                {displayPlans.map(plan => {
                    const isCurrent = currentSub?.status === 'active' && currentSub.plan_id === plan.id;
                    const isPremium = plan.name.toLowerCase().includes('premium');
                    const featureList = (plan.features || '').split(',').map(f => f.trim()).filter(Boolean);

                    return (
                        <div
                            key={plan.id}
                            style={{
                                background: isPremium ? 'linear-gradient(180deg, rgba(229, 9, 20, 0.1) 0%, var(--bg-secondary) 100%)' : 'var(--bg-secondary)',
                                border: isPremium ? '2px solid var(--accent)' : '1px solid var(--border)',
                                borderRadius: '20px',
                                padding: '36px 30px',
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'space-between',
                                position: 'relative',
                                boxShadow: isPremium ? '0 10px 30px rgba(229, 9, 20, 0.2)' : 'none',
                                transform: isPremium ? 'scale(1.03)' : 'none',
                                transition: 'transform 0.3s ease'
                            }}
                        >
                            {isPremium && (
                                <div style={{
                                    position: 'absolute',
                                    top: '-13px',
                                    left: '50%',
                                    transform: 'translateX(-50%)',
                                    background: 'var(--accent)',
                                    color: 'white',
                                    padding: '4px 16px',
                                    borderRadius: '20px',
                                    fontSize: '11px',
                                    fontWeight: 800,
                                    letterSpacing: '0.5px',
                                    textTransform: 'uppercase'
                                }}>
                                    Most Popular
                                </div>
                            )}

                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                    <h3 style={{ margin: 0, fontSize: '24px', fontWeight: 800 }}>{plan.name}</h3>
                                    {isCurrent && (
                                        <span style={{
                                            background: 'rgba(46, 204, 113, 0.2)',
                                            color: '#2ecc71',
                                            padding: '4px 10px',
                                            borderRadius: '12px',
                                            fontSize: '11px',
                                            fontWeight: 700
                                        }}>
                                            Current Plan
                                        </span>
                                    )}
                                </div>

                                <div style={{ marginBottom: '24px' }}>
                                    <span style={{ fontSize: '36px', fontWeight: 800 }}>${plan.price}</span>
                                    <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}> / month</span>
                                </div>

                                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px', marginBottom: '30px' }}>
                                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '14px', letterSpacing: '0.5px' }}>
                                        What's included:
                                    </p>
                                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {featureList.map((feat, idx) => (
                                            <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '14px', lineHeight: 1.4 }}>
                                                <div style={{
                                                    background: isPremium ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
                                                    borderRadius: '50%',
                                                    padding: '3px',
                                                    marginTop: '2px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    flexShrink: 0
                                                }}>
                                                    <Check size={11} color="white" />
                                                </div>
                                                <span>{feat}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>

                            <button
                                onClick={() => handleSelectPlan(plan)}
                                disabled={isCurrent}
                                className={isPremium ? "btn-primary" : "btn-secondary"}
                                style={{
                                    width: '100%',
                                    padding: '14px',
                                    fontSize: '15px',
                                    fontWeight: 700,
                                    borderRadius: '10px',
                                    cursor: isCurrent ? 'default' : 'pointer',
                                    opacity: isCurrent ? 0.6 : 1
                                }}
                            >
                                {isCurrent ? 'Current Plan Active' : (plan.price === 0 ? 'Default Plan' : `Get ${plan.name}`)}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Value Props & Guarantees */}
            <div style={{
                background: 'var(--bg-secondary)',
                borderRadius: '20px',
                padding: '40px',
                border: '1px solid var(--border)',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '30px'
            }}>
                <div style={{ display: 'flex', gap: '16px' }}>
                    <ShieldCheck size={28} color="var(--accent-hover)" style={{ flexShrink: 0 }} />
                    <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: '16px', fontWeight: 700 }}>Secure Billing</h4>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '13px' }}>
                            256-bit encrypted card processing and simulated gateway support.
                        </p>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '16px' }}>
                    <Zap size={28} color="var(--accent-hover)" style={{ flexShrink: 0 }} />
                    <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: '16px', fontWeight: 700 }}>Instant Activation</h4>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '13px' }}>
                            Immediate entitlement activation with real-time AI supervisor alerts.
                        </p>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '16px' }}>
                    <Award size={28} color="var(--accent-hover)" style={{ flexShrink: 0 }} />
                    <div>
                        <h4 style={{ margin: '0 0 6px', fontSize: '16px', fontWeight: 700 }}>Cancel Anytime</h4>
                        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '13px' }}>
                            Manage renewal anytime directly from your profile settings with one click.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Subscription;
