import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Shield, CreditCard, Camera, Check, AlertCircle, Sparkles, LogOut, Settings } from 'lucide-react';
import api from '../services/api';

const Profile = () => {
    const navigate = useNavigate();
    const [user, setUser] = useState({ name: '', email: '', avatar: '', bio: '', preferred_language: 'en' });
    const [subscription, setSubscription] = useState({
        status: 'none',
        plan_name: 'Free',
        plan_price: 0,
        features: 'Standard definition, Ad-supported, 1 screen',
        expires_at: null,
        auto_renew: false
    });
    const [languages, setLanguages] = useState([]);
    const [isEditing, setIsEditing] = useState(false);
    const [formData, setFormData] = useState({ name: '', bio: '', preferred_language: 'en' });
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfileData = async () => {
            setLoading(true);
            try {
                const token = localStorage.getItem('access_token') || localStorage.getItem('token');
                if (!token) {
                    return navigate('/login');
                }

                // 1) Fetch User details
                const userRes = await api.get('/users/me');
                setUser(userRes.data);
                setFormData({
                    name: userRes.data.name || '',
                    bio: userRes.data.bio || '',
                    preferred_language: userRes.data.preferred_language || 'en'
                });

                // 2) Fetch Subscription status
                try {
                    const subRes = await api.get('/subscription/status');
                    setSubscription(subRes.data);
                } catch (e) {
                    console.warn("Could not load subscription status", e);
                }

                // 3) Fetch TMDB supported languages
                try {
                    const langRes = await api.get('/tmdb/languages');
                    if (Array.isArray(langRes.data)) {
                        setLanguages(langRes.data);
                    }
                } catch (e) {
                    console.warn("Could not load languages", e);
                }
            } catch (err) {
                console.error('Error fetching profile', err);
                if (err.response?.status === 401) {
                    navigate('/login');
                }
            } finally {
                setLoading(false);
            }
        };

        fetchProfileData();
    }, [navigate]);

    const handleAvatarUpload = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (event) => {
            const base64Data = event.target.result;
            try {
                const res = await api.post('/users/avatar', {
                    avatar_base64: base64Data
                });
                setUser(prev => ({ ...prev, avatar: res.data.avatar }));
                setMessage({ type: 'success', text: 'Profile avatar updated successfully!' });
                setTimeout(() => setMessage(null), 3000);
            } catch (err) {
                console.error('Error uploading avatar', err);
                setMessage({ type: 'error', text: 'Failed to upload avatar image.' });
            }
        };
        reader.readAsDataURL(file);
    };

    const handleSaveProfile = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const res = await api.put('/users/me', {
                name: formData.name,
                bio: formData.bio,
                avatar: user.avatar,
                preferred_language: formData.preferred_language
            });
            setUser(res.data);
            setIsEditing(false);
            setMessage({ type: 'success', text: 'Profile updated successfully!' });
            setTimeout(() => setMessage(null), 3000);
        } catch (err) {
            console.error('Error updating profile', err);
            setMessage({ type: 'error', text: 'Failed to save changes.' });
        } finally {
            setSaving(false);
        }
    };

    const handleCancelAutoRenew = async () => {
        if (!window.confirm("Are you sure you want to cancel auto-renewal? You will keep access until your expiration date.")) return;
        try {
            const res = await api.post('/subscription/cancel');
            setSubscription(prev => ({ ...prev, auto_renew: false }));
            setMessage({ type: 'success', text: res.data.message || 'Auto-renewal cancelled.' });
            setTimeout(() => setMessage(null), 4000);
        } catch (err) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to cancel auto-renewal.' });
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('token');
        navigate('/login');
    };

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Loading profile...
            </div>
        );
    }

    const isActiveSub = subscription.status === 'active';

    return (
        <div style={{ padding: '100px 4% 80px', color: 'var(--text-primary)', maxWidth: '960px', margin: '0 auto' }}>
            <h1 style={{ fontSize: '32px', marginBottom: '30px', fontWeight: 800 }}>Account & Settings</h1>

            {message && (
                <div style={{
                    padding: '12px 18px',
                    borderRadius: '8px',
                    marginBottom: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    background: message.type === 'success' ? 'rgba(46, 204, 113, 0.15)' : 'rgba(231, 76, 60, 0.15)',
                    border: `1px solid ${message.type === 'success' ? '#2ecc71' : '#e74c3c'}`,
                    color: message.type === 'success' ? '#2ecc71' : '#ff6b6b',
                    fontSize: '14px'
                }}>
                    {message.type === 'success' ? <Check size={18} /> : <AlertCircle size={18} />}
                    {message.text}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
                {/* 1. Profile Overview Card */}
                <div style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '16px',
                    padding: '30px',
                    border: '1px solid var(--border)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '24px' }}>
                        <div style={{ position: 'relative' }}>
                            <div style={{
                                width: '84px',
                                height: '84px',
                                borderRadius: '50%',
                                background: user.avatar ? `url(${user.avatar}) center/cover` : 'var(--accent)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                overflow: 'hidden',
                                boxShadow: '0 4px 14px rgba(0,0,0,0.4)'
                            }}>
                                {!user.avatar && <User size={40} color="white" />}
                            </div>
                            <label style={{
                                position: 'absolute',
                                bottom: '0',
                                right: '0',
                                background: 'var(--accent)',
                                borderRadius: '50%',
                                width: '28px',
                                height: '28px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                boxShadow: '0 2px 6px rgba(0,0,0,0.5)'
                            }} title="Change Avatar">
                                <Camera size={14} color="white" />
                                <input type="file" onChange={handleAvatarUpload} style={{ display: 'none' }} accept="image/*" />
                            </label>
                        </div>

                        <div style={{ flex: 1 }}>
                            <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 700 }}>{user.name || 'StreamHub User'}</h2>
                            <p style={{ margin: '0 0 6px', color: 'var(--text-secondary)', fontSize: '14px' }}>{user.email}</p>
                            <span style={{
                                background: 'rgba(255,255,255,0.08)',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: 'var(--text-secondary)',
                                textTransform: 'uppercase'
                            }}>
                                {user.role || 'Member'}
                            </span>
                        </div>
                    </div>

                    {/* Edit Form / Details */}
                    {isEditing ? (
                        <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div>
                                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Full Name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        borderRadius: '8px',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border)',
                                        color: 'white',
                                        fontSize: '14px'
                                    }}
                                    required
                                />
                            </div>

                            <div>
                                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Bio</label>
                                <textarea
                                    value={formData.bio}
                                    onChange={e => setFormData({ ...formData, bio: e.target.value })}
                                    rows={2}
                                    placeholder="Tell us about your movie tastes..."
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        borderRadius: '8px',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border)',
                                        color: 'white',
                                        fontSize: '14px',
                                        resize: 'none'
                                    }}
                                />
                            </div>

                            <div>
                                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Preferred Language</label>
                                <select
                                    value={formData.preferred_language}
                                    onChange={e => setFormData({ ...formData, preferred_language: e.target.value })}
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        borderRadius: '8px',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border)',
                                        color: 'white',
                                        fontSize: '14px'
                                    }}
                                >
                                    {languages.map(l => (
                                        <option key={l.code} value={l.code} style={{ background: '#1c1c24' }}>
                                            {l.name} ({l.code})
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                                <button type="submit" className="btn-primary" disabled={saving} style={{ padding: '8px 18px', fontSize: '13px' }}>
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                                <button type="button" className="btn-secondary" onClick={() => setIsEditing(false)} style={{ padding: '8px 18px', fontSize: '13px' }}>
                                    Cancel
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div>
                            {user.bio && (
                                <p style={{ margin: '0 0 16px', color: 'var(--text-secondary)', fontSize: '14px', fontStyle: 'italic' }}>
                                    "{user.bio}"
                                </p>
                            )}
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid var(--border)', fontSize: '13px' }}>
                                <span style={{ color: 'var(--text-secondary)' }}>Preferred Language:</span>
                                <span>{languages.find(l => l.code === user.preferred_language)?.name || user.preferred_language || 'English'}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid var(--border)', fontSize: '13px' }}>
                                <span style={{ color: 'var(--text-secondary)' }}>Account Status:</span>
                                <span style={{ color: '#2ecc71', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Shield size={14} /> Verified Member
                                </span>
                            </div>
                            <button
                                onClick={() => setIsEditing(true)}
                                className="btn-secondary"
                                style={{ width: '100%', marginTop: '18px', padding: '10px', fontSize: '13px' }}
                            >
                                Edit Profile Details
                            </button>
                        </div>
                    )}
                </div>

                {/* 2. Subscription & Entitlement Card */}
                <div style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '16px',
                    padding: '30px',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                }}>
                    <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                            <div>
                                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Current Plan</span>
                                <h3 style={{ margin: '4px 0 0', fontSize: '24px', fontWeight: 800, color: isActiveSub ? 'var(--accent-hover)' : 'white' }}>
                                    StreamHub {subscription.plan_name}
                                </h3>
                            </div>
                            <span style={{
                                padding: '6px 12px',
                                borderRadius: '20px',
                                fontSize: '12px',
                                fontWeight: 700,
                                background: isActiveSub ? 'rgba(46, 204, 113, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                                border: `1px solid ${isActiveSub ? '#2ecc71' : 'var(--border)'}`,
                                color: isActiveSub ? '#2ecc71' : 'var(--text-secondary)'
                            }}>
                                {isActiveSub ? 'ACTIVE' : (subscription.status === 'expired' ? 'EXPIRED' : 'FREE TIER')}
                            </span>
                        </div>

                        <div style={{ fontSize: '28px', fontWeight: 800, margin: '14px 0 10px' }}>
                            ${subscription.plan_price || 0}
                            <span style={{ fontSize: '14px', fontWeight: 400, color: 'var(--text-secondary)' }}> / month</span>
                        </div>

                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: 1.5, marginBottom: '20px' }}>
                            {subscription.features || 'Standard streaming quality, limited library access.'}
                        </p>

                        {subscription.expires_at && (
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: '12px 16px',
                                borderRadius: '8px',
                                fontSize: '13px',
                                color: 'var(--text-secondary)',
                                marginBottom: '20px',
                                border: '1px solid var(--border)'
                            }}>
                                <div>Billing Renewal Date: <strong style={{ color: 'white' }}>{new Date(subscription.expires_at).toLocaleDateString()}</strong></div>
                                {subscription.auto_renew && (
                                    <span style={{ fontSize: '11px', color: '#2ecc71' }}>• Auto-renewal active</span>
                                )}
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <button
                            onClick={() => navigate('/subscription')}
                            className="btn-primary"
                            style={{ width: '100%', padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
                        >
                            <Sparkles size={16} />
                            {isActiveSub ? 'Change / Upgrade Plan' : 'Upgrade to Premium'}
                        </button>

                        {isActiveSub && subscription.auto_renew && (
                            <button
                                onClick={handleCancelAutoRenew}
                                style={{
                                    background: 'transparent',
                                    border: '1px solid var(--border)',
                                    color: 'var(--text-secondary)',
                                    padding: '8px',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                }}
                            >
                                Cancel Auto-Renewal
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Account Settings Footer */}
            <div style={{
                marginTop: '30px',
                background: 'var(--bg-secondary)',
                borderRadius: '16px',
                padding: '24px 30px',
                border: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px'
            }}>
                <div>
                    <h4 style={{ margin: '0 0 4px', fontSize: '16px' }}>Account Security</h4>
                    <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
                        Logged in with StreamHub Secure Token Session
                    </p>
                </div>

                <button
                    onClick={handleLogout}
                    style={{
                        background: 'rgba(231, 76, 60, 0.15)',
                        border: '1px solid rgba(231, 76, 60, 0.3)',
                        color: '#ff6b6b',
                        padding: '10px 20px',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                    }}
                >
                    <LogOut size={16} /> Sign Out
                </button>
            </div>
        </div>
    );
};

export default Profile;
