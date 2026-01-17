/** Drag and drop upload zone component */
import React, { useCallback, useState } from "react";
import { FileWithPreview } from "../types";
import { X, FileImage, Camera } from "lucide-react";
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
  const [selectedFiles, setSelectedFiles] = useState<FileWithPreview[]>([]);

  const processFilesWithoutReset = useCallback(
    (files: File[]) => {
      const fileArray: FileWithPreview[] = files
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

  const handleCameraCapture = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        // Add to existing files instead of replacing
        const newFiles = Array.from(files);
        const existingFiles = selectedFiles;
        const combinedFiles = [...existingFiles, ...newFiles];

        // Apply max files limit if set
        const finalFiles = maxFiles ? combinedFiles.slice(0, maxFiles) : combinedFiles;

        // Process the combined files
        processFilesWithoutReset(finalFiles);
      }
    },
    [selectedFiles, maxFiles, processFilesWithoutReset]
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
      marginTop: mobileSpacing.md,
      display: 'flex',
      flexDirection: 'column' as const,
      width: '100%',
      maxHeight: 'none',
      '@media (min-width: 768px)': {
        marginTop: spacing.md,
      },
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
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: mobileSpacing.md,
      width: '100%',
      maxWidth: '100%',
      boxSizing: 'border-box' as const,
      paddingBottom: mobileSpacing.xs,
      '@media (min-width: 480px)': {
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: spacing.md,
        paddingBottom: spacing.xs,
      },
      '@media (min-width: 768px)': {
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: spacing.md,
        paddingBottom: spacing.xs,
      },
    },
    
    fileCard: {
      position: 'relative' as const,
      aspectRatio: '1',
      borderRadius: borderRadius.md,
      overflow: 'hidden' as const,
      backgroundColor: colors.neutral[100],
      border: `1px solid ${colors.neutral[200]}`,
      boxShadow: shadows.sm,
      transition: `all ${transitions.base}`,
    } as React.CSSProperties,
    
    thumbnail: {
      width: '100%',
      height: '100%',
      objectFit: 'cover' as const,
      display: 'block',
    },
    
    thumbnailPlaceholder: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: colors.neutral[100],
    },
    
    removeButton: {
      position: 'absolute' as const,
      top: '6px',
      right: '6px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '26px',
      height: '26px',
      minWidth: '26px',
      minHeight: '26px',
      padding: 0,
      backgroundColor: 'rgba(220, 53, 69, 0.85)',
      border: 'none',
      borderRadius: borderRadius.full,
      cursor: 'pointer',
      transition: `all ${transitions.fast}`,
      color: colors.text.inverse,
      flexShrink: 0,
      zIndex: 10,
      boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
      touchAction: 'manipulation',
      '@media (min-width: 768px)': {
        width: '28px',
        height: '28px',
        minWidth: '28px',
        minHeight: '28px',
        top: '8px',
        right: '8px',
      },
    } as React.CSSProperties,

    cameraSection: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      gap: mobileSpacing.sm,
      marginTop: mobileSpacing.md,
      '@media (min-width: 768px)': {
        flexDirection: 'row' as const,
        justifyContent: 'center',
        marginTop: spacing.md,
        gap: spacing.md,
      },
    },

    cameraButton: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
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
      minHeight: touchTargets.large,
      '@media (min-width: 768px)': {
        padding: `${spacing.sm} ${spacing.lg}`,
        fontSize: typography.fontSize.sm,
      },
    } as React.CSSProperties,

    divider: {
      display: 'flex',
      alignItems: 'center',
      gap: mobileSpacing.sm,
      color: colors.text.tertiary,
      fontSize: mobileTypography.fontSize.xs,
      margin: `${mobileSpacing.sm} 0`,
      '@media (min-width: 768px)': {
        margin: `${spacing.sm} 0`,
        fontSize: typography.fontSize.xs,
      },
    },

    dividerLine: {
      flex: 1,
      height: '1px',
      backgroundColor: colors.neutral[300],
    },
  };

  return (
    <>
      <input
        type="file"
        id="camera-input"
        accept="image/*"
        capture="environment"
        onChange={handleCameraCapture}
        style={{ display: "none" }}
        multiple={_multiple}
      />

      <div style={styles.cameraSection}>
        <button
          style={styles.cameraButton}
          onClick={() => document.getElementById('camera-input')?.click()}
          type="button"
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = colors.primary.hover;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = colors.primary.main;
          }}
        >
          <Camera size={24} />
          Take Photo
        </button>
        {!compact && (
          <div style={styles.secondaryText}>
            Take {maxFiles ? `${maxFiles} photos` : 'photos'} of the part
          </div>
        )}
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
                    <FileImage size={24} color={colors.neutral[400]} />
                  </div>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(index);
                  }}
                  style={styles.removeButton}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(220, 53, 69, 1)';
                    e.currentTarget.style.transform = 'scale(1.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(220, 53, 69, 0.85)';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                  aria-label="Remove file"
                >
                  <X size={14} strokeWidth={2.5} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};
