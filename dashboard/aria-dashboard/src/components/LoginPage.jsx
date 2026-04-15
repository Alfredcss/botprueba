import React, { useState } from 'react'
import bgImage from '../assets/background.png'
import logoImage from '../assets/logo.png'

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');

  .login-root {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    font-family: 'DM Sans', sans-serif;
    background: #1a1035;
  }

  .login-bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 80% 60% at 50% 100%, #3d1f6e 0%, transparent 70%),
      radial-gradient(ellipse 60% 40% at 20% 80%, #5a2d82 0%, transparent 60%),
      radial-gradient(ellipse 50% 40% at 80% 70%, #2a1560 0%, transparent 60%),
      linear-gradient(180deg, #0d0820 0%, #1a1035 40%, #2d1558 70%, #3d1f6e 100%);
    z-index: 1;
    opacity: 0.75;
  }

  .login-bg-lavender {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 45%;
    background:
      radial-gradient(ellipse 120% 100% at 50% 100%, #3f4ea0ff 0%, #4a2080 30%, transparent 70%);
    z-index: 2;
  }

  .login-stars {
    position: absolute;
    inset: 0;
    z-index: 3;
background-image:
      radial-gradient(1px 1px at 15% 10%, rgba(255,255,255,0.8) 0%, transparent 100%),
      radial-gradient(1px 1px at 35% 5%, rgba(255,255,255,0.6) 0%, transparent 100%),
      radial-gradient(1px 1px at 55% 15%, rgba(255,255,255,1) 0%, transparent 100%),
      radial-gradient(1.5px 1.5px at 75% 8%, rgba(255,255,255,0.7) 0%, transparent 100%),
      radial-gradient(1px 1px at 90% 20%, rgba(255,255,255,0.5) 0%, transparent 100%),
      radial-gradient(1px 1px at 25% 25%, rgba(255,255,255,0.4) 0%, transparent 100%),
      radial-gradient(1px 1px at 65% 12%, rgba(255,255,255,0.6) 0%, transparent 100%),
      radial-gradient(1.5px 1.5px at 45% 22%, rgba(255,255,255,0.5) 0%, transparent 100%);

    
  }




  .login-card {
    position: relative;
    z-index: 10;
    width: 100%;
    max-width: 440px;
    margin: 0 1.5rem;
    background: rgba(37, 17, 69, 0.34);
    backdrop-filter: blur(5px);
    -webkit-backdrop-filter: blur(5px);
    border: 1px solid rgba(150, 100, 220, 0.25);
    border-radius: 24px;
    padding: 2.5rem 2rem;
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.08);
  }

  .login-icon-wrap {
    display: flex;
    justify-content: center;
  }

  .login-icon-circle {
    width: 120px;
    height: 120px;
  }

  .login-title {
    text-align: center;
    font-size: 1.85rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0 0 0.5rem;
    letter-spacing: -0.02em;
  }

  .login-subtitle {
    text-align: center;
    font-size: 0.875rem;
    color: rgba(190, 170, 230, 0.75);
    margin: 0 0 2rem;
    line-height: 1.5;
  }

  .login-field {
    margin-bottom: 1rem;
  }

  .login-field label {
    display: block;
    font-size: 0.78rem;
    font-weight: 500;
    color: rgba(200, 180, 240, 0.7);
    margin-bottom: 0.4rem;
    letter-spacing: 0.01em;
  }

  .login-field-inner {
    position: relative;
  }

  .login-field input {
    width: 100%;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(150, 100, 220, 0.2);
    border-radius: 12px;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    font-family: 'DM Sans', sans-serif;
    color: rgba(255, 255, 255, 0.9);
    outline: none;
    transition: border-color 0.2s, background 0.2s;
  }

  .login-field input::placeholder {
    color: rgba(180, 160, 220, 0.35);
  }

  .login-field input:focus {
    border-color: rgba(160, 110, 255, 0.6);
    background: rgba(255, 255, 255, 0.09);
  }

  .login-field input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .eye-btn {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    color: rgba(180, 150, 240, 0.5);
    transition: color 0.2s;
  }

  .eye-btn:hover { color: rgba(200, 170, 255, 0.8); }

  .login-error {
    background: rgba(220, 60, 60, 0.12);
    border: 1px solid rgba(220, 60, 60, 0.25);
    border-radius: 10px;
    padding: 0.6rem 0.85rem;
    font-size: 0.83rem;
    color: #f87171;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .login-btn {
    width: 100%;
    padding: 0.85rem 1rem;
    background: #ffffff;
    color: #1a0d40;
    border: none;
    border-radius: 50px;
    font-size: 0.95rem;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    letter-spacing: 0.01em;
    transition: background 0.2s, transform 0.15s, opacity 0.2s;
  }

  .login-btn:hover:not(:disabled) {
    background: #f0eaff;
    transform: translateY(-1px);
  }

  .login-btn:active:not(:disabled) {
    transform: translateY(0);
  }

  .login-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  @keyframes spin-inline {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .spin {
    display: inline-block;
    animation: spin-inline 0.8s linear infinite;
  }
`

export default function LoginPage({ onLogin, loading, error }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email || !password) return
    await onLogin(email, password)
  }

  return (
    <>
      <style>{styles}</style>
      <div className="login-root">

        {/* 1. bgImage — capa más abajo, difuminada y semitransparente */}
        <div style={{
        backgroundSize: '80%',
          inset: 0,
          backgroundImage: `url(${bgImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center 20%',
          backgroundRepeat: 'no-repeat',
          filter: 'blur(3px)',
          transform: 'scale(1.05)',
          zIndex: 0,
          opacity: 0.35          // ← sube para que se vea más, baja para que sea más sutil
        }} />

        {/* 2. Gradientes morados encima */}
        <div className="login-bg" />
        <div className="login-bg-lavender" />
        <div className="login-stars" />

        {/* 3. Card del login */}
        <div className="login-card">
          <div className="login-icon-wrap">
            <div className="login-icon-circle">
              <img
                src={logoImage}
                alt="Logo"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
          </div>

          <h1 className="login-title">¡bienvenido!</h1>
          <p className="login-subtitle">
            Inicia sesión para acceder a tus leads,<br />
            Da el 121%
          </p>

          <form onSubmit={handleSubmit}>
            <div className="login-field">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                autoComplete="email"
                disabled={loading}
              />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Password</label>
              <div className="login-field-inner">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  disabled={loading}
                  style={{ paddingRight: '2.75rem' }}
                />
                <button
                  type="button"
                  className="eye-btn"
                  onClick={() => setShowPassword(v => !v)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {error && (
              <div className="login-error">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                {error}
              </div>
            )}

            <button className="login-btn" type="submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="spin" style={{ display: 'inline-block', marginRight: 8 }}>⟳</span>
                  Signing in...
                </>
              ) : 'Log In'}
            </button>
          </form>
        </div>
      </div>
    </>
  )
}
