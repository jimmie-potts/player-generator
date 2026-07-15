import type { ReactNode } from "react";

export interface SectionHelpProps {
  children: ReactNode;
  className?: string;
  defaultOpen?: boolean;
  title: string;
}

export function SectionHelp({
  children,
  className = "",
  defaultOpen = false,
  title,
}: SectionHelpProps) {
  const classes = ["section-help", className].filter(Boolean).join(" ");

  return (
    <details className={classes} open={defaultOpen}>
      <summary>{title}</summary>
      <div className="section-help__content">{children}</div>
    </details>
  );
}
