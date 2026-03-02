/** Parts tracking dashboard component */
import React, { useEffect, useRef, useState } from "react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography } from "../styles/design-system";
import { BarChart, RefreshCw, Search, Download, CloudSync } from "lucide-react";
import { describeApiError, getTrackerProgress, getProcessedParts, getFailedParts, getRemainingParts, getQueuedParts, resetPartStatus as apiResetPartStatus, getDailyStats, exportDailyStatsExcel, syncTrackerFromR2 } from "../services/api";

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

type DashboardTab = 'overview' | 'processed' | 'failed' | 'queued' | 'remaining';
type ListTab = Exclude<DashboardTab, 'overview'>;

interface TrackerData {
  progress: ProgressStats;
  part_stats: { [key: string]: PartStats };  // Symbol number -> detailed stats
}

interface TrackerLists {
  processed: string[];
  failed: { [key: string]: string };
  queued: string[];
  remaining: string[];
}

interface CachedTrackerSummary {
  data: TrackerData;
  cachedAt: number;
}

export const PartsTrackingDashboard: React.FC = () => {
  const summaryCacheKey = 'tescon_tracker_dashboard_summary';
  const legacyAutoSyncCacheKey = 'tescon_tracker_dashboard_last_auto_sync';
  const autoRefreshMs = 10000;
  const summaryCacheMaxAgeMs = 30000;
  const [trackerData, setTrackerData] = useState<TrackerData | null>(null);
  const [trackerLists, setTrackerLists] = useState<TrackerLists>({
    processed: [],
    failed: {},
    queued: [],
    remaining: []
  });
  const [loadedTabs, setLoadedTabs] = useState<Partial<Record<ListTab, boolean>>>({});
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [selectedTab, setSelectedTab] = useState<DashboardTab>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [dailyStatsDate, setDailyStatsDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [dailyStatsStatus, setDailyStatsStatus] = useState<string>('all');
  const [dailyStatsData, setDailyStatsData] = useState<any>(null);
  const [exporting, setExporting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [showingCachedSummary, setShowingCachedSummary] = useState(false);
  const [cachedSummaryAgeMs, setCachedSummaryAgeMs] = useState<number | null>(null);
  const summaryRequestInFlight = useRef(false);
  const tabRequestInFlight = useRef<Partial<Record<ListTab, boolean>>>({});

  const getCachedSummary = (): CachedTrackerSummary | null => {
    try {
      const cachedSummary = localStorage.getItem(summaryCacheKey);
      if (!cachedSummary) {
        return null;
      }

      const parsed = JSON.parse(cachedSummary) as CachedTrackerSummary | TrackerData;
      const hasWrappedCache =
        typeof (parsed as CachedTrackerSummary)?.cachedAt === 'number' &&
        !!(parsed as CachedTrackerSummary)?.data;

      if (hasWrappedCache) {
        return parsed as CachedTrackerSummary;
      }

      if ((parsed as TrackerData)?.progress) {
        return {
          data: parsed as TrackerData,
          cachedAt: 0
        };
      }

      localStorage.removeItem(summaryCacheKey);
      return null;
    } catch (error) {
      console.warn('Failed to load cached tracker summary:', error);
      localStorage.removeItem(summaryCacheKey);
      return null;
    }
  };

  const applyCachedSummary = (cachedSummary: CachedTrackerSummary) => {
    setTrackerData(cachedSummary.data);
    setShowingCachedSummary(true);
    setCachedSummaryAgeMs(cachedSummary.cachedAt > 0 ? Math.max(0, Date.now() - cachedSummary.cachedAt) : null);
  };

  const persistSummary = (nextTrackerData: TrackerData) => {
    const cachedSummary: CachedTrackerSummary = {
      data: nextTrackerData,
      cachedAt: Date.now()
    };

    localStorage.setItem(summaryCacheKey, JSON.stringify(cachedSummary));
  };

  const clearDashboardCache = () => {
    localStorage.removeItem(summaryCacheKey);
    localStorage.removeItem(legacyAutoSyncCacheKey);
  };

  const getCacheAgeLabel = () => {
    if (cachedSummaryAgeMs === null) {
      return null;
    }

    const seconds = Math.max(1, Math.round(cachedSummaryAgeMs / 1000));
    if (seconds < 60) {
      return `${seconds}s old`;
    }

    const minutes = Math.round(seconds / 60);
    return `${minutes}m old`;
  };

  const fetchTrackerSummary = async (allowCacheFallback: boolean = false) => {
    if (summaryRequestInFlight.current) {
      return trackerData !== null;
    }

    summaryRequestInFlight.current = true;
    try {
      setSummaryError(null);
      const progress = await getTrackerProgress();

      const nextTrackerData = {
        progress: progress.progress,
        part_stats: progress.part_stats || {}
      };

      console.log('📊 Tracker data received:', {
        processed_count: progress.progress?.processed_count,
        total_parts: progress.progress?.total_parts,
        timestamp: new Date().toISOString()
      });

      setTrackerData(nextTrackerData);
      setShowingCachedSummary(false);
      setCachedSummaryAgeMs(0);
      persistSummary(nextTrackerData);
      return true;
    } catch (error) {
      const errorMessage = describeApiError(error);
      console.error('Failed to fetch tracker data:', errorMessage, error);
      setSummaryError(errorMessage);

      if (allowCacheFallback) {
        const cachedSummary = getCachedSummary();
        if (cachedSummary?.data?.progress) {
          applyCachedSummary(cachedSummary);
        }
      }

      return false;
    } finally {
      summaryRequestInFlight.current = false;
      setLoading(false);
    }
  };

  const fetchTabData = async (tab: ListTab, forceRefresh: boolean = false) => {
    if (!forceRefresh && loadedTabs[tab]) {
      return;
    }

    if (tabRequestInFlight.current[tab]) {
      return;
    }

    tabRequestInFlight.current[tab] = true;
    setTabLoading(true);

    try {
      switch (tab) {
        case 'processed': {
          const processed = await getProcessedParts();
          setTrackerLists((current) => ({
            ...current,
            processed: processed.processed_parts || []
          }));
          break;
        }
        case 'failed': {
          const failed = await getFailedParts();
          setTrackerLists((current) => ({
            ...current,
            failed: failed.failed_parts || {}
          }));
          break;
        }
        case 'queued': {
          const queued = await getQueuedParts();
          setTrackerLists((current) => ({
            ...current,
            queued: queued.queued_parts || []
          }));
          break;
        }
        case 'remaining': {
          const remaining = await getRemainingParts();
          setTrackerLists((current) => ({
            ...current,
            remaining: remaining.remaining_parts || []
          }));
          break;
        }
      }

      setLoadedTabs((current) => ({
        ...current,
        [tab]: true
      }));
    } catch (error) {
      console.error(`Failed to fetch ${tab} parts:`, describeApiError(error), error);
    } finally {
      tabRequestInFlight.current[tab] = false;
      setTabLoading(false);
    }
  };

  const refreshCurrentView = async (forceTabRefresh: boolean = false) => {
    await fetchTrackerSummary(true);

    if (selectedTab === 'overview') {
      await fetchDailyStats();
      return;
    }

    await fetchTabData(selectedTab, forceTabRefresh);
  };

  useEffect(() => {
    const cachedSummary = getCachedSummary();
    const hasFreshCachedSummary =
      !!cachedSummary &&
      cachedSummary.cachedAt > 0 &&
      (Date.now() - cachedSummary.cachedAt <= summaryCacheMaxAgeMs);

    if (cachedSummary && hasFreshCachedSummary) {
      applyCachedSummary(cachedSummary);
      setLoading(false);
    }

    void fetchTrackerSummary(true);
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      void refreshCurrentView(selectedTab !== 'overview');
    }, autoRefreshMs);

    return () => window.clearInterval(interval);
  }, [selectedTab, dailyStatsDate, dailyStatsStatus, autoRefreshMs]);

  const fetchDailyStats = async () => {
    try {
      const data = await getDailyStats(dailyStatsDate, dailyStatsStatus === 'all' ? undefined : dailyStatsStatus);
      setDailyStatsData(data);
    } catch (error) {
      console.error('Failed to fetch daily stats:', describeApiError(error), error);
    }
  };

  useEffect(() => {
    if (selectedTab === 'overview') {
      void fetchDailyStats();
    }
  }, [dailyStatsDate, dailyStatsStatus, selectedTab]);

  useEffect(() => {
    if (selectedTab !== 'overview') {
      void fetchTabData(selectedTab);
    }
  }, [selectedTab]);

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
      console.log('Manual sync from R2 starting...');
      const syncResult = await syncTrackerFromR2();
      const nextTrackerData = {
        progress: syncResult.stats,
        part_stats: trackerData?.part_stats || {}
      };

      setTrackerData(nextTrackerData);
      setSummaryError(null);
      setShowingCachedSummary(false);
      setCachedSummaryAgeMs(0);
      setLoadedTabs({});
      clearDashboardCache();
      persistSummary(nextTrackerData);
      console.log('Manual sync completed, refreshing visible data...');

      if (selectedTab !== 'overview') {
        await fetchTabData(selectedTab, true);
      } else {
        await fetchDailyStats();
      }
    } catch (error) {
      console.error('Failed to sync tracker:', describeApiError(error), error);
      alert(`Failed to sync tracker with R2 storage. ${describeApiError(error)}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleClearCache = async () => {
    clearDashboardCache();
    setLoadedTabs({});
    setTrackerLists({
      processed: [],
      failed: {},
      queued: [],
      remaining: []
    });
    setTrackerData(null);
    setDailyStatsData(null);
    setShowingCachedSummary(false);
    setCachedSummaryAgeMs(null);
    setSummaryError(null);
    setLoading(true);

    try {
      await refreshCurrentView(true);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshClick = async () => {
    setRefreshing(true);
    try {
      await refreshCurrentView(true);
    } finally {
      setRefreshing(false);
    }
  };

  const resetPartStatus = async (partNumber: string) => {
    try {
      await apiResetPartStatus(partNumber);
      await fetchTrackerSummary();
      if (selectedTab !== 'overview') {
        await fetchTabData(selectedTab, true);
      }
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
    secondaryButton: {
      display: 'flex',
      alignItems: 'center',
      gap: mobileSpacing.xs,
      padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
      backgroundColor: colors.background.main,
      color: colors.text.primary,
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      fontSize: mobileTypography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      transition: `all ${transitions.base}`,
    } as React.CSSProperties,
    statusBanner: {
      marginBottom: mobileSpacing.md,
      padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
      borderRadius: borderRadius.md,
      border: `1px solid ${colors.neutral[200]}`,
      fontSize: mobileTypography.fontSize.sm,
      lineHeight: 1.5,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: mobileSpacing.sm,
      flexWrap: 'wrap' as const,
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
          <p style={{ color: colors.text.secondary, marginBottom: spacing.md }}>
            {summaryError ? `Failed to load tracker data: ${summaryError}` : 'Failed to load tracker data'}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: mobileSpacing.sm, flexWrap: 'wrap' }}>
            <button
              style={styles.refreshButton}
              onClick={handleRefreshClick}
              disabled={refreshing}
            >
              <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
              Retry
            </button>
            <button
              style={styles.secondaryButton}
              onClick={() => {
                void handleClearCache();
              }}
            >
              Clear Cache
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { progress } = trackerData;

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
        if (!loadedTabs.processed && tabLoading) {
          return <p style={{ textAlign: 'center', color: colors.text.secondary }}>Loading processed parts...</p>;
        }

        const filteredProcessed = filterParts(trackerLists.processed, searchQuery);
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
        if (!loadedTabs.failed && tabLoading) {
          return <p style={{ textAlign: 'center', color: colors.text.secondary }}>Loading failed parts...</p>;
        }

        const filteredFailed = Object.entries(trackerLists.failed).filter(([partNumber]) =>
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
        if (!loadedTabs.queued && tabLoading) {
          return <p style={{ textAlign: 'center', color: colors.text.secondary }}>Loading queued parts...</p>;
        }

        const filteredQueued = filterParts(trackerLists.queued, searchQuery);
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
        if (!loadedTabs.remaining && tabLoading) {
          return <p style={{ textAlign: 'center', color: colors.text.secondary }}>Loading remaining parts...</p>;
        }

        const filteredRemaining = filterParts(trackerLists.remaining, searchQuery);
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
                    gap: mobileSpacing.md
                  }}>
                    <div style={{ textAlign: 'center', padding: mobileSpacing.sm }}>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xl,
                        fontWeight: typography.fontWeight.bold,
                        color: colors.success,
                        marginBottom: mobileSpacing.xs,
                        letterSpacing: '-1px',
                        lineHeight: 1.2
                      }}>
                        {dailyStatsData.completed_count}
                      </div>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xs,
                        color: colors.text.secondary,
                        fontWeight: typography.fontWeight.medium,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        Completed
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', padding: mobileSpacing.sm }}>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xl,
                        fontWeight: typography.fontWeight.bold,
                        color: colors.warning,
                        marginBottom: mobileSpacing.xs,
                        letterSpacing: '-1px',
                        lineHeight: 1.2
                      }}>
                        {dailyStatsData.queued_count}
                      </div>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xs,
                        color: colors.text.secondary,
                        fontWeight: typography.fontWeight.medium,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        Queued
                      </div>
                    </div>
                    <div style={{ textAlign: 'center', padding: mobileSpacing.sm }}>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xl,
                        fontWeight: typography.fontWeight.bold,
                        color: dailyStatsData.failed_count > 0 ? colors.error : colors.neutral[300],
                        marginBottom: mobileSpacing.xs,
                        letterSpacing: '-1px',
                        lineHeight: 1.2
                      }}>
                        {dailyStatsData.failed_count}
                      </div>
                      <div style={{
                        fontSize: mobileTypography.fontSize.xs,
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
      {(summaryError || showingCachedSummary) && (
        <div
          style={{
            ...styles.statusBanner,
            backgroundColor: summaryError ? '#fff7ed' : '#eff6ff',
            borderColor: summaryError ? '#fdba74' : '#bfdbfe',
            color: summaryError ? '#9a3412' : '#1d4ed8',
          }}
        >
          <span>
            {summaryError
              ? `Live tracker update failed: ${summaryError}. ${showingCachedSummary ? `Showing cached data${getCacheAgeLabel() ? ` (${getCacheAgeLabel()})` : ''}.` : 'Use refresh or clear cache to retry.'}`
              : `Showing cached tracker data${getCacheAgeLabel() ? ` (${getCacheAgeLabel()})` : ''} while live data refreshes.`}
          </span>
          <button
            style={styles.secondaryButton}
            onClick={() => {
              void handleClearCache();
            }}
          >
            Clear Cache
          </button>
        </div>
      )}

      <div style={styles.header}>
        <div style={styles.title}>
          <BarChart size={32} />
          Parts Tracking Dashboard
        </div>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: mobileSpacing.sm,
          alignItems: 'flex-end'
        }}>
          {/* First row: Date and Status filters */}
          {selectedTab === 'overview' && (
            <div style={{
              display: 'flex',
              gap: mobileSpacing.sm,
              alignItems: 'center'
            }}>
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
                  color: colors.text.primary,
                  width: '140px'
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
                  cursor: 'pointer',
                  width: '120px'
                }}
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="queued">Queued</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          )}

          {/* Second row: Action buttons */}
          <div style={{
            display: 'flex',
            gap: mobileSpacing.sm,
            alignItems: 'center',
            flexWrap: 'nowrap'
          }}>
            {selectedTab === 'overview' && (
              <button
                style={{
                  ...styles.refreshButton,
                  backgroundColor: colors.success,
                  display: 'flex',
                  alignItems: 'center',
                  gap: mobileSpacing.xs,
                  padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
                  fontSize: mobileTypography.fontSize.sm,
                  minWidth: '80px',
                  justifyContent: 'center'
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
                <Download size={14} />
                {exporting ? 'Export' : 'Export'}
              </button>
            )}
            <button
              style={{
                ...styles.refreshButton,
                backgroundColor: colors.warning,
                display: 'flex',
                alignItems: 'center',
                gap: mobileSpacing.xs,
                padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
                fontSize: mobileTypography.fontSize.sm,
                minWidth: '70px',
                justifyContent: 'center'
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
              <CloudSync size={14} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
              {syncing ? 'Sync' : 'Sync'}
            </button>
            <button
              style={{
                ...styles.refreshButton,
                display: 'flex',
                alignItems: 'center',
                gap: mobileSpacing.xs,
                padding: `${mobileSpacing.sm} ${mobileSpacing.md}`,
                fontSize: mobileTypography.fontSize.sm,
                minWidth: '85px',
                justifyContent: 'center'
              }}
              onClick={handleRefreshClick}
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
              <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
              {refreshing ? 'Refresh' : 'Refresh'}
            </button>
            <button
              style={{
                ...styles.secondaryButton,
                minWidth: '110px',
                justifyContent: 'center'
              }}
              onClick={() => {
                void handleClearCache();
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = colors.neutral[400];
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = colors.neutral[300];
              }}
            >
              Clear Cache
            </button>
          </div>
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
            onClick={() => setSelectedTab(tab.key as DashboardTab)}
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
