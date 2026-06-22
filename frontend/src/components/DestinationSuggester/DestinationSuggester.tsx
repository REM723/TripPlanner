import { useState } from 'react';

interface DestinationSuggesterProps {
  recommended: string;
  alternatives: string[];
  onConfirm: () => void;
  onChooseDifferent: (destination: string) => void;
}

export function DestinationSuggester({
  recommended,
  alternatives,
  onConfirm,
  onChooseDifferent,
}: DestinationSuggesterProps) {
  const others = alternatives.filter((d) => d !== recommended);
  const [selected, setSelected] = useState(recommended);

  function handleContinue() {
    if (selected === recommended) onConfirm();
    else onChooseDifferent(selected);
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10">
      <div>
        <h1 className="text-2xl font-semibold text-ink">We picked a destination for you</h1>
        <p className="mt-1 text-ink-muted">Based on your budget, days, and preferences. Pick a different one if you'd rather go elsewhere.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => setSelected(recommended)}
          className={`flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-transform duration-150 ease-out active:scale-[0.98] ${
            selected === recommended ? 'border-accent bg-accent-soft' : 'border-border bg-surface-raised hover:border-accent/50'
          }`}
        >
          <span className="text-lg font-semibold text-ink">{recommended}</span>
        </button>

        {others.map((destination) => (
          <button
            key={destination}
            type="button"
            onClick={() => setSelected(destination)}
            className={`flex flex-col items-start gap-1 rounded-xl border-2 p-4 text-left transition-transform duration-150 ease-out active:scale-[0.98] ${
              selected === destination ? 'border-accent bg-accent-soft' : 'border-border bg-surface-raised hover:border-accent/50'
            }`}
          >
            <span className="text-lg font-semibold text-ink">{destination}</span>
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={handleContinue}
        className="self-start rounded-lg bg-accent px-4 py-2.5 font-medium text-white transition-[transform,background-color] duration-150 ease-out hover:bg-accent-strong active:scale-[0.98]"
      >
        Continue
      </button>
    </div>
  );
}
