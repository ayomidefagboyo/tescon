/** Main application component */
import React, { useState } from "react";
import { UploadZone } from "./components/UploadZone";
import { ProgressBar } from "./components/ProgressBar";
import { DownloadButton } from "./components/DownloadButton";
import { JobStatusComponent } from "./components/JobStatus";
import { FileWithPreview } from "./types";
import { processSingleImage, processBulkImages, healthCheck } from "./services/api";
import { CheckCircle2, XCircle, Settings } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows, transitions } from "./styles/design-system";

function App() {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedBlob, setProcessedBlob] = useState<Blob | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [format, setFormat] = useState<"PNG" | "JPEG" | "JPG">("PNG");
  const [whiteBackground, setWhiteBackground] = useState(true);
  const [health, setHealth] = useState<{ gpu_available: boolean; model_loaded: boolean } | null>(null);

  React.useEffect(() => {
    healthCheck()
      .then((data) => {
        setHealth({ gpu_available: data.gpu_available, model_loaded: data.model_loaded });
      })
      .catch((error) => {
        console.error("Health check failed:", error);
      });
  }, []);

  const handleFilesSelected = (selectedFiles: FileWithPreview[]) => {
    setFiles(selectedFiles);
    setProcessedBlob(null);
    setJobId(null);
  };

  const handleProcess = async () => {
    if (files.length === 0) return;

    setProcessing(true);
    setProgress(0);
    setProcessedBlob(null);
    setJobId(null);

    try {
      if (files.length === 1 && !files[0].name.toLowerCase().endsWith(".zip")) {
        const blob = await processSingleImage(
          files[0],
          format,
          whiteBackground,
          (progressData) => {
            setProgress(progressData.percentage);
          }
        );
        setProcessedBlob(blob);
      } else {
        const jobResponse = await processBulkImages(files, format, whiteBackground);
        setJobId(jobResponse.job_id);
      }
    } catch (error: any) {
      console.error("Processing error:", error);
      alert(`Processing failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setProcessing(false);
      setProgress(0);
    }
  };

  const handleJobComplete = () => {
    setProcessing(false);
  };

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
    
    mainContent: {
      display: 'grid',
      gridTemplateColumns: files.length > 0 ? '1fr 400px' : '1fr',
      gap: spacing.lg,
      flex: 1,
      minHeight: 0,
      overflow: 'hidden',
    },
    
    leftPanel: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.md,
      minHeight: 0,
    },
    
    rightPanel: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.md,
    },
    
    optionsCard: {
      padding: spacing.lg,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.lg,
      boxShadow: shadows.base,
    },
    
    optionsTitle: {
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: spacing.md,
      display: 'flex',
      alignItems: 'center',
      gap: spacing.xs,
    },
    
    optionsGrid: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.md,
    },
    
    formGroup: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.xs,
    },
    
    label: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.primary,
      textTransform: 'uppercase' as const,
      letterSpacing: '0.05em',
    },
    
    select: {
      padding: `${spacing.sm} ${spacing.md}`,
      fontSize: typography.fontSize.sm,
      color: colors.text.primary,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      transition: `border-color ${transitions.base}`,
      outline: 'none',
    } as React.CSSProperties,
    
    toggleContainer: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing.sm,
    },
    
    toggle: {
      position: 'relative' as const,
      width: '44px',
      height: '22px',
      backgroundColor: whiteBackground ? colors.primary.main : colors.neutral[300],
      borderRadius: borderRadius.full,
      cursor: 'pointer',
      transition: `background-color ${transitions.base}`,
    },
    
    toggleKnob: {
      position: 'absolute' as const,
      top: '2px',
      left: whiteBackground ? '24px' : '2px',
      width: '18px',
      height: '18px',
      backgroundColor: colors.background.main,
      borderRadius: borderRadius.full,
      transition: `left ${transitions.base}`,
      boxShadow: shadows.sm,
    },
    
    processButton: {
      width: '100%',
      padding: `${spacing.md} ${spacing.lg}`,
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.inverse,
      backgroundColor: processing ? colors.neutral[400] : colors.primary.main,
      border: 'none',
      borderRadius: borderRadius.md,
      cursor: processing ? 'not-allowed' : 'pointer',
      transition: `all ${transitions.base}`,
      boxShadow: processing ? 'none' : shadows.base,
      marginTop: spacing.md,
    } as React.CSSProperties,
    
    completionCard: {
      padding: spacing.lg,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.success}20`,
      borderRadius: borderRadius.lg,
      textAlign: 'center' as const,
      boxShadow: shadows.md,
    },
    
    completionTitle: {
      fontSize: typography.fontSize.lg,
      fontWeight: typography.fontWeight.semibold,
      color: colors.success,
      marginBottom: spacing.md,
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
            <p style={styles.subtitle}>Professional spare-part image processing</p>
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

      <div style={styles.mainContent}>
        <div style={styles.leftPanel}>
          <UploadZone
            onFilesSelected={handleFilesSelected}
            maxFiles={100}
            compact={files.length > 0}
          />

          {processing && files.length === 1 && !files[0].name.toLowerCase().endsWith(".zip") && (
            <div className="fade-in">
              <ProgressBar progress={progress} label="Processing image..." />
            </div>
          )}

          {processedBlob && (
            <div style={styles.completionCard} className="fade-in">
              <h3 style={styles.completionTitle}>Processing Complete!</h3>
              <DownloadButton
                blob={processedBlob}
                filename={`processed_${files[0]?.name || "image"}.${format.toLowerCase()}`}
                label="Download Processed Image"
              />
            </div>
          )}

          {jobId && (
            <div className="fade-in">
              <JobStatusComponent 
                jobId={jobId} 
                onComplete={handleJobComplete}
                onRetry={(newJobId) => {
                  setJobId(newJobId);
                  setProcessing(true);
                }}
                outputFormat={format}
                whiteBackground={whiteBackground}
              />
            </div>
          )}
        </div>

        {files.length > 0 && (
          <div style={styles.rightPanel} className="fade-in">
            <div style={styles.optionsCard}>
              <h3 style={styles.optionsTitle}>
                <Settings size={16} />
                Options
              </h3>
              <div style={styles.optionsGrid}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Output Format</label>
                  <select
                    value={format}
                    onChange={(e) => setFormat(e.target.value as "PNG" | "JPEG" | "JPG")}
                    style={styles.select}
                    onFocus={(e) => e.currentTarget.style.borderColor = colors.primary.light}
                    onBlur={(e) => e.currentTarget.style.borderColor = colors.neutral[300]}
                  >
                    <option value="PNG">PNG</option>
                    <option value="JPEG">JPEG</option>
                  </select>
                </div>
                
                <div style={styles.formGroup}>
                  <label style={styles.label}>White Background</label>
                  <div style={styles.toggleContainer}>
                    <div 
                      style={styles.toggle}
                      onClick={() => setWhiteBackground(!whiteBackground)}
                    >
                      <div style={styles.toggleKnob} />
                    </div>
                    <span style={{ fontSize: typography.fontSize.xs, color: colors.text.secondary }}>
                      {whiteBackground ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>
                
                <button
                  onClick={handleProcess}
                  disabled={processing}
                  style={styles.processButton}
                  onMouseEnter={(e) => {
                    if (!processing) {
                      e.currentTarget.style.backgroundColor = colors.primary.hover;
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = shadows.md;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!processing) {
                      e.currentTarget.style.backgroundColor = colors.primary.main;
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = shadows.base;
                    }
                  }}
                >
                  {processing ? "Processing..." : `Process ${files.length} file${files.length > 1 ? "s" : ""}`}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
