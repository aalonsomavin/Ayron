import React from "react";

/**
 * Ayron Card — white surface, hairline border, optional soft shadow.
 * Compose freely; optional header (title/subtitle/actions) + body.
 */
export function Card({
  children,
  title,
  subtitle,
  actions = null,
  padding = 20,
  elevated = false,
  interactive = false,
  style = {},
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const hasHeader = title || subtitle || actions;

  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "var(--ay-surface)",
        border: "1px solid var(--ay-border)",
        borderRadius: "var(--ay-radius-lg)",
        boxShadow: elevated ? "var(--ay-shadow-sm)" : interactive && hover ? "var(--ay-shadow-md)" : "none",
        borderColor: interactive && hover ? "var(--ay-border-strong)" : "var(--ay-border)",
        transition: "box-shadow var(--ay-dur-normal) var(--ay-ease), border-color var(--ay-dur-normal) var(--ay-ease)",
        cursor: interactive ? "pointer" : "default",
        overflow: "hidden",
        ...style,
      }}
      {...rest}
    >
      {hasHeader ? (
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
            padding: `${padding}px ${padding}px ${children ? 0 : padding}px`,
          }}
        >
          <div>
            {title ? (
              <div style={{ fontFamily: "var(--ay-font-sans)", fontSize: 16, fontWeight: 600, color: "var(--ay-text)", letterSpacing: "-0.01em" }}>{title}</div>
            ) : null}
            {subtitle ? (
              <div style={{ fontFamily: "var(--ay-font-sans)", fontSize: 13, color: "var(--ay-text-muted)", marginTop: 3 }}>{subtitle}</div>
            ) : null}
          </div>
          {actions ? <div style={{ flex: "none" }}>{actions}</div> : null}
        </div>
      ) : null}
      {children ? <div style={{ padding }}>{children}</div> : null}
    </div>
  );
}
