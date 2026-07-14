import {
  useId,
  useRef,
  type KeyboardEvent,
  type ReactNode,
} from "react";

export type ComparisonMode = "tiers" | "top25" | "custom";

export interface ComparisonModeTabsProps {
  selectedMode: ComparisonMode;
  onModeChange: (mode: ComparisonMode) => void;
  children: ReactNode;
  label?: string;
}

const MODES: ReadonlyArray<{ mode: ComparisonMode; label: string }> = [
  { mode: "tiers", label: "Tier sample" },
  { mode: "top25", label: "Top 25" },
  { mode: "custom", label: "Custom list" },
];

export function ComparisonModeTabs({
  selectedMode,
  onModeChange,
  children,
  label = "Comparison player set",
}: ComparisonModeTabsProps) {
  const instanceId = useId();
  const tabRefs = useRef(new Map<ComparisonMode, HTMLButtonElement>());

  const tabId = (mode: ComparisonMode) => `${instanceId}-${mode}-tab`;
  const panelId = (mode: ComparisonMode) => `${instanceId}-${mode}-panel`;

  function selectFromKeyboard(
    event: KeyboardEvent<HTMLButtonElement>,
    currentMode: ComparisonMode,
  ) {
    const currentIndex = MODES.findIndex(({ mode }) => mode === currentMode);
    let nextIndex: number | null = null;

    switch (event.key) {
      case "ArrowLeft":
        nextIndex = (currentIndex - 1 + MODES.length) % MODES.length;
        break;
      case "ArrowRight":
        nextIndex = (currentIndex + 1) % MODES.length;
        break;
      case "Home":
        nextIndex = 0;
        break;
      case "End":
        nextIndex = MODES.length - 1;
        break;
      default:
        return;
    }

    event.preventDefault();
    const mode = MODES[nextIndex].mode;
    onModeChange(mode);
    tabRefs.current.get(mode)?.focus();
  }

  return (
    <div className="comparison-mode-tabs">
      <div className="comparison-mode-tabs__list" role="tablist" aria-label={label}>
        {MODES.map(({ mode, label: modeLabel }) => {
          const selected = selectedMode === mode;
          return (
            <button
              key={mode}
              ref={(node) => {
                if (node) tabRefs.current.set(mode, node);
                else tabRefs.current.delete(mode);
              }}
              className="comparison-mode-tabs__tab"
              id={tabId(mode)}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={panelId(mode)}
              tabIndex={selected ? 0 : -1}
              onClick={() => onModeChange(mode)}
              onKeyDown={(event) => selectFromKeyboard(event, mode)}
            >
              {modeLabel}
            </button>
          );
        })}
      </div>
      {MODES.map(({ mode }) => {
        const selected = selectedMode === mode;
        return (
          <div
            key={mode}
            className="comparison-mode-tabs__panel"
            id={panelId(mode)}
            role="tabpanel"
            aria-labelledby={tabId(mode)}
            tabIndex={selected ? 0 : -1}
            hidden={!selected}
          >
            {selected ? children : null}
          </div>
        );
      })}
    </div>
  );
}
