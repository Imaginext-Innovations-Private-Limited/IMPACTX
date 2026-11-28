import React, { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Upload, FileText, AlertCircle, CheckCircle2, Sparkles, BookOpen } from 'lucide-react';
import api, { getErrorMessage } from '../api/client';

const MAX_MB = 15;

export default function UploadPage() {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedDoc, setUploadedDoc] = useState(null);

  const validateAndSelect = (file) => {
    setError('');
    setUploadedDoc(null);
    if (!file) return;

    const isPdfName = file.name.toLowerCase().endsWith('.pdf');
    const isPdfMime = !file.type || file.type === 'application/pdf' || file.type === 'application/x-pdf';
    if (!isPdfName || !isPdfMime) {
      setSelectedFile(null);
      setError('Unsupported file format. Please select a valid .pdf document.');
      return;
    }

    if (file.size === 0) {
      setSelectedFile(null);
      setError('The selected PDF file is empty.');
      return;
    }

    if (file.size > MAX_MB * 1024 * 1024) {
      setSelectedFile(null);
      setError(`PDF exceeds the maximum file size of ${MAX_MB} MB.`);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    validateAndSelect(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setError('');
    setUploading(true);
    setProgress(0);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const { data } = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (evt) => {
          if (evt.total) {
            setProgress(Math.round((evt.loaded / evt.total) * 100));
          }
        },
      });
      setUploadedDoc(data.document);
      setProgress(100);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to upload and extract PDF text.'));
    } finally {
      setUploading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Upload Educational Notes</h1>
          <p className="page-subtitle">
            Upload a PDF document to extract text with PyMuPDF for accessible reading, AI
            simplification, audio playback, and practice questions.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: '22px' }}>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          style={{
            border: `2px dashed ${dragActive ? 'var(--primary)' : 'var(--border-strong)'}`,
            backgroundColor: dragActive ? 'var(--primary-soft)' : 'var(--bg-subtle)',
            borderRadius: '14px',
            padding: '44px 24px',
            textAlign: 'center',
            cursor: 'pointer',
          }}
        >
          <Upload size={34} color="var(--primary)" style={{ marginBottom: '12px' }} />
          <h2 className="card-title">Drag & drop your PDF here, or click to browse</h2>
          <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            Accepted format: PDF only (max {MAX_MB} MB). Scanned/image-only PDFs are detected safely.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            style={{ display: 'none' }}
            onChange={(e) => validateAndSelect(e.target.files?.[0])}
          />
        </div>

        {selectedFile && (
          <div
            style={{
              marginTop: '18px',
              padding: '14px 16px',
              borderRadius: '10px',
              backgroundColor: 'var(--bg-subtle)',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FileText size={20} color="var(--primary)" />
              <div>
                <div style={{ fontWeight: 600 }}>{selectedFile.name}</div>
                <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
                  Size: {formatBytes(selectedFile.size)}
                </div>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handleUpload}
              disabled={uploading}
            >
              {uploading ? `Uploading (${progress}%)...` : 'Upload & Extract Text'}
            </button>
          </div>
        )}

        {uploading && (
          <div style={{ marginTop: '14px' }}>
            <div style={{ height: '8px', backgroundColor: 'var(--bg-subtle)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${progress}%`,
                  backgroundColor: 'var(--primary)',
                  transition: 'width 0.15s ease',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {uploadedDoc && (
        <div className="card">
          {uploadedDoc.status === 'needs_ocr' ? (
            <div className="alert alert-warning">
              <AlertCircle size={18} />
              <div>
                <strong>Scanned or Empty PDF Detected:</strong> {uploadedDoc.status_message}
              </div>
            </div>
          ) : (
            <div className="alert alert-success">
              <CheckCircle2 size={18} />
              <div>
                <strong>Upload Successful:</strong> Extracted {uploadedDoc.word_count} words across{' '}
                {uploadedDoc.page_count} page(s).
              </div>
            </div>
          )}

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '16px' }}>
            <Link to={`/reader/${uploadedDoc.id}`} className="btn btn-primary btn-sm">
              <BookOpen size={15} /> Open in Accessible Reader
            </Link>
            {uploadedDoc.extracted_text && (
              <Link to={`/simplify/${uploadedDoc.id}`} className="btn btn-secondary btn-sm">
                <Sparkles size={15} /> Simplify with AI
              </Link>
            )}
          </div>

          <h3 className="card-title">Extracted Text Preview</h3>
          <div
            className="accessible-reading-surface"
            style={{ maxHeight: '360px', overflowY: 'auto', whiteSpace: 'pre-wrap' }}
          >
            {uploadedDoc.extracted_text || 'No selectable text found in this PDF.'}
          </div>
        </div>
      )}
    </div>
  );
}
