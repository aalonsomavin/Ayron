import * as React from "react";

/** Text field with hairline border and blue focus ring. */
export interface InputProps {
  value?: string;
  defaultValue?: string;
  placeholder?: string;
  type?: string;
  /** @default "md" */
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  /** Error state — red border + ring. */
  invalid?: boolean;
  /** Leading adornment (icon node). */
  leading?: React.ReactNode;
  /** Trailing adornment (icon / shortcut hint). */
  trailing?: React.ReactNode;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  style?: React.CSSProperties;
}

export function Input(props: InputProps): JSX.Element;
