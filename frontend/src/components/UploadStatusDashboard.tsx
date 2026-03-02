/** Upload queue dashboard component for tracking active and recent uploads */
import React, { useState, useEffect } from "react";
import { uploadTracker, UploadAttempt } from "../services/uploadTracker";
import { RefreshCw, AlertCircle, Clock, CheckCircle, RotateCcw } from "lucide-react";

interface UploadStatusDashboardProps {
  compact?: boolean;
}

export const UploadStatusDashboard: React.FC<UploadStatusDashboardProps> = ({
  compact = false
}) => {
  const [uploads, setUploads] = useState<UploadAttempt[]>([]);

  // Load uploads from tracker
  const loadUploads = () => {
    const allUploads = uploadTracker.getAllUploads();
    // Sort by timestamp, newest first
    const sorted = allUploads.sort((a, b) => b.timestamp - a.timestamp);
    setUploads(sorted);
  };

  // Auto-refresh every 2 seconds
  useEffect(() => {
    loadUploads();
    const interval = setInterval(loadUploads, 2000);
    return () => clearInterval(interval);
  }, []);

  // Retry failed upload
  const handleRetryUpload = (upload: UploadAttempt) => {
    const didRetry = uploadTracker.retryUpload(upload.id);
    if (didRetry) {
      loadUploads();
    }
  };

  const getStatusIcon = (status: UploadAttempt['status']) => {
    const iconStyle: React.CSSProperties = { flexShrink: 0 };

    switch (status) {
      case 'pending':
        return <Clock size={16} style={{ ...iconStyle, color: '#1565c0' }} />;
      case 'in_progress':
        return <RefreshCw size={16} style={{ ...iconStyle, color: '#ff9800', animation: 'spin 1s linear infinite' }} />;
      case 'completed':
        return <CheckCircle size={16} style={{ ...iconStyle, color: '#2e7d32' }} />;
      case 'failed':
        return <AlertCircle size={16} style={{ ...iconStyle, color: '#c62828' }} />;
      default:
        return null;
    }
  };

  const getStatusText = (upload: UploadAttempt) => {
    switch (upload.status) {
      case 'pending':
        return 'Queued';
      case 'in_progress':
        return 'Uploading...';
      case 'completed':
        return 'Completed';
      case 'failed':
        return `Failed (${upload.retryCount}/${upload.maxRetries} retries)`;
      default:
        return upload.status;
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    if (diff < 60000) { // Less than 1 minute
      return 'Just now';
    } else if (diff < 3600000) { // Less than 1 hour
      return `${Math.floor(diff / 60000)}m ago`;
    } else if (diff < 86400000) { // Less than 1 day
      return `${Math.floor(diff / 3600000)}h ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const counts = uploadTracker.getPendingCount();
  const successCount = uploadTracker.getSuccessCount();
  const recentUploads = compact ? uploads.slice(0, 5) : uploads;

  if (compact && uploads.length === 0 && successCount === 0) {
    return null; // Hide when compact and no uploads
  }

  const styles = {
    container: {
      background: '#f8f9fa',
      border: '1px solid #e9ecef',
      borderRadius: '8px',
      padding: '16px',
      margin: '16px 0'
    } as React.CSSProperties,

    header: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '12px',
      gap: '12px'
    } as React.CSSProperties,

    title: {
      fontSize: '16px',
      fontWeight: '600',
      color: '#333',
      margin: '0'
    } as React.CSSProperties,

    statusSummary: {
      display: 'flex',
      gap: '12px',
      fontSize: '14px',
      flexWrap: 'wrap',
      flex: 1
    } as React.CSSProperties,

    summaryItem: (type: 'pending' | 'failed' | 'completed') => ({
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      padding: '4px 8px',
      borderRadius: '12px',
      fontSize: '12px',
      fontWeight: '500',
      background: type === 'pending' ? '#e3f2fd' : type === 'failed' ? '#ffebee' : '#e8f5e8',
      color: type === 'pending' ? '#1565c0' : type === 'failed' ? '#c62828' : '#2e7d32'
    } as React.CSSProperties),

    actions: {
      display: 'flex',
      gap: '8px'
    } as React.CSSProperties,

    iconButton: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '32px',
      height: '32px',
      border: '1px solid #ddd',
      background: 'white',
      borderRadius: '6px',
      cursor: 'pointer',
      transition: 'all 0.2s'
    } as React.CSSProperties,

    uploadList: {
      maxHeight: compact ? '200px' : '400px',
      overflowY: 'auto'
    } as React.CSSProperties,

    uploadItem: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 12px',
      borderBottom: '1px solid #e9ecef',
      transition: 'background 0.2s'
    } as React.CSSProperties,

    uploadInfo: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      flex: 1
    } as React.CSSProperties,

    uploadDetails: {
      flex: 1
    } as React.CSSProperties,

    partNumber: {
      fontWeight: '600',
      color: '#333',
      fontSize: '14px'
    } as React.CSSProperties,

    uploadMeta: {
      fontSize: '12px',
      color: '#666',
      display: 'flex',
      gap: '8px'
    } as React.CSSProperties,

    retryButton: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '24px',
      height: '24px',
      border: 'none',
      background: '#fff3cd',
      color: '#856404',
      borderRadius: '4px',
      cursor: 'pointer',
      transition: 'all 0.2s'
    } as React.CSSProperties,

    emptyState: {
      textAlign: 'center',
      color: '#666',
      padding: '20px',
      fontSize: '14px'
    } as React.CSSProperties
  };

  return (
    <div style={styles.container}>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <div style={styles.header}>
        <h3 style={styles.title}>
          Upload Queue
        </h3>

        <div style={styles.statusSummary}>
          {counts.pending + counts.inProgress > 0 && (
            <div style={styles.summaryItem('pending')}>
              <Clock size={12} />
              {counts.pending + counts.inProgress} active
            </div>
          )}
          {counts.failed > 0 && (
            <div style={styles.summaryItem('failed')}>
              <AlertCircle size={12} />
              {counts.failed} failed
            </div>
          )}
          {successCount > 0 && (
            <div style={styles.summaryItem('completed')}>
              <CheckCircle size={12} />
              {successCount} uploaded
            </div>
          )}
        </div>
      </div>

      {recentUploads.length > 0 && (
        <div style={styles.uploadList}>
          {recentUploads.map((upload, index) => (
            <div
              key={upload.id}
              style={{
                ...styles.uploadItem,
                borderBottom: index === recentUploads.length - 1 ? 'none' : '1px solid #e9ecef'
              }}
            >
              <div style={styles.uploadInfo}>
                {getStatusIcon(upload.status)}
                <div style={styles.uploadDetails}>
                  <div style={styles.partNumber}>{upload.partNumber}</div>
                  <div style={styles.uploadMeta}>
                    <span>{getStatusText(upload)}</span>
                    <span>•</span>
                    <span>{formatTimestamp(upload.timestamp)}</span>
                    {upload.lastError && (
                      <>
                        <span>•</span>
                        <span title={upload.lastError} style={{ color: '#c62828' }}>
                          {upload.lastError.length > 30
                            ? `${upload.lastError.substring(0, 30)}...`
                            : upload.lastError}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div>
                {upload.status === 'failed' && upload.files.length > 0 && (
                  <button
                    style={styles.retryButton}
                    onClick={() => handleRetryUpload(upload)}
                    title="Retry upload"
                  >
                    <RotateCcw size={12} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {uploads.length === 0 && (
        <div style={styles.emptyState}>
          No uploads in queue
        </div>
      )}
    </div>
  );
};
