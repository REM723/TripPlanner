import { useState, type FormEvent } from 'react';
import type { TripInput } from '../../api/types';
import { PREFERENCES } from '../../lib/preferences';
import { FormField } from './FormField';

interface InputFormProps {
  initialValue?: TripInput;
  onSubmit: (input: TripInput) => void;
}

interface FormValues {
  destination: string;
  adults: string;
  children: string;
  days: string;
  budgetInr: string;
  preferences: string[];
  hotelType: string;
  foodPreferences: string;
  mobilityConstraints: string;
  startingCity: string;
  mustVisitPlaces: string;
}

function toFormValues(input?: TripInput): FormValues {
  return {
    destination: input?.destination ?? '',
    adults: input ? String(input.adults) : '2',
    children: input ? String(input.children) : '0',
    days: input ? String(input.days) : '',
    budgetInr: input ? String(input.budgetInr) : '',
    preferences: input?.preferences ?? [],
    hotelType: input?.hotelType ?? 'Standard',
    foodPreferences: input?.foodPreferences ?? '',
    mobilityConstraints: input?.mobilityConstraints ?? '',
    startingCity: input?.startingCity ?? '',
    mustVisitPlaces: input?.mustVisitPlaces?.join(', ') ?? '',
  };
}

type Errors = Partial<Record<'budgetInr' | 'adults' | 'children' | 'days' | 'preferences', string>>;

function validate(values: FormValues): Errors {
  const errors: Errors = {};

  if (!values.budgetInr || Number(values.budgetInr) <= 0) {
    errors.budgetInr = 'Enter a budget greater than ₹0.';
  }
  if (values.adults === '' || Number(values.adults) < 1) {
    errors.adults = 'At least one adult is required.';
  }
  if (values.children !== '' && Number(values.children) < 0) {
    errors.children = 'Children cannot be negative.';
  }
  if (!values.days || Number(values.days) <= 0) {
    errors.days = 'Trip must be at least 1 day.';
  }
  if (values.preferences.length === 0) {
    errors.preferences = 'Pick at least one preference.';
  }

  return errors;
}

const inputClass =
  'rounded-lg border border-border bg-surface-raised px-3 py-2 text-ink outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft';

export function InputForm({ initialValue, onSubmit }: InputFormProps) {
  const [values, setValues] = useState<FormValues>(() => toFormValues(initialValue));
  const [errors, setErrors] = useState<Errors>({});

  function set<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function togglePreference(value: string) {
    setValues((prev) => ({
      ...prev,
      preferences: prev.preferences.includes(value)
        ? prev.preferences.filter((p) => p !== value)
        : [...prev.preferences, value],
    }));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validate(values);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    const mustVisitPlaces = values.mustVisitPlaces
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    onSubmit({
      destination: values.destination.trim() || undefined,
      adults: Number(values.adults),
      children: values.children === '' ? 0 : Number(values.children),
      days: Number(values.days),
      preferences: values.preferences,
      budgetInr: Number(values.budgetInr),
      hotelType: values.hotelType,
      foodPreferences: values.foodPreferences.trim() || undefined,
      mobilityConstraints: values.mobilityConstraints.trim() || undefined,
      startingCity: values.startingCity.trim() || undefined,
      mustVisitPlaces: mustVisitPlaces.length > 0 ? mustVisitPlaces : undefined,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto flex max-w-2xl flex-col gap-4 rounded-lg bg-surface/90 px-4 py-6">
      <img src="/Banner.png" alt="" className="w-full rounded-lg" />

      <div>
        <h1 className="text-2xl font-semibold text-ink">Plan your trip</h1>
        <p className="mt-1 text-ink-muted">
          Tell us your budget and a few preferences. We will suggest a destination and a day-by-day plan that fits.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <FormField label="Adults" htmlFor="adults" error={errors.adults}>
          <input
            id="adults"
            type="number"
            min={1}
            inputMode="numeric"
            className={inputClass}
            value={values.adults}
            onChange={(e) => set('adults', e.target.value)}
          />
        </FormField>
        <FormField label="Children" htmlFor="children" error={errors.children}>
          <input
            id="children"
            type="number"
            min={0}
            inputMode="numeric"
            className={inputClass}
            value={values.children}
            onChange={(e) => set('children', e.target.value)}
          />
        </FormField>
        <FormField label="Days" htmlFor="days" error={errors.days}>
          <input
            id="days"
            type="number"
            min={1}
            inputMode="numeric"
            className={inputClass}
            value={values.days}
            onChange={(e) => set('days', e.target.value)}
          />
        </FormField>
        <FormField label="Budget (₹)" htmlFor="budgetInr" error={errors.budgetInr}>
          <input
            id="budgetInr"
            type="number"
            min={1}
            inputMode="numeric"
            placeholder="80000"
            className={inputClass}
            value={values.budgetInr}
            onChange={(e) => set('budgetInr', e.target.value)}
          />
        </FormField>
      </div>

      <FormField label="What do you want to do there?" htmlFor="preferences" error={errors.preferences}>
        <div id="preferences" className="flex flex-wrap gap-2">
          {PREFERENCES.map((pref) => {
            const selected = values.preferences.includes(pref.value);
            return (
              <button
                key={pref.value}
                type="button"
                aria-pressed={selected}
                onClick={() => togglePreference(pref.value)}
                className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                  selected
                    ? 'border-accent bg-accent-soft text-accent-strong'
                    : 'border-border bg-surface-raised text-ink-muted hover:border-accent/50'
                }`}
              >
                {pref.label}
              </button>
            );
          })}
        </div>
      </FormField>

      <details className="group rounded-lg border border-border bg-surface-raised">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-ink-muted">
          More details (optional)
        </summary>
        <div className="flex flex-col gap-4 border-t border-border px-4 py-4">
          <FormField label="Destination" htmlFor="destination">
            <input
              id="destination"
              type="text"
              placeholder="Leave blank for a suggestion"
              className={inputClass}
              value={values.destination}
              onChange={(e) => set('destination', e.target.value)}
            />
          </FormField>
          <FormField label="Starting city" htmlFor="startingCity">
            <input
              id="startingCity"
              type="text"
              className={inputClass}
              value={values.startingCity}
              onChange={(e) => set('startingCity', e.target.value)}
            />
          </FormField>
          <FormField label="Hotel type" htmlFor="hotelType">
            <select
              id="hotelType"
              className={inputClass}
              value={values.hotelType}
              onChange={(e) => set('hotelType', e.target.value)}
            >
              <option value="Budget">Budget</option>
              <option value="Standard">Standard</option>
              <option value="Luxury">Luxury</option>
            </select>
          </FormField>
          <FormField label="Food preferences" htmlFor="foodPreferences">
            <input
              id="foodPreferences"
              type="text"
              placeholder="e.g. Vegetarian"
              className={inputClass}
              value={values.foodPreferences}
              onChange={(e) => set('foodPreferences', e.target.value)}
            />
          </FormField>
          <FormField label="Mobility constraints" htmlFor="mobilityConstraints">
            <input
              id="mobilityConstraints"
              type="text"
              placeholder="e.g. wheelchair access needed"
              className={inputClass}
              value={values.mobilityConstraints}
              onChange={(e) => set('mobilityConstraints', e.target.value)}
            />
          </FormField>
          <FormField label="Must-visit places" htmlFor="mustVisitPlaces">
            <input
              id="mustVisitPlaces"
              type="text"
              placeholder="Comma-separated"
              className={inputClass}
              value={values.mustVisitPlaces}
              onChange={(e) => set('mustVisitPlaces', e.target.value)}
            />
          </FormField>
        </div>
      </details>

      <button
        type="submit"
        className="rounded-lg bg-accent px-4 py-2.5 font-medium text-white transition-[transform,background-color] duration-150 ease-out hover:bg-accent-strong active:scale-[0.98]"
      >
        Plan my trip
      </button>
    </form>
  );
}
