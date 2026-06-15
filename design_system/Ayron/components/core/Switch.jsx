import React from "react";

/**
 * Ayron Switch — toggle. Ink when on. Controlled or uncontrolled.
 */
export function Switch({ checked, defaultChecked = false, disabled = false, size = "md", onChange, style = {} }) {
  const [internal, setInternal] = React.useState(defaultChecked);
  const on = checked !== undefined ? checked : internal;

  const dims = size === "sm" ? { w: 32, h: 18, k: 14 } : { w: 40, h: 22, k: 18 };
  const pad = (dims.h - dims.k) / 2;

  const toggle = () => {
    if (disabled) return;
    if (checked === undefined) setInternal(!on);
    onChange && onChange(!on);
  };

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      disabled={disabled}
      onClick={toggle}
      style={{
        position: "relative",
        width: dims.w,
        height: dims.h,
        flex: "none",
        border: "none",
        borderRadius: "var(--ay-radius-full)",
        background: disabled ? "var(--ay-neutral-200)" : on ? "var(--ay-ink)" : "var(--ay-neutral-300)",
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "background var(--ay-dur-normal) var(--ay-ease)",
        padding: 0,
        ...style,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: pad,
          left: on ? dims.w - dims.k - pad : pad,
          width: dims.k,
          height: dims.k,
          borderRadius: "50%",
          background: "#fff",
          boxShadow: "var(--ay-shadow-sm)",
          transition: "left var(--ay-dur-normal) var(--ay-ease-out)",
        }}
      />
    </button>
  );
}
