/** Progress bar component */
import React from "react";
import { colors, spacing, typography, borderRadius } from "../styles/design-system";

interface ProgressBarProps {
  progress: number;
  label?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, label }) => {
  const styles = {
    container: {
      width: '100%',
    },
    
    labelContainer: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: spacing.sm,
    },
    
    label: {
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.primary,
    },
    
    percentage: {
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.semibold,
      color: colors.primary.main,
    },
    
    track: {
      width: '100%',
      height: '8px',
      backgroundColor: colors.neutral[200],
      borderRadius: borderRadius.full,
      overflow: 'hidden',
      position: 'relative' as const,
    },
    
    fill: {
      height: '100%',
      backgroundColor: colors.primary.light,
      background: `linear-gradient(90deg, ${colors.primary.main} 0%, ${colors.primary.light} 100%)`,
      borderRadius: borderRadius.full,
      transition: 'width 0.3s ease-out',
      width: `${Math.min(100, Math.max(0, progress))}%`,
      position: 'relative' as const,
    } as React.CSSProperties,
    
    shimmer: {
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
      animation: progress < 100 ? 'shimmer 2s infinite' : 'none',
    } as React.CSSProperties,
  };

  return (
    <div style={styles.container}>
      {label && (
        <div style={styles.labelContainer}>
          <div style={styles.label}>{label}</div>
          <div style={styles.percentage}>{Math.round(progress)}%</div>
        </div>
      )}
      <div style={styles.track}>
        <div style={styles.fill}>
          <div style={styles.shimmer} />
        </div>
      </div>
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  );
};
