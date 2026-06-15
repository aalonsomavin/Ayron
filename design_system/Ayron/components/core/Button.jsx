import React from "react";

/**
 * Ayron Button — solid ink primary by default (Cursor-adjacent).
 * Variants: primary | secondary | ghost | danger | link
 * Sizes: sm | md | lg
 */
export function Button({
  children,
  variant = "primary",
  size = "md",
  disabled = false,
  leftIcon = null,
  rightIcon = null,
  fullWidth = false,
  type = "button",
  onClick,
  style = {},
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [active, setActive] = React.useState(false);

  const sizes = {
    sm: { height: 30, padding: "0 10px", font: 13, gap: 6, radius: "var(--ay-radius-sm)" },
    md: { height: 36, padding: "0 14px", font: 14, gap: 7, radius: "var(--ay-radius-md)" },
    lg: { height: 44, padding: "0 20px", font: 15, gap: 8, radius: "var(--ay-radius-md)" },
  };
  const s = sizes[size] || sizes.md;

  const variants = {
    primary: {
      background: disabled ? "var(--ay-neutral-200)" : hover ? "var(--ay-primary-hover)" : "var(--ay-primary)",
      color: disabled ? "var(--ay-text-disabled)" : "var(--ay-primary-text)",
      border: "1px solid transparent",
    },
    secondary: {
      background: disabled ? "var(--ay-bg)" : hover ? "var(--ay-surface-hover)" : "var(--ay-surface)",
      color: disabled ? "var(--ay-text-disabled)" : "var(--ay-text)",
      border: "1px solid var(--ay-border-strong)",
    },
    ghost: {
      background: hover && !disabled ? "var(--ay-surface-hover)" : "transparent",
      color: disabled ? "var(--ay-text-disabled)" : "var(--ay-text)",
      border: "1px solid transparent",
    },
    danger: {
      background: disabled ? "var(--ay-neutral-200)" : hover ? "var(--ay-danger-700)" : "var(--ay-danger-500)",
      color: disabled ? "var(--ay-text-disabled)" : "#fff",
      border: "1px solid transparent",
    },
    link: {
      background: "transparent",
      color: disabled ? "var(--ay-text-disabled)" : "var(--ay-text-link)",
      border: "1px solid transparent",
      textDecoration: hover ? "underline" : "none",
    },
  };
  const v = variants[variant] || variants.primary;

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: s.gap,
        height: s.height,
        padding: variant === "link" ? 0 : s.padding,
        width: fullWidth ? "100%" : "auto",
        fontFamily: "var(--ay-font-sans)",
        fontSize: s.font,
        fontWeight: 500,
        lineHeight: 1,
        letterSpacing: "-0.005em",
        borderRadius: variant === "link" ? 0 : s.radius,
        cursor: disabled ? "not-allowed" : "pointer",
        transform: active && !disabled && variant !== "link" ? "translateY(0.5px)" : "none",
        transition: "background var(--ay-dur-fast) var(--ay-ease), color var(--ay-dur-fast) var(--ay-ease), box-shadow var(--ay-dur-fast) var(--ay-ease)",
        boxShadow: variant === "secondary" && !disabled ? "var(--ay-shadow-xs)" : "none",
        whiteSpace: "nowrap",
        ...v,
        ...style,
      }}
      {...rest}
    >
      {leftIcon ? <span style={{ display: "inline-flex", marginLeft: variant === "link" ? 0 : -2 }}>{leftIcon}</span> : null}
      {children}
      {rightIcon ? <span style={{ display: "inline-flex", marginRight: variant === "link" ? 0 : -2 }}>{rightIcon}</span> : null}
    </button>
  );
}
