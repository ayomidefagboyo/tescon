/** Parts tracking dashboard component */
import React, { useState, useEffect } from "react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography } from "../styles/design-system";
import { BarChart, CheckCircle, Clock, RefreshCw, Search, Target, TrendingUp, Calendar } from "lucide-react";
import { getTrackerProgress, getProcessedParts, getFailedParts, getRemainingParts, getQueuedParts, resetPartStatus as apiResetPartStatus } from "../services/api";

interface ProgressStats {
  total_parts: number;
  processed_count: number;
  failed_count: number;
  queued_count: number;
  remaining_count: number;
  progress_percentage: number;
  success_rate: number;
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

// Pie Chart Component
interface PieChartProps {
  processed: number;
  queued: number;
  failed: number;
  remaining: number;
}

const PieChart: React.FC<PieChartProps> = ({ processed, queued, failed, remaining }) => {
  const total = processed + queued + failed + remaining;

  if (total === 0) {
    return <div style={{ textAlign: 'center', padding: '40px', color: colors.text.secondary }}>No data available</div>;
  }

  // Calculate percentages
  const processedPercent = (processed / total) * 100;
  const queuedPercent = (queued / total) * 100;
  const failedPercent = (failed / total) * 100;
  const remainingPercent = (remaining / total) * 100;

  // Calculate cumulative angles for SVG
  let currentAngle = 0;
  const segments = [
    { label: 'Processed', value: processed, percent: processedPercent, color: colors.success, angle: currentAngle },
    { label: 'Queued', value: queued, percent: queuedPercent, color: colors.warning, angle: currentAngle += processedPercent * 3.6 },
    { label: 'Failed', value: failed, percent: failedPercent, color: colors.error, angle: currentAngle += queuedPercent * 3.6 },
    { label: 'Remaining', value: remaining, percent: remainingPercent, color: colors.neutral[400], angle: currentAngle += failedPercent * 3.6 }
  ].filter(seg => seg.value > 0);

  // Create SVG path for donut segment
  const createArc = (startAngle: number, endAngle: number, radius: number, innerRadius: number) => {
    const start = polarToCartesian(100, 100, radius, endAngle);
    const end = polarToCartesian(100, 100, radius, startAngle);
    const innerStart = polarToCartesian(100, 100, innerRadius, endAngle);
    const innerEnd = polarToCartesian(100, 100, innerRadius, startAngle);

    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

    return [
      "M", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
      "L", innerEnd.x, innerEnd.y,
      "A", innerRadius, innerRadius, 0, largeArcFlag, 1, innerStart.x, innerStart.y,
      "Z"
    ].join(" ");
  };

  const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: mobileSpacing.md }}>
      {/* SVG Donut Chart */}
      <svg width="200" height="200" viewBox="0 0 200 200">
        {segments.map((seg, idx) => {
          const nextAngle = idx < segments.length - 1 ? segments[idx + 1].angle : 360;
          return (
            <path
              key={seg.label}
              d={createArc(seg.angle, nextAngle, 80, 50)}
              fill={seg.color}
              opacity="0.9"
            />
          );
        })}
        {/* Center text */}
        <text x="100" y="95" textAnchor="middle" fontSize="24" fontWeight="bold" fill={colors.text.primary}>
          {((processed / total) * 100).toFixed(1)}%
        </text>
        <text x="100" y="115" textAnchor="middle" fontSize="12" fill={colors.text.secondary}>
          Complete
        </text>
      </svg>

      {/* Legend */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: mobileSpacing.sm, width: '100%' }}>
        {segments.map(seg => (
          <div key={seg.label} style={{ display: 'flex', alignItems: 'center', gap: mobileSpacing.xs }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '2px',
              backgroundColor: seg.color
            }} />
            <span style={{ fontSize: mobileTypography.fontSize.xs, color: colors.text.secondary }}>
              {seg.label}: {seg.value.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export const PartsTrackingDashboard: React.FC = () => {
  const [trackerData, setTrackerData] = useState<TrackerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<'overview' | 'processed' | 'failed' | 'queued' | 'remaining'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [dailyTarget, setDailyTarget] = useState(100); // Default: 100 parts per day

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
      flexDirection: 'column' as const,
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
        // Calculate daily progress using queued parts (uploaded today)
        // This tracks upload activity, not processing (which happens later via GitHub Actions)
        const today = new Date().toISOString().split('T')[0];
        const queuedToday = queued_parts.filter(partNum => {
          const partStats = trackerData?.part_stats?.[partNum];
          if (!partStats?.queued_at) return false;
          // Check if queued_at date matches today
          const queuedDate = partStats.queued_at.split('T')[0];
          return queuedDate === today;
        }).length;

        const dailyProgress = (queuedToday / dailyTarget) * 100;

        return (
          <>
            {/* Top Section: Daily Target, Completion ETA, Progress Distribution - Side by Side */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: spacing.lg,
              marginBottom: spacing.lg
            }}>
              {/* Daily Target */}
              <div style={{
                backgroundColor: colors.background.main,
                padding: spacing.lg,
                borderRadius: borderRadius.lg,
                boxShadow: shadows.sm,
                border: `1px solid ${colors.neutral[200]}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.md }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: borderRadius.lg,
                    backgroundColor: `${colors.primary.main}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Target size={20} color={colors.primary.main} />
                  </div>
                  <h3 style={{
                    fontSize: typography.fontSize.lg,
                    fontWeight: typography.fontWeight.bold,
                    color: colors.text.primary,
                    margin: 0
                  }}>
                    Daily Target
                  </h3>
                </div>

                <div style={{ marginBottom: spacing.md }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: spacing.xs,
                    marginBottom: spacing.sm
                  }}>
                    <span style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary }}>
                      Target:
                    </span>
                    <input
                      type="number"
                      value={dailyTarget}
                      onChange={(e) => setDailyTarget(Number(e.target.value))}
                      style={{
                        width: '80px',
                        padding: `${spacing.xs} ${spacing.sm}`,
                        border: `2px solid ${colors.neutral[300]}`,
                        borderRadius: borderRadius.md,
                        fontSize: typography.fontSize.base,
                        fontWeight: typography.fontWeight.semibold,
                        textAlign: 'center'
                      }}
                    />
                    <span style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary }}>
                      parts/day
                    </span>
                  </div>
                </div>

                <div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: spacing.xs
                  }}>
                    <span style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary }}>
                      Today's Progress
                    </span>
                    <span style={{
                      fontSize: typography.fontSize.lg,
                      fontWeight: typography.fontWeight.bold,
                      color: colors.text.primary
                    }}>
                      {queuedToday} / {dailyTarget}
                    </span>
                  </div>
                  <div style={{
                    height: '10px',
                    backgroundColor: colors.neutral[200],
                    borderRadius: borderRadius.full,
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(dailyProgress, 100)}%`,
                      backgroundColor: dailyProgress >= 100 ? colors.success : colors.primary.main,
                      transition: transitions.base,
                      borderRadius: borderRadius.full
                    }} />
                  </div>
                  <div style={{
                    fontSize: typography.fontSize.xs,
                    color: colors.text.tertiary,
                    marginTop: spacing.xs,
                    textAlign: 'right'
                  }}>
                    {dailyProgress.toFixed(1)}% of daily target
                  </div>
                </div>
              </div>

              {/* Completion ETA */}
              <div style={{
                backgroundColor: colors.background.main,
                padding: spacing.lg,
                borderRadius: borderRadius.lg,
                boxShadow: shadows.sm,
                border: `1px solid ${colors.neutral[200]}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.md }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: borderRadius.lg,
                    backgroundColor: `${colors.primary.main}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Calendar size={20} color={colors.primary.main} />
                  </div>
                  <h3 style={{
                    fontSize: typography.fontSize.lg,
                    fontWeight: typography.fontWeight.bold,
                    color: colors.text.primary,
                    margin: 0
                  }}>
                    Completion ETA
                  </h3>
                </div>

                <div style={{ textAlign: 'center', padding: `${spacing.md} 0` }}>
                  <div style={{
                    fontSize: typography.fontSize['2xl'],
                    fontWeight: typography.fontWeight.bold,
                    color: colors.primary.main,
                    marginBottom: spacing.xs
                  }}>
                    {(() => {
                      if (progress.remaining_count === 0) return 'Complete!';

                      const daysRemaining = Math.ceil(progress.remaining_count / dailyTarget);
                      const completionDate = new Date();
                      completionDate.setDate(completionDate.getDate() + daysRemaining);

                      return completionDate.toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      });
                    })()}
                  </div>
                  <div style={{
                    fontSize: typography.fontSize.sm,
                    color: colors.text.secondary
                  }}>
                    {progress.remaining_count === 0
                      ? 'All parts uploaded! 🎉'
                      : `${Math.ceil(progress.remaining_count / dailyTarget).toLocaleString()} days remaining`
                    }
                  </div>
                </div>
              </div>

              {/* Progress Distribution */}
              <div style={{
                backgroundColor: colors.background.main,
                padding: spacing.lg,
                borderRadius: borderRadius.lg,
                boxShadow: shadows.sm,
                border: `1px solid ${colors.neutral[200]}`
              }}>
                <h3 style={{
                  fontSize: typography.fontSize.lg,
                  fontWeight: typography.fontWeight.bold,
                  marginBottom: spacing.md,
                  color: colors.text.primary
                }}>Progress Distribution</h3>

                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center'
                }}>
                  <PieChart
                    processed={progress.processed_count}
                    queued={progress.queued_count}
                    failed={progress.failed_count}
                    remaining={progress.remaining_count}
                  />
                </div>
              </div>
            </div>

            {/* Stats Grid - 2 per row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: spacing.lg,
              marginBottom: spacing.lg
            }}>
              {/* Total Parts */}
              <div style={styles.statCard}>
                <div style={{ ...styles.statIcon, backgroundColor: `${colors.primary.main}20` }}>
                  <BarChart size={24} color={colors.primary.main} />
                </div>
                <div style={styles.statValue}>{progress.total_parts.toLocaleString()}</div>
                <div style={styles.statLabel}>Total Parts</div>
                <div style={{
                  fontSize: typography.fontSize.xs,
                  color: colors.text.tertiary,
                  marginTop: spacing.xs
                }}>
                  From Excel catalog
                </div>
              </div>

              {/* Processed */}
              <div style={styles.statCard}>
                <div style={{ ...styles.statIcon, backgroundColor: `${colors.success}20` }}>
                  <CheckCircle size={24} color={colors.success} />
                </div>
                <div style={styles.statValue}>{progress.processed_count.toLocaleString()}</div>
                <div style={styles.statLabel}>Processed</div>
                <div style={styles.progressBar}>
                  <div style={{ ...styles.progressFill, width: `${progress.progress_percentage}%` }} />
                </div>
                <div style={{
                  fontSize: typography.fontSize.xs,
                  color: colors.text.tertiary,
                  marginTop: spacing.xs,
                  textAlign: 'right'
                }}>
                  {progress.progress_percentage.toFixed(1)}% complete
                </div>
              </div>

              {/* Queued */}
              <div style={styles.statCard}>
                <div style={{ ...styles.statIcon, backgroundColor: `${colors.warning}20` }}>
                  <Clock size={24} color={colors.warning} />
                </div>
                <div style={styles.statValue}>{progress.queued_count.toLocaleString()}</div>
                <div style={styles.statLabel}>Queued</div>
                <div style={{
                  fontSize: typography.fontSize.xs,
                  color: colors.text.tertiary,
                  marginTop: spacing.xs
                }}>
                  Awaiting processing
                </div>
              </div>

              {/* Success Rate */}
              <div style={styles.statCard}>
                <div style={{ ...styles.statIcon, backgroundColor: `${colors.success}20` }}>
                  <TrendingUp size={24} color={colors.success} />
                </div>
                <div style={styles.statValue}>{progress.success_rate.toFixed(1)}%</div>
                <div style={styles.statLabel}>Success Rate</div>
                <div style={{
                  fontSize: typography.fontSize.xs,
                  color: colors.text.tertiary,
                  marginTop: spacing.xs
                }}>
                  {progress.failed_count} failed of {progress.processed_count + progress.failed_count} attempted
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

      {progress.progress_percentage > 0 && (
        <div style={{
          padding: mobileSpacing.md,
          backgroundColor: `${colors.primary.main}10`,
          borderRadius: borderRadius.md,
          marginBottom: mobileSpacing.lg,
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: mobileTypography.fontSize.lg,
            fontWeight: typography.fontWeight.semibold,
            color: colors.text.primary,
            marginBottom: mobileSpacing.xs,
          }}>
            {progress.progress_percentage.toFixed(1)}% Complete
          </div>
          <div style={{
            fontSize: mobileTypography.fontSize.sm,
            color: colors.text.secondary,
          }}>
            Success Rate: {progress.success_rate.toFixed(1)}%
          </div>
        </div>
      )}

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