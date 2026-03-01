/** Upload status dashboard component for tracking failed uploads */
import React, { useState, useEffect } from "react";
import { uploadTracker, UploadAttempt } from "../services/uploadTracker";
import { RefreshCw, AlertCircle, Clock, CheckCircle, X, RotateCcw } from "lucide-react";

interface UploadStatusDashboardProps {
  compact?: boolean;
}

export const UploadStatusDashboard: React.FC<UploadStatusDashboardProps> = ({
  compact = false
}) => {
  const [uploads, setUploads] = useState<UploadAttempt[]>([]);
  const [refreshing, setRefreshing] = useState(false);

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

  // Manual refresh
  const handleRefresh = () => {
    setRefreshing(true);
    loadUploads();
    setTimeout(() => setRefreshing(false), 500);
  };

  // Retry failed upload
  const handleRetryUpload = (upload: UploadAttempt) => {
    // Since files aren't stored in localStorage, we need user to re-upload
    alert(`To retry ${upload.partNumber}, please use the upload form again with the same part number.`);
  };

  // Clear completed uploads
  const handleClearCompleted = () => {
    const activeUploads = uploads.filter(u =>
      u.status === 'pending' || u.status === 'in_progress' || u.status === 'failed'
    );
    uploadTracker.clearAll();
    // Re-add active uploads
    activeUploads.forEach(upload => {
      // Note: This is a simplified approach - in production you'd want better state management
    });
    loadUploads();
  };

  const getStatusIcon = (status: UploadAttempt['status']) => {
    switch (status) {
      case 'pending':
        return <Clock size={16} className="status-icon pending" />;
      case 'in_progress':
        return <RefreshCw size={16} className="status-icon in-progress spinning" />;
      case 'completed':
        return <CheckCircle size={16} className="status-icon completed" />;
      case 'failed':
        return <AlertCircle size={16} className="status-icon failed" />;
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
  const recentUploads = compact ? uploads.slice(0, 5) : uploads;

  if (compact && uploads.length === 0) {
    return null; // Hide when compact and no uploads
  }

  return (
    <div className="upload-status-dashboard">
      <style jsx>{`
        .upload-status-dashboard {
          background: #f8f9fa;
          border: 1px solid #e9ecef;
          border-radius: 8px;
          padding: 16px;
          margin: 16px 0;
        }

        .dashboard-header {
          display: flex;
          justify-content: between;
          align-items: center;
          margin-bottom: 12px;
          gap: 12px;
        }

        .dashboard-title {
          font-size: 16px;
          font-weight: 600;
          color: #333;
          margin: 0;
        }

        .status-summary {
          display: flex;
          gap: 12px;
          font-size: 14px;
          flex-wrap: wrap;
          flex: 1;
        }

        .summary-item {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
        }

        .summary-item.pending {
          background: #e3f2fd;
          color: #1565c0;
        }
        .summary-item.failed {
          background: #ffebee;
          color: #c62828;
        }
        .summary-item.completed {
          background: #e8f5e8;
          color: #2e7d32;
        }

        .dashboard-actions {
          display: flex;
          gap: 8px;
        }

        .btn-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border: 1px solid #ddd;
          background: white;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-icon:hover {
          background: #f8f9fa;
          border-color: #adb5bd;
        }

        .btn-icon.spinning svg {
          animation: spin 1s linear infinite;
        }

        .upload-list {
          max-height: ${compact ? '200px' : '400px'};
          overflow-y: auto;
        }

        .upload-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          border-bottom: 1px solid #e9ecef;
          transition: background 0.2s;
        }

        .upload-item:hover {
          background: #f1f3f4;
        }

        .upload-item:last-child {
          border-bottom: none;
        }

        .upload-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        .upload-details {
          flex: 1;
        }

        .part-number {
          font-weight: 600;
          color: #333;
          font-size: 14px;
        }

        .upload-meta {
          font-size: 12px;
          color: #666;
          display: flex;
          gap: 8px;
        }

        .status-icon {
          flex-shrink: 0;
        }

        .status-icon.pending { color: #1565c0; }
        .status-icon.in-progress { color: #ff9800; }
        .status-icon.completed { color: #2e7d32; }
        .status-icon.failed { color: #c62828; }

        .upload-actions {
          display: flex;
          gap: 4px;
        }

        .btn-retry {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          border: none;
          background: #fff3cd;
          color: #856404;
          border-radius: 4px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .btn-retry:hover {
          background: #ffeaa7;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .spinning {
          animation: spin 1s linear infinite;
        }
      `}</style>

      <div className="dashboard-header">
        <h3 className="dashboard-title">
          {compact ? 'Upload Status' : 'Upload Queue'}
        </h3>

        <div className="status-summary">
          {counts.pending + counts.inProgress > 0 && (
            <div className="summary-item pending">
              <Clock size={12} />
              {counts.pending + counts.inProgress} active
            </div>
          )}
          {counts.failed > 0 && (
            <div className="summary-item failed">
              <AlertCircle size={12} />
              {counts.failed} failed
            </div>
          )}
          {uploads.filter(u => u.status === 'completed').length > 0 && (
            <div className="summary-item completed">
              <CheckCircle size={12} />
              {uploads.filter(u => u.status === 'completed').length} done
            </div>
          )}
        </div>

        <div className="dashboard-actions">
          <button
            className={`btn-icon ${refreshing ? 'spinning' : ''}`}
            onClick={handleRefresh}
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
          {!compact && uploads.some(u => u.status === 'completed') && (
            <button
              className="btn-icon"
              onClick={handleClearCompleted}
              title="Clear completed"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {recentUploads.length > 0 && (
        <div className="upload-list">
          {recentUploads.map((upload) => (
            <div key={upload.id} className="upload-item">
              <div className="upload-info">
                {getStatusIcon(upload.status)}
                <div className="upload-details">
                  <div className="part-number">{upload.partNumber}</div>
                  <div className="upload-meta">
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

              <div className="upload-actions">
                {upload.status === 'failed' && (
                  <button
                    className="btn-retry"
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
        <div style={{
          textAlign: 'center',
          color: '#666',
          padding: '20px',
          fontSize: '14px'
        }}>
          No uploads in queue
        </div>
      )}
    </div>
  );
};