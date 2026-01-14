/** Validation summary display */
import React from "react";
import { FilenameValidationResponse } from "../types";
import { Package, CheckCircle2, AlertCircle, FileText } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows } from "../styles/design-system";

interface ValidationSummaryProps {
  validation: FilenameValidationResponse;
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({ validation }) => {
  const styles = {
    card: {
      padding: spacing.md,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.md,
      marginBottom: spacing.md,
    },
    
    title: {
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: spacing.sm,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.xs,
    },
    
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: spacing.xs,
    },
    
    stat: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing.xs,
      fontSize: typography.fontSize.xs,
      padding: spacing.xs,
      backgroundColor: colors.neutral[50],
      borderRadius: borderRadius.sm,
    },
    
    statLabel: {
      color: colors.text.secondary,
    },
    
    statValue: {
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
    },
    
    partsSection: {
      marginTop: spacing.sm,
      paddingTop: spacing.sm,
      borderTop: `1px solid ${colors.neutral[200]}`,
    },
    
    partsTitle: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.secondary,
      marginBottom: spacing.xs,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
    },
    
    partsList: {
      display: 'flex',
      flexWrap: 'wrap' as const,
      gap: spacing.xs,
    },
    
    partBadge: {
      padding: `4px ${spacing.xs}`,
      backgroundColor: colors.primary.light + '15',
      color: colors.primary.main,
      borderRadius: borderRadius.sm,
      fontSize: '10px',
      fontWeight: typography.fontWeight.medium,
      fontFamily: typography.fontFamily.mono,
    },
  };

  return (
    <div style={styles.card}>
      <div style={styles.title}>
        <FileText size={14} />
        Upload Summary
      </div>

      <div style={styles.statsGrid}>
        <div style={styles.stat}>
          <CheckCircle2 size={12} color={colors.success} />
          <span style={styles.statLabel}>Valid:</span>
          <span style={styles.statValue}>{validation.valid_files}</span>
        </div>
        
        <div style={styles.stat}>
          <AlertCircle size={12} color={colors.error} />
          <span style={styles.statLabel}>Invalid:</span>
          <span style={styles.statValue}>{validation.invalid_files}</span>
        </div>
        
        <div style={styles.stat}>
          <Package size={12} color={colors.primary.main} />
          <span style={styles.statLabel}>Parts:</span>
          <span style={styles.statValue}>{validation.unique_parts}</span>
        </div>
        
        <div style={styles.stat}>
          <FileText size={12} color={colors.text.secondary} />
          <span style={styles.statLabel}>Total:</span>
          <span style={styles.statValue}>{validation.total_files}</span>
        </div>
      </div>

      {validation.parts_summary && validation.parts_summary.length > 0 && (
        <div style={styles.partsSection}>
          <div style={styles.partsTitle}>Part Numbers Found:</div>
          <div style={styles.partsList}>
            {validation.parts_summary.slice(0, 10).map((part, index) => (
              <div key={index} style={styles.partBadge} title={`${part.view_count} views`}>
                {part.part_number} ({part.view_count})
              </div>
            ))}
            {validation.parts_summary.length > 10 && (
              <div style={{ ...styles.partBadge, backgroundColor: colors.neutral[100], color: colors.text.secondary }}>
                +{validation.parts_summary.length - 10} more
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

