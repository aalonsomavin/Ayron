import * as React from "react";

/**
 * Primary action button for Ayron. Solid near-black ink by default.
 * @startingPoint section="Core" subtitle="Buttons in every variant & size" viewport="700x220"
 */
export interface ButtonProps {
  children?: React.ReactNode;
  /** Visual style. @default "primary" */
  variant?: "primary" | "secondary" | "ghost" | "danger" | "link";
  /** @default "md" */
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
  type?: "button" | "submit" | "reset";
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  style?: React.CSSProperties;
}

export function Button(props: ButtonProps): JSX.Element;
