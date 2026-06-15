import * as React from "react";

/** Small status/label pill. */
export interface BadgeProps {
  children?: React.ReactNode;
  /** @default "neutral" */
  tone?: "neutral" | "accent" | "success" | "warning" | "danger" | "info";
  /** @default "soft" */
  variant?: "soft" | "solid" | "outline";
  /** Show a leading status dot. */
  dot?: boolean;
  style?: React.CSSProperties;
}

export function Badge(props: BadgeProps): JSX.Element;
