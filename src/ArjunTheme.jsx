import React, { useState, useEffect } from 'react';
import './arjun-theme.css';

/**
 * 1.5-Second Opening Animation (Gandiva Bow & Celestial Chakra)
 * Automatically unmounts after 1500ms for maximum efficiency.
 */
export function ArjunOpeningAnimation() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div className="arjun-splash-overlay" aria-hidden="true">
      <div className="relative flex items-center justify-center w-44 h-44">
        {/* Sacred Geometric Chakra Ring */}
        <svg
          className="absolute inset-0 w-full h-full opacity-25"
          style={{ animation: 'chakraSpin 8s linear infinite' }}
          viewBox="0 0 100 100"
        >
          <circle cx="50" cy="50" r="44" fill="none" stroke="#d4af37" strokeWidth="0.6" strokeDasharray="4 3" />
          <polygon
            points="50,8 61,36 91,36 67,54 76,83 50,65 24,83 33,54 9,36 39,36"
            fill="none"
            stroke="#d4af37"
            strokeWidth="0.5"
          />
        </svg>

        {/* Gandiva Bow & Astral Arrow */}
        <svg className="w-28 h-28" viewBox="0 0 120 120" fill="none">
          {/* Bow Arc */}
          <path
            className="arjun-bow-svg"
            d="M22 78 C38 26, 82 26, 98 78"
            stroke="url(#goldGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          {/* Bow String */}
          <path
            className="arjun-bow-svg"
            d="M22 78 L60 92 L98 78"
            stroke="#f3e5ab"
            strokeWidth="1.2"
            strokeOpacity="0.8"
          />
          {/* Astral Arrow */}
          <g className="arjun-arrow-svg">
            <line x1="60" y1="95" x2="60" y2="20" stroke="#38bdf8" strokeWidth="2.2" strokeLinecap="round" />
            <polygon points="60,12 54,24 60,21 66,24" fill="#f3e5ab" />
          </g>
          <defs>
            <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#9c7a44" />
              <stop offset="50%" stopColor="#f3e5ab" />
              <stop offset="100%" stopColor="#d4af37" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <h1 className="artifact-title text-3xl font-bold mt-3">ARJUN</h1>
      <p className="text-xs tracking-[0.3em] uppercase text-[#9c7a44] mt-1">
        Unwavering Focus • Celestial Defense
      </p>
    </div>
  );
}

/**
 * Sleek Artifact Container with Vedic Corner Filigree
 */
export function ArtifactCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`artifact-card p-6 ${className}`}>
      {/* Top-Left & Bottom-Right Artifact Corner Accents */}
      <svg className="absolute top-2 left-2 w-4 h-4 text-[#d4af37]/60 pointer-events-none" viewBox="0 0 24 24" fill="none">
        <path d="M2 22V6C2 3.79 3.79 2 6 2H22" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="6" cy="6" r="1.5" fill="currentColor" />
      </svg>
      <svg className="absolute bottom-2 right-2 w-4 h-4 text-[#d4af37]/60 pointer-events-none rotate-180" viewBox="0 0 24 24" fill="none">
        <path d="M2 22V6C2 3.79 3.79 2 6 2H22" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="6" cy="6" r="1.5" fill="currentColor" />
      </svg>

      {title && (
        <div className="mb-4 pb-3 border-b border-[#d4af37]/20 flex items-center justify-between">
          <div>
            <h3 className="artifact-title text-lg font-bold">{title}</h3>
            {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          </div>
          {/* Mini Chakra Emblem */}
          <span className="w-2 h-2 rotate-45 bg-[#d4af37] shadow-[0_0_8px_#d4af37]" />
        </div>
      )}
      {children}
    </div>
  );
}

/**
 * Arjun App Header (Replaces Aegis Header)
 */
export function ArjunHeader({ rightSlot }) {
  return (
    <header className="w-full border-b border-[#d4af37]/20 bg-[#090a0f]/90 backdrop-blur-md px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg border border-[#d4af37]/50 bg-[#12141f] flex items-center justify-center shadow-[0_0_15px_rgba(212,175,55,0.2)]">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none">
            <path d="M4 16C7 6 17 6 20 16" stroke="#d4af37" strokeWidth="2" strokeLinecap="round" />
            <line x1="12" y1="19" x2="12" y2="5" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" />
            <polygon points="12,3 9,7 15,7" fill="#f3e5ab" />
          </svg>
        </div>
        <div>
          <span className="artifact-title text-xl font-extrabold block leading-none">
            ARJUN
          </span>
          <span className="text-[10px] tracking-[0.22em] uppercase text-[#9c7a44]">
            Gandiva Protocol Active
          </span>
        </div>
      </div>
      <div>{rightSlot}</div>
    </header>
  );
}
