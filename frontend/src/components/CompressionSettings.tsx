/** Compression settings component */
import React from "react";
import { Sliders, Info } from "lucide-react";
import { colors, spacing, typography, borderRadius, transitions } from "../styles/design-system";

interface CompressionSettingsProps {
  quality: number;
  maxDimension: number;
  onQualityChange: (quality: number) => void;
  onMaxDimensionChange: (dimension: number) => void;
}

export const CompressionSettings: React.FC<CompressionSettingsProps> = ({
  quality,
  maxDimension,
  onQualityChange,
  onMaxDimensionChange,
}) => {
  const presets = [
    { name: "High Quality", quality: 95, dimension: 4096, desc: "Largest files" },
    { name: "Balanced", quality: 85, dimension: 2048, desc: "Recommended" },
    { name: "Web Optimized", quality: 80, dimension: 1600, desc: "Smaller files" },
    { name: "Compact", quality: 75, dimension: 1200, desc: "Smallest" },
  ];

  const styles = {
    container: {
      marginBottom: spacing.md,
    },
    
    label: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.primary,
      marginBottom: spacing.xs,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.xs,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
    },
    
    presetGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: spacing.xs,
      marginBottom: spacing.sm,
    },
    
    presetButton: {
      padding: spacing.xs,
      fontSize: '11px',
      fontWeight: typography.fontWeight.medium,
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.sm,
      backgroundColor: colors.background.main,
      cursor: 'pointer',
      transition: `all ${transitions.fast}`,
      textAlign: 'left' as const,
    } as React.CSSProperties,
    
    presetName: {
      display: 'block',
      fontWeight: typography.fontWeight.semibold,
      marginBottom: '2px',
    },
    
    presetDesc: {
      display: 'block',
      color: colors.text.tertiary,
      fontSize: '10px',
    },
    
    slider: {
      width: '100%',
      height: '4px',
      marginTop: spacing.xs,
    },
    
    sliderLabel: {
      fontSize: '11px',
      color: colors.text.secondary,
      marginTop: '4px',
      display: 'flex',
      justifyContent: 'space-between',
    },
    
    tooltip: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '14px',
      height: '14px',
      borderRadius: borderRadius.full,
      backgroundColor: colors.neutral[200],
      cursor: 'help',
    },
  };

  return (
    <div style={styles.container}>
      <div style={styles.label}>
        <Sliders size={12} />
        Compression
        <div style={styles.tooltip} title="Reduce file size while maintaining quality">
          <Info size={10} color={colors.text.tertiary} />
        </div>
      </div>

      <div style={styles.presetGrid}>
        {presets.map((preset) => (
          <button
            key={preset.name}
            style={{
              ...styles.presetButton,
              borderColor: quality === preset.quality && maxDimension === preset.dimension 
                ? colors.primary.main 
                : colors.neutral[300],
              backgroundColor: quality === preset.quality && maxDimension === preset.dimension
                ? `${colors.primary.light}10`
                : colors.background.main,
            }}
            onClick={() => {
              onQualityChange(preset.quality);
              onMaxDimensionChange(preset.dimension);
            }}
          >
            <span style={styles.presetName}>{preset.name}</span>
            <span style={styles.presetDesc}>{preset.desc}</span>
          </button>
        ))}
      </div>

      <div>
        <div style={{ fontSize: '10px', color: colors.text.secondary, marginBottom: '4px' }}>
          Quality: {quality}% • Max size: {maxDimension}px
        </div>
      </div>
    </div>
  );
};

