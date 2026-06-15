import React from "react";

/**
 * Ayron Badge — small status/label pill.
 * Tones: neutral | accent | success | warning | danger | info
 * Variants: soft (tinted) | solid | outline
 */
export function Badge({
  children,
  tone = "neutral",
  variant = "soft",
  dot = false,
  style = {},
}) {
  const palette = {
    neutral: { fg: "var(--ay-neutral-700)", bg: "var(--ay-neutral-100)", bd: "var(--ay-border-strong)", solid: "var(--ay-ink)" },
    accent: { fg: "var(--ay-blue-700)", bg: "var(--ay-blue-50)", bd: "var(--ay-blue-300)", solid: "var(--ay-blue-600)" },
    success: { fg: "var(--ay-success-700)", bg: "var(--ay-success-50)", bd: "#bfe6cd", solid: "var(--ay-success-500)" },
    warning: { fg: "var(--ay-warning-700)", bg: "var(--ay-warning-50)", bd: "#f2d9b3", solid: "var(--ay-warning-500)" },
    danger: { fg: "var(--ay-danger-700)", bg: "var(--ay-danger-50)", bd: "#f3c2c2", solid: "var(--ay-danger-500)" },
    info: { fg: "var(--ay-info-500)", bg: "var(--ay-info-50)", bd: "var(--ay-blue-300)", solid: "var(--ay-info-500)" },
  };
  const p = palette[tone] || palette.neutral;

  const styles =
    variant === "solid"
      ? { background: p.solid, color: "#fff", border: "1px solid transparent" }
      : variant === "outline"
      ? { background: "transparent", color: p.fg, border: `1px solid ${p.bd}` }
      : { background: p.bg, color: p.fg, border: "1px solid transparent" };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        height: 20,
        padding: "0 8px",
        fontFamily: "var(--ay-font-sans)",
        fontSize: 12,
        fontWeight: 500,
        lineHeight: 1,
        borderRadius: "var(--ay-radius-full)",
        whiteSpace: "nowrap",
        ...styles,
        ...style,
      }}
    >
      {dot ? (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: variant === "solid" ? "rgba(255,255,255,0.9)" : p.solid,
          }}
        />
      ) : null}
      {children}
    </span>
  );
}
