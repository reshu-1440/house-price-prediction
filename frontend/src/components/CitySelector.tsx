import { useState } from "react";
import { formatCityLabel, normalizeLocationSlug } from "../utils/validation";

interface CitySelectorProps {
  value: string;
  cities: string[];
  error?: string;
  onChange: (slug: string) => void;
}

const CUSTOM_OPTION = "__custom__";

export function CitySelector({ value, cities, error, onChange }: CitySelectorProps) {
  const normalizedValue = normalizeLocationSlug(value);
  const isKnownCity = cities.includes(normalizedValue);
  const [customMode, setCustomMode] = useState(!isKnownCity && normalizedValue !== "");

  const selectValue = customMode || (!isKnownCity && normalizedValue !== "")
    ? CUSTOM_OPTION
    : normalizedValue || cities[0] || "";

  return (
    <div className="field-group">
      <label htmlFor="location-select" className="field-label">
        City <span className="required-star">*</span>
      </label>

      <select
        id="location-select"
        className={`select-input ${error ? "input-error" : ""}`}
        value={selectValue}
        onChange={(e) => {
          const picked = e.target.value;
          if (picked === CUSTOM_OPTION) {
            setCustomMode(true);
            onChange(isKnownCity ? "" : value);
          } else {
            setCustomMode(false);
            onChange(picked);
          }
        }}
      >
        {cities.map((slug) => (
          <option key={slug} value={slug}>
            {formatCityLabel(slug)}
          </option>
        ))}
        <option value={CUSTOM_OPTION}>Other city (custom input)...</option>
      </select>

      {selectValue === CUSTOM_OPTION && (
        <input
          id="location-custom-input"
          type="text"
          className={`text-input custom-city-input ${error ? "input-error" : ""}`}
          value={value}
          placeholder="Enter city name (e.g. mysore, kochi)"
          maxLength={100}
          onChange={(e) => onChange(e.target.value)}
        />
      )}

      {error ? (
        <p className="field-error">{error}</p>
      ) : selectValue === CUSTOM_OPTION ? (
        <p className="field-hint">
          Cities outside the {cities.length} trained markets use global baseline pricing.
        </p>
      ) : null}
    </div>
  );
}
