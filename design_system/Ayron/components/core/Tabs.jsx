import React from "react";

/**
 * Ayron Tabs — underline style, dev-tool feel.
 * Controlled via value/onChange or uncontrolled via defaultValue.
 * items: [{ value, label, count? }]
 */
export function Tabs({ items = [], value, defaultValue, onChange, style = {} }) {
  const [internal, setInternal] = React.useState(defaultValue ?? (items[0] && items[0].value));
  const active = value !== undefined ? value : internal;

  const select = (v) => {
    if (value === undefined) setInternal(v);
    onChange && onChange(v);
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 4,
        borderBottom: "1px solid var(--ay-border)",
        ...style,
      }}
    >
      {items.map((it) => {
        const on = it.value === active;
        return (
          <button
            key={it.value}
            onClick={() => select(it.value)}
            style={{
              position: "relative",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              border: "none",
              background: "transparent",
              padding: "0 4px 10px",
              marginBottom: -1,
              cursor: "pointer",
              fontFamily: "var(--ay-font-sans)",
              fontSize: 14,
              fontWeight: on ? 600 : 500,
              color: on ? "var(--ay-text)" : "var(--ay-text-muted)",
              borderBottom: `2px solid ${on ? "var(--ay-ink)" : "transparent"}`,
              transition: "color var(--ay-dur-fast) var(--ay-ease)",
            }}
          >
            {it.label}
            {it.count != null ? (
              <span
                style={{
                  fontFamily: "var(--ay-font-mono)",
                  fontSize: 11,
                  fontWeight: 500,
                  color: on ? "var(--ay-text-muted)" : "var(--ay-text-subtle)",
                  background: "var(--ay-bg-muted)",
                  borderRadius: "var(--ay-radius-full)",
                  padding: "1px 6px",
                }}
              >
                {it.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
