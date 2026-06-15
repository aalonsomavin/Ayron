import * as React from "react";

/** Binary toggle — ink track when on. */
export interface SwitchProps {
  checked?: boolean;
  defaultChecked?: boolean;
  disabled?: boolean;
  /** @default "md" */
  size?: "sm" | "md";
  onChange?: (checked: boolean) => void;
  style?: React.CSSProperties;
}

export function Switch(props: SwitchProps): JSX.Element;
