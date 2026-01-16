/** Drag and drop upload zone component */
import React, { useCallback, useState } from "react";
import { FileWithPreview } from "../types";
import { CloudUpload, X, FileImage } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows, transitions, mobileSpacing, mobileTypography, touchTargets } from "../styles/design-system";

interface UploadZoneProps {
  onFilesSelected: (files: FileWithPreview[]) => void;
  acceptedTypes?: string[];
  maxFiles?: number;
  compact?: boolean;
  multiple?: boolean;
  disabled?: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFilesSelected,
  acceptedTypes = [".jpg", ".jpeg", ".png", ".webp", ".zip"],
  maxFiles,
  compact = false,
  multiple: _multiple = true,
  disabled: _disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const processFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;

      const fileArray: FileWithPreview[] = Array.from(files)
        .filter((file) => {
          const ext = "." + file.name.split(".").pop()?.toLowerCase();
          return acceptedTypes.includes(ext) || file.name.toLowerCase().endsWith(".zip");
        })
        .slice(0, maxFiles || files.length)
        .map((file) => {
          const fileWithPreview = file as FileWithPreview;
          if (file.type.startsWith("image/")) {
            fileWithPreview.preview = URL.createObjectURL(file);
          }
          return fileWithPreview;
        });

      setSelectedFiles(fileArray);
      onFilesSelected(fileArray);
    },
    [acceptedTypes, maxFiles, onFilesSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      processFiles(e.dataTransfer.files);
    },
    [processFiles]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      processFiles(e.target.files);
    },
    [processFiles]
  );

  const removeFile = useCallback(
    (index: number) => {
      const newFiles = selectedFiles.filter((_, i) => i !== index);
      setSelectedFiles(newFiles);
      onFilesSelected(newFiles);
    },
    [selectedFiles, onFilesSelected]
  );

  const styles = {
    dropZone: {
      border: `2px solid ${isDragging ? colors.primary.main : colors.neutral[300]}`,
      borderRadius: borderRadius.lg,
      padding: compact ? `${mobileSpacing.md}` : `${mobileSpacing.lg} ${mobileSpacing.md}`,
      textAlign: 'center' as const,
      backgroundColor: isDragging ? `${colors.primary.light}08` : colors.background.main,
      cursor: 'pointer',
      transition: `all ${transitions.base}`,
      boxShadow: isDragging ? `0 0 0 4px ${colors.primary.light}20` : 'none',
      minHeight: touchTargets.large,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '100%',
      boxSizing: 'border-box' as const,
      '@media (min-width: 768px)': {
        padding: compact ? `${spacing.md} ${spacing.md}` : `${spacing.lg} ${spacing.xl}`,
        maxHeight: compact ? '140px' : '280px',
      },
    },
    
    iconContainer: {
      display: 'inline-flex',
      padding: compact ? spacing.xs : spacing.sm,
      backgroundColor: isDragging ? colors.primary.light : colors.neutral[100],
      borderRadius: borderRadius.full,
      marginBottom: compact ? spacing.xs : spacing.sm,
      transition: `all ${transitions.base}`,
    },
    
    mainText: {
      fontSize: compact ? mobileTypography.fontSize.base : mobileTypography.fontSize.lg,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: mobileSpacing.xs,
    },

    secondaryText: {
      fontSize: mobileTypography.fontSize.sm,
      color: colors.text.secondary,
      marginBottom: mobileSpacing.xs,
    },

    supportedText: {
      fontSize: mobileTypography.fontSize.xs,
      color: colors.text.tertiary,
    },
    
    filesSection: {
      flex: 1,
      minHeight: 0,
      display: 'flex',
      flexDirection: 'column' as const,
      overflow: 'hidden',
    },
    
    filesTitle: {
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: spacing.sm,
      padding: `0 ${spacing.xs}`,
    },
    
    filesGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr',
      gap: mobileSpacing.sm,
      overflowY: 'auto' as const,
      overflowX: 'hidden' as const,
      paddingRight: mobileSpacing.xs,
      flex: 1,
      minHeight: 0,
      alignContent: 'flex-start',
      width: '100%',
      maxWidth: '100%',
      boxSizing: 'border-box' as const,
      '@media (min-width: 480px)': {
        gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(200px, 1fr))',
      },
      '@media (min-width: 768px)': {
        gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: spacing.sm,
        paddingRight: spacing.xs,
      },
    },
    
    fileCard: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing.sm,
      padding: spacing.sm,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.md,
      boxShadow: shadows.sm,
      transition: `all ${transitions.base}`,
    } as React.CSSProperties,
    
    thumbnail: {
      width: '40px',
      height: '40px',
      objectFit: 'cover' as const,
      borderRadius: borderRadius.sm,
      backgroundColor: colors.neutral[100],
      flexShrink: 0,
    },
    
    thumbnailPlaceholder: {
      width: '40px',
      height: '40px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: borderRadius.sm,
      backgroundColor: colors.neutral[100],
      flexShrink: 0,
    },
    
    fileInfo: {
      flex: 1,
      minWidth: 0,
    },
    
    fileName: {
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.primary,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap' as const,
      marginBottom: '2px',
    },
    
    fileSize: {
      fontSize: '11px',
      color: colors.text.secondary,
    },
    
    removeButton: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '24px',
      height: '24px',
      padding: 0,
      backgroundColor: 'transparent',
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.full,
      cursor: 'pointer',
      transition: `all ${transitions.fast}`,
      color: colors.text.secondary,
      flexShrink: 0,
    } as React.CSSProperties,
  };

  return (
    <>
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        style={styles.dropZone}
        data-upload-zone
      >
        <input
          type="file"
          id="file-input"
          multiple
          accept={acceptedTypes.join(",")}
          onChange={handleFileInput}
          style={{ display: "none" }}
        />
        <label htmlFor="file-input" style={{ cursor: 'pointer', display: 'block' }}>
          <div style={styles.iconContainer} data-upload-icon>
            <CloudUpload 
              size={compact ? 32 : 48} 
              color={isDragging ? colors.primary.main : colors.neutral[400]}
              strokeWidth={1.5}
            />
          </div>
          <div style={styles.mainText}>
            {isDragging ? "Drop files here" : "Drag & drop images or ZIP"}
          </div>
          {!compact && (
            <>
              <div style={styles.secondaryText}>or click to browse</div>
              <div style={styles.supportedText}>
                JPG, PNG, WEBP, ZIP • Max {maxFiles || "unlimited"} files
              </div>
            </>
          )}
        </label>
      </div>

      {selectedFiles.length > 0 && (
        <div style={styles.filesSection}>
          <div style={styles.filesTitle}>{selectedFiles.length} file{selectedFiles.length > 1 ? 's' : ''} selected</div>
          <div style={styles.filesGrid} data-files-grid>
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                style={styles.fileCard}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = shadows.md;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = shadows.sm;
                }}
              >
                {file.preview ? (
                  <img
                    src={file.preview}
                    alt={file.name}
                    style={styles.thumbnail}
                  />
                ) : (
                  <div style={styles.thumbnailPlaceholder}>
                    <FileImage size={18} color={colors.neutral[400]} />
                  </div>
                )}
                <div style={styles.fileInfo}>
                  <div style={styles.fileName}>{file.name}</div>
                  <div style={styles.fileSize}>
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  style={styles.removeButton}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = colors.error;
                    e.currentTarget.style.borderColor = colors.error;
                    e.currentTarget.style.color = colors.text.inverse;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = colors.neutral[300];
                    e.currentTarget.style.color = colors.text.secondary;
                  }}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};
