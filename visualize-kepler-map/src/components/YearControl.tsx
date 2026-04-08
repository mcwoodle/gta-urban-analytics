import * as React from 'react';

export interface YearControlProps {
  year: number;
  setYear: (y: number) => void;
  years?: number[];
}

export function YearControl({
  year,
  setYear,
  years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
}: YearControlProps): JSX.Element | null {
  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const y = parseInt(e.target.value, 10);
    setYear(y);
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: 600, // Placed to the right of the RadiusControl
        zIndex: 100,
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '10px 14px',
        borderRadius: 6,
        fontFamily: 'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        pointerEvents: 'auto',
        userSelect: 'none',
        display: 'flex',
        alignItems: 'center',
        gap: '10px'
      }}
    >
      <label style={{ fontWeight: 600 }}>Data Year:</label>
      <select
        value={year}
        onChange={onChange}
        style={{
          background: '#1f262e',
          color: '#e6e6e6',
          border: '1px solid #3a4552',
          padding: '4px 8px',
          borderRadius: 4,
          outline: 'none',
          cursor: 'pointer',
          fontFamily: 'inherit'
        }}
      >
        {years.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </div>
  );
}
