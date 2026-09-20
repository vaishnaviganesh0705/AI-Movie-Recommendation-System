import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, Send, Sparkles, Bot, User as UserIcon, RotateCcw } from 'lucide-react';
import api from '../services/api';

const QUICK_PROMPTS = [
    "Recommend Tamil comedy movies under 2 hours",
    "Show top sci-fi movies",
    "What subscription plans are available?",
    "Recommend some relaxing songs",
    "How do I manage my profile?"
];

const ChatModal = ({ onClose }) => {
    const [messages, setMessages] = useState([
        {
            text: "Hello! I am the StreamHub Multi-Agent Supervisor. I route your queries across specialized agents: Movie Discovery, TV Curator, Music DJ, Subscription & Billing, Profile Manager, and Content Planner. How can I help you today?",
            sender: 'ai',
            agent: 'Supervisor Agent'
        }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    const handleSend = async (messageText = null) => {
        const queryText = (messageText || input).trim();
        if (!queryText) return;

        const updatedMessages = [...messages, { text: queryText, sender: 'user' }];
        setMessages(updatedMessages);
        setInput('');
        setIsLoading(true);

        try {
            // Build conversation history for the multi-agent context agent
            const historyPayload = updatedMessages.map(m => ({
                sender: m.sender || 'user',
                text: m.text || '',
                role: m.sender === 'user' ? 'user' : 'assistant',
                content: m.text || ''
            }));

            const res = await api.post('/chat', {
                prompt: queryText,
                history: historyPayload
            });

            setMessages(prev => [
                ...prev,
                {
                    text: res.data.response,
                    sender: 'ai',
                    agent: res.data.agent || 'AI Assistant',
                    data: res.data.data
                }
            ]);
        } catch (err) {
            console.error('Chat error', err);
            let rawDetail = err.response?.data?.detail;
            let errDetail = "Network Error";
            if (typeof rawDetail === 'string') {
                errDetail = rawDetail;
            } else if (Array.isArray(rawDetail)) {
                errDetail = rawDetail.map(e => e.msg || e.loc?.join('.') || JSON.stringify(e)).join(', ');
            } else if (rawDetail && typeof rawDetail === 'object') {
                errDetail = JSON.stringify(rawDetail);
            } else if (err.message) {
                errDetail = err.message;
            }

            setMessages(prev => [
                ...prev,
                {
                    text: `Sorry, I encountered an issue communicating with the agent network: ${errDetail}`,
                    sender: 'ai',
                    agent: 'System Alert'
                }
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleResetChat = () => {
        setMessages([
            {
                text: "Memory cleared. What would you like to explore next?",
                sender: 'ai',
                agent: 'Supervisor Agent'
            }
        ]);
    };

    const renderMessageContent = (text) => {
        if (!text) return null;
        // Match Markdown image syntax: ![alt](url)
        const parts = text.split(/!\[([^\]]*)\]\((.*?)\)/g);
        const elements = [];

        for (let i = 0; i < parts.length; i++) {
            if (i % 3 === 0) {
                // Strip bold markers and format clean lines
                let cleanText = parts[i];
                elements.push(<span key={i}>{cleanText}</span>);
            } else if (i % 3 === 1) {
                const imgAlt = parts[i];
                const imgUrl = parts[i + 1];
                elements.push(
                    <div key={`img-box-${i}`} style={{ display: 'inline-block', margin: '6px 8px 6px 0', verticalAlign: 'middle' }}>
                        <img
                            src={imgUrl}
                            alt={imgAlt}
                            style={{ height: '75px', borderRadius: '6px', boxShadow: '0 4px 8px rgba(0,0,0,0.5)', objectFit: 'cover' }}
                        />
                    </div>
                );
            }
        }
        return elements;
    };

    return createPortal(
        <div style={{
            position: 'fixed',
            bottom: '25px',
            right: '25px',
            width: '420px',
            maxWidth: 'calc(100vw - 32px)',
            height: '620px',
            maxHeight: 'calc(100vh - 50px)',
            background: 'var(--bg-secondary)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '24px',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 25px 60px rgba(0,0,0,0.85)',
            zIndex: 99999,
            overflow: 'hidden'
        }}>
            {/* Header */}
            <div style={{
                padding: '16px 20px',
                background: 'linear-gradient(135deg, #181824, #0f0f16)',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                        background: 'var(--accent)',
                        padding: '8px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 0 12px rgba(229, 9, 20, 0.4)'
                    }}>
                        <Sparkles size={18} color="white" />
                    </div>
                    <div>
                        <h3 style={{ margin: 0, fontSize: '15px', color: 'white', fontWeight: 700 }}>StreamHub AI Hub</h3>
                        <span style={{ fontSize: '11px', color: '#2ecc71', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#2ecc71', display: 'inline-block' }} />
                            Multi-Agent Network Active
                        </span>
                    </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                        onClick={handleResetChat}
                        title="Clear conversation context"
                        style={{
                            background: 'rgba(255,255,255,0.08)',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            padding: '6px',
                            borderRadius: '50%',
                            display: 'flex'
                        }}
                    >
                        <RotateCcw size={15} />
                    </button>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'rgba(255,255,255,0.08)',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            padding: '6px',
                            borderRadius: '50%',
                            display: 'flex'
                        }}
                    >
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Message Area */}
            <div style={{
                flex: 1,
                padding: '18px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                background: 'var(--bg-primary)'
            }}>
                {messages.map((m, i) => (
                    <div
                        key={i}
                        style={{
                            alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '88%',
                            display: 'flex',
                            gap: '10px',
                            alignItems: 'flex-start',
                            flexDirection: m.sender === 'user' ? 'row-reverse' : 'row'
                        }}
                    >
                        <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            flexShrink: 0,
                            background: m.sender === 'user' ? 'var(--bg-tertiary)' : 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginTop: '2px'
                        }}>
                            {m.sender === 'user' ? <UserIcon size={14} color="white" /> : <Bot size={14} color="white" />}
                        </div>

                        <div>
                            {/* Agent Badge for AI messages */}
                            {m.sender === 'ai' && m.agent && (
                                <div style={{
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    color: 'var(--accent-hover)',
                                    marginBottom: '4px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}>
                                    <span>🤖</span> {m.agent}
                                </div>
                            )}

                            <div style={{
                                background: m.sender === 'user' ? 'var(--accent)' : 'var(--bg-secondary)',
                                color: 'white',
                                padding: '12px 16px',
                                borderRadius: m.sender === 'user' ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
                                fontSize: '13.5px',
                                lineHeight: '1.55',
                                wordBreak: 'break-word',
                                border: '1px solid rgba(255,255,255,0.06)',
                                whiteSpace: 'pre-wrap'
                            }}>
                                {m.sender === 'ai' ? renderMessageContent(m.text) : m.text}
                            </div>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '10px', alignItems: 'flex-start', maxWidth: '88%' }}>
                        <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            background: 'var(--accent)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            marginTop: '2px'
                        }}>
                            <Bot size={14} color="white" />
                        </div>
                        <div style={{
                            background: 'var(--bg-secondary)',
                            padding: '12px 16px',
                            borderRadius: '4px 18px 18px 18px',
                            fontSize: '13px',
                            color: 'var(--text-secondary)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-hover)', animation: 'pulse 1s infinite' }} />
                            Consulting agent network & TMDB...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Quick Suggestions Chips */}
            <div style={{
                padding: '8px 14px',
                background: 'var(--bg-secondary)',
                borderTop: '1px solid rgba(255,255,255,0.06)',
                display: 'flex',
                gap: '8px',
                overflowX: 'auto',
                whiteSpace: 'nowrap'
            }}>
                {QUICK_PROMPTS.map((prompt, idx) => (
                    <button
                        key={idx}
                        onClick={() => handleSend(prompt)}
                        disabled={isLoading}
                        style={{
                            background: 'rgba(255,255,255,0.06)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: 'var(--text-secondary)',
                            padding: '4px 10px',
                            borderRadius: '12px',
                            fontSize: '11px',
                            cursor: 'pointer',
                            flexShrink: 0
                        }}
                    >
                        {prompt}
                    </button>
                ))}
            </div>

            {/* Input Area */}
            <div style={{
                padding: '12px 16px',
                background: 'var(--bg-secondary)',
                borderTop: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                gap: '8px',
                alignItems: 'center'
            }}>
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSend()}
                    placeholder="Ask movie, tv, music or subscription agents..."
                    disabled={isLoading}
                    style={{
                        flex: 1,
                        padding: '11px 16px',
                        borderRadius: '20px',
                        border: '1px solid rgba(255,255,255,0.15)',
                        background: 'var(--bg-primary)',
                        color: 'white',
                        outline: 'none',
                        fontSize: '13px'
                    }}
                />
                <button
                    onClick={() => handleSend()}
                    disabled={isLoading || !input.trim()}
                    style={{
                        background: input.trim() ? 'var(--accent)' : 'var(--bg-tertiary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: input.trim() && !isLoading ? 'pointer' : 'default',
                        flexShrink: 0
                    }}
                >
                    <Send size={16} />
                </button>
            </div>
        </div>,
        document.body
    );
};

export default ChatModal;
