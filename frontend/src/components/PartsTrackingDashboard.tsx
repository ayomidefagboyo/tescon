/** Parts tracking dashboard component */
import React, { useState, useEffect } from "react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography } from "../styles/design-system";
import { BarChart, CheckCircle, XCircle, Clock, RefreshCw, FileText, Upload, Search } from "lucide-react";

interface ProgressStats {
  total_parts: number;
  processed_count: number;
  failed_count: number;
  remaining_count: number;
  progress_percentage: number;
  success_rate: number;
}

interface PartStatus {
  part_number: string;
  status: 'completed' | 'failed' | 'pending';
  image_count?: number;
  error_reason?: string;
  completed_at?: string;
  failed_at?: string;
}

interface TrackerData {
  progress: ProgressStats;
  processed_parts: string[];
  failed_parts: { [key: string]: string };
  remaining_parts: string[];
}

export const PartsTrackingDashboard: React.FC = () => {
  const [trackerData, setTrackerData] = useState<TrackerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'processed' | 'failed' | 'remaining'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const fetchTrackerData = async () => {
    setRefreshing(true);
    try {
      const [progressRes, processedRes, failedRes, remainingRes] = await Promise.all([
        fetch('/api/tracker/progress'),
        fetch('/api/tracker/parts/processed'),
        fetch('/api/tracker/parts/failed'),
        fetch('/api/tracker/parts/remaining')
      ]);

      const [progress, processed, failed, remaining] = await Promise.all([
        progressRes.json(),
        processedRes.json(),
        failedRes.json(),
        remainingRes.json()
      ]);

      setTrackerData({
        progress: progress.progress,
        processed_parts: processed.processed_parts,
        failed_parts: failed.failed_parts,
        remaining_parts: remaining.remaining_parts
      });
    } catch (error) {
      console.error('Failed to fetch tracker data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTrackerData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchTrackerData, 30000);
    return () => clearInterval(interval);
  }, []);

  const resetPartStatus = async (partNumber: string) => {
    try {
      await fetch(`/api/tracker/parts/${partNumber}/reset`, { method: 'POST' });
      await fetchTrackerData();
    } catch (error) {
      console.error('Failed to reset part status:', error);
    }
  };

  const styles = {
    container: {
      padding: mobileSpacing.lg,
      maxWidth: '1200px',
      margin: '0 auto',
      '@media (min-width: 768px)': {
        padding: spacing.xl,
      },
    },

    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: mobileSpacing.lg,
      flexDirection: 'column' as const,
      gap: mobileSpacing.md,
      '@media (min-width: 768px)': {
        flexDirection: 'row' as const,
        gap: spacing.md,
        marginBottom: spacing.xl,
      },
    },

    title: {
      fontSize: mobileTypography.fontSize.xl,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      display: 'flex',
      alignItems: 'center',
      gap: mobileSpacing.sm,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.xxl,
        gap: spacing.sm,
      },
    },

    refreshButton: {
      display: 'flex',
      alignItems: 'center',
      gap: mobileSpacing.xs,
      padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
      backgroundColor: colors.primary.main,
      color: colors.text.inverse,
      border: 'none',
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      fontSize: mobileTypography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      transition: `all ${transitions.base}`,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.sm,
        padding: `${spacing.sm} ${spacing.lg}`,
        gap: spacing.xs,
      },
    } as React.CSSProperties,

    statsGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr',
      gap: mobileSpacing.md,
      marginBottom: mobileSpacing.lg,
      '@media (min-width: 640px)': {
        gridTemplateColumns: 'repeat(2, 1fr)',
      },
      '@media (min-width: 1024px)': {
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: spacing.lg,
        marginBottom: spacing.xl,
      },
    },

    statCard: {
      backgroundColor: colors.background.main,
      padding: mobileSpacing.lg,
      borderRadius: borderRadius.lg,
      boxShadow: shadows.sm,
      border: `1px solid ${colors.neutral[200]}`,
      '@media (min-width: 768px)': {
        padding: spacing.lg,
      },
    },

    statIcon: {
      width: '48px',
      height: '48px',
      borderRadius: borderRadius.full,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: mobileSpacing.md,
      '@media (min-width: 768px)': {
        marginBottom: spacing.md,
      },
    },

    statValue: {
      fontSize: mobileTypography.fontSize.xl,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      marginBottom: mobileSpacing.xs,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.xxl,
        marginBottom: spacing.xs,
      },
    },

    statLabel: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.sm,
      },
    },

    progressBar: {
      width: '100%',
      height: '8px',
      backgroundColor: colors.neutral[200],
      borderRadius: borderRadius.full,
      overflow: 'hidden',
      marginTop: mobileSpacing.sm,
      '@media (min-width: 768px)': {
        marginTop: spacing.sm,
      },
    },

    progressFill: {
      height: '100%',
      backgroundColor: colors.success,
      borderRadius: borderRadius.full,
      transition: `width ${transitions.base}`,
    },

    tabsContainer: {
      display: 'flex',
      borderBottom: `2px solid ${colors.neutral[200]}`,
      marginBottom: mobileSpacing.lg,
      overflowX: 'auto' as const,
      '@media (min-width: 768px)': {
        marginBottom: spacing.xl,
      },
    },

    tab: {
      padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
      borderBottom: '2px solid transparent',
      cursor: 'pointer',
      fontSize: mobileTypography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.secondary,
      transition: `all ${transitions.base}`,
      whiteSpace: 'nowrap' as const,
      '@media (min-width: 768px)': {
        padding: `${spacing.sm} ${spacing.lg}`,
        fontSize: typography.fontSize.sm,
      },
    } as React.CSSProperties,

    activeTab: {
      color: colors.primary.main,
      borderBottomColor: colors.primary.main,
    },

    searchContainer: {
      marginBottom: mobileSpacing.lg,
      position: 'relative' as const,
      '@media (min-width: 768px)': {
        marginBottom: spacing.lg,
      },
    },

    searchInput: {
      width: '100%',
      padding: `${mobileSpacing.sm} ${mobileSpacing.md} ${mobileSpacing.sm} 40px`,
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.md,
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.primary,
      backgroundColor: colors.background.main,
      transition: `border-color ${transitions.base}`,
      '@media (min-width: 768px)': {
        padding: `${spacing.sm} ${spacing.lg} ${spacing.sm} 48px`,
        fontSize: typography.fontSize.sm,
      },
    } as React.CSSProperties,

    searchIcon: {
      position: 'absolute' as const,
      left: mobileSpacing.sm,
      top: '50%',
      transform: 'translateY(-50%)',
      color: colors.text.tertiary,
      '@media (min-width: 768px)': {
        left: spacing.sm,
      },
    },

    partsList: {
      display: 'grid',
      gap: mobileSpacing.md,
      '@media (min-width: 768px)': {
        gap: spacing.md,
      },
    },

    partCard: {
      backgroundColor: colors.background.main,
      padding: mobileSpacing.md,
      borderRadius: borderRadius.md,
      boxShadow: shadows.sm,
      border: `1px solid ${colors.neutral[200]}`,
      '@media (min-width: 768px)': {
        padding: spacing.lg,
      },
    },

    partHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: mobileSpacing.sm,
      '@media (min-width: 768px)': {
        marginBottom: spacing.sm,
      },
    },

    partNumber: {
      fontSize: mobileTypography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.lg,
      },
    },

    statusBadge: {
      padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
      borderRadius: borderRadius.full,
      fontSize: mobileTypography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.xs,
        padding: `${spacing.xs} ${spacing.sm}`,
      },
    },

    partDetails: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
      lineHeight: 1.5,
      '@media (min-width: 768px)': {
        fontSize: typography.fontSize.sm,
      },
    },

    resetButton: {
      padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
      backgroundColor: 'transparent',
      color: colors.warning,
      border: `1px solid ${colors.warning}`,
      borderRadius: borderRadius.sm,
      cursor: 'pointer',
      fontSize: mobileTypography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      transition: `all ${transitions.base}`,
      marginTop: mobileSpacing.sm,
      '@media (min-width: 768px)': {
        marginTop: spacing.sm,
        fontSize: typography.fontSize.xs,
      },
    } as React.CSSProperties,
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={{ textAlign: 'center', padding: spacing.xl }}>
          <RefreshCw size={48} style={{ animation: 'spin 1s linear infinite', color: colors.primary.main }} />
          <p style={{ marginTop: spacing.md, color: colors.text.secondary }}>Loading tracker data...</p>
        </div>
      </div>
    );
  }

  if (!trackerData) {
    return (
      <div style={styles.container}>
        <div style={{ textAlign: 'center', padding: spacing.xl }}>
          <p style={{ color: colors.text.secondary }}>Failed to load tracker data</p>
        </div>
      </div>
    );
  }

  const { progress, processed_parts, failed_parts, remaining_parts } = trackerData;

  const getStatusBadgeStyle = (status: string) => {
    const baseStyle = styles.statusBadge;
    switch (status) {
      case 'completed':
        return { ...baseStyle, backgroundColor: `${colors.success}20`, color: colors.success };
      case 'failed':
        return { ...baseStyle, backgroundColor: `${colors.error}20`, color: colors.error };
      default:
        return { ...baseStyle, backgroundColor: `${colors.warning}20`, color: colors.warning };
    }
  };

  const filterParts = (parts: string[], query: string) => {
    if (!query) return parts.slice(0, 50); // Limit to 50 for performance
    return parts.filter(part => part.toLowerCase().includes(query.toLowerCase())).slice(0, 50);
  };

  const renderTabContent = () => {
    switch (selectedTab) {
      case 'processed':
        const filteredProcessed = filterParts(processed_parts, searchQuery);
        return (
          <div style={styles.partsList}>
            {filteredProcessed.length === 0 ? (
              <p style={{ textAlign: 'center', color: colors.text.secondary }}>No processed parts found</p>
            ) : (
              filteredProcessed.map(partNumber => (
                <div key={partNumber} style={styles.partCard}>
                  <div style={styles.partHeader}>
                    <div style={styles.partNumber}>{partNumber}</div>
                    <div style={getStatusBadgeStyle('completed')}>Completed</div>
                  </div>
                </div>
              ))
            )}
          </div>
        );

      case 'failed':
        const filteredFailed = Object.entries(failed_parts).filter(([partNumber]) =>
          partNumber.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 50);
        return (
          <div style={styles.partsList}>
            {filteredFailed.length === 0 ? (
              <p style={{ textAlign: 'center', color: colors.text.secondary }}>No failed parts found</p>
            ) : (
              filteredFailed.map(([partNumber, error]) => (
                <div key={partNumber} style={styles.partCard}>
                  <div style={styles.partHeader}>
                    <div style={styles.partNumber}>{partNumber}</div>
                    <div style={getStatusBadgeStyle('failed')}>Failed</div>
                  </div>
                  <div style={styles.partDetails}>
                    <strong>Error:</strong> {error}
                  </div>
                  <button
                    style={styles.resetButton}
                    onClick={() => resetPartStatus(partNumber)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = colors.warning;
                      e.currentTarget.style.color = colors.text.inverse;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = colors.warning;
                    }}
                  >
                    Reset Status
                  </button>
                </div>
              ))
            )}
          </div>
        );

      case 'remaining':
        const filteredRemaining = filterParts(remaining_parts, searchQuery);
        return (
          <div style={styles.partsList}>
            {filteredRemaining.length === 0 ? (
              <p style={{ textAlign: 'center', color: colors.text.secondary }}>No remaining parts found</p>
            ) : (
              filteredRemaining.map(partNumber => (
                <div key={partNumber} style={styles.partCard}>
                  <div style={styles.partHeader}>
                    <div style={styles.partNumber}>{partNumber}</div>
                    <div style={getStatusBadgeStyle('pending')}>Pending</div>
                  </div>
                </div>
              ))
            )}
          </div>
        );

      default:
        return (
          <div style={styles.statsGrid}>
            <div style={styles.statCard}>
              <div style={{ ...styles.statIcon, backgroundColor: `${colors.primary.main}20` }}>
                <BarChart size={24} color={colors.primary.main} />
              </div>
              <div style={styles.statValue}>{progress.total_parts.toLocaleString()}</div>
              <div style={styles.statLabel}>Total Parts</div>
            </div>

            <div style={styles.statCard}>
              <div style={{ ...styles.statIcon, backgroundColor: `${colors.success}20` }}>
                <CheckCircle size={24} color={colors.success} />
              </div>
              <div style={styles.statValue}>{progress.processed_count.toLocaleString()}</div>
              <div style={styles.statLabel}>Processed</div>
              <div style={styles.progressBar}>
                <div style={{ ...styles.progressFill, width: `${progress.progress_percentage}%` }} />
              </div>
            </div>

            <div style={styles.statCard}>
              <div style={{ ...styles.statIcon, backgroundColor: `${colors.error}20` }}>
                <XCircle size={24} color={colors.error} />
              </div>
              <div style={styles.statValue}>{progress.failed_count.toLocaleString()}</div>
              <div style={styles.statLabel}>Failed</div>
            </div>

            <div style={styles.statCard}>
              <div style={{ ...styles.statIcon, backgroundColor: `${colors.warning}20` }}>
                <Clock size={24} color={colors.warning} />
              </div>
              <div style={styles.statValue}>{progress.remaining_count.toLocaleString()}</div>
              <div style={styles.statLabel}>Remaining</div>
            </div>
          </div>
        );
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>
          <BarChart size={32} />
          Parts Tracking Dashboard
        </div>
        <button
          style={styles.refreshButton}
          onClick={fetchTrackerData}
          disabled={refreshing}
          onMouseEnter={(e) => {
            if (!refreshing) {
              e.currentTarget.style.backgroundColor = colors.primary.dark;
            }
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = colors.primary.main;
          }}
        >
          <RefreshCw size={16} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {progress.progress_percentage > 0 && (
        <div style={{
          padding: mobileSpacing.md,
          backgroundColor: `${colors.primary.main}10`,
          borderRadius: borderRadius.md,
          marginBottom: mobileSpacing.lg,
          textAlign: 'center',
          '@media (min-width: 768px)': {
            padding: spacing.lg,
            marginBottom: spacing.xl,
          },
        }}>
          <div style={{
            fontSize: mobileTypography.fontSize.lg,
            fontWeight: typography.fontWeight.semibold,
            color: colors.text.primary,
            marginBottom: mobileSpacing.xs,
            '@media (min-width: 768px)': {
              fontSize: typography.fontSize.xl,
              marginBottom: spacing.xs,
            },
          }}>
            {progress.progress_percentage.toFixed(1)}% Complete
          </div>
          <div style={{
            fontSize: mobileTypography.fontSize.sm,
            color: colors.text.secondary,
            '@media (min-width: 768px)': {
              fontSize: typography.fontSize.sm,
            },
          }}>
            Success Rate: {progress.success_rate.toFixed(1)}%
          </div>
        </div>
      )}

      <div style={styles.tabsContainer}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'processed', label: `Processed (${progress.processed_count})` },
          { key: 'failed', label: `Failed (${progress.failed_count})` },
          { key: 'remaining', label: `Remaining (${progress.remaining_count})` },
        ].map(tab => (
          <div
            key={tab.key}
            style={{
              ...styles.tab,
              ...(selectedTab === tab.key ? styles.activeTab : {})
            }}
            onClick={() => setSelectedTab(tab.key as any)}
          >
            {tab.label}
          </div>
        ))}
      </div>

      {selectedTab !== 'overview' && (
        <div style={styles.searchContainer}>
          <Search size={16} style={styles.searchIcon} />
          <input
            type="text"
            placeholder="Search parts..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={styles.searchInput}
          />
        </div>
      )}

      {renderTabContent()}
    </div>
  );
};