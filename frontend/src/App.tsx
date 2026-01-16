/** Main application component */
import React, { useState, useEffect } from "react";
import { ProcessPartResponse } from "./types";
import { healthCheck } from "./services/api";
import { CheckCircle2, XCircle } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows } from "./styles/design-system";
import { StepByStepWorkflow } from "./components/StepByStepWorkflow";

function App() {
  const [health, setHealth] = useState<{ gpu_available: boolean; model_loaded: boolean } | null>(null);

  useEffect(() => {
    healthCheck()
      .then((data) => {
        setHealth({ gpu_available: data.gpu_available, model_loaded: data.model_loaded });
      })
      .catch((error) => {
        console.error("Health check failed:", error);
      });
  }, []);


  const styles = {
    container: {
      height: '100vh',
      display: 'flex',
      flexDirection: 'column' as const,
      maxWidth: '1200px',
      margin: '0 auto',
      padding: `${spacing.xl} ${spacing.xl}`,
      fontFamily: typography.fontFamily.base,
    } as React.CSSProperties,

    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: spacing.lg,
      flexShrink: 0,
    },

    logoAndTitle: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing.md,
    },

    logo: {
      height: '48px',
      width: 'auto',
    },

    titleGroup: {
      display: 'flex',
      flexDirection: 'column' as const,
    },

    title: {
      fontSize: typography.fontSize['2xl'],
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      letterSpacing: '-0.02em',
      lineHeight: 1.2,
    },

    subtitle: {
      fontSize: typography.fontSize.sm,
      color: colors.text.secondary,
      fontWeight: typography.fontWeight.normal,
    },

    healthBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: spacing.xs,
      padding: `${spacing.xs} ${spacing.sm}`,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.md,
      fontSize: typography.fontSize.xs,
      color: colors.text.secondary,
      boxShadow: shadows.sm,
    },

    healthIcon: {
      width: '14px',
      height: '14px',
    },
  };

  return (
    <div style={styles.container} data-responsive-container>
      <div style={styles.header}>
        <div style={styles.logoAndTitle} data-logo-title>
          <img 
            src="/logo.png" 
            alt="TESCON Logo" 
            style={styles.logo}
            data-logo
            onError={(e) => {
              e.currentTarget.style.display = 'none';
            }}
          />
          <div style={styles.titleGroup}>
            <h1 style={styles.title}>Image Background Removal</h1>
            <p style={styles.subtitle}>Spare-part catalog processing</p>
          </div>
        </div>

        {health && (
          <div style={styles.healthBadge} data-health-badge>
            {health.model_loaded ? (
              <CheckCircle2 style={{ ...styles.healthIcon, color: colors.success }} />
            ) : (
              <XCircle style={{ ...styles.healthIcon, color: colors.error }} />
            )}
            <span>{health.model_loaded ? 'Ready' : 'Offline'}</span>
          </div>
        )}
      </div>

      <StepByStepWorkflow
        onSuccess={(_response: ProcessPartResponse) => {
          // Success is handled within the component
        }}
        onError={(_error: string) => {
          // Error is handled within the component
        }}
      />
    </div>
  );
}

export default App;
