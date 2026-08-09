export const palette = {
  ink: "#10231B",
  muted: "#52645C",
  canvas: "#F4F8F5",
  surface: "#FFFFFF",
  forest: "#0C6B45",
  forestDark: "#084B32",
  mint: "#DDF4E9",
  amber: "#A85B00",
  amberSoft: "#FFF0D5",
  red: "#A92D35",
  redSoft: "#FCE7E8",
  blue: "#215AA8",
  blueSoft: "#E8F0FC",
  border: "#CCD9D1",
  focus: "#006DFF",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;
export const radius = { sm: 8, md: 14, lg: 22, pill: 999 } as const;
export const typeScale = {
  caption: 13,
  body: 16,
  title: 24,
  display: 34,
} as const;
export const minTouchTarget = 48;

export const appTheme = {
  palette,
  spacing,
  radius,
  typeScale,
  minTouchTarget,
} as const;
export type AppTheme = typeof appTheme;
