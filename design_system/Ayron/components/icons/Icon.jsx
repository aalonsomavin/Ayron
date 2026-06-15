import React from "react";

/** Lucide icon path data used across Ayron. */
export const ICON_PATHS = {
  message:  '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
  dashboard:'<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
  zap:      '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  search:   '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  plus:     '<path d="M5 12h14"/><path d="M12 5v14"/>',
  send:     '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  sparkles: '<path d="M9.94 14.66 12 21l2.06-6.34L21 12l-6.94-2.66L12 3l-2.06 6.34L3 12z"/>',
  check:    '<path d="M20 6 9 17l-5-5"/>',
  clock:    '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  play:     '<polygon points="6 3 20 12 6 21 6 3"/>',
  chevright:'<path d="m9 18 6-6-6-6"/>',
  chevdown: '<path d="m6 9 6 6 6-6"/>',
  refresh:  '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  arrowup:  '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
  arrowdown:'<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
  table:    '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
  filter:   '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
  dots:     '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
  settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
};

/**
 * Inline SVG icon (Lucide path data). Inherits currentColor.
 */
export function Icon({ name, size = 18, stroke = 2, style = {} }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: "block", flex: "none", ...style }}
      dangerouslySetInnerHTML={{ __html: ICON_PATHS[name] || "" }}
    />
  );
}
