import * as React from "react";

/** Inline SVG icon rendering Lucide path data; inherits currentColor. */
export interface IconProps {
  /** Icon key (Lucide-based set). */
  name: "message" | "dashboard" | "database" | "zap" | "search" | "plus" | "send" |
        "sparkles" | "check" | "clock" | "play" | "chevright" | "chevdown" | "refresh" |
        "arrowup" | "arrowdown" | "table" | "filter" | "dots" | "settings";
  /** Pixel size. @default 18 */
  size?: number;
  /** Stroke width. @default 2 */
  stroke?: number;
  style?: React.CSSProperties;
}

export const ICON_PATHS: Record<string, string>;
export function Icon(props: IconProps): JSX.Element;
