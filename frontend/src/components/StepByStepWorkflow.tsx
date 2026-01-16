/** Step-by-step workflow component for streamlined part processing */
import { useState, useEffect } from "react";
import { UploadZone } from "./UploadZone";
import { getPartInfo, processPartImages, PartInfo, ProcessPartResponse } from "../services/api";
import { FileWithPreview } from "../types";
import { ChevronLeft, ChevronRight, Upload, Search, Image, CheckCircle } from "lucide-react";

interface StepByStepWorkflowProps {
  onSuccess?: (response: ProcessPartResponse) => void;
  onError?: (error: string) => void;
}

type WorkflowStep = "upload" | "part-number" | "review" | "processing" | "complete";

export function StepByStepWorkflow({ onSuccess, onError }: StepByStepWorkflowProps) {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>("upload");
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [partNumber, setPartNumber] = useState("");
  const [partInfo, setPartInfo] = useState<PartInfo | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ProcessPartResponse | null>(null);

  // Handle file selection
  const handleFilesSelected = (selectedFiles: File[]) => {
    if (selectedFiles.length < 2 || selectedFiles.length > 4) {
      setError("Please upload 2-4 images");
      return;
    }

    const filesWithPreview = selectedFiles.map((file) => {
      const fileWithPreview = file as FileWithPreview;
      fileWithPreview.preview = URL.createObjectURL(file);
      return fileWithPreview;
    });

    setFiles(filesWithPreview);
    setError(null);
  };

  // Handle next step from upload
  const handleUploadNext = () => {
    if (files.length < 2 || files.length > 4) {
      setError("Please upload 2-4 images before proceeding");
      return;
    }
    setCurrentStep("part-number");
    setError(null);
  };

  // Handle part number lookup
  const handlePartNumberNext = async () => {
    if (!partNumber.trim()) {
      setError("Please enter a part number");
      return;
    }

    try {
      const info = await getPartInfo(partNumber.trim());
      setPartInfo(info);
      setCurrentStep("review");
      setError(null);
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError(`Part number '${partNumber.trim()}' not found in database`);
      } else {
        setError("Failed to load part information. Please check your connection and try again.");
      }
    }
  };

  // Handle final processing
  const handleProcessImages = async () => {
    if (!partInfo) {
      setError("Part information is missing");
      return;
    }

    setCurrentStep("processing");
    setProcessing(true);
    setError(null);

    try {
      const result = await processPartImages(
        files,
        partInfo.part_number,
        undefined, // Auto-assign view numbers 1, 2, 3...
        "PNG",
        true, // White background
        85, // Compression quality
        2048, // Max dimension
        true, // Add label
        "bottom-left" // Label position
      );

      setResponse(result);
      setCurrentStep("complete");
      setProcessing(false);

      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err: any) {
      setProcessing(false);
      const errorMessage = err.response?.data?.detail || err.message || "Processing failed";
      setError(errorMessage);
      setCurrentStep("review"); // Go back to review step

      if (onError) {
        onError(errorMessage);
      }
    }
  };

  // Reset workflow
  const handleStartOver = () => {
    setCurrentStep("upload");
    setFiles([]);
    setPartNumber("");
    setPartInfo(null);
    setProcessing(false);
    setError(null);
    setResponse(null);

    // Cleanup preview URLs
    files.forEach((file) => {
      if (file.preview) {
        URL.revokeObjectURL(file.preview);
      }
    });
  };

  // Cleanup preview URLs on unmount
  useEffect(() => {
    return () => {
      files.forEach((file) => {
        if (file.preview) {
          URL.revokeObjectURL(file.preview);
        }
      });
    };
  }, [files]);

  const renderStepIndicator = () => {
    const steps = [
      { key: "upload", label: "Upload Photos", icon: Upload },
      { key: "part-number", label: "Part Number", icon: Search },
      { key: "review", label: "Review", icon: Image },
      { key: "processing", label: "Processing", icon: CheckCircle },
    ];

    const stepIndex = steps.findIndex(step => step.key === currentStep);

    return (
      <div className="step-indicator">
        {steps.map((step, index) => {
          const Icon = step.icon;
          const isActive = step.key === currentStep;
          const isCompleted = index < stepIndex || currentStep === "complete";

          return (
            <div key={step.key} className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
              <div className="step-icon">
                <Icon size={16} />
              </div>
              <span className="step-label">{step.label}</span>
            </div>
          );
        })}
      </div>
    );
  };

  const renderUploadStep = () => (
    <div className="step-content">
      <h2>Step 1: Upload Part Photos</h2>
      <p>Take 2-4 clear photos of the part from different angles</p>

      <UploadZone
        onFilesSelected={handleFilesSelected}
        multiple={true}
        maxFiles={4}
        disabled={processing}
      />

      {files.length > 0 && (
        <div className="files-preview">
          <h4>Selected Photos ({files.length}/4):</h4>
          <div className="files-grid">
            {files.map((file, index) => (
              <div key={index} className="file-preview">
                {file.preview && (
                  <img src={file.preview} alt={`Photo ${index + 1}`} />
                )}
                <span className="file-label">View {index + 1}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="step-actions">
        <button
          className="btn-primary"
          onClick={handleUploadNext}
          disabled={files.length < 2 || files.length > 4}
        >
          Next: Enter Part Number
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );

  const renderPartNumberStep = () => (
    <div className="step-content">
      <h2>Step 2: Enter Part Number</h2>
      <p>Enter the part number to look up description and details</p>

      <div className="part-number-input">
        <label htmlFor="part-number">Part Number</label>
        <input
          id="part-number"
          type="text"
          value={partNumber}
          onChange={(e) => setPartNumber(e.target.value)}
          placeholder="Enter part number..."
          onKeyPress={(e) => e.key === 'Enter' && handlePartNumberNext()}
          autoFocus
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="step-actions">
        <button
          className="btn-secondary"
          onClick={() => setCurrentStep("upload")}
        >
          <ChevronLeft size={16} />
          Back
        </button>
        <button
          className="btn-primary"
          onClick={handlePartNumberNext}
          disabled={!partNumber.trim()}
        >
          Look Up Part Info
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );

  const renderReviewStep = () => (
    <div className="step-content">
      <h2>Step 3: Review & Process</h2>
      <p>Review the information and start processing</p>

      {partInfo && (
        <div className="part-info-card">
          <h3>Part Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <strong>Part Number:</strong>
              <span>{partInfo.part_number}</span>
            </div>
            <div className="info-item">
              <strong>Description:</strong>
              <span>{partInfo.description || "N/A"}</span>
            </div>
            <div className="info-item">
              <strong>Location:</strong>
              <span>{partInfo.location || "N/A"}</span>
            </div>
            {partInfo.item_note && (
              <div className="info-item">
                <strong>Item Note:</strong>
                <span>{partInfo.item_note}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="processing-preview">
        <h4>Processing Preview</h4>
        <ul>
          <li>✓ Background removal</li>
          <li>✓ White background applied</li>
          <li>✓ Description label added to image</li>
          <li>✓ Saved with proper naming to Google Drive</li>
          <li>✓ Files organized by part number</li>
        </ul>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="step-actions">
        <button
          className="btn-secondary"
          onClick={() => setCurrentStep("part-number")}
        >
          <ChevronLeft size={16} />
          Back
        </button>
        <button
          className="btn-primary"
          onClick={handleProcessImages}
          disabled={!partInfo}
        >
          Process Images
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );

  const renderProcessingStep = () => (
    <div className="step-content">
      <h2>Processing Your Images...</h2>
      <div className="processing-animation">
        <div className="spinner"></div>
        <p>Removing backgrounds and applying labels...</p>
        <p className="processing-note">This may take a moment depending on image size.</p>
      </div>
    </div>
  );

  const renderCompleteStep = () => (
    <div className="step-content">
      <div className="success-content">
        <CheckCircle size={48} className="success-icon" />
        <h2>Processing Complete!</h2>

        {response && (
          <div className="success-details">
            <p><strong>Part:</strong> {response.part_number}</p>
            <p><strong>Files Processed:</strong> {response.files_saved}</p>
            <p><strong>Status:</strong> {response.message}</p>

            {response.saved_paths.length > 0 && (
              <div className="saved-files">
                <h4>Saved Files:</h4>
                <ul>
                  {response.saved_paths.map((file: { filename: string; url: string }, index: number) => (
                    <li key={index}>
                      <a href={file.url} target="_blank" rel="noopener noreferrer">
                        {file.filename}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="step-actions">
          <button className="btn-primary" onClick={handleStartOver}>
            Process Another Part
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="step-workflow">
      {currentStep !== "complete" && renderStepIndicator()}

      {currentStep === "upload" && renderUploadStep()}
      {currentStep === "part-number" && renderPartNumberStep()}
      {currentStep === "review" && renderReviewStep()}
      {currentStep === "processing" && renderProcessingStep()}
      {currentStep === "complete" && renderCompleteStep()}

      <style>{`
        .step-workflow {
          max-width: 100%;
          margin: 0;
          padding: 12px;
          width: 100%;
          box-sizing: border-box;
        }

        @media (min-width: 768px) {
          .step-workflow {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
          }
        }

        .step-indicator {
          display: flex;
          justify-content: space-between;
          margin-bottom: 20px;
          padding: 0 8px;
          overflow-x: auto;
        }

        @media (min-width: 768px) {
          .step-indicator {
            justify-content: center;
            margin-bottom: 40px;
            padding: 0 20px;
          }
        }

        .step {
          display: flex;
          flex-direction: column;
          align-items: center;
          flex: 1;
          min-width: 60px;
          max-width: 80px;
          position: relative;
        }

        @media (min-width: 768px) {
          .step {
            max-width: 120px;
            min-width: 100px;
          }
        }

        .step:not(:last-child)::after {
          content: '';
          position: absolute;
          top: 14px;
          left: calc(100% - 10px);
          width: calc(100% - 20px);
          height: 2px;
          background: #e0e0e0;
          z-index: -1;
          display: none;
        }

        @media (min-width: 480px) {
          .step:not(:last-child)::after {
            display: block;
          }
        }

        @media (min-width: 768px) {
          .step:not(:last-child)::after {
            top: 16px;
            left: calc(100% - 20px);
            width: calc(100% - 40px);
          }
        }

        .step.completed:not(:last-child)::after {
          background: #007bff;
        }

        .step-icon {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: #e0e0e0;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 6px;
          transition: all 0.3s ease;
        }

        @media (min-width: 768px) {
          .step-icon {
            width: 32px;
            height: 32px;
            margin-bottom: 8px;
          }
        }

        .step.active .step-icon {
          background: #007bff;
          color: white;
        }

        .step.completed .step-icon {
          background: #28a745;
          color: white;
        }

        .step-label {
          font-size: 10px;
          text-align: center;
          color: #666;
          font-weight: 500;
          line-height: 1.2;
        }

        @media (min-width: 768px) {
          .step-label {
            font-size: 12px;
          }
        }

        .step.active .step-label {
          color: #007bff;
          font-weight: 600;
        }

        .step-content {
          background: white;
          border-radius: 8px;
          padding: 16px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
          margin-bottom: 16px;
        }

        @media (min-width: 768px) {
          .step-content {
            padding: 30px;
          }
        }

        .step-content h2 {
          margin: 0 0 8px 0;
          color: #333;
          font-size: 20px;
        }

        @media (min-width: 768px) {
          .step-content h2 {
            font-size: 24px;
          }
        }

        .step-content > p {
          margin: 0 0 16px 0;
          color: #666;
          font-size: 14px;
        }

        @media (min-width: 768px) {
          .step-content > p {
            margin-bottom: 24px;
            font-size: 16px;
          }
        }

        .files-preview {
          margin: 16px 0;
        }

        @media (min-width: 768px) {
          .files-preview {
            margin: 20px 0;
          }
        }

        .files-preview h4 {
          margin-bottom: 12px;
          font-size: 14px;
          color: #333;
        }

        @media (min-width: 768px) {
          .files-preview h4 {
            margin-bottom: 16px;
            font-size: 16px;
          }
        }

        .files-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }

        @media (min-width: 480px) {
          .files-grid {
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          }
        }

        @media (min-width: 768px) {
          .files-grid {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 16px;
          }
        }

        .file-preview {
          position: relative;
          border-radius: 8px;
          overflow: hidden;
          background: #f8f9fa;
          aspect-ratio: 1;
        }

        .file-preview img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .file-label {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          background: rgba(0,0,0,0.7);
          color: white;
          padding: 4px 6px;
          font-size: 10px;
          text-align: center;
        }

        @media (min-width: 768px) {
          .file-label {
            padding: 4px 8px;
            font-size: 12px;
          }
        }

        .part-number-input {
          margin-bottom: 20px;
        }

        @media (min-width: 768px) {
          .part-number-input {
            margin-bottom: 24px;
          }
        }

        .part-number-input label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #333;
          font-size: 14px;
        }

        @media (min-width: 768px) {
          .part-number-input label {
            font-size: 16px;
          }
        }

        .part-number-input input {
          width: 100%;
          padding: 14px 16px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          font-size: 16px;
          box-sizing: border-box;
          transition: border-color 0.3s ease;
        }

        .part-number-input input:focus {
          outline: none;
          border-color: #007bff;
        }

        .part-info-card {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 20px;
        }

        @media (min-width: 768px) {
          .part-info-card {
            padding: 24px;
            margin-bottom: 24px;
          }
        }

        .part-info-card h3 {
          margin: 0 0 12px 0;
          color: #333;
          font-size: 16px;
        }

        @media (min-width: 768px) {
          .part-info-card h3 {
            margin-bottom: 16px;
            font-size: 18px;
          }
        }

        .info-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
        }

        @media (min-width: 480px) {
          .info-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (min-width: 768px) {
          .info-grid {
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          }
        }

        .info-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .info-item strong {
          color: #666;
          font-size: 14px;
        }

        .info-item span {
          color: #333;
          font-size: 16px;
        }

        .processing-preview {
          background: #e8f5e8;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 24px;
        }

        .processing-preview h4 {
          margin: 0 0 12px 0;
          color: #28a745;
        }

        .processing-preview ul {
          margin: 0;
          padding-left: 0;
          list-style: none;
        }

        .processing-preview li {
          margin: 8px 0;
          color: #333;
          font-size: 14px;
        }

        .processing-animation {
          text-align: center;
          padding: 40px 20px;
        }

        .spinner {
          width: 48px;
          height: 48px;
          border: 4px solid #e0e0e0;
          border-top: 4px solid #007bff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto 20px auto;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .processing-animation p {
          margin: 8px 0;
          font-size: 16px;
          color: #333;
        }

        .processing-note {
          font-size: 14px !important;
          color: #666 !important;
        }

        .success-content {
          text-align: center;
          padding: 20px;
        }

        .success-icon {
          color: #28a745;
          margin-bottom: 16px;
        }

        .success-details {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 24px;
          margin: 24px 0;
          text-align: left;
        }

        .success-details p {
          margin: 8px 0;
          font-size: 16px;
        }

        .saved-files {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #e0e0e0;
        }

        .saved-files h4 {
          margin-bottom: 12px;
          color: #333;
        }

        .saved-files ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .saved-files li {
          margin: 8px 0;
        }

        .saved-files a {
          color: #007bff;
          text-decoration: none;
          font-size: 14px;
        }

        .saved-files a:hover {
          text-decoration: underline;
        }

        .error-message {
          color: #dc3545;
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 4px;
          padding: 12px;
          margin: 16px 0;
          font-size: 14px;
        }

        .step-actions {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-top: 20px;
        }

        @media (min-width: 480px) {
          .step-actions {
            flex-direction: row;
            justify-content: space-between;
            gap: 16px;
            margin-top: 32px;
          }
        }

        .step-actions button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 16px 20px;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s ease;
          border: none;
          min-height: 48px;
          justify-content: center;
          flex: 1;
          width: 100%;
          box-sizing: border-box;
        }

        @media (min-width: 480px) {
          .step-actions button {
            padding: 12px 24px;
            min-width: 140px;
            width: auto;
            flex: none;
          }
        }

        .btn-primary {
          background: #007bff;
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          background: #0056b3;
          transform: translateY(-1px);
        }

        .btn-primary:disabled {
          background: #ccc;
          cursor: not-allowed;
          transform: none;
        }

        .btn-secondary {
          background: #6c757d;
          color: white;
        }

        .btn-secondary:hover {
          background: #545b62;
          transform: translateY(-1px);
        }

        @media (max-width: 600px) {
          .step-workflow {
            padding: 16px;
          }

          .step-content {
            padding: 20px;
          }

          .files-grid {
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          }

          .info-grid {
            grid-template-columns: 1fr;
          }

          .step-actions {
            flex-direction: column;
          }

          .step-actions button {
            min-width: auto;
          }
        }
      `}</style>
    </div>
  );
}