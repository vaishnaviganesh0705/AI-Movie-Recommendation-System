import React from 'react';
import { useLocation } from 'react-router-dom';

const Placeholder = () => {
    const location = useLocation();
    const title = location.pathname.substring(1).toUpperCase();

    return (
        <div style={{ padding: '120px 4%', color: 'var(--text-primary)', textAlign: 'center', minHeight: '80vh' }}>
            <h1 style={{ fontSize: '42px', marginBottom: '20px', textTransform: 'capitalize' }}>{title}</h1>
            <p style={{ color: 'var(--text-secondary)' }}>This section is currently under development. Content will be available soon.</p>
        </div>
    );
};

export default Placeholder;
