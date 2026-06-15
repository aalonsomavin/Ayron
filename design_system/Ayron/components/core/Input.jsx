import React from "react";

/**
 * Ayron Input — hairline border, blue focus ring.
 * Supports leading/trailing adornments, sizes, error state.
 */
export function Input({
  value,
  defaultValue,
  placeholder,
  type = "text",
  size = "md",
  disabled = false,
  invalid = false,
  leading = null,
  trailing = null,
  onChange,
  style = {},
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const sizes = {
    sm: { height: 32, font: 13, pad: 10 },
    md: { height: 38, font: 14, pad: 12 },
    lg: { height: 44, font: 15, pad: 14 },
  };
  const s = sizes[size] || sizes.md;

  const borderColor = invalid
    ? "var(--ay-danger-500)"
    : focus
    ? "var(--ay-accent)"
    : "var(--ay-border-strong)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        height: s.height,
        padding: `0 ${s.pad}px`,
        background: disabled ? "var(--ay-bg-muted)" : "var(--ay-surface)",
        border: `1px solid ${borderColor}`,
        borderRadius: "var(--ay-radius-md)",
        boxShadow: focus
          ? invalid
            ? "0 0 0 3px rgba(220,38,38,0.18)"
            : "var(--ay-shadow-focus)"
          : "none",
        transition: "border-color var(--ay-dur-fast) var(--ay-ease), box-shadow var(--ay-dur-fast) var(--ay-ease)",
        cursor: disabled ? "not-allowed" : "text",
        ...style,
      }}
    >
      {leading ? <span style={{ display: "inline-flex", color: "var(--ay-text-subtle)" }}>{leading}</span> : null}
      <input
        type={type}
        value={value}
        defaultValue={defaultValue}
        placeholder={placeholder}
        disabled={disabled}
        onChange={onChange}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={{
          flex: 1,
          minWidth: 0,
          border: "none",
          outline: "none",
          background: "transparent",
          fontFamily: "var(--ay-font-sans)",
          fontSize: s.font,
          color: "var(--ay-text)",
          height: "100%",
          padding: 0,
        }}
        {...rest}
      />
      {trailing ? <span style={{ display: "inline-flex", color: "var(--ay-text-subtle)" }}>{trailing}</span> : null}
    </div>
  );
}
