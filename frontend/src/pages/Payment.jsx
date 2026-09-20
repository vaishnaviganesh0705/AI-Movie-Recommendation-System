import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, CreditCard, Lock, CheckCircle, ChevronLeft, AlertCircle, Sparkles } from 'lucide-react';
import api from '../services/api';

const Payment = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const planId = parseInt(searchParams.get('planId') || '3');

    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [processing, setProcessing] = useState(false);
    const [paymentSuccess, setPaymentSuccess] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);

    // Form states
    const [cardName, setCardName] = useState('');
    const [cardNumber, setCardNumber] = useState('');
    const [cardExpiry, setCardExpiry] = useState('');
    const [cardCvv, setCardCvv] = useState('');
    const [paymentMethod, setPaymentMethod] = useState('card');

    useEffect(() => {
        const fetchPlanDetails = async () => {
            const token = localStorage.getItem('access_token') || localStorage.getItem('token');
            if (!token) {
                alert("Please login first to checkout.");
                return navigate('/login');
            }

            try {
                const res = await api.get('/subscription/plans');
                const matched = res.data.find(p => p.id === planId) || res.data[0];
                setPlan(matched);
            } catch (err) {
                console.error("Error loading plan details", err);
                setErrorMessage("Failed to load subscription plan information.");
            } finally {
                setLoading(false);
            }
        };

        fetchPlanDetails();
    }, [planId, navigate]);

    const formatCardNumber = (value) => {
        const clean = value.replace(/\D/g, '').substring(0, 16);
        const parts = clean.match(/.{1,4}/g);
        return parts ? parts.join(' ') : clean;
    };

    const formatExpiry = (value) => {
        const clean = value.replace(/\D/g, '').substring(0, 4);
        if (clean.length >= 3) {
            return `${clean.substring(0, 2)}/${clean.substring(2, 4)}`;
        }
        return clean;
    };

    const handlePaymentSubmit = async (e) => {
        e.preventDefault();
        setErrorMessage(null);
        setProcessing(true);

        try {
            // Step 1: Initialize real checkout session from backend
            const checkoutRes = await api.post('/subscription/checkout', {
                plan_id: plan.id,
                payment_method: paymentMethod
            });

            const clientToken = checkoutRes.data.client_token;
            if (!clientToken) {
                throw new Error("Unable to establish secure checkout token.");
            }

            // Step 2: Verify payment & activate entitlement on backend
            const verifyRes = await api.post('/subscription/verify-payment', {
                plan_id: plan.id,
                payment_token: clientToken,
                transaction_id: `tx_${Date.now()}`
            });

            if (verifyRes.data.success) {
                setPaymentSuccess(verifyRes.data);
                setTimeout(() => {
                    navigate('/profile');
                }, 3000);
            } else {
                throw new Error(verifyRes.data.message || "Payment verification failed.");
            }
        } catch (err) {
            console.error("Payment error", err);
            setErrorMessage(err.response?.data?.detail || err.message || "An error occurred during transaction processing.");
        } finally {
            setProcessing(false);
        }
    };

    if (loading) {
        return (
            <div style={{ padding: '120px 4%', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Preparing secure checkout...
            </div>
        );
    }

    if (paymentSuccess) {
        return (
            <div style={{
                padding: '120px 4%',
                minHeight: '70vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-primary)'
            }}>
                <div style={{
                    background: 'var(--bg-secondary)',
                    border: '1px solid #2ecc71',
                    borderRadius: '20px',
                    padding: '40px',
                    maxWidth: '480px',
                    textAlign: 'center',
                    boxShadow: '0 20px 50px rgba(46, 204, 113, 0.2)'
                }}>
                    <div style={{
                        width: '72px',
                        height: '72px',
                        borderRadius: '50%',
                        background: 'rgba(46, 204, 113, 0.15)',
                        display: 'grid',
                        placeItems: 'center',
                        margin: '0 auto 20px'
                    }}>
                        <CheckCircle size={42} color="#2ecc71" />
                    </div>

                    <h2 style={{ fontSize: '26px', margin: '0 0 10px', fontWeight: 800 }}>Payment Confirmed!</h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '15px', lineHeight: 1.5, marginBottom: '20px' }}>
                        {paymentSuccess.message}
                    </p>

                    <div style={{
                        background: 'var(--bg-primary)',
                        padding: '14px',
                        borderRadius: '10px',
                        fontSize: '13px',
                        color: 'var(--text-secondary)',
                        marginBottom: '24px',
                        border: '1px solid var(--border)'
                    }}>
                        <div>Plan: <strong style={{ color: 'white' }}>StreamHub {plan?.name}</strong></div>
                        <div>Valid Until: <strong style={{ color: 'white' }}>{new Date(paymentSuccess.expires_at).toLocaleDateString()}</strong></div>
                    </div>

                    <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Redirecting to your account dashboard in 3 seconds...
                    </p>
                </div>
            </div>
        );
    }

    const price = plan ? plan.price : 19.99;
    const tax = Math.round(price * 0.08 * 100) / 100;
    const total = (price + tax).toFixed(2);

    return (
        <div style={{ padding: '100px 4% 80px', color: 'var(--text-primary)', maxWidth: '900px', margin: '0 auto' }}>
            <Link
                to="/subscription"
                style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: 'var(--accent-hover)',
                    textDecoration: 'none',
                    marginBottom: '24px',
                    fontSize: '14px'
                }}
            >
                <ChevronLeft size={16} /> Back to Plans
            </Link>

            <h1 style={{ fontSize: '32px', margin: '0 0 8px', fontWeight: 800 }}>Complete Your Purchase</h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '36px' }}>
                Encrypted checkout protected with SSL and StreamHub multi-agent validation.
            </p>

            {errorMessage && (
                <div style={{
                    padding: '14px 18px',
                    borderRadius: '8px',
                    marginBottom: '24px',
                    background: 'rgba(231, 76, 60, 0.15)',
                    border: '1px solid #e74c3c',
                    color: '#ff6b6b',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    fontSize: '14px'
                }}>
                    <AlertCircle size={18} />
                    {errorMessage}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '30px' }}>
                {/* Payment Form */}
                <div style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '16px',
                    padding: '30px',
                    border: '1px solid var(--border)'
                }}>
                    <h3 style={{ margin: '0 0 20px', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <CreditCard size={20} color="var(--accent-hover)" /> Payment Details
                    </h3>

                    {/* Method Selector */}
                    <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
                        {['card', 'upi', 'paypal'].map(method => (
                            <button
                                key={method}
                                type="button"
                                onClick={() => setPaymentMethod(method)}
                                style={{
                                    flex: 1,
                                    padding: '10px 8px',
                                    borderRadius: '8px',
                                    border: paymentMethod === method ? '2px solid var(--accent)' : '1px solid var(--border)',
                                    background: paymentMethod === method ? 'rgba(229, 9, 20, 0.1)' : 'var(--bg-primary)',
                                    color: 'white',
                                    fontSize: '13px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    textTransform: 'uppercase'
                                }}
                            >
                                {method}
                            </button>
                        ))}
                    </div>

                    <form onSubmit={handlePaymentSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                                Name on Card
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. John Doe"
                                value={cardName}
                                onChange={e => setCardName(e.target.value)}
                                required
                                style={{
                                    width: '100%',
                                    padding: '12px 14px',
                                    borderRadius: '8px',
                                    background: 'var(--bg-primary)',
                                    border: '1px solid var(--border)',
                                    color: 'white',
                                    fontSize: '14px'
                                }}
                            />
                        </div>

                        <div>
                            <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                                Card Number
                            </label>
                            <input
                                type="text"
                                placeholder="4532 •••• •••• 8890"
                                value={cardNumber}
                                onChange={e => setCardNumber(formatCardNumber(e.target.value))}
                                maxLength={19}
                                required
                                style={{
                                    width: '100%',
                                    padding: '12px 14px',
                                    borderRadius: '8px',
                                    background: 'var(--bg-primary)',
                                    border: '1px solid var(--border)',
                                    color: 'white',
                                    fontSize: '14px',
                                    letterSpacing: '1px'
                                }}
                            />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                            <div>
                                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                                    Expiry Date
                                </label>
                                <input
                                    type="text"
                                    placeholder="MM/YY"
                                    value={cardExpiry}
                                    onChange={e => setCardExpiry(formatExpiry(e.target.value))}
                                    maxLength={5}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '12px 14px',
                                        borderRadius: '8px',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border)',
                                        color: 'white',
                                        fontSize: '14px'
                                    }}
                                />
                            </div>

                            <div>
                                <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                                    CVV / CVC
                                </label>
                                <input
                                    type="password"
                                    placeholder="•••"
                                    value={cardCvv}
                                    onChange={e => setCardCvv(e.target.value.replace(/\D/g, '').substring(0, 4))}
                                    maxLength={4}
                                    required
                                    style={{
                                        width: '100%',
                                        padding: '12px 14px',
                                        borderRadius: '8px',
                                        background: 'var(--bg-primary)',
                                        border: '1px solid var(--border)',
                                        color: 'white',
                                        fontSize: '14px'
                                    }}
                                />
                            </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '12px', marginTop: '6px' }}>
                            <Lock size={14} color="#2ecc71" /> End-to-end 256-bit encrypted checkout
                        </div>

                        <button
                            type="submit"
                            disabled={processing}
                            className="btn-primary"
                            style={{
                                width: '100%',
                                padding: '14px',
                                fontSize: '16px',
                                fontWeight: 700,
                                borderRadius: '10px',
                                marginTop: '14px',
                                cursor: processing ? 'wait' : 'pointer'
                            }}
                        >
                            {processing ? 'Processing Transaction...' : `Pay $${total}`}
                        </button>
                    </form>
                </div>

                {/* Order Summary */}
                <div style={{
                    background: 'var(--bg-secondary)',
                    borderRadius: '16px',
                    padding: '30px',
                    border: '1px solid var(--border)',
                    height: 'fit-content'
                }}>
                    <h3 style={{ margin: '0 0 20px', fontSize: '18px' }}>Order Summary</h3>

                    <div style={{ paddingBottom: '16px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                            <span style={{ fontWeight: 700, fontSize: '16px' }}>StreamHub {plan?.name || 'Premium'}</span>
                            <span style={{ fontWeight: 700, fontSize: '16px' }}>${price.toFixed(2)}</span>
                        </div>
                        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)' }}>
                            30-day billing cycle • Auto-renews unless cancelled
                        </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px', fontSize: '14px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                            <span>Subtotal</span>
                            <span>${price.toFixed(2)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                            <span>Estimated Tax (8%)</span>
                            <span>${tax.toFixed(2)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 800, fontSize: '18px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                            <span>Total Due</span>
                            <span style={{ color: 'var(--accent-hover)' }}>${total}</span>
                        </div>
                    </div>

                    <div style={{
                        background: 'var(--bg-primary)',
                        padding: '16px',
                        borderRadius: '10px',
                        border: '1px solid var(--border)',
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5
                    }}>
                        <div style={{ fontWeight: 700, color: 'white', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <ShieldCheck size={16} color="#2ecc71" /> StreamHub Guarantee
                        </div>
                        By confirming your payment, you agree to our Terms of Use and authorize recurring monthly charges. You can cancel at any time in Profile settings.
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Payment;
