/** Job status display component */
import React, { useEffect, useState } from "react";
import { JobStatusResponse, JobStatus } from "../types";
import { getJobStatus, downloadJobResults, retryFailedImages } from "../services/api";
import { ProgressBar } from "./ProgressBar";
import { Download, RefreshCw, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows, transitions } from "../styles/design-system";

interface JobStatusProps {
  jobId: string;
  onComplete?: () => void;
  onRetry?: (newJobId: string) => void;
  outputFormat?: "PNG" | "JPEG" | "JPG";
  whiteBackground?: boolean;
}

export const JobStatusComponent: React.FC<JobStatusProps> = ({ 
  jobId, 
  onComplete,
  onRetry,
  outputFormat = "PNG",
  whiteBackground = true
}) => {
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [showFailedList, setShowFailedList] = useState(false);

  const styles = {
    card: {
      padding: spacing.lg,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.lg,
      boxShadow: shadows.base,
    } as React.CSSProperties,
    
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: spacing.md,
    },
    
    title: {
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
    },
    
    loadingText: {
      fontSize: typography.fontSize.sm,
      color: colors.text.secondary,
    },
    
    statsRow: {
      display: 'flex',
      gap: spacing.sm,
      marginTop: spacing.md,
      marginBottom: spacing.md,
    },
    
    statItem: {
      flex: 1,
      padding: spacing.sm,
      backgroundColor: colors.neutral[50],
      borderRadius: borderRadius.sm,
      textAlign: 'center' as const,
    },
    
    statLabel: {
      fontSize: '10px',
      color: colors.text.secondary,
      marginBottom: '2px',
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
    },
    
    statValue: {
      fontSize: typography.fontSize.lg,
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
    },
    
    failedSection: {
      marginTop: spacing.md,
      padding: spacing.sm,
      backgroundColor: `${colors.error}05`,
      border: `1px solid ${colors.error}20`,
      borderRadius: borderRadius.sm,
    },
    
    failedHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      cursor: 'pointer',
      userSelect: 'none' as const,
    },
    
    failedTitle: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.semibold,
      color: colors.error,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.xs,
    },
    
    failedList: {
      marginTop: spacing.xs,
      paddingLeft: spacing.md,
      maxHeight: '120px',
      overflowY: 'auto' as const,
      fontSize: '11px',
      color: colors.text.secondary,
    },
    
    buttonGroup: {
      display: 'flex',
      gap: spacing.sm,
      marginTop: spacing.md,
    },
    
    primaryButton: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: spacing.xs,
      flex: 1,
      padding: `${spacing.sm} ${spacing.md}`,
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.inverse,
      backgroundColor: colors.primary.main,
      border: 'none',
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      transition: `all ${transitions.base}`,
      boxShadow: shadows.sm,
    } as React.CSSProperties,
    
    secondaryButton: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: spacing.xs,
      flex: 1,
      padding: `${spacing.sm} ${spacing.md}`,
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.semibold,
      color: colors.warning,
      backgroundColor: 'transparent',
      border: `2px solid ${colors.warning}`,
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      transition: `all ${transitions.base}`,
    } as React.CSSProperties,
  };

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const jobStatus = await getJobStatus(jobId);
        setStatus(jobStatus);
        setLoading(false);

        if (jobStatus.status === JobStatus.COMPLETED || jobStatus.status === JobStatus.FAILED) {
          if (onComplete) {
            onComplete();
          }
          return;
        }

        setTimeout(pollStatus, 2000);
      } catch (error) {
        console.error("Error fetching job status:", error);
        setLoading(false);
      }
    };

    pollStatus();
  }, [jobId, onComplete]);

  const handleDownload = async () => {
    if (!status || status.status !== JobStatus.COMPLETED) return;

    setDownloading(true);
    try {
      const blob = await downloadJobResults(jobId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `processed_${jobId}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Error downloading results:", error);
      alert("Failed to download results");
    } finally {
      setDownloading(false);
    }
  };

  const handleRetry = async () => {
    if (!status || !status.failed_images || status.failed_images.length === 0) return;

    setRetrying(true);
    try {
      const retryResponse = await retryFailedImages(jobId, outputFormat, whiteBackground);
      if (onRetry) {
        onRetry(retryResponse.job_id);
      } else {
        window.location.reload();
      }
    } catch (error: any) {
      console.error("Error retrying failed images:", error);
      alert(`Failed to retry: ${error.response?.data?.detail || error.message}`);
    } finally {
      setRetrying(false);
    }
  };

  const getStatusBadge = () => {
    const badgeStyles = {
      base: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: spacing.xs,
        padding: `4px ${spacing.sm}`,
        borderRadius: borderRadius.full,
        fontSize: '11px',
        fontWeight: typography.fontWeight.medium,
      },
      processing: {
        backgroundColor: `${colors.info}15`,
        color: colors.info,
      },
      completed: {
        backgroundColor: `${colors.success}15`,
        color: colors.success,
      },
      failed: {
        backgroundColor: `${colors.error}15`,
        color: colors.error,
      },
    };

    const statusConfig = {
      [JobStatus.PROCESSING]: { icon: Loader2, label: 'Processing', style: badgeStyles.processing, spin: true },
      [JobStatus.COMPLETED]: { icon: CheckCircle2, label: 'Completed', style: badgeStyles.completed, spin: false },
      [JobStatus.FAILED]: { icon: XCircle, label: 'Failed', style: badgeStyles.failed, spin: false },
    };

    const config = statusConfig[status!.status];
    const Icon = config.icon;

    return (
      <div style={{ ...badgeStyles.base, ...config.style }}>
        <Icon size={14} style={config.spin ? { animation: 'spin 1s linear infinite' } : undefined} />
        {config.label}
      </div>
    );
  };

  if (loading) {
    return (
      <div style={styles.card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
          <Loader2 size={18} color={colors.primary.main} style={{ animation: 'spin 1s linear infinite' }} />
          <span style={styles.loadingText}>Loading...</span>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div style={{ ...styles.card, borderColor: colors.error }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: spacing.sm }}>
          <XCircle size={18} color={colors.error} />
          <span style={{ ...styles.loadingText, color: colors.error }}>Error loading status</span>
        </div>
      </div>
    );
  }

  const progress = status.total_images > 0 
    ? (status.processed_count / status.total_images) * 100 
    : 0;

  return (
    <div style={styles.card} className="fade-in">
      <div style={styles.header}>
        <h3 style={styles.title}>Job {status.job_id.slice(0, 8)}</h3>
        {getStatusBadge()}
      </div>

      <ProgressBar progress={progress} label={`${status.processed_count} / ${status.total_images} images`} />

      <div style={styles.statsRow} data-stats-row>
        <div style={styles.statItem}>
          <div style={styles.statLabel}>Total</div>
          <div style={styles.statValue}>{status.total_images}</div>
        </div>
        <div style={styles.statItem}>
          <div style={styles.statLabel}>Done</div>
          <div style={{ ...styles.statValue, color: colors.success }}>{status.processed_count}</div>
        </div>
        {status.failed_count > 0 && (
          <div style={styles.statItem}>
            <div style={styles.statLabel}>Failed</div>
            <div style={{ ...styles.statValue, color: colors.error }}>{status.failed_count}</div>
          </div>
        )}
      </div>

      {status.failed_images && status.failed_images.length > 0 && (
        <div style={styles.failedSection}>
          <div style={styles.failedHeader} onClick={() => setShowFailedList(!showFailedList)}>
            <div style={styles.failedTitle}>
              <XCircle size={12} />
              {status.failed_images.length} failed
            </div>
            {showFailedList ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
          {showFailedList && (
            <ul style={styles.failedList}>
              {status.failed_images.map((filename, index) => (
                <li key={index}>{filename}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {status.status === JobStatus.COMPLETED && (
        <div style={styles.buttonGroup}>
          <button
            onClick={handleDownload}
            disabled={downloading}
            style={styles.primaryButton}
            onMouseEnter={(e) => {
              if (!downloading) {
                e.currentTarget.style.backgroundColor = colors.primary.hover;
                e.currentTarget.style.boxShadow = shadows.md;
              }
            }}
            onMouseLeave={(e) => {
              if (!downloading) {
                e.currentTarget.style.backgroundColor = colors.primary.main;
                e.currentTarget.style.boxShadow = shadows.sm;
              }
            }}
          >
            {downloading ? (
              <>
                <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                Downloading
              </>
            ) : (
              <>
                <Download size={16} />
                Download ZIP
              </>
            )}
          </button>
          
          {status.failed_count > 0 && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              style={styles.secondaryButton}
              onMouseEnter={(e) => {
                if (!retrying) {
                  e.currentTarget.style.backgroundColor = `${colors.warning}10`;
                }
              }}
              onMouseLeave={(e) => {
                if (!retrying) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {retrying ? (
                <>
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  Retrying
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  Retry {status.failed_count}
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
