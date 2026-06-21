// ========================================================================
// Lite-profile shader patch: disable flat shading on EnhancedColumnLayer
// ========================================================================
//
// Root cause: deck.gl's H3HexagonLayer hardcodes `flatShading: true` when
// creating the hexagon-cell sublayer (EnhancedColumnLayer). This triggers
// a `#define FLAT_SHADING 1` in the column layer's fragment shader, which
// includes a block using `dFdx`/`dFdy` derivatives plus the phong/gouraud
// lighting module. Certain mobile GPUs (confirmed on real Android devices)
// reject this GLSL — the EnhancedColumnLayer fails to compile its fragment
// shader and the map crashes.
//
// Fix (lite profile only): monkey-patch EnhancedColumnLayer.prototype.getShaders
// to strip the FLAT_SHADING define from the returned shader config. This
// prevents the derivative-based lighting block from being compiled at all,
// while keeping enable3d/extrusion (z-height geometry is controlled by the
// `extruded` prop and vertex shader, not by the FLAT_SHADING fragment block).
// The columns render flat-colored by count, which is acceptable for mobile.
//
// The full/desktop build is unaffected — the guard checks getProfile().
// ========================================================================

import { EnhancedColumnLayer } from '@kepler.gl/deckgl-layers';
import { getProfile } from '../config/visualization';

/**
 * Apply the lite-profile shader patch. Call once at app startup, before
 * any Kepler layers are constructed.
 *
 * Safe to call unconditionally — it no-ops when profile !== 'lite'.
 */
export function applyLiteLightingPatch(): void {
  if (getProfile() !== 'lite') {
    return;
  }

  const OriginalGetShaders = EnhancedColumnLayer.prototype.getShaders;

  EnhancedColumnLayer.prototype.getShaders = function patchedGetShaders(
    this: InstanceType<typeof EnhancedColumnLayer>,
    ...args: any[]
  ) {
    // Temporarily override this.props.flatShading so the parent ColumnLayer's
    // getShaders() never sets defines.FLAT_SHADING = 1.
    const originalFlatShading = (this as any).props?.flatShading;
    if ((this as any).props) {
      (this as any).props.flatShading = false;
    }

    const shaders = OriginalGetShaders.apply(this, args);

    // Restore original prop value to avoid side-effects on other code paths
    if ((this as any).props) {
      (this as any).props.flatShading = originalFlatShading;
    }

    // Belt-and-suspenders: also strip FLAT_SHADING from defines if it somehow
    // got set (e.g., if the parent class logic changes in a future version)
    if (shaders.defines && shaders.defines.FLAT_SHADING !== undefined) {
      delete shaders.defines.FLAT_SHADING;
    }

    return shaders;
  };

  // Also set material: false on the class defaultProps. When deck.gl's
  // lighting module sees material=false, it sets lighting_uEnabled=false
  // in the shader uniforms. This is an additional safety net — even if
  // FLAT_SHADING were somehow still defined, the lighting function would
  // effectively be a no-op.
  if (EnhancedColumnLayer.defaultProps) {
    (EnhancedColumnLayer.defaultProps as any).material = false;
  } else {
    (EnhancedColumnLayer as any).defaultProps = { material: false };
  }

  // eslint-disable-next-line no-console
  console.info(
    '[viz] lite profile: patched EnhancedColumnLayer to disable flat shading + lighting'
  );
}
