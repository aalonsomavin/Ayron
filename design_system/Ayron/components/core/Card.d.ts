import * as React from "react";

/**
 * Surface container — white, hairline border, optional soft shadow.
 * @startingPoint section="Core" subtitle="Content surface with header" viewport="700x260"
 */
export interface CardProps {
  children?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Right-aligned header actions (buttons, menus). */
  actions?: React.ReactNode;
  /** Inner padding in px. @default 20 */
  padding?: number;
  /** Resting soft shadow. @default false */
  elevated?: boolean;
  /** Hover lift + pointer cursor (clickable cards). */
  interactive?: boolean;
  style?: React.CSSProperties;
}

export function Card(props: CardProps): JSX.Element;
