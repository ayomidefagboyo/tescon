/** Parts tracking dashboard component */
import React, { useState, useEffect } from "react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography } from "../styles/design-system";
import { BarChart, RefreshCw, Search, Download, CloudSync } from "lucide-react";
import { getTrackerProgress, getProcessedParts, getFailedParts, getRemainingParts, getQueuedParts, resetPartStatus as apiResetPartStatus, getDailyStats, exportDailyStatsExcel, syncTrackerFromR2 } from "../services/api";

interface ProgressStats {
  total_parts: number;
  processed_count: number;
  failed_count: number;
  queued_count: number;
  remaining_count: number;
  progress_percentage: number;
  success_rate: number;
  completed_today?: number;
  queued_today?: number;
  failed_today?: number;
}

interface PartStats {
  status: string;
  image_count?: number;
  processing_time?: number;
  completed_at?: string;
  queued_at?: string;
  failed_at?: string;
  error_reason?: string;
}

interface TrackerData {
  progress: ProgressStats;
  processed_parts: string[];  // Array of exact symbol numbers
  failed_parts: { [key: string]: string };  // Symbol number -> error message
  queued_parts: string[];  // Array of exact symbol numbers
  remaining_parts: string[];  // Array of exact symbol numbers
  part_stats: { [key: string]: PartStats };  // Symbol number -> detailed stats
}

export const PartsTrackingDashboard: React.FC = () => {
  const [trackerData, setTrackerData] = useState<TrackerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'processed' | 'failed' | 'queued' | 'remaining'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [dailyStatsDate, setDailyStatsDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [dailyStatsStatus, setDailyStatsStatus] = useState<string>('all');
  const [dailyStatsData, setDailyStatsData] = useState<any>(null);
  const [exporting, setExporting] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const fetchTrackerData = async () => {
    setRefreshing(true);
    try {
      const [progress, processed, failed, queued, remaining] = await Promise.all([
        getTrackerProgress(),
        getProcessedParts(),
        getFailedParts(),
        getQueuedParts(),
        getRemainingParts()
      ]);

      setTrackerData({
        progress: progress.progress,
        processed_parts: processed.processed_parts,
        failed_parts: failed.failed_parts,
        queued_parts: queued.queued_parts,
        remaining_parts: remaining.remaining_parts,
        part_stats: progress.part_stats || {}
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
    const interval = setInterval(fetchTrackerData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDailyStats = async () => {
    try {
      const data = await getDailyStats(dailyStatsDate, dailyStatsStatus === 'all' ? undefined : dailyStatsStatus);
      setDailyStatsData(data);
    } catch (error) {
      console.error('Failed to fetch daily stats:', error);
    }
  };

  useEffect(() => {
    if (selectedTab === 'overview') {
      fetchDailyStats();
    }
  }, [dailyStatsDate, dailyStatsStatus, selectedTab]);

  const handleExportDailyStats = async () => {
    setExporting(true);
    try {
      const blob = await exportDailyStatsExcel(dailyStatsDate, dailyStatsStatus === 'all' ? undefined : dailyStatsStatus);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `daily_stats_${dailyStatsDate}${dailyStatsStatus !== 'all' ? `_${dailyStatsStatus}` : ''}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export daily stats:', error);
      alert('Failed to export daily stats. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleSyncTracker = async () => {
    setSyncing(true);
    try {
      const result = await syncTrackerFromR2();
      console.log('Sync result:', result);
      // Refresh tracker data after sync (silent update, no alert)
      await fetchTrackerData();
    } catch (error) {
      console.error('Failed to sync tracker:', error);
      alert('Failed to sync tracker with R2 storage. Please try again.');
    } finally {
      setSyncing(false);
    }
  };

  const resetPartStatus = async (partNumber: string) => {
    try {
      await apiResetPartStatus(partNumber);
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
    },
    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: mobileSpacing.lg,
      flexDirection: 'row' as const,
      flexWrap: 'wrap' as const,
      gap: mobileSpacing.md,
    },
    title: {
      fontSize: mobileTypography.fontSize.xl,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      display: 'flex',
      alignItems: 'center',
      gap: mobileSpacing.sm,
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
    } as React.CSSProperties,
    statsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: mobileSpacing.md,
      marginBottom: mobileSpacing.lg,
    },
    statCard: {
      backgroundColor: colors.background.main,
      padding: mobileSpacing.lg,
      borderRadius: borderRadius.lg,
      boxShadow: shadows.sm,
      border: `1px solid ${colors.neutral[200]}`,
    },
    statIcon: {
      width: '48px',
      height: '48px',
      borderRadius: borderRadius.full,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: mobileSpacing.md,
    },
    statValue: {
      fontSize: mobileTypography.fontSize.xl,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
      marginBottom: mobileSpacing.xs,
    },
    statLabel: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
    },
    progressBar: {
      width: '100%',
      height: '8px',
      backgroundColor: colors.neutral[200],
      borderRadius: borderRadius.full,
      overflow: 'hidden',
      marginTop: mobileSpacing.sm,
    },
    progressFill: {
      height: '100%',
      backgroundColor: colors.success,
      borderRadius: borderRadius.full,
      transition: `width ${transitions.base}`,
    },
    tabsContainer: {
      display: 'flex',
      flexWrap: 'wrap' as const,
      gap: mobileSpacing.xs,
      borderBottom: `2px solid ${colors.neutral[200]}`,
      marginBottom: mobileSpacing.lg,
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
    } as React.CSSProperties,
    activeTab: {
      color: colors.primary.main,
      borderBottomColor: colors.primary.main,
    },
    searchContainer: {
      marginBottom: mobileSpacing.lg,
      position: 'relative' as const,
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
    } as React.CSSProperties,
    searchIcon: {
      position: 'absolute' as const,
      left: mobileSpacing.sm,
      top: '50%',
      transform: 'translateY(-50%)',
      color: colors.text.tertiary,
    },
    partsList: {
      display: 'grid',
      gap: mobileSpacing.md,
      maxHeight: 'calc(100vh - 500px)',
      overflowY: 'auto' as const,
      overflowX: 'hidden' as const,
    },
    partCard: {
      backgroundColor: colors.background.main,
      padding: mobileSpacing.md,
      borderRadius: borderRadius.md,
      boxShadow: shadows.sm,
      border: `1px solid ${colors.neutral[200]}`,
      gap: mobileSpacing.xs,
    },
    partHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: mobileSpacing.sm,
    },
    partNumber: {
      fontSize: mobileTypography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
    },
    statusBadge: {
      padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
      borderRadius: borderRadius.full,
      fontSize: mobileTypography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
    },
    partDetails: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
      lineHeight: 1.5,
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

  const { progress, processed_parts, failed_parts, queued_parts, remaining_parts } = trackerData;

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
    if (!query) return parts.slice(0, 50);
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

      case 'queued':
        const filteredQueued = filterParts(queued_parts, searchQuery);
        return (
          <div style={styles.partsList}>
            {filteredQueued.length === 0 ? (
              <p style={{ textAlign: 'center', color: colors.text.secondary }}>No queued parts found</p>
            ) : (
              filteredQueued.map(partNumber => (
                <div key={partNumber} style={styles.partCard}>
                  <div style={styles.partHeader}>
                    <div style={styles.partNumber}>{partNumber}</div>
                    <div style={getStatusBadgeStyle('queued')}>Queued</div>
                  </div>
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
        // Render simplified premium overview
        return (
          <>
            {/* Main Stats - 2 cards side by side */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: spacing.xl,
              marginBottom: spacing.xl
            }}>
              {/* Daily Activity */}
              <div style={{
                backgroundColor: colors.background.main,
                padding: spacing.xl,
                borderRadius: borderRadius.xl,
                boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
                border: `1px solid ${colors.neutral[200]}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: spacing.lg }}>
                  <h3 style={{
                    fontSize: typography.fontSize.xl,
                    fontWeight: typography.fontWeight.bold,
                    color: colors.text.primary,
                    margin: 0,
                    letterSpacing: '-0.5px'
                  }}>
                    Daily Activity
                  </h3>
                  {dailyStatsData && (
                    <div style={{
                      fontSize: typography.fontSize.sm,
                      color: colors.text.secondary,
                      fontWeight: typography.fontWeight.medium,
                      backgroundColor: `${colors.neutral[100]}`,
                      padding: `${spacing.xs} ${spacing.md}`,
                      borderRadius: borderRadius.full
                    }}>
                      {new Date(dailyStatsData.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                  )}
                </div>

                {dailyStatsData ? (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr 1fr',
                    gap: spacing.xl
                  }}>
                    <div style={{ textAlign: 'center', padding: spacing.md }}>
                      <div style={{
                        fontSize: '3rem',
                        fontWeight: typography.fontWeight.bold,
                        color: colors.success,
                        marginBottom: spacing.sm,
                        letterSpacing: '-1px'
                      }}>
                        {dailyStatsData.completed_count}
                      </div>
                      <div style={{
                        fontSize: typography.fontSize.sm,
                        color: colors.text.secondary,
                        fontWeight: typography.fontWeight.medium,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        Completed
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', padding: spacing.md }}>
                      <div style={{
                        fontSize: '3rem',
                        fontWeight: typography.fontWeight.bold,
                        color: colors.warning,
                        marginBottom: spacing.sm,
                        letterSpacing: '-1px'
                      }}>
                        {dailyStatsData.queued_count}
                      </div>
                      <div style={{
                        fontSize: typography.fontSize.sm,
                        color: colors.text.secondary,
                        fontWeight: typography.fontWeight.medium,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        Queued
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', padding: spacing.md }}>
                      <div style={{
                        fontSize: '3rem',
                        fontWeight: typography.fontWeight.bold,
                        color: dailyStatsData.failed_count > 0 ? colors.error : colors.neutral[300],
                        marginBottom: spacing.sm,
                        letterSpacing: '-1px'
                      }}>
                        {dailyStatsData.failed_count}
                      </div>
                      <div style={{
                        fontSize: typography.fontSize.sm,
                        color: colors.text.secondary,
                        fontWeight: typography.fontWeight.medium,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        Failed
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', color: colors.text.secondary, padding: spacing.xl }}>
                    Loading daily stats...
                  </div>
                )}
              </div>

              {/* Overall Progress Summary */}
              <div style={{
                backgroundColor: colors.background.main,
                padding: spacing.xl,
                borderRadius: borderRadius.xl,
                boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
                border: `1px solid ${colors.neutral[200]}`
              }}>
                <h3 style={{
                  fontSize: typography.fontSize.xl,
                  fontWeight: typography.fontWeight.bold,
                  color: colors.text.primary,
                  marginBottom: spacing.lg,
                  letterSpacing: '-0.5px'
                }}>
                  Overall Progress
                </h3>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: spacing.lg,
                  marginBottom: spacing.lg
                }}>
                  <div>
                    <div style={{
                      fontSize: typography.fontSize.sm,
                      color: colors.text.secondary,
                      marginBottom: spacing.xs,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      fontWeight: typography.fontWeight.medium
                    }}>
                      Catalog
                    </div>
                    <div style={{
                      fontSize: typography.fontSize['2xl'],
                      fontWeight: typography.fontWeight.bold,
                      color: colors.text.primary,
                      letterSpacing: '-1px'
                    }}>
                      {progress.total_parts.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{
                      fontSize: typography.fontSize.sm,
                      color: colors.text.secondary,
                      marginBottom: spacing.xs,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      fontWeight: typography.fontWeight.medium
                    }}>
                      Completed
                    </div>
                    <div style={{
                      fontSize: typography.fontSize['2xl'],
                      fontWeight: typography.fontWeight.bold,
                      color: colors.success,
                      letterSpacing: '-1px'
                    }}>
                      {progress.processed_count.toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{
                  marginTop: spacing.md
                }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: spacing.sm
                  }}>
                    <span style={{
                      fontSize: typography.fontSize.sm,
                      color: colors.text.secondary,
                      fontWeight: typography.fontWeight.medium
                    }}>
                      Progress
                    </span>
                    <span style={{
                      fontSize: typography.fontSize.sm,
                      fontWeight: typography.fontWeight.bold,
                      color: colors.primary.main
                    }}>
                      {progress.progress_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{
                    height: '12px',
                    backgroundColor: colors.neutral[200],
                    borderRadius: borderRadius.full,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${progress.progress_percentage}%`,
                      background: `linear-gradient(90deg, ${colors.success} 0%, ${colors.primary.main} 100%)`,
                      transition: 'width 0.6s ease',
                      borderRadius: borderRadius.full
                    }} />
                  </div>
                </div>

                {/* Success rate */}
                <div style={{
                  marginTop: spacing.lg,
                  paddingTop: spacing.lg,
                  borderTop: `1px solid ${colors.neutral[200]}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{
                    fontSize: typography.fontSize.sm,
                    color: colors.text.secondary,
                    fontWeight: typography.fontWeight.medium
                  }}>
                    Success Rate
                  </span>
                  <span style={{
                    fontSize: typography.fontSize.lg,
                    fontWeight: typography.fontWeight.bold,
                    color: progress.success_rate >= 95 ? colors.success : colors.warning
                  }}>
                    {progress.success_rate.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </>
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
        <div style={{ display: 'flex', gap: mobileSpacing.sm, alignItems: 'center', flexWrap: 'wrap' }}>
          {selectedTab === 'overview' && (
            <>
              <input
                type="date"
                value={dailyStatsDate}
                onChange={(e) => setDailyStatsDate(e.target.value)}
                style={{
                  padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
                  border: `1px solid ${colors.neutral[300]}`,
                  borderRadius: borderRadius.md,
                  fontSize: mobileTypography.fontSize.sm,
                  backgroundColor: colors.background.main,
                  color: colors.text.primary
                }}
              />
              <select
                value={dailyStatsStatus}
                onChange={(e) => setDailyStatsStatus(e.target.value)}
                style={{
                  padding: `${mobileSpacing.xs} ${mobileSpacing.sm}`,
                  border: `1px solid ${colors.neutral[300]}`,
                  borderRadius: borderRadius.md,
                  fontSize: mobileTypography.fontSize.sm,
                  backgroundColor: colors.background.main,
                  color: colors.text.primary,
                  cursor: 'pointer'
                }}
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="queued">Queued</option>
                <option value="failed">Failed</option>
              </select>
              <button
                style={{
                  ...styles.refreshButton,
                  backgroundColor: colors.success,
                  display: 'flex',
                  alignItems: 'center',
                  gap: mobileSpacing.xs
                }}
                onClick={handleExportDailyStats}
                disabled={exporting}
                onMouseEnter={(e) => {
                  if (!exporting) {
                    e.currentTarget.style.backgroundColor = '#059669';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = colors.success;
                }}
              >
                <Download size={16} />
                {exporting ? 'Exporting...' : 'Export Excel'}
              </button>
            </>
          )}
          <button
            style={{
              ...styles.refreshButton,
              backgroundColor: colors.warning
            }}
            onClick={handleSyncTracker}
            disabled={syncing}
            onMouseEnter={(e) => {
              if (!syncing) {
                e.currentTarget.style.backgroundColor = '#d97706';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = colors.warning;
            }}
          >
            <CloudSync size={16} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
            {syncing ? 'Syncing...' : 'Sync R2'}
          </button>
          <button
            style={styles.refreshButton}
            onClick={fetchTrackerData}
            disabled={refreshing}
            onMouseEnter={(e) => {
              if (!refreshing) {
                e.currentTarget.style.backgroundColor = colors.primary.hover;
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
      </div>

      <div style={styles.tabsContainer}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'processed', label: `Processed (${progress.processed_count})` },
          { key: 'queued', label: `Queued (${progress.queued_count})` },
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