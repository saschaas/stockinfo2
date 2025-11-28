/**
 * Design System Theme Configuration
 *
 * This file contains all design tokens for the application.
 * Modify values here to change the look and feel across the entire app.
 */

export const theme = {
  colors: {
    // Background colors - warm cream tones
    background: {
      primary: '#FDF8F3',     // Main page background (warm cream)
      secondary: '#FAF5EF',   // Alternate sections
      tertiary: '#F5EDE4',    // Darker cream for emphasis
      card: '#FFFFFF',        // Card backgrounds
    },

    // Primary accent - Teal (professional, financial)
    primary: {
      50: '#F0F9F7',
      100: '#D1F0E9',
      200: '#A3E1D4',
      300: '#75D1BE',
      400: '#47C2A9',
      500: '#2A9D8F',   // Primary accent
      600: '#238577',
      700: '#1C6D5F',
      800: '#155447',
      900: '#0E3C2F',
    },

    // Semantic colors - muted, soft palette
    success: {
      bg: '#E8F5E9',
      light: '#C8E6C9',
      main: '#4CAF50',
      dark: '#2E7D32',
      text: '#1B5E20',
    },
    warning: {
      bg: '#FFF8E1',
      light: '#FFE082',
      main: '#FFB300',
      dark: '#FF8F00',
      text: '#E65100',
    },
    danger: {
      bg: '#FFEBEE',
      light: '#EF9A9A',
      main: '#E57373',
      dark: '#D32F2F',
      text: '#B71C1C',
    },
    neutral: {
      bg: '#F5F5F5',
      light: '#E0E0E0',
      main: '#9E9E9E',
      dark: '#616161',
      text: '#212121',
    },

    // Text colors
    text: {
      primary: '#2D3748',
      secondary: '#4A5568',
      muted: '#718096',
      inverse: '#FFFFFF',
    },

    // Border colors - warm tones
    border: {
      light: '#E8E0D8',
      main: '#D4C8BC',
      dark: '#B8A99A',
    },
  },

  // Typography
  typography: {
    fontFamily: {
      sans: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      mono: '"JetBrains Mono", "Fira Code", Consolas, monospace',
    },
    fontSize: {
      xs: '0.75rem',     // 12px
      sm: '0.875rem',    // 14px
      base: '1rem',      // 16px
      lg: '1.125rem',    // 18px
      xl: '1.25rem',     // 20px
      '2xl': '1.5rem',   // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem',  // 36px
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75,
    },
  },

  // Border Radius - generous rounding
  borderRadius: {
    sm: '0.375rem',   // 6px
    md: '0.5rem',     // 8px
    lg: '0.75rem',    // 12px
    xl: '1rem',       // 16px
    '2xl': '1.25rem', // 20px - card default
    '3xl': '1.5rem',  // 24px
    full: '9999px',
  },

  // Shadows - soft, subtle
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.03)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
    card: '0 2px 8px rgba(0, 0, 0, 0.04), 0 4px 24px rgba(0, 0, 0, 0.02)',
    elevated: '0 4px 12px rgba(0, 0, 0, 0.08), 0 8px 32px rgba(0, 0, 0, 0.04)',
  },

  // Spacing scale
  spacing: {
    xs: '0.25rem',  // 4px
    sm: '0.5rem',   // 8px
    md: '1rem',     // 16px
    lg: '1.5rem',   // 24px
    xl: '2rem',     // 32px
    '2xl': '3rem',  // 48px
    '3xl': '4rem',  // 64px
  },

  // Transitions
  transitions: {
    fast: '150ms ease',
    normal: '250ms ease',
    slow: '350ms ease',
  },
} as const;

// Decision/Recommendation colors for investment signals
export const decisionColors = {
  strongBuy: {
    bg: '#E8F5E9',
    text: '#1B5E20',
    border: '#A5D6A7',
    gradient: 'linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%)',
  },
  buy: {
    bg: '#F1F8E9',
    text: '#33691E',
    border: '#C5E1A5',
    gradient: 'linear-gradient(135deg, #F1F8E9 0%, #DCEDC8 100%)',
  },
  hold: {
    bg: '#FFF8E1',
    text: '#F57F17',
    border: '#FFE082',
    gradient: 'linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%)',
  },
  sell: {
    bg: '#FFF3E0',
    text: '#E65100',
    border: '#FFCC80',
    gradient: 'linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%)',
  },
  strongSell: {
    bg: '#FFEBEE',
    text: '#B71C1C',
    border: '#EF9A9A',
    gradient: 'linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%)',
  },
  avoid: {
    bg: '#FFEBEE',
    text: '#C62828',
    border: '#EF9A9A',
    gradient: 'linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%)',
  },
} as const;

// Risk level colors
export const riskColors = {
  low: {
    bg: '#E8F5E9',
    text: '#2E7D32',
    main: '#4CAF50',
  },
  medium: {
    bg: '#FFF8E1',
    text: '#F57F17',
    main: '#FFB300',
  },
  elevated: {
    bg: '#FFF3E0',
    text: '#E65100',
    main: '#FF9800',
  },
  high: {
    bg: '#FFEBEE',
    text: '#C62828',
    main: '#F44336',
  },
} as const;

// Signal colors for technical indicators
export const signalColors = {
  bullish: {
    bg: '#E8F5E9',
    text: '#2E7D32',
    main: '#4CAF50',
  },
  bearish: {
    bg: '#FFEBEE',
    text: '#C62828',
    main: '#F44336',
  },
  neutral: {
    bg: '#F5F5F5',
    text: '#616161',
    main: '#9E9E9E',
  },
} as const;

// Helper function to get decision color based on decision string
export function getDecisionColor(decision: string) {
  const normalized = decision.toLowerCase().replace(/[^a-z]/g, '');
  if (normalized.includes('strongbuy')) return decisionColors.strongBuy;
  if (normalized.includes('buy')) return decisionColors.buy;
  if (normalized.includes('hold')) return decisionColors.hold;
  if (normalized.includes('strongsell')) return decisionColors.strongSell;
  if (normalized.includes('sell')) return decisionColors.sell;
  if (normalized.includes('avoid')) return decisionColors.avoid;
  return decisionColors.hold;
}

// Helper function to get risk color based on risk level
export function getRiskColor(level: string) {
  const normalized = level.toLowerCase();
  if (normalized.includes('low')) return riskColors.low;
  if (normalized.includes('medium') || normalized.includes('moderate')) return riskColors.medium;
  if (normalized.includes('elevated')) return riskColors.elevated;
  if (normalized.includes('high')) return riskColors.high;
  return riskColors.medium;
}

// Helper function to get signal color based on signal type
export function getSignalColor(signal: string) {
  const normalized = signal.toLowerCase();
  if (normalized.includes('bullish') || normalized.includes('buy') || normalized.includes('positive')) {
    return signalColors.bullish;
  }
  if (normalized.includes('bearish') || normalized.includes('sell') || normalized.includes('negative')) {
    return signalColors.bearish;
  }
  return signalColors.neutral;
}

export default theme;
