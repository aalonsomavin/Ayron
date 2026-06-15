import React from "react";

/**
 * Ayron Avatar — user/agent identity. Initials fallback, optional image,
 * optional status dot. The agent avatar uses the ink mark.
 */
export function Avatar({ name = "", src = null, size = 32, agent = false, status = null, style = {} }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");

  return (
    <span style={{ position: "relative", display: "inline-flex", flex: "none", ...style }}>
      <span
        style={{
          width: size,
          height: size,
          borderRadius: "var(--ay-radius-full)",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          background: agent ? "var(--ay-ink)" : "var(--ay-neutral-150)",
          color: agent ? "#fff" : "var(--ay-neutral-700)",
          border: "1px solid var(--ay-border)",
          fontFamily: "var(--ay-font-sans)",
          fontSize: Math.round(size * 0.4),
          fontWeight: 600,
          letterSpacing: "-0.02em",
          userSelect: "none",
        }}
      >
        {src ? (
          <img src={src} alt={name} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : agent ? (
          <span style={{ fontSize: Math.round(size * 0.5) }}>A</span>
        ) : (
          initials || "?"
        )}
      </span>
      {status ? (
        <span
          style={{
            position: "absolute",
            right: -1,
            bottom: -1,
            width: Math.max(8, size * 0.28),
            height: Math.max(8, size * 0.28),
            borderRadius: "50%",
            border: "2px solid var(--ay-surface)",
            background:
              status === "online"
                ? "var(--ay-success-500)"
                : status === "busy"
                ? "var(--ay-warning-500)"
                : "var(--ay-neutral-400)",
          }}
        />
      ) : null}
    </span>
  );
}
