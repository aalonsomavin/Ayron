import * as React from "react";

export interface TabItem {
  value: string;
  label: React.ReactNode;
  /** Optional count chip. */
  count?: number;
}

/** Underline tab bar. Controlled (value/onChange) or uncontrolled (defaultValue). */
export interface TabsProps {
  items: TabItem[];
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  style?: React.CSSProperties;
}

export function Tabs(props: TabsProps): JSX.Element;
