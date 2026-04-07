// Custom hexbin radius slider.
//
// Absolutely positioned over the map, top-left, outside Kepler's left panel.
// Reads the current `worldUnitSize` (km) off the live layer instance and
// dispatches `layerVisConfigChange` through `wrapTo('map')` so Kepler knows
// which map id to target.

import * as React from 'react';
import { useDispatch } from 'react-redux';
import { wrapTo, layerVisConfigChange } from '@kepler.gl/actions';
import { useHexbinLayer } from '../hooks/useHexbinLayer';

const forward = wrapTo('map');

// Debounce slider input so rapid scrubbing doesn't thrash the GPU re-bin.
const DEBOUNCE_MS = 150;

export function RadiusControl(): JSX.Element | null {
  const dispatch = useDispatch();
  const layer = useHexbinLayer();
  const [localValue, setLocalValue] = React.useState<number | null>(null);
  const timerRef = React.useRef<number | null>(null);

  // Sync local state with store when the layer first appears or its value
  // is changed from elsewhere (e.g. Kepler's own side panel).
  const storeValue: number | undefined = layer?.config?.visConfig?.worldUnitSize;
  React.useEffect(() => {
    if (storeValue !== undefined && localValue === null) {
      setLocalValue(storeValue);
    }
  }, [storeValue, localValue]);

  if (!layer || localValue === null) return null;

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const km = parseFloat(e.target.value);
    setLocalValue(km);
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
    }
    timerRef.current = window.setTimeout(() => {
      dispatch(forward(layerVisConfigChange(layer, { worldUnitSize: km })) as any);
    }, DEBOUNCE_MS);
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: 340,
        zIndex: 100,
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '10px 14px',
        borderRadius: 6,
        fontFamily:
          'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        pointerEvents: 'auto',
        userSelect: 'none'
      }}
    >
      <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>
        Hexbin radius: {localValue.toFixed(2)} km
      </label>
      <input
        type="range"
        min={0.05}
        max={2.0}
        step={0.05}
        value={localValue}
        onChange={onChange}
        style={{ width: 220 }}
      />
    </div>
  );
}
