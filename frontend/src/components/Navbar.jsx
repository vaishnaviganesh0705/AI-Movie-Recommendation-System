import React, { useState, useEffect } from 'react';
import { Search, Bell, Sparkles, User, Menu, Bookmark, CheckCheck } from 'lucide-react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import './Navbar.css';
import ChatModal from './ChatModal';

const Navbar = () => {
    const navigate = useNavigate();
    const [isAIChatOpen, setIsAIChatOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [showNotif, setShowNotif] = useState(false);

    useEffect(() => {
        let isCancelled = false;

        const fetchNotifs = async () => {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) {
                setNotifications([]);
                return;
            }
            try {
                const res = await api.get('/notifications');
                if (!isCancelled && Array.isArray(res.data)) {
                    setNotifications(res.data);
                }
            } catch (e) {
                // If 401, clear notifications so we don't display stale data
                if (e.response?.status === 401 && !isCancelled) {
                    setNotifications([]);
                }
            }
        };

        fetchNotifs();
        const interval = setInterval(fetchNotifs, 20000);
        return () => {
            isCancelled = true;
            clearInterval(interval);
        };
    }, []);

    const markAsRead = async (id) => {
        try {
            await api.put(`/notifications/${id}/read`);
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
        } catch (e) {
            console.error("Failed to mark notification read", e);
        }
    };

    const markAllAsRead = async () => {
        try {
            await api.put('/notifications/read-all');
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        } catch (e) {
            console.error("Failed to mark all read", e);
        }
    };

    const unreadCount = notifications.filter(n => !n.is_read).length;

    return (
        <header className="ott-navbar glass-hover">
            <div className="nav-left">
                <Link to="/home" className="nav-brand">
                    STREAM<span>HUB</span>
                </Link>

                <nav className="nav-links desktop-only">
                    <NavLink to="/home" className={({ isActive }) => isActive ? "active-link" : ""}>Home</NavLink>
                    <NavLink to="/movies" className={({ isActive }) => isActive ? "active-link" : ""}>Movies</NavLink>
                    <NavLink to="/tv" className={({ isActive }) => isActive ? "active-link" : ""}>TV Shows</NavLink>
                    <NavLink to="/music" className={({ isActive }) => isActive ? "active-link" : ""}>Music</NavLink>
                </nav>
            </div>

            <div className="nav-right">
                <div className="nav-ai-button desktop-only" onClick={() => setIsAIChatOpen(true)}>
                    <Sparkles size={16} /> Ask StreamHub AI
                </div>

                <div className="nav-icon-group">
                    <button className="icon-btn search-btn" onClick={() => navigate('/search')} title="Search">
                        <Search size={22} />
                    </button>

                    {/* Notifications Dropdown */}
                    <div style={{ position: 'relative' }}>
                        <button className="icon-btn bell-btn desktop-only" onClick={() => setShowNotif(!showNotif)} title="Notifications">
                            <Bell size={22} />
                            {unreadCount > 0 && <span className="notification-dot"></span>}
                        </button>

                        {showNotif && (
                            <div style={{
                                position: 'absolute',
                                top: '100%',
                                right: '0',
                                width: '320px',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border)',
                                borderRadius: '12px',
                                padding: '14px',
                                zIndex: 1000,
                                maxHeight: '420px',
                                overflowY: 'auto',
                                boxShadow: 'var(--glass-shadow)',
                                backdropFilter: 'blur(16px)'
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '0 0 12px', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
                                    <h4 style={{ margin: 0, fontSize: '15px' }}>Notifications ({unreadCount})</h4>
                                    {unreadCount > 0 && (
                                        <button
                                            onClick={markAllAsRead}
                                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', color: 'var(--accent)', cursor: 'pointer' }}
                                        >
                                            <CheckCheck size={14} /> Mark all read
                                        </button>
                                    )}
                                </div>

                                {notifications.length === 0 ? (
                                    <p style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>
                                        No notifications yet.
                                    </p>
                                ) : (
                                    notifications.map(n => (
                                        <div
                                            key={n.id}
                                            onClick={() => !n.is_read && markAsRead(n.id)}
                                            style={{
                                                padding: '10px',
                                                borderBottom: '1px solid var(--border)',
                                                cursor: 'pointer',
                                                background: n.is_read ? 'transparent' : 'rgba(155, 92, 255, 0.08)',
                                                borderRadius: '6px',
                                                marginBottom: '6px'
                                            }}
                                        >
                                            <div style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px', color: n.is_read ? 'var(--text-primary)' : 'var(--accent-hover)' }}>
                                                {n.title}
                                            </div>
                                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                                                {n.message}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    <button className="icon-btn" onClick={() => navigate('/watchlist')} title="Watchlist">
                        <Bookmark size={20} />
                    </button>

                    <div className="profile-btn" onClick={() => navigate('/profile')} title="My Profile">
                        <User size={18} />
                    </div>

                    <button className="icon-btn mobile-menu-btn mobile-only" onClick={() => navigate('/movies')}>
                        <Menu size={24} />
                    </button>
                </div>
            </div>

            {isAIChatOpen && <ChatModal onClose={() => setIsAIChatOpen(false)} />}
        </header>
    );
};

export default Navbar;
