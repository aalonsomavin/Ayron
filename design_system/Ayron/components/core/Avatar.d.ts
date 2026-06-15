import * as React from "react";

/** User / agent identity chip. Initials fallback or image; `agent` renders the ink Ayron mark. */
export interface AvatarProps {
  name?: string;
  src?: string | null;
  /** Pixel diameter. @default 32 */
  size?: number;
  /** Render the Ayron agent mark (ink). */
  agent?: boolean;
  /** Presence dot. */
  status?: "online" | "busy" | "offline" | null;
  style?: React.CSSProperties;
}

export function Avatar(props: AvatarProps): JSX.Element;
