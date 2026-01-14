/** TESCON Design System - Colors, Typography, and Spacing */

export const colors = {
  // Primary Brand Colors (TESCON)
  primary: {
    main: '#1B4F72',
    hover: '#2874A6',
    light: '#3498DB',
  },
  
  // Neutral Colors
  neutral: {
    50: '#FAFBFC',
    100: '#F5F6F7',
    200: '#ECF0F1',
    300: '#D5DBDB',
    400: '#BDC3C7',
    500: '#95A5A6',
    600: '#7F8C8D',
    700: '#5D6D7E',
    800: '#2C3E50',
    900: '#1C2833',
  },
  
  // Status Colors
  success: '#27AE60',
  warning: '#F39C12',
  error: '#E74C3C',
  info: '#3498DB',
  
  // Background
  background: {
    main: '#FFFFFF',
    secondary: '#F8F9FA',
  },
  
  // Text
  text: {
    primary: '#2C3E50',
    secondary: '#5D6D7E',
    tertiary: '#95A5A6',
    inverse: '#FFFFFF',
  },
};

export const typography = {
  fontFamily: {
    base: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", "Segoe UI", "Roboto", sans-serif',
    mono: '"SF Mono", "Roboto Mono", "Courier New", monospace',
  },
  
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '32px',
    '4xl': '40px',
  },
  
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
};

export const spacing = {
  xs: '8px',
  sm: '12px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
  '3xl': '64px',
  '4xl': '80px',
};

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px rgba(0, 0, 0, 0.1)',
  md: '0 4px 6px rgba(0, 0, 0, 0.07)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px rgba(0, 0, 0, 0.1)',
};

export const transitions = {
  fast: '150ms ease-in-out',
  base: '200ms ease-in-out',
  slow: '300ms ease-in-out',
};

export const breakpoints = {
  mobile: '768px',
  tablet: '1024px',
  desktop: '1440px',
};

