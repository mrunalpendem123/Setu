import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Sequence,
  Img,
  staticFile,
} from "remotion";

// ─────────────────────────────────────────────────────────────────────────────
// BRAND TOKENS (from Sarvam branding)
// ─────────────────────────────────────────────────────────────────────────────
const C = {
  navy:    "#0D1240",
  navyMid: "#1A2060",
  indigo:  "#3B4CB8",
  amber:   "#F59E0B",
  orange:  "#FF6B35",
  lavBg:   "#EDE9FF",
  lavMid:  "#C4B5FD",
  lavPink: "#F0ABFC",
  lavBlue: "#93C5FD",
  white:   "#FFFFFF",
  offW:    "#F8F7FF",
  gray:    "#F0EFF5",
  text:    "#0D0F1A",
  muted:   "#8884A0",
  green:   "#22C55E",
  greenD:  "#16A34A",
  meesho:  "#F43F5E",
};

// Easing helpers
const eOut  = (t: number) => 1 - Math.pow(1 - t, 3);
const eInOut = (t: number) => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2,3)/2;

function lerp(f: number, [a, b]: [number, number], [x, y]: [number, number], ease = eOut) {
  return interpolate(f, [a, b], [x, y], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// SARVAM LOGO — geometric lotus / gateway mandala
// 4 interlocking lens shapes + outer arc petals + center diamond
// ─────────────────────────────────────────────────────────────────────────────
const SarvamLogo: React.FC<{
  size: number;
  color?: string;
  spin?: boolean;
  frame?: number;
  opacity?: number;
}> = ({ size, color = C.white, spin = false, frame = 0, opacity = 1 }) => {
  const rot = spin ? (frame / 120) * 360 : 0;
  const r = 40; // outer radius
  const pw = 13; // petal half-width

  // A single petal: elongated lens pointing up
  const petal = `M0,${-r} C${pw},${-r*0.6} ${pw},${r*0.6} 0,${r} C${-pw},${r*0.6} ${-pw},${-r*0.6} 0,${-r} Z`;

  // Outer scallop arcs (8 lobes on the outside circle)
  const outerR = r + 7;
  const lobePoints = Array.from({length: 8}, (_, i) => {
    const a = (i * Math.PI * 2) / 8;
    return `${Math.sin(a)*outerR},${-Math.cos(a)*outerR}`;
  });

  return (
    <svg
      width={size}
      height={size}
      viewBox="-55 -55 110 110"
      style={{ transform: `rotate(${rot}deg)`, opacity }}
    >
      <g fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        {/* 4 interlocking lens/eye shapes at 0°/45°/90°/135° */}
        {[0, 45, 90, 135].map(angle => (
          <path key={angle} d={petal} transform={`rotate(${angle})`} opacity="0.9" />
        ))}
        {/* Outer ring */}
        <circle cx="0" cy="0" r={r + 3} strokeWidth="1.5" opacity="0.4" />
        {/* Inner ring */}
        <circle cx="0" cy="0" r="14" strokeWidth="1.2" opacity="0.5" />
      </g>
      {/* Center diamond */}
      <path
        d="M0,-7 L7,0 L0,7 L-7,0 Z"
        fill={color}
        opacity="0.9"
      />
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// BACKGROUNDS
// ─────────────────────────────────────────────────────────────────────────────

// Sarvam brand bg: dark navy → orange sunset gradient
const SarvamBg: React.FC = () => (
  <AbsoluteFill
    style={{
      background: `linear-gradient(180deg,
        ${C.navy} 0%,
        ${C.navyMid} 30%,
        ${C.indigo} 62%,
        #C47A2B 85%,
        ${C.amber} 100%)`,
    }}
  />
);

// App UI bg: soft lavender blobs like the Sarvam app / ChatGPT demo
const LavBg: React.FC<{ frame: number }> = ({ frame }) => {
  // Slowly drifting blobs
  const shift = Math.sin(frame / 80) * 4;
  return (
    <AbsoluteFill
      style={{
        background: C.lavBg,
        overflow: "hidden",
      }}
    >
      <div style={{
        position: "absolute", inset: 0,
        background: `
          radial-gradient(ellipse 70% 55% at ${20 + shift}% ${18 - shift*0.5}%, ${C.lavBlue}BB 0%, transparent 55%),
          radial-gradient(ellipse 60% 50% at ${78 - shift}% 15%, ${C.lavMid}99 0%, transparent 50%),
          radial-gradient(ellipse 65% 55% at 55% ${75 + shift*0.3}%, ${C.lavPink}88 0%, transparent 55%),
          radial-gradient(ellipse 50% 45% at ${10 + shift*0.5}% 75%, ${C.lavMid}77 0%, transparent 50%)
        `,
      }} />
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// GATEWAY DECORATIVE SHAPE (Mughal arch / dome motif from Sarvam branding)
// ─────────────────────────────────────────────────────────────────────────────
const Gateway: React.FC<{
  size: number;
  color: string;
  opacity?: number;
  scale?: number;
}> = ({ size, color, opacity = 1, scale = 1 }) => {
  // Pointed arch / lantern shape — like the Sarvam gateway branding element
  const s = size / 2;
  const path = `
    M ${s},0
    C ${s},${-s*0.3} ${s*0.75},${-s*0.85} 0,${-s}
    C ${-s*0.75},${-s*0.85} ${-s},${-s*0.3} ${-s},0
    C ${-s},${s*0.5} ${-s*0.5},${s*0.85} 0,${s}
    C ${s*0.5},${s*0.85} ${s},${s*0.5} ${s},0 Z
  `;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`${-s} ${-s} ${size} ${size}`}
      style={{ transform: `scale(${scale})`, opacity }}
    >
      <path d={path} fill={color} />
    </svg>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// PHONE FRAME
// ─────────────────────────────────────────────────────────────────────────────
const Phone: React.FC<{
  children: React.ReactNode;
  scale?: number;
  y?: number;
  opacity?: number;
}> = ({ children, scale = 1, y = 0, opacity = 1 }) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
    <div style={{
      width: 490, height: 1020,
      background: "#0A0A0A",
      borderRadius: 66,
      boxShadow: "0 50px 100px rgba(0,0,0,0.6), inset 0 0 0 1.5px #252525",
      overflow: "hidden",
      position: "relative",
      flexShrink: 0,
      transform: `scale(${scale}) translateY(${y}px)`,
      opacity,
    }}>
      {/* Dynamic Island */}
      <div style={{
        position: "absolute", top: 14, left: "50%",
        transform: "translateX(-50%)",
        width: 130, height: 38,
        background: "#0A0A0A", borderRadius: 24, zIndex: 999,
      }} />
      {/* Screen */}
      <div style={{
        position: "absolute", inset: 0,
        background: C.white, overflow: "hidden", borderRadius: 66,
      }}>
        {children}
      </div>
    </div>
  </AbsoluteFill>
);

// Status bar inside phone
const StatusBar: React.FC = () => (
  <div style={{
    height: 90, display: "flex", alignItems: "flex-end",
    padding: "0 30px 8px", justifyContent: "space-between", flexShrink: 0,
  }}>
    <span style={{ fontSize: 22, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>9:41</span>
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      {/* Signal bars */}
      <svg width="18" height="13" viewBox="0 0 18 13" fill={C.text}>
        <rect x="0" y="5" width="3" height="8" rx="1"/>
        <rect x="5" y="3" width="3" height="10" rx="1"/>
        <rect x="10" y="1" width="3" height="12" rx="1"/>
        <rect x="15" y="0" width="3" height="13" rx="1" opacity="0.3"/>
      </svg>
      {/* Wifi */}
      <svg width="16" height="12" viewBox="0 0 16 12" fill={C.text}>
        <path d="M8 9.5a1.5 1.5 0 100 3 1.5 1.5 0 000-3z"/>
        <path d="M8 6c-1.7 0-3.2.7-4.3 1.8l1.2 1.2C5.8 8.1 6.8 7.5 8 7.5s2.2.6 3.1 1.5l1.2-1.2C11.2 6.7 9.7 6 8 6z"/>
        <path d="M8 2.5C5.3 2.5 2.9 3.7 1.2 5.5l1.2 1.2C3.8 5.1 5.8 4 8 4s4.2 1.1 5.6 2.7l1.2-1.2C13.1 3.7 10.7 2.5 8 2.5z"/>
      </svg>
      {/* Battery */}
      <svg width="26" height="13" viewBox="0 0 26 13" fill="none">
        <rect x=".5" y=".5" width="22" height="12" rx="3.5" stroke={C.text} strokeOpacity=".35"/>
        <rect x="2" y="2" width="16" height="9" rx="2" fill={C.text}/>
        <path d="M24 4.5v4a2.3 2.3 0 000-4z" fill={C.text} fillOpacity=".4"/>
      </svg>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// PRODUCT IMAGES — real Unsplash photos (models wearing ethnic wear)
// ─────────────────────────────────────────────────────────────────────────────
// Helper — wraps staticFile for product images
const K1 = staticFile("kurta1.webp");
const K2 = staticFile("kurta2.webp");
const K3 = staticFile("kurta3.jpg");
const K4 = staticFile("kurta4.webp");

const PRODUCTS = [
  {
    id: 1,
    title: "Classic White Cotton Kurta",
    merchant: "Meesho",
    price: "₹899",
    original: "₹1,499",
    discount: "40% off",
    rating: "4.8",
    reviews: "3,241",
    img: K1,
    color: "#F0EEE8",
  },
  {
    id: 2,
    title: "Pintuck Linen Kurta",
    merchant: "Ajio",
    price: "₹1,299",
    original: "₹1,999",
    discount: "35% off",
    rating: "4.7",
    reviews: "1,876",
    img: K2,
    color: "#EEF0F0",
  },
  {
    id: 3,
    title: "Off-White Mandarin Kurta",
    merchant: "Myntra",
    price: "₹1,099",
    original: "₹1,799",
    discount: "39% off",
    rating: "4.6",
    reviews: "2,103",
    img: K3,
    color: "#F4F2EC",
  },
  {
    id: 4,
    title: "Premium Linen Band Collar Kurta",
    merchant: "Meesho",
    price: "₹1,499",
    original: "₹2,499",
    discount: "40% off",
    rating: "4.9",
    reviews: "987",
    img: K4,
    color: "#EEEFEE",
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 1 — LOGO REVEAL (0–89, 3s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneLogoReveal: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();

  // Concentric gateway rings expanding from center
  const rings = [1, 1.6, 2.3, 3.2, 4.2];

  const logoSc = spring({ frame, fps, config: { damping: 12, stiffness: 70 } });
  const logoOp = lerp(frame, [0, 20], [0, 1]);

  const wordOp = lerp(frame, [20, 45], [0, 1]);
  const wordY  = lerp(frame, [20, 45], [28, 0]);

  const tagOp  = lerp(frame, [40, 70], [0, 1]);
  const tagY   = lerp(frame, [40, 70], [20, 0]);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />

      {/* Decorative concentric gateway rings */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        {rings.map((s, i) => {
          const ring_op = lerp(frame, [i*4, i*4+30], [0, 1]);
          const pulseS = s + Math.sin(frame/25 + i*0.8) * 0.04;
          return (
            <div key={i} style={{
              position: "absolute",
              opacity: ring_op * (0.07 - i * 0.012),
              transform: `scale(${pulseS})`,
            }}>
              <Gateway size={440} color={i % 2 === 0 ? "#A78BFA" : "#FB923C"} />
            </div>
          );
        })}
      </AbsoluteFill>

      {/* Logo + text */}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 0 }}>
        {/* Logo */}
        <div style={{
          transform: `scale(${logoSc})`,
          opacity: logoOp,
          marginBottom: 44,
          filter: "drop-shadow(0 0 32px rgba(165,132,250,0.6))",
        }}>
          <SarvamLogo size={160} color={C.white} spin frame={frame} />
        </div>

        {/* "sarvam" wordmark */}
        <div style={{
          opacity: wordOp,
          transform: `translateY(${wordY}px)`,
          fontSize: 88,
          fontWeight: 800,
          color: C.white,
          fontFamily: "Georgia, 'Times New Roman', serif",
          letterSpacing: -2,
          lineHeight: 1,
        }}>
          sarvam
        </div>

        {/* Tagline */}
        <div style={{
          opacity: tagOp,
          transform: `translateY(${tagY}px)`,
          fontSize: 30,
          color: "rgba(255,255,255,0.65)",
          fontFamily: "Georgia, serif",
          fontStyle: "italic",
          marginTop: 18,
          letterSpacing: 0.5,
        }}>
          AI for all, from India
        </div>

        {/* Tag chips */}
        <div style={{
          opacity: lerp(frame, [55, 80], [0, 1]),
          transform: `translateY(${lerp(frame, [55, 80], [16, 0])}px)`,
          display: "flex", gap: 14, marginTop: 60, flexWrap: "wrap", justifyContent: "center", padding: "0 60px",
        }}>
          {["Sarvam AI", "Hyperswitch", "UPI Native", "Setu Protocol"].map(t => (
            <div key={t} style={{
              background: "rgba(255,255,255,0.12)",
              border: "1.5px solid rgba(255,255,255,0.22)",
              borderRadius: 100, padding: "10px 26px",
              fontSize: 24, color: "rgba(255,255,255,0.8)",
              fontFamily: "system-ui, sans-serif", fontWeight: 500,
            }}>{t}</div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 2 — ASK ANYTHING (90–179, 3s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneAskInput: React.FC<{ frame: number }> = ({ frame }) => {
  const barOp = lerp(frame, [0, 20], [0, 1]);
  const barY  = lerp(frame, [0, 20], [40, 0]);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        {/* Floating "Ask anything" pill */}
        <div style={{
          opacity: barOp,
          transform: `translateY(${barY}px)`,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(20px)",
          borderRadius: 100,
          padding: "26px 32px",
          display: "flex",
          alignItems: "center",
          gap: 24,
          boxShadow: "0 8px 40px rgba(139,92,246,0.18), 0 2px 12px rgba(0,0,0,0.08)",
          width: 820,
        }}>
          {/* + */}
          <span style={{ fontSize: 40, color: "#444", fontWeight: 300, lineHeight: 1 }}>+</span>

          {/* Placeholder */}
          <span style={{
            flex: 1, fontSize: 36, color: "#999",
            fontFamily: "system-ui, sans-serif", letterSpacing: -0.3,
          }}>Ask anything</span>

          {/* Mic icon */}
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#666" strokeWidth="1.8" strokeLinecap="round">
            <rect x="9" y="2" width="6" height="11" rx="3"/>
            <path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="19" x2="12" y2="22"/>
            <line x1="8" y1="22" x2="16" y2="22"/>
          </svg>

          {/* Sarvam wave button */}
          <div style={{
            width: 64, height: 64, borderRadius: "50%",
            background: "#DDD",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <SarvamLogo size={36} color="#888" spin frame={frame} />
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 3 — USER TYPES (180–299, 4s)
// ─────────────────────────────────────────────────────────────────────────────
const QUERY = "Show me a simple white kurta for men";

const SceneTyping: React.FC<{ frame: number }> = ({ frame }) => {
  // Expand pill to card
  const expand = lerp(frame, [0, 25], [0, 1]);
  const cardH = lerp(frame, [0, 25], [100, 320]);

  // Type the text
  const charCount = Math.floor(lerp(frame, [15, 90], [0, QUERY.length]));
  const typed = QUERY.slice(0, charCount);
  const showCursor = frame % 24 < 12;

  // Send button appears when typing is done
  const btnOp = lerp(frame, [92, 110], [0, 1]);
  const btnSc = lerp(frame, [92, 110], [0.7, 1]);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          background: "rgba(255,255,255,0.94)",
          backdropFilter: "blur(20px)",
          borderRadius: 36,
          padding: "30px 36px",
          width: 820,
          minHeight: cardH,
          boxShadow: "0 8px 40px rgba(139,92,246,0.18), 0 2px 12px rgba(0,0,0,0.08)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}>
          {/* Text area */}
          <div style={{
            fontSize: 38,
            fontFamily: "system-ui, sans-serif",
            color: C.text,
            lineHeight: 1.45,
            minHeight: 160,
            letterSpacing: -0.4,
          }}>
            {typed}
            {showCursor && (
              <span style={{
                display: "inline-block",
                width: 3, height: 42,
                background: "#3B4CB8",
                verticalAlign: "middle",
                marginLeft: 2,
                borderRadius: 2,
              }} />
            )}
          </div>

          {/* Bottom row */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginTop: 24,
          }}>
            <div style={{ display: "flex", gap: 28 }}>
              <span style={{ fontSize: 36, color: "#666" }}>+</span>
              <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#666" strokeWidth="1.8" strokeLinecap="round">
                <rect x="9" y="2" width="6" height="11" rx="3"/>
                <path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="19" x2="12" y2="22"/>
                <line x1="8" y1="22" x2="16" y2="22"/>
              </svg>
            </div>
            {/* Send button */}
            <div style={{
              opacity: btnOp,
              transform: `scale(${btnSc})`,
              width: 68, height: 68, borderRadius: "50%",
              background: C.text,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 19V5M5 12l7-7 7 7"/>
              </svg>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 4 — SEARCHING (300–359, 2s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneSearching: React.FC<{ frame: number }> = ({ frame }) => {
  const op = lerp(frame, [0, 15], [0, 1]);
  const y  = lerp(frame, [0, 15], [20, 0]);
  const dot1 = Math.sin(frame / 8) * 0.5 + 0.5;
  const dot2 = Math.sin(frame / 8 + 2) * 0.5 + 0.5;
  const dot3 = Math.sin(frame / 8 + 4) * 0.5 + 0.5;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          opacity: op,
          transform: `translateY(${y}px)`,
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(20px)",
          borderRadius: 100,
          padding: "28px 56px",
          display: "flex",
          alignItems: "center",
          gap: 20,
          boxShadow: "0 8px 40px rgba(139,92,246,0.18)",
        }}>
          <SarvamLogo size={44} color={C.navyMid} spin frame={frame * 3} />
          <span style={{
            fontSize: 40,
            fontFamily: "system-ui, sans-serif",
            color: C.text,
            fontWeight: 500,
          }}>
            Searching products
          </span>
          <div style={{ display: "flex", gap: 7, alignItems: "center" }}>
            {[dot1, dot2, dot3].map((d, i) => (
              <div key={i} style={{
                width: 10, height: 10, borderRadius: "50%",
                background: C.navyMid,
                opacity: 0.3 + d * 0.7,
              }} />
            ))}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 5 — PHONE WITH CHAT + PRODUCTS (360–569, ~7s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneChatProducts: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();

  const phoneSc = spring({ frame, fps, config: { damping: 18, stiffness: 60 } });
  const phoneY  = lerp(frame, [0, 30], [80, 0]);
  const phoneOp = lerp(frame, [0, 20], [0, 1]);

  // User bubble
  const ub_op = lerp(frame, [12, 28], [0, 1]);
  const ub_y  = lerp(frame, [12, 28], [12, 0]);

  // Thinking indicator
  const thinkOp = frame > 28 && frame < 65 ? lerp(frame, [28, 40], [0, 1]) : 0;

  // AI text
  const ai_op = lerp(frame, [65, 82], [0, 1]);
  const ai_y  = lerp(frame, [65, 82], [12, 0]);

  // Product cards
  const p1sc = spring({ frame: Math.max(0, frame - 88), fps, config: { damping: 14, stiffness: 100 } });
  const p2sc = spring({ frame: Math.max(0, frame - 100), fps, config: { damping: 14, stiffness: 100 } });
  const p3sc = spring({ frame: Math.max(0, frame - 112), fps, config: { damping: 14, stiffness: 100 } });
  const p4sc = spring({ frame: Math.max(0, frame - 124), fps, config: { damping: 14, stiffness: 100 } });
  const pScales = [p1sc, p2sc, p3sc, p4sc];

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />

      <Phone
        scale={phoneSc * 0.86}
        y={phoneY}
        opacity={phoneOp}
      >
        <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.white }}>
          <StatusBar />

          {/* Chat header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 14,
            padding: "6px 28px 16px",
            borderBottom: "1px solid #F0F0F5",
          }}>
            <span style={{ fontSize: 32, color: C.text, fontWeight: 300 }}>≡</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1 }}>
              <SarvamLogo size={32} color={C.navyMid} />
              <span style={{ fontSize: 26, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>
                sarvam
              </span>
            </div>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={C.text} strokeWidth="1.8">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "hidden", padding: "18px 22px 10px", display: "flex", flexDirection: "column", gap: 12 }}>

            {/* User bubble */}
            <div style={{
              opacity: ub_op, transform: `translateY(${ub_y}px)`,
              display: "flex", justifyContent: "flex-end",
            }}>
              <div style={{
                maxWidth: "78%", padding: "14px 20px",
                background: "#F0EEF8", color: C.text,
                borderRadius: 22, borderBottomRightRadius: 6,
                fontSize: 20, lineHeight: 1.5, fontFamily: "system-ui",
              }}>
                Show me a simple white kurta for men
              </div>
            </div>

            {/* Thinking */}
            {frame > 28 && (
              <div style={{
                opacity: thinkOp,
                display: "flex", alignItems: "center", gap: 12,
              }}>
                <SarvamLogo size={36} color={C.navyMid} spin frame={frame * 2} />
                <span style={{ fontSize: 20, color: C.muted, fontFamily: "system-ui" }}>
                  Thinking ›
                </span>
              </div>
            )}

            {/* AI response */}
            <div style={{
              opacity: ai_op, transform: `translateY(${ai_y}px)`,
              fontSize: 20, color: C.text, lineHeight: 1.6,
              fontFamily: "system-ui",
            }}>
              Here are clean, simple white kurtas for men — great fits from Meesho, Ajio & Myntra. ✨
            </div>

            {/* Product 2×2 grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {PRODUCTS.slice(0, 4).map((p, i) => (
                <div key={p.id} style={{
                  transform: `scale(${pScales[i]})`,
                  borderRadius: 18,
                  overflow: "hidden",
                  background: C.white,
                  border: "1px solid #EEE",
                  boxShadow: "0 3px 12px rgba(0,0,0,0.08)",
                }}>
                  <div style={{
                    width: "100%",
                    paddingBottom: "100%",
                    position: "relative",
                    background: `${p.color}22`,
                    overflow: "hidden",
                  }}>
                    <Img
                      src={p.img}
                      style={{
                        position: "absolute", inset: 0,
                        width: "100%", height: "100%",
                        objectFit: "cover",
                      }}
                    />
                    {/* Discount badge */}
                    <div style={{
                      position: "absolute", top: 8, right: 8,
                      background: C.green, color: C.white,
                      fontSize: 14, fontWeight: 700,
                      padding: "2px 8px", borderRadius: 100,
                      fontFamily: "system-ui",
                    }}>{p.discount}</div>
                  </div>
                  <div style={{ padding: "10px 12px" }}>
                    <div style={{
                      fontSize: 17, fontWeight: 600, color: C.text,
                      lineHeight: 1.3, marginBottom: 4,
                      fontFamily: "system-ui",
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}>{p.title}</div>
                    <div style={{ fontSize: 17, fontWeight: 800, color: C.orange, fontFamily: "system-ui" }}>{p.price}</div>
                    <div style={{
                      fontSize: 14, color: C.muted, marginTop: 4,
                      display: "flex", alignItems: "center", gap: 5,
                      fontFamily: "system-ui",
                    }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#CCC" }} />
                      {p.merchant}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Input bar */}
          <div style={{
            borderTop: "1px solid #F0F0F5", padding: "10px 20px 28px",
            background: C.white, flexShrink: 0,
          }}>
            <div style={{
              display: "flex", alignItems: "center",
              background: "#F5F4FA", borderRadius: 100,
              padding: "10px 10px 10px 24px",
            }}>
              <span style={{ flex: 1, fontSize: 20, color: "#AAA", fontFamily: "system-ui" }}>Ask anything</span>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#888" strokeWidth="1.8" strokeLinecap="round">
                <rect x="9" y="2" width="6" height="11" rx="3"/>
                <path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="19" x2="12" y2="22"/>
                <line x1="8" y1="22" x2="16" y2="22"/>
              </svg>
              <div style={{
                width: 50, height: 50, borderRadius: "50%",
                background: "#DDD", marginLeft: 8,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <SarvamLogo size={28} color="#999" spin frame={frame} />
              </div>
            </div>
          </div>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 6 — PRODUCT DETAIL (570–719, 5s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneProductDetail: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();
  const p = PRODUCTS[0]; // Banarasi Kurta

  const slideY = lerp(frame, [0, 30], [60, 0]);
  const op = lerp(frame, [0, 20], [0, 1]);

  const infoY = lerp(frame, [20, 50], [80, 0]);
  const infoOp = lerp(frame, [20, 50], [0, 1]);

  const merchantOp = lerp(frame, [40, 60], [0, 1]);
  const btnSc = spring({ frame: Math.max(0, frame - 55), fps, config: { damping: 12, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <Phone scale={0.86} y={slideY} opacity={op}>
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <StatusBar />

          {/* Full-bleed product image */}
          <div style={{
            position: "relative",
            height: 440,
            overflow: "hidden",
            flexShrink: 0,
          }}>
            <Img
              src={p.img}
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            />
            {/* Close + more buttons */}
            <div style={{
              position: "absolute", top: 16, right: 16,
              display: "flex", gap: 10,
            }}>
              {["···", "✕"].map(icon => (
                <div key={icon} style={{
                  width: 52, height: 52, borderRadius: "50%",
                  background: "rgba(255,255,255,0.85)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 20, color: C.text, fontWeight: 600, fontFamily: "system-ui",
                }}>{icon}</div>
              ))}
            </div>
            {/* Dot indicator */}
            <div style={{
              position: "absolute", bottom: 14, left: "50%",
              transform: "translateX(-50%)",
              display: "flex", gap: 6,
            }}>
              {[1,0,0].map((a, i) => (
                <div key={i} style={{
                  width: a ? 20 : 7, height: 7,
                  borderRadius: 4,
                  background: a ? C.white : "rgba(255,255,255,0.5)",
                }} />
              ))}
            </div>
          </div>

          {/* Product info */}
          <div style={{
            flex: 1,
            padding: "22px 24px",
            opacity: infoOp,
            transform: `translateY(${infoY}px)`,
            overflowY: "hidden",
          }}>
            <div style={{
              fontSize: 30, fontWeight: 800, color: C.text,
              fontFamily: "system-ui", lineHeight: 1.25, marginBottom: 16,
            }}>
              {p.title}
            </div>

            {/* Size selector */}
            <div style={{
              marginBottom: 18,
              fontSize: 22, color: C.muted, fontFamily: "system-ui",
            }}>
              Size
            </div>
            <div style={{
              display: "flex",
              gap: 10,
              marginBottom: 20,
            }}>
              {["S", "M", "L", "XL"].map((s, i) => (
                <div key={s} style={{
                  width: 64, height: 64, borderRadius: 14,
                  border: `2px solid ${i === 1 ? C.navyMid : "#E0E0E0"}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22, fontWeight: i === 1 ? 700 : 400,
                  color: i === 1 ? C.navyMid : C.muted,
                  background: i === 1 ? "#EDE9FF" : C.white,
                  fontFamily: "system-ui",
                }}>{s}</div>
              ))}
            </div>

            {/* Merchant row */}
            <div style={{
              opacity: merchantOp,
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "16px 0",
              borderTop: "1px solid #F0F0F0",
              borderBottom: "1px solid #F0F0F0",
              marginBottom: 20,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                {/* Meesho "M" badge */}
                <div style={{
                  width: 46, height: 46, borderRadius: 12,
                  background: C.meesho,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 22, fontWeight: 800, color: C.white,
                  fontFamily: "system-ui",
                }}>M</div>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>Meesho</div>
                  <div style={{ fontSize: 18, color: C.green, fontFamily: "system-ui" }}>Free shipping · 7-day returns</div>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: C.orange, fontFamily: "system-ui" }}>{p.price}</div>
                <div style={{ fontSize: 18, color: C.muted, textDecoration: "line-through", fontFamily: "system-ui" }}>{p.original}</div>
              </div>
            </div>

            {/* Buy button */}
            <div style={{
              transform: `scale(${btnSc})`,
              width: "100%", padding: "20px",
              background: C.text,
              borderRadius: 18, textAlign: "center",
              fontSize: 26, fontWeight: 700, color: C.white,
              fontFamily: "system-ui",
            }}>
              Buy Now
            </div>
          </div>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 7 — CHECKOUT (720–869, 5s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneCheckout: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();
  const p = PRODUCTS[0];

  const slideY = lerp(frame, [0, 28], [50, 0]);
  const op = lerp(frame, [0, 18], [0, 1]);

  const row = (delay: number) => ({
    opacity: lerp(frame, [delay, delay + 18], [0, 1]),
    transform: `translateY(${lerp(frame, [delay, delay + 18], [12, 0])}px)`,
  });

  const btnSc = spring({ frame: Math.max(0, frame - 80), fps, config: { damping: 12, stiffness: 90 } });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <Phone scale={0.86} y={slideY} opacity={op}>
        <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.white }}>
          <StatusBar />

          {/* Header */}
          <div style={{
            padding: "0 28px 16px",
            borderBottom: "1px solid #F0F0F5",
            flexShrink: 0,
          }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: C.text, fontFamily: "system-ui" }}>
              Complete Your Order
            </div>
          </div>

          {/* Scroll content */}
          <div style={{ flex: 1, overflowY: "hidden", padding: "20px 24px" }}>
            {/* Product summary */}
            <div style={{
              ...row(8),
              display: "flex", alignItems: "center", gap: 16,
              padding: "16px", background: "#F8F7FF", borderRadius: 16, marginBottom: 20,
            }}>
              <div style={{
                width: 80, height: 80, borderRadius: 14, overflow: "hidden", flexShrink: 0,
              }}>
                <Img src={p.img} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>
                  {p.title}
                </div>
                <div style={{ fontSize: 18, color: C.muted, fontFamily: "system-ui" }}>Size: M · Qty: 1</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: C.orange, fontFamily: "system-ui" }}>{p.price}</div>
              </div>
            </div>

            {/* Payment row */}
            <div style={{
              ...row(22),
              display: "flex", alignItems: "center",
              padding: "18px 0", borderBottom: "1px solid #F0F0F5",
            }}>
              <div style={{
                width: 52, height: 52, borderRadius: 12,
                background: "#F0F0F0",
                display: "flex", alignItems: "center", justifyContent: "center",
                marginRight: 18, flexShrink: 0,
              }}>
                <span style={{ fontSize: 28 }}>📱</span>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: C.text, fontFamily: "system-ui" }}>UPI</div>
                <div style={{ fontSize: 18, color: C.muted, fontFamily: "system-ui" }}>raj@okaxis</div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </div>

            {/* Address row */}
            <div style={{
              ...row(36),
              display: "flex", alignItems: "center",
              padding: "18px 0", borderBottom: "1px solid #F0F0F5",
            }}>
              <div style={{
                width: 52, height: 52, borderRadius: 12,
                background: "#F0F0F0",
                display: "flex", alignItems: "center", justifyContent: "center",
                marginRight: 18, flexShrink: 0,
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={C.text} strokeWidth="1.8">
                  <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
                  <circle cx="12" cy="9" r="2.5"/>
                </svg>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: C.text, fontFamily: "system-ui" }}>Raj Kumar</div>
                <div style={{ fontSize: 18, color: C.muted, fontFamily: "system-ui" }}>12 MG Road, Bengaluru — 560001</div>
              </div>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={C.muted} strokeWidth="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </div>

            {/* Shipping row */}
            <div style={{
              ...row(50),
              display: "flex", alignItems: "center",
              padding: "18px 0", borderBottom: "1px solid #F0F0F5",
            }}>
              <div style={{
                width: 52, height: 52, borderRadius: 12,
                background: "#F0F0F0",
                display: "flex", alignItems: "center", justifyContent: "center",
                marginRight: 18, flexShrink: 0,
              }}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={C.text} strokeWidth="1.8">
                  <rect x="1" y="3" width="15" height="13" rx="2"/>
                  <path d="M16 8h4l3 3v5h-7V8z"/>
                  <circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
                </svg>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: C.text, fontFamily: "system-ui" }}>Delhivery Standard</div>
                <div style={{ fontSize: 18, color: C.green, fontFamily: "system-ui" }}>Free · 3–5 business days</div>
              </div>
            </div>

            {/* Totals */}
            <div style={{ ...row(62), padding: "16px 0" }}>
              {[
                { l: "Subtotal", v: "₹3,499" },
                { l: "GST (18%)", v: "₹630" },
                { l: "Delivery", v: "Free" },
              ].map(({ l, v }) => (
                <div key={l} style={{
                  display: "flex", justifyContent: "space-between",
                  fontSize: 20, color: C.muted, fontFamily: "system-ui", padding: "4px 0",
                }}>
                  <span>{l}</span><span>{v}</span>
                </div>
              ))}
              <div style={{
                display: "flex", justifyContent: "space-between",
                fontSize: 24, fontWeight: 800, color: C.text,
                fontFamily: "system-ui", marginTop: 10,
                padding: "10px 0 0",
                borderTop: "1px solid #EEE",
              }}>
                <span>Pay Meesho</span><span>₹4,129</span>
              </div>
            </div>

            {/* Pay button */}
            <div style={{
              transform: `scale(${btnSc})`,
              width: "100%", padding: "22px",
              background: C.text,
              borderRadius: 20, textAlign: "center",
              fontSize: 28, fontWeight: 700, color: C.white,
              fontFamily: "system-ui",
              marginTop: 10,
            }}>
              Pay Meesho
            </div>

            {/* Hyperswitch badge */}
            <div style={{
              ...row(80),
              display: "flex", alignItems: "center", justifyContent: "center",
              gap: 8, marginTop: 14,
              fontSize: 18, color: C.muted, fontFamily: "system-ui",
            }}>
              🔒 Secured by <strong style={{ color: "#4F46E5" }}>Hyperswitch</strong>
            </div>
          </div>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 8 — PROCESSING (870–929, 2s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneProcessing: React.FC<{ frame: number }> = ({ frame }) => {
  const op = lerp(frame, [0, 14], [0, 1]);
  const y  = lerp(frame, [0, 14], [20, 0]);
  const dot = (phase: number) => Math.abs(Math.sin(frame / 10 + phase)) * 0.7 + 0.3;

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{
          opacity: op,
          transform: `translateY(${y}px)`,
          background: C.text,
          borderRadius: 100,
          padding: "26px 56px",
          display: "flex", alignItems: "center", gap: 20,
          boxShadow: "0 12px 48px rgba(0,0,0,0.25)",
        }}>
          {/* Spinning dots loader */}
          <div style={{ display: "flex", gap: 7 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 10, height: 10, borderRadius: "50%",
                background: C.white, opacity: dot(i * 1.5),
              }} />
            ))}
          </div>
          <span style={{
            fontSize: 38, color: C.white,
            fontFamily: "system-ui", fontWeight: 500,
          }}>Working on it</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 9 — GREEN CHECKMARK (930–989, 2s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneCheck: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();
  const sc = spring({ frame, fps, config: { damping: 9, stiffness: 80 } });
  const ripple1 = lerp(frame, [5, 35], [1, 1.8]);
  const ripple2 = lerp(frame, [10, 42], [1, 2.2]);
  const rippleOp1 = lerp(frame, [5, 35], [0.4, 0]);
  const rippleOp2 = lerp(frame, [10, 42], [0.25, 0]);

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        {/* Ripple rings */}
        <div style={{
          position: "absolute",
          width: 180, height: 180, borderRadius: "50%",
          border: `3px solid ${C.green}`,
          opacity: rippleOp1,
          transform: `scale(${ripple1})`,
        }} />
        <div style={{
          position: "absolute",
          width: 180, height: 180, borderRadius: "50%",
          border: `2px solid ${C.green}`,
          opacity: rippleOp2,
          transform: `scale(${ripple2})`,
        }} />

        {/* Green check */}
        <div style={{
          width: 180, height: 180, borderRadius: "50%",
          background: `linear-gradient(135deg, ${C.green}, ${C.greenD})`,
          display: "flex", alignItems: "center", justifyContent: "center",
          transform: `scale(${sc})`,
          boxShadow: `0 20px 60px ${C.green}55`,
        }}>
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// SCENE 10 — PURCHASE CONFIRMED (990–1079, 3s)
// ─────────────────────────────────────────────────────────────────────────────
const SceneConfirmed: React.FC<{ frame: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();
  const p = PRODUCTS[0];

  const slideY = lerp(frame, [0, 28], [50, 0]);
  const op = lerp(frame, [0, 18], [0, 1]);

  const row = (delay: number) => ({
    opacity: lerp(frame, [delay, delay + 18], [0, 1]),
    transform: `translateY(${lerp(frame, [delay, delay + 18], [10, 0])}px)`,
  });

  const checkSc = spring({ frame: Math.max(0, frame - 5), fps, config: { damping: 12, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <SarvamBg />
      <Phone scale={0.86} y={slideY} opacity={op}>
        <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.white }}>
          <StatusBar />

          {/* Chat header */}
          <div style={{
            display: "flex", alignItems: "center", gap: 14,
            padding: "0 28px 16px",
            borderBottom: "1px solid #F0F0F5",
          }}>
            <span style={{ fontSize: 32, color: C.text, fontWeight: 300 }}>≡</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1 }}>
              <SarvamLogo size={32} color={C.navyMid} />
              <span style={{ fontSize: 26, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>sarvam</span>
            </div>
          </div>

          <div style={{ flex: 1, padding: "20px 22px", overflowY: "hidden" }}>
            {/* Purchase complete card */}
            <div style={{
              ...row(6),
              background: C.white,
              border: "1.5px solid #E8E8F0",
              borderRadius: 20,
              padding: "18px",
              marginBottom: 18,
              boxShadow: "0 4px 20px rgba(0,0,0,0.06)",
            }}>
              {/* Header */}
              <div style={{
                display: "flex", alignItems: "center", gap: 10,
                marginBottom: 16,
              }}>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  background: C.green,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transform: `scale(${checkSc})`,
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </div>
                <span style={{
                  fontSize: 22, fontWeight: 700, color: C.text,
                  fontFamily: "system-ui",
                }}>Purchase complete</span>
              </div>

              {/* Product row */}
              <div style={{
                display: "flex", gap: 16, alignItems: "center",
                padding: "12px 0",
                borderTop: "1px solid #F0F0F5",
                borderBottom: "1px solid #F0F0F5",
                marginBottom: 12,
              }}>
                <div style={{
                  width: 80, height: 80, borderRadius: 12, overflow: "hidden", flexShrink: 0,
                }}>
                  <Img src={p.img} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: C.text, fontFamily: "system-ui" }}>{p.title}</div>
                  <div style={{ fontSize: 18, color: C.muted, fontFamily: "system-ui" }}>Quantity: 1</div>
                </div>
              </div>

              {/* Order details */}
              {[
                { l: "Estimated delivery", v: "Wednesday, Mar 4", bold: true },
                { l: "Sold by", v: "Meesho" },
                { l: "Paid", v: "₹4,129" },
              ].map(({ l, v, bold }) => (
                <div key={l} style={{
                  display: "flex", justifyContent: "space-between",
                  fontSize: 20, fontFamily: "system-ui", padding: "4px 0",
                }}>
                  <span style={{ color: C.muted }}>{l}</span>
                  <span style={{ fontWeight: bold ? 700 : 600, color: C.text }}>{v}</span>
                </div>
              ))}

              {/* View details button */}
              <div style={{
                ...row(30),
                marginTop: 14,
                padding: "14px",
                border: "1.5px solid #E0E0E8",
                borderRadius: 14,
                textAlign: "center",
                fontSize: 22, fontWeight: 600, color: C.text,
                fontFamily: "system-ui",
              }}>
                View details
              </div>
            </div>

            {/* AI follow-up */}
            <div style={{
              ...row(45),
              fontSize: 20, color: C.text, lineHeight: 1.6,
              fontFamily: "system-ui",
            }}>
              🎉 Meesho confirmed your order! Your white kurta will arrive in 3–5 days. ✨
            </div>

            {/* Feedback row */}
            <div style={{
              ...row(60),
              display: "flex", gap: 20, marginTop: 14,
            }}>
              {["👍", "🔄"].map(icon => (
                <span key={icon} style={{ fontSize: 24 }}>{icon}</span>
              ))}
            </div>
          </div>

          {/* Input */}
          <div style={{
            borderTop: "1px solid #F0F0F5", padding: "10px 20px 28px",
            background: C.white, flexShrink: 0,
          }}>
            <div style={{
              display: "flex", alignItems: "center",
              background: "#F5F4FA", borderRadius: 100,
              padding: "10px 10px 10px 24px",
            }}>
              <span style={{ flex: 1, fontSize: 20, color: "#AAA", fontFamily: "system-ui" }}>Ask anything</span>
              <div style={{
                width: 50, height: 50, borderRadius: "50%",
                background: "#DDD",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <SarvamLogo size={28} color="#999" spin frame={frame} />
              </div>
            </div>
          </div>
        </div>
      </Phone>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPOSITION — 36 seconds @ 30fps = 1080 frames
// ─────────────────────────────────────────────────────────────────────────────
export const SarvamDemo: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {/* S1: Logo Reveal       0–89   (3s) */}
      <Sequence from={0}   durationInFrames={90}>
        <SceneLogoReveal   frame={frame} />
      </Sequence>
      {/* S2: Ask Input         90–179 (3s) */}
      <Sequence from={90}  durationInFrames={90}>
        <SceneAskInput     frame={frame - 90} />
      </Sequence>
      {/* S3: User Types        180–299 (4s) */}
      <Sequence from={180} durationInFrames={120}>
        <SceneTyping       frame={frame - 180} />
      </Sequence>
      {/* S4: Searching         300–359 (2s) */}
      <Sequence from={300} durationInFrames={60}>
        <SceneSearching    frame={frame - 300} />
      </Sequence>
      {/* S5: Chat + Products   360–569 (~7s) */}
      <Sequence from={360} durationInFrames={210}>
        <SceneChatProducts frame={frame - 360} />
      </Sequence>
      {/* S6: Product Detail    570–719 (5s) */}
      <Sequence from={570} durationInFrames={150}>
        <SceneProductDetail frame={frame - 570} />
      </Sequence>
      {/* S7: Checkout          720–869 (5s) */}
      <Sequence from={720} durationInFrames={150}>
        <SceneCheckout     frame={frame - 720} />
      </Sequence>
      {/* S8: Processing        870–929 (2s) */}
      <Sequence from={870} durationInFrames={60}>
        <SceneProcessing   frame={frame - 870} />
      </Sequence>
      {/* S9: Green Check       930–989 (2s) */}
      <Sequence from={930} durationInFrames={60}>
        <SceneCheck        frame={frame - 930} />
      </Sequence>
      {/* S10: Confirmed        990–1079 (3s) */}
      <Sequence from={990} durationInFrames={90}>
        <SceneConfirmed    frame={frame - 990} />
      </Sequence>
    </AbsoluteFill>
  );
};
