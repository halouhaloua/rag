export interface ColorScheme {
  name: string;
  baseHue: number;
  hueRange: number;
  saturation: [number, number];
  lightness: [number, number];
}

export const presetColorSchemes: Record<string, ColorScheme> = {
  vibrant: {
    name: '鲜艳色系',
    baseHue: 0,
    hueRange: 360,
    saturation: [70, 85],
    lightness: [45, 55],
  },
  pastel: {
    name: '柔和色系',
    baseHue: 0,
    hueRange: 360,
    saturation: [50, 65],
    lightness: [65, 75],
  },
  ocean: {
    name: '海洋色系',
    baseHue: 180,
    hueRange: 120,
    saturation: [60, 80],
    lightness: [40, 60],
  },
  forest: {
    name: '森林色系',
    baseHue: 90,
    hueRange: 90,
    saturation: [55, 75],
    lightness: [35, 50],
  },
  sunset: {
    name: '日落色系',
    baseHue: 0,
    hueRange: 60,
    saturation: [70, 90],
    lightness: [50, 65],
  },
  corporate: {
    name: '商务色系',
    baseHue: 210,
    hueRange: 180,
    saturation: [45, 65],
    lightness: [40, 55],
  },
};

const SCHEME_PREVIEW_COUNT = 5;

function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${f(0)}${f(8)}${f(4)}`;
}

function generateColorForIndex(
  scheme: ColorScheme,
  index: number,
  total: number,
): string {
  const { baseHue, hueRange, saturation, lightness } = scheme;
  const hueStep = hueRange / Math.max(total, 1);
  const hue = (baseHue + index * hueStep) % 360;
  const satRange = saturation[1] - saturation[0];
  const sat = saturation[0] + (Math.sin(index * 0.5) * 0.5 + 0.5) * satRange;
  const lightRange = lightness[1] - lightness[0];
  const light = lightness[0] + (Math.cos(index * 0.7) * 0.5 + 0.5) * lightRange;
  return hslToHex(hue, sat, light);
}

export class EntityColorService {
  private colorMap: Map<string, string> = new Map();
  private entityTypes: string[] = [];
  private scheme: ColorScheme;

  constructor(scheme?: ColorScheme) {
    this.scheme = scheme ?? presetColorSchemes.vibrant;
    if (!this.scheme) {
      this.scheme = {
        name: 'vibrant',
        baseHue: 0,
        hueRange: 360,
        saturation: [70, 85],
        lightness: [45, 55],
      };
    }
  }

  clear() {
    this.colorMap.clear();
    this.entityTypes = [];
  }

  getColor(entityType: string): string {
    if (!this.colorMap.has(entityType)) {
      this.updateEntityTypes([...this.entityTypes, entityType]);
    }
    return this.colorMap.get(entityType) || '#9bb5ff';
  }

  getColorMap(): Record<string, string> {
    const result: Record<string, string> = {};
    this.colorMap.forEach((color, type) => {
      result[type] = color;
    });
    return result;
  }

  getEntityTypes(): string[] {
    return [...this.entityTypes];
  }

  getScheme(): ColorScheme {
    return { ...this.scheme };
  }

  setScheme(scheme: ColorScheme) {
    this.scheme = scheme;
    this.regenerateColors();
  }

  setSchemeByName(schemeName: string) {
    const scheme = presetColorSchemes[schemeName];
    if (scheme) {
      this.setScheme(scheme);
    }
  }

  updateEntityTypes(types: string[]) {
    const newTypes = [...new Set(types)].sort();
    const hasChanged =
      newTypes.length !== this.entityTypes.length ||
      newTypes.some((t, i) => t !== this.entityTypes[i]);
    if (hasChanged) {
      this.entityTypes = newTypes;
      this.regenerateColors();
    }
  }

  private regenerateColors() {
    const total = this.entityTypes.length;
    const newColorMap = new Map<string, string>();
    this.entityTypes.forEach((type, index) => {
      const color = generateColorForIndex(this.scheme, index, total);
      newColorMap.set(type, color);
    });
    this.colorMap = newColorMap;
  }
}

export const entityColorService = new EntityColorService();

export function getSchemePreviewDots(schemeName: string): string[] {
  const scheme = presetColorSchemes[schemeName] || presetColorSchemes.vibrant;
  if (!scheme) return [];
  return Array.from({ length: SCHEME_PREVIEW_COUNT }, (_, i) =>
    generateColorForIndex(scheme, i, SCHEME_PREVIEW_COUNT),
  );
}
