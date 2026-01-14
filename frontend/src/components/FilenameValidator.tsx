/** Filename validation and renaming interface */
import React, { useState } from "react";
import { AlertCircle, Edit2, Save, X } from "lucide-react";
import { colors, spacing, typography, borderRadius, transitions } from "../styles/design-system";

interface FilenameValidatorProps {
  invalidFiles: Array<{ filename: string; error: string }>;
  onRename: (oldName: string, newName: string) => void;
  onSkip: (filename: string) => void;
}

export const FilenameValidator: React.FC<FilenameValidatorProps> = ({
  invalidFiles,
  onRename,
  onSkip,
}) => {
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [partNumber, setPartNumber] = useState("");
  const [viewNumber, setViewNumber] = useState("1");
  const [description, setDescription] = useState("");

  const handleEdit = (filename: string) => {
    setEditingFile(filename);
    
    // Try to pre-fill from filename
    const nameWithoutExt = filename.replace(/\.(jpg|jpeg|png|webp)$/i, '');
    const nameParts = nameWithoutExt.split('_', 2);  // Split only first 2 underscores
    const remainder = nameWithoutExt.split('_').slice(2).join('_');  // Everything after 2nd underscore
    
    if (nameParts.length >= 1) setPartNumber(nameParts[0] || "");
    if (nameParts.length >= 2) setViewNumber(nameParts[1] || "1");
    if (remainder) setDescription(remainder || "");
  };

  const handleSave = (oldFilename: string) => {
    const ext = oldFilename.split('.').pop() || 'jpg';
    const newName = `${partNumber}_${viewNumber}_${description}.${ext}`;
    onRename(oldFilename, newName);
    setEditingFile(null);
    setPartNumber("");
    setViewNumber("1");
    setDescription("");
  };

  const styles = {
    card: {
      padding: spacing.lg,
      backgroundColor: `${colors.error}08`,
      border: `1px solid ${colors.error}30`,
      borderRadius: borderRadius.lg,
      marginBottom: spacing.md,
    },
    
    header: {
      display: 'flex',
      alignItems: 'center',
      gap: spacing.sm,
      marginBottom: spacing.md,
    },
    
    title: {
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.error,
    },
    
    fileList: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.sm,
      maxHeight: '300px',
      overflowY: 'auto' as const,
    },
    
    fileItem: {
      padding: spacing.sm,
      backgroundColor: colors.background.main,
      border: `1px solid ${colors.neutral[200]}`,
      borderRadius: borderRadius.md,
      display: 'flex',
      flexDirection: 'column' as const,
      gap: spacing.xs,
    },
    
    fileHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    
    filename: {
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      color: colors.text.primary,
      fontFamily: typography.fontFamily.mono,
    },
    
    error: {
      fontSize: typography.fontSize.xs,
      color: colors.error,
      marginTop: '2px',
    },
    
    editForm: {
      display: 'grid',
      gridTemplateColumns: '1fr 60px',
      gap: spacing.xs,
      marginTop: spacing.sm,
    },
    
    input: {
      padding: `6px ${spacing.sm}`,
      fontSize: typography.fontSize.xs,
      border: `1px solid ${colors.neutral[300]}`,
      borderRadius: borderRadius.sm,
      outline: 'none',
    } as React.CSSProperties,
    
    buttonGroup: {
      display: 'flex',
      gap: spacing.xs,
      marginTop: spacing.xs,
    },
    
    button: {
      padding: `${spacing.xs} ${spacing.sm}`,
      fontSize: typography.fontSize.xs,
      fontWeight: typography.fontWeight.medium,
      border: 'none',
      borderRadius: borderRadius.sm,
      cursor: 'pointer',
      transition: `all ${transitions.fast}`,
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
    } as React.CSSProperties,
    
    editButton: {
      backgroundColor: colors.primary.light,
      color: colors.text.inverse,
    },
    
    saveButton: {
      backgroundColor: colors.success,
      color: colors.text.inverse,
    },
    
    skipButton: {
      backgroundColor: 'transparent',
      color: colors.text.secondary,
      border: `1px solid ${colors.neutral[300]}`,
    },
  };

  if (invalidFiles.length === 0) return null;

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <AlertCircle size={18} color={colors.error} />
        <div style={styles.title}>
          {invalidFiles.length} file{invalidFiles.length > 1 ? 's' : ''} with invalid names
        </div>
      </div>
      
      <div style={{ fontSize: typography.fontSize.xs, color: colors.text.secondary, marginBottom: spacing.sm }}>
        Expected format: <strong>PartNumber_ViewNumber_Description.jpg</strong>
        <br />Example: 58802935_1_BEARING.jpg or 74452282_2_FAN TYPE.jpg
      </div>

      <div style={styles.fileList}>
        {invalidFiles.map((item, index) => (
          <div key={index} style={styles.fileItem}>
            <div style={styles.fileHeader}>
              <div>
                <div style={styles.filename}>{item.filename}</div>
                <div style={styles.error}>{item.error}</div>
              </div>
              
              {editingFile !== item.filename && (
                <div style={{ display: 'flex', gap: spacing.xs }}>
                  <button
                    style={{ ...styles.button, ...styles.editButton }}
                    onClick={() => handleEdit(item.filename)}
                  >
                    <Edit2 size={12} />
                    Rename
                  </button>
                  <button
                    style={{ ...styles.button, ...styles.skipButton }}
                    onClick={() => onSkip(item.filename)}
                  >
                    <X size={12} />
                    Skip
                  </button>
                </div>
              )}
            </div>

            {editingFile === item.filename && (
              <>
                <div style={styles.editForm}>
                  <input
                    type="text"
                    placeholder="Part Number"
                    value={partNumber}
                    onChange={(e) => setPartNumber(e.target.value)}
                    style={styles.input}
                  />
                  <input
                    type="text"
                    placeholder="View"
                    value={viewNumber}
                    onChange={(e) => setViewNumber(e.target.value)}
                    style={styles.input}
                  />
                  <input
                    type="text"
                    placeholder="Description"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    style={{ ...styles.input, gridColumn: '1 / -1' }}
                  />
                </div>
                <div style={styles.buttonGroup}>
                  <button
                    style={{ ...styles.button, ...styles.saveButton }}
                    onClick={() => handleSave(item.filename)}
                  >
                    <Save size={12} />
                    Save as: {partNumber}_{viewNumber}_{description}.{item.filename.split('.').pop()}
                  </button>
                  <button
                    style={{ ...styles.button, ...styles.skipButton }}
                    onClick={() => setEditingFile(null)}
                  >
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

