import React, { ChangeEvent, FormEvent, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { apiService } from './api';
import { GeneratePosterResponse, PosterFormState } from './types';
import postergenLogo from './postergen-logo.png';

const CLOUD_RUN_BASE_URL = 'https://postergen-backend-367063486603.us-east4.run.app';
const resolvedEnv =
  typeof import.meta !== 'undefined' && 'env' in import.meta
    ? (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env
    : undefined;
const API_BASE_URL = resolvedEnv?.VITE_API_BASE_URL ?? CLOUD_RUN_BASE_URL;

const INITIAL_FORM_STATE: PosterFormState = {
  gcs_input_bucket: '',
  gcs_output_bucket: '',
  pdf_path: '',
  logo: '',
  aff_logo: '',
  text_model: 'gpt-4o-2024-08-06',
  multimodal_model: 'gpt-4o-2024-08-06',
  image_model: 'dall-e-3',
  fast_llm_model: 'gpt-4.1-mini-2025-04-14',
  fast_search: false,
  output_path: 'poster.pptx',
  debug_mode: false,
  width: 54,
  height: 36,
  url: '',
};

const REQUIRED_FIELDS: Array<keyof PosterFormState> = [
  'gcs_input_bucket',
  'gcs_output_bucket',
  'pdf_path',
];

const validateForm = (form: PosterFormState): string | null => {
  for (const field of REQUIRED_FIELDS) {
    const value = form[field];

    if (typeof value === 'string') {
      if (!value.trim()) {
        return 'Please fill out all required fields.';
      }
    } else if (value == null) {
      return 'Please fill out all required fields.';
    }
  }

  if (form.width <= 0 || form.height <= 0) {
    return 'Poster dimensions must be positive numbers.';
  }

  const ratio = form.height ? form.width / form.height : 0;
  if (form.height && (ratio < 1.4 || ratio > 2.0)) {
    return `Poster ratio ${ratio.toFixed(2)} is out of range (1.4 - 2.0).`;
  }

  return null;
};

const copyToClipboard = async (value: string) => {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
};

const App: React.FC = () => {
  const [form, setForm] = useState<PosterFormState>({ ...INITIAL_FORM_STATE });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GeneratePosterResponse | null>(null);
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');

  const posterRatio = useMemo(() => {
    if (!form.height) {
      return 0;
    }

    return form.width / form.height;
  }, [form.width, form.height]);

  const posterRatioDisplay = useMemo(
    () => (form.height ? posterRatio.toFixed(2) : '—'),
    [posterRatio, form.height],
  );

  const isRatioValid = form.height > 0 && posterRatio >= 1.4 && posterRatio <= 2.0;

  const handleStringChange =
    (field: keyof PosterFormState) => (event: ChangeEvent<HTMLInputElement>) => {
      setForm((prev: PosterFormState) => ({ ...prev, [field]: event.target.value }));
    };

  const handleNumberChange =
    (field: 'width' | 'height') => (event: ChangeEvent<HTMLInputElement>) => {
      const numericValue = Number(event.target.value);
      setForm((prev: PosterFormState) => ({
        ...prev,
        [field]: Number.isFinite(numericValue) ? numericValue : prev[field],
      }));
    };

  const handleCheckboxChange =
    (field: 'fast_search' | 'debug_mode') => (event: ChangeEvent<HTMLInputElement>) => {
      setForm((prev: PosterFormState) => ({ ...prev, [field]: event.target.checked }));
    };

  const resetForm = () => {
    setForm({ ...INITIAL_FORM_STATE });
    setShowAdvanced(false);
    setError(null);
    setResult(null);
    setCopyStatus('idle');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResult(null);
    setCopyStatus('idle');

    const validationError = validateForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiService.generatePoster(form);
      setResult(response);
  } catch (error: unknown) {
      let message = 'An unexpected error occurred while generating the poster.';

      if (isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        message = typeof detail === 'string' ? detail : error.message;
      } else if (error instanceof Error) {
        message = error.message;
      }

      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCopyOutputPath = async () => {
    if (!result?.output_path) {
      return;
    }

    try {
      await copyToClipboard(result.output_path);
      setCopyStatus('copied');
      setTimeout(() => setCopyStatus('idle'), 3000);
    } catch (err) {
      console.error('Failed to copy output path', err);
      setCopyStatus('error');
      setTimeout(() => setCopyStatus('idle'), 3000);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1 style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <img
            src={postergenLogo}
            alt="PosterGen Logo"
            style={{ height: '1.5em', marginRight: '0.5em' }}
          />
          PosterGen WebUI
        </h1>
        <p>🎨 Generate design-aware academic posters from PDF papers stored in Google Cloud Storage</p>
        <p style={{ marginTop: '8px', fontSize: '0.95rem', color: '#4b5563' }}>
          Backend: {API_BASE_URL}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="main-form">
        <div className="form-section">
          <h3 className="section-title">☁️ Cloud Storage Inputs</h3>
          <div className="form-group">
            <label htmlFor="gcs_input_bucket">Input bucket *</label>
            <input
              id="gcs_input_bucket"
              type="text"
              value={form.gcs_input_bucket}
              onChange={handleStringChange('gcs_input_bucket')}
              placeholder="postergen-input"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="pdf_path">PDF path in input bucket *</label>
            <input
              id="pdf_path"
              type="text"
              value={form.pdf_path}
              onChange={handleStringChange('pdf_path')}
              placeholder="your-paper-folder/paper.pdf"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="gcs_output_bucket">Output bucket *</label>
            <input
              id="gcs_output_bucket"
              type="text"
              value={form.gcs_output_bucket}
              onChange={handleStringChange('gcs_output_bucket')}
              placeholder="postergen-output"
              required
            />
          </div>
        </div>

        <div className="form-section">
          <h3 className="section-title">🏷️ Optional Logos</h3>
          <div className="form-group">
            <label htmlFor="logo">Conference logo (path in input bucket)</label>
            <input
              id="logo"
              type="text"
              value={form.logo}
              onChange={handleStringChange('logo')}
              placeholder="your-paper-folder/logo.png"
            />
          </div>
          <div className="form-group">
            <label htmlFor="aff_logo">Affiliation logo (path in input bucket)</label>
            <input
              id="aff_logo"
              type="text"
              value={form.aff_logo}
              onChange={handleStringChange('aff_logo')}
              placeholder="your-paper-folder/affiliation.png"
            />
          </div>
        </div>

        <div className="form-section">
          <h3 className="section-title">📐 Poster Settings</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="width">Width (inches)</label>
              <input
                id="width"
                type="number"
                min="10"
                max="120"
                step="0.1"
                value={form.width}
                onChange={handleNumberChange('width')}
              />
            </div>
            <div className="form-group">
              <label htmlFor="height">Height (inches)</label>
              <input
                id="height"
                type="number"
                min="10"
                max="120"
                step="0.1"
                value={form.height}
                onChange={handleNumberChange('height')}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Aspect ratio</label>
            <div
              style={{
                padding: '10px 12px',
                borderRadius: '6px',
                border: `1px solid ${isRatioValid ? '#d1d5db' : '#f97316'}`,
                backgroundColor: isRatioValid ? '#f9fafb' : '#fff7ed',
                color: isRatioValid ? '#374151' : '#b45309',
              }}
            >
              {posterRatioDisplay}{' '}
              {isRatioValid ? '(within recommended range)' : '(needs adjustment)'}
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="output_path">Output filename</label>
            <input
              id="output_path"
              type="text"
              value={form.output_path}
              onChange={handleStringChange('output_path')}
              placeholder="poster.pptx"
            />
          </div>
          <div className="form-group">
            <label htmlFor="url">Poster URL (optional QR link)</label>
            <input
              id="url"
              type="text"
              value={form.url}
              onChange={handleStringChange('url')}
              placeholder="https://example.com"
            />
          </div>
        </div>

        <div className="form-section">
          <button
            type="button"
            className="button"
            style={{ marginBottom: '16px', backgroundColor: '#4b5563' }}
            onClick={() => setShowAdvanced((prev: boolean) => !prev)}
          >
            {showAdvanced ? 'Hide advanced model settings' : 'Show advanced model settings'}
          </button>

          {showAdvanced && (
            <div
              className="form-section"
              style={{ border: '1px dashed #d1d5db', borderRadius: '8px', padding: '16px' }}
            >
              <h4 className="section-title" style={{ fontSize: '1.1rem' }}>
                Advanced
              </h4>
              <div className="form-group">
                <label htmlFor="text_model">Text model</label>
                <input
                  id="text_model"
                  type="text"
                  value={form.text_model}
                  onChange={handleStringChange('text_model')}
                />
              </div>
              <div className="form-group">
                <label htmlFor="multimodal_model">Multimodal model</label>
                <input
                  id="multimodal_model"
                  type="text"
                  value={form.multimodal_model}
                  onChange={handleStringChange('multimodal_model')}
                />
              </div>
              <div className="form-group">
                <label htmlFor="image_model">Image model</label>
                <input
                  id="image_model"
                  type="text"
                  value={form.image_model}
                  onChange={handleStringChange('image_model')}
                />
              </div>
              <div className="form-group">
                <label htmlFor="fast_llm_model">Fast LLM model</label>
                <input
                  id="fast_llm_model"
                  type="text"
                  value={form.fast_llm_model}
                  onChange={handleStringChange('fast_llm_model')}
                />
              </div>
              <div className="form-row">
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="checkbox"
                    checked={form.fast_search}
                    onChange={handleCheckboxChange('fast_search')}
                  />
                  Enable fast search
                </label>
              </div>
              <div className="form-row">
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="checkbox"
                    checked={form.debug_mode}
                    onChange={handleCheckboxChange('debug_mode')}
                  />
                  Enable debug mode
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="form-section" style={{ display: 'flex', gap: '12px' }}>
          <button type="submit" className="button" disabled={isSubmitting}>
            {isSubmitting ? 'Generating poster...' : 'Generate poster'}
          </button>
          <button
            type="button"
            className="button"
            style={{ backgroundColor: '#6b7280' }}
            onClick={resetForm}
            disabled={isSubmitting}
          >
            Reset form
          </button>
        </div>

        {error && (
          <div className="error-message" style={{ marginTop: '16px', color: '#b91c1c' }}>
            {error}
          </div>
        )}

        {result && (
          <div
            className="success-message"
            style={{
              marginTop: '16px',
              backgroundColor: '#ecfdf5',
              border: '1px solid #34d399',
              borderRadius: '8px',
              padding: '16px',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '8px', color: '#047857' }}>
              Poster generated successfully!
            </div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px',
                flexWrap: 'wrap',
              }}
            >
              <span>{result.output_path}</span>
              <button
                type="button"
                className="button"
                style={{ width: 'auto', padding: '8px 16px' }}
                onClick={handleCopyOutputPath}
              >
                {copyStatus === 'copied'
                  ? 'Copied!'
                  : copyStatus === 'error'
                  ? 'Copy failed'
                  : 'Copy path'}
              </button>
            </div>
          </div>
        )}
      </form>

      <div className="preview-wrapper">
        <div className="preview-section">
          <h3 className="section-title">ℹ️ Tips</h3>
          <ul style={{ paddingLeft: '20px', color: '#4b5563', fontSize: '0.95rem' }}>
            <li style={{ marginBottom: '8px' }}>
              Ensure the service account running the frontend has read/write access to the specified buckets.
            </li>
            <li style={{ marginBottom: '8px' }}>
              Poster generation can take several minutes; keep the browser tab open until the response returns.
            </li>
            <li style={{ marginBottom: '8px' }}>
              Use separate folders per poster in the output bucket to keep assets organized.
            </li>
            <li>Advanced settings mirror the FastAPI defaults—you can leave them as-is unless you need to experiment.</li>
          </ul>
        </div>

        <div className="section-divider"></div>

        <div className="preview-section">
          <h3 className="section-title">🧪 Request summary</h3>
          <div className="json-content" style={{ maxHeight: 'none' }}>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {JSON.stringify(
                {
                  ...form,
                  width: `${form.width}"`,
                  height: `${form.height}"`,
                  poster_ratio: posterRatioDisplay,
                },
                null,
                2,
              )}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;