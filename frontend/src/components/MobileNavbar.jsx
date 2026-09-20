import React from 'react';
import { Home, Search, Heart, User } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const MobileNavbar = () => {
    return (
        <nav style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            height: '70px',
            background: 'var(--bg-secondary)',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-around',
            alignItems: 'center',
            zIndex: 100
        }} className="mobile-nav-visible-only">
            {/* The mobile-nav-visible-only class will hide this on desktop using CSS (handled later) */}
            <NavLink to="/home" style={{ color: 'var(--text-secondary)' }}><Home size={24} /></NavLink>
            <NavLink to="/search" style={{ color: 'var(--text-secondary)' }}><Search size={24} /></NavLink>
            <NavLink to="/watchlist" style={{ color: 'var(--text-secondary)' }}><Heart size={24} /></NavLink>
            <NavLink to="/profile" style={{ color: 'var(--text-secondary)' }}><User size={24} /></NavLink>
        </nav>
    );
};

export default MobileNavbar;
