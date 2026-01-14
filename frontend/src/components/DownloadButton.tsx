/** Download button component */
import React from "react";
import { Download } from "lucide-react";
import { colors, spacing, typography, borderRadius, shadows, transitions } from "../styles/design-system";

interface DownloadButtonProps {
  blob: Blob;
  filename: string;
  label?: string;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({ blob, filename, label = "Download" }) => {
  const [isHovered, setIsHovered] = React.useState(false);

  const handleDownload = () => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const styles = {
    button: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: spacing.sm,
      padding: `14px 28px`,
      fontSize: typography.fontSize.base,
      fontWeight: typography.fontWeight.semibold,
      color: colors.text.inverse,
      backgroundColor: isHovered ? colors.primary.hover : colors.primary.main,
      border: 'none',
      borderRadius: borderRadius.md,
      cursor: 'pointer',
      transition: `all ${transitions.base}`,
      boxShadow: isHovered ? shadows.md : shadows.base,
      transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
    } as React.CSSProperties,
  };

  return (
    <button
      onClick={handleDownload}
      style={styles.button}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Download size={20} />
      {label}
    </button>
  );
};
