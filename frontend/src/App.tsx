/** Main application component */
import React, { useState, useEffect } from "react";
import { healthCheck } from "./services/api";
import { CheckCircle2, XCircle, Wifi, WifiOff } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography, touchTargets } from "./styles/design-system";
import { StepByStepWorkflow } from "./components/StepByStepWorkflow";
import { PartsTrackingDashboard } from "./components/PartsTrackingDashboard";
import { UploadStatusDashboard } from "./components/UploadStatusDashboard";

function App() {
  const [health, setHealth] = useState<{ gpu_available: boolean; model_loaded: boolean } | null>(null);
  const [currentView, setCurrentView] = useState<'workflow' | 'dashboard'>('workflow');
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Network status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Health check and periodic connectivity check
  useEffect(() => {
    const checkConnectivity = () => {
      healthCheck()
        .then((data) => {
          setHealth({ gpu_available: data.gpu_available, model_loaded: data.model_loaded });
          if (!isOnline) setIsOnline(true); // Backend is reachable, so we're online
        })
        .catch((error) => {
          console.error("Health check failed:", error);
          // Don't immediately set offline on health check failure
          // as it might just be the backend that's down, not the network
        });
    };

    // Initial check
    checkConnectivity();

    // Periodic health checks every 30 seconds
    const interval = setInterval(checkConnectivity, 30000);

    return () => clearInterval(interval);
  }, [isOnline]);


  const styles = {
      container: {
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column' as const,
        width: '100%',
        maxWidth: 'none',
        margin: '0',
        padding: `${mobileSpacing.lg} ${mobileSpacing.md}`,
        fontFamily: typography.fontFamily.base,
        boxSizing: 'border-box' as const,
        overflow: 'visible',
        '@media (min-width: 768px)': {
          maxWidth: '1200px',
          margin: '0 auto',
          padding: `${spacing.xl} ${spacing.xl}`,
        },
      } as React.CSSProperties,

    header: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: mobileSpacing.lg,
      flexShrink: 0,
      textAlign: 'center' as const,
      position: 'relative' as const,
      '@media (min-width: 768px)': {
        flexDirection: 'row',
        alignItems: 'center',
        textAlign: 'left',
      },
    },

    logoAndTitle: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      gap: mobileSpacing.sm,
      '@media (min-width: 768px)': {
        flexDirection: 'row',
        gap: spacing.md,
      },
    },

    logo: {
      height: '32px',
      width: 'auto',
      '@media (min-width: 768px)': {
        height: '48px',
      },
    },

    titleGroup: {
      display: 'flex',
      flexDirection: 'column' as const,
    },

    title: {
      fontSize: mobileTypography.fontSize.xl,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      letterSpacing: '-0.02em',
      lineHeight: 1.2,
      margin: 0,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize['2xl'],
      },
    },

    subtitle: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
      fontWeight: typography.fontWeight.normal,
      margin: 0,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.sm,
      },
    },

    healthBadge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: mobileSpacing.xs,
      padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.md,
      fontSize: mobileTypography.fontSize.xs,
      color: colors.text.secondary,
      boxShadow: shadows.sm,
      minHeight: touchTargets.small,
      '@media (min-width: 768px)': {
        gap: spacing.xs,
        padding: `${spacing.xs} ${spacing.sm}`,
        fontSize: typography.fontSize.xs,
      },
    },

    healthIcon: {
      width: '16px',
      height: '16px',
      '@media (min-width: 768px)': {
        width: '14px',
        height: '14px',
      },
    },

    networkBadge: (isOnline: boolean) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      padding: '6px 12px',
      borderRadius: borderRadius.full,
      border: `1px solid ${isOnline ? '#10b981' : '#ef4444'}`,
      backgroundColor: isOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
      fontSize: '12px',
      fontWeight: typography.fontWeight.medium,
      position: 'absolute' as const,
      top: '0',
      right: '0',
      '@media (min-width: 768px)': {
        position: 'static' as const,
        fontSize: '13px',
      },
    } as React.CSSProperties),

    navigationTabs: {
      display: 'flex',
      borderBottom: `2px solid ${colors.neutral[200]}`,
      marginBottom: mobileSpacing.lg,
      overflowX: 'auto' as const,
      '@media (min-width: 768px)': {
        marginBottom: spacing.xl,
      },
    },

    navTab: {
      padding: `${mobileSpacing.sm} ${mobileSpacing.lg}`,
      borderBottom: '2px solid transparent',
      cursor: 'pointer',
      fontSize: mobileTypography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.secondary,
      transition: `all ${transitions.base}`,
      whiteSpace: 'nowrap' as const,
      '@media (min-width: 768px)': {
        padding: `${spacing.sm} ${spacing.xl}`,
        fontSize: typography.fontSize.sm,
      },
    } as React.CSSProperties,

    activeNavTab: {
      color: colors.primary.main,
      borderBottomColor: colors.primary.main,
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

        {/* Network Status Badge */}
        <div style={styles.networkBadge(isOnline)}>
          {isOnline ? (
            <>
              <Wifi size={16} style={{ color: '#10b981' }} />
              <span style={{ color: '#10b981' }}>Online</span>
            </>
          ) : (
            <>
              <WifiOff size={16} style={{ color: '#ef4444' }} />
              <span style={{ color: '#ef4444' }}>Offline</span>
            </>
          )}
        </div>
      </div>

      <div style={styles.navigationTabs}>
        <div
          style={{
            ...styles.navTab,
            ...(currentView === 'workflow' ? styles.activeNavTab : {})
          }}
          onClick={() => setCurrentView('workflow')}
        >
          Process Parts
        </div>
        <div
          style={{
            ...styles.navTab,
            ...(currentView === 'dashboard' ? styles.activeNavTab : {})
          }}
          onClick={() => setCurrentView('dashboard')}
        >
          Tracking Dashboard
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {currentView === 'workflow' ? (
          <>
            <StepByStepWorkflow
              onError={(_error: string) => {
                // Error is handled within the component
              }}
            />
            <UploadStatusDashboard compact={true} />
          </>
        ) : (
          <>
            <PartsTrackingDashboard />
            <UploadStatusDashboard compact={false} />
          </>
        )}
      </div>

      {health && (
        <div style={{...styles.healthBadge, marginTop: mobileSpacing.lg, alignSelf: 'center'}} data-health-badge>
          {health.model_loaded ? (
            <CheckCircle2 style={{ ...styles.healthIcon, color: colors.success }} />
          ) : (
            <XCircle style={{ ...styles.healthIcon, color: colors.error }} />
          )}
          <span>{health.model_loaded ? 'Ready' : 'Offline'}</span>
        </div>
      )}
    </div>
  );
}

export default App;
