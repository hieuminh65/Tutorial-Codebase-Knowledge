import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_BASE_URL } from '../../utils/apiConfig';
import AppHeader from '../common/AppHeader';
import './InputForm.css';

function InputForm() {
  const [geminiKey, setGeminiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [includePatterns, setIncludePatterns] = useState('');
  const [excludePatterns, setExcludePatterns] = useState('');
  const [maxFileSize, setMaxFileSize] = useState(100); // Default 100KB
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingPatterns, setIsFetchingPatterns] = useState(false);
  const [error, setError] = useState(null);
  const [patternError, setPatternError] = useState(null);
  const [patternSuggestions, setPatternSuggestions] = useState([]);
  const [patternStatus, setPatternStatus] = useState({}); // Map of pattern -> 'include' or 'exclude'
  const [fileCount, setFileCount] = useState(0);
  const [generatedTutorialLink, setGeneratedTutorialLink] = useState(null);
  const navigate = useNavigate();

  // Function to update max file size and filter patterns
  const handleMaxFileSizeChange = (newSize) => {
    const sizeInBytes = newSize * 1024;
    setMaxFileSize(newSize);

    // Move patterns that exceed the size limit to the exclude list
    if (patternSuggestions.length > 0) {
      const updatedStatus = { ...patternStatus };

      patternSuggestions.forEach(pattern => {
        // If the pattern's size exceeds the max file size, move it to exclude
        if (pattern.size > sizeInBytes) {
          updatedStatus[pattern.pattern] = 'exclude';
        }
        // If size is now under the limit and was previously auto-excluded, move back to include
        else if (pattern.size <= sizeInBytes && updatedStatus[pattern.pattern] === 'exclude') {
          // Check if this pattern was auto-excluded (not manually moved by the user)
          // We don't have a way to track manual vs auto exclusions currently,
          // so we'll assume patterns are auto-excluded for simplicity
          updatedStatus[pattern.pattern] = 'include';
        }
      });

      setPatternStatus(updatedStatus);
    }
  };

  // Update includePatterns and excludePatterns when patternStatus changes
  useEffect(() => {
    if (Object.keys(patternStatus).length === 0) return;

    const includedPatterns = [];
    const excludedPatterns = [];

    Object.entries(patternStatus).forEach(([pattern, status]) => {
      if (status === 'include') {
        includedPatterns.push(pattern);
      } else if (status === 'exclude') {
        excludedPatterns.push(pattern);
      }
    });

    setIncludePatterns(includedPatterns.join(','));
    setExcludePatterns(excludedPatterns.join(','));
  }, [patternStatus]);

  // Calculate total file counts for included and excluded patterns
  const calculateFileCounts = () => {
    let includedFilesCount = 0;
    let excludedFilesCount = 0;

    patternSuggestions.forEach(pattern => {
      if (patternStatus[pattern.pattern] === 'include') {
        includedFilesCount += pattern.count;
      } else if (patternStatus[pattern.pattern] === 'exclude') {
        excludedFilesCount += pattern.count;
      }
    });

    return { includedFilesCount, excludedFilesCount };
  };

  const { includedFilesCount, excludedFilesCount } = calculateFileCounts();

  const fetchPatterns = async () => {
    if (!repoUrl) {
      setPatternError("Please enter a GitHub repository URL first");
      return;
    }

    setIsFetchingPatterns(true);
    setPatternError(null);
    setPatternSuggestions([]);
    setPatternStatus({});

    try {
      const response = await axios.post(`${API_BASE_URL}/fetch-patterns`, {
        github_token: githubToken || null,
        repo_url: repoUrl
      });

      if (response.status === 200) {
        const patterns = response.data.patterns;
        setPatternSuggestions(patterns);
        setFileCount(response.data.file_count);

        // Set all patterns to 'include' by default
        const initialStatus = {};
        patterns.forEach(pattern => {
          initialStatus[pattern.pattern] = 'include';
        });
        setPatternStatus(initialStatus);
      } else {
        setPatternError('Failed to fetch file patterns.');
      }
    } catch (err) {
      console.error("Pattern fetch failed:", err);
      const errorMsg = err.response?.data?.details || err.response?.data?.error || err.message || 'An unknown error occurred.';
      setPatternError(`Failed to fetch patterns: ${errorMsg}`);
    } finally {
      setIsFetchingPatterns(false);
    }
  };

  const movePattern = (pattern) => {
    setPatternStatus(prevStatus => {
      const newStatus = { ...prevStatus };
      // Toggle between 'include' and 'exclude'
      newStatus[pattern] = newStatus[pattern] === 'include' ? 'exclude' : 'include';
      return newStatus;
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setGeneratedTutorialLink(null);

    try {
      console.log(`Sending request to: ${API_BASE_URL}/start-job`);
      const response = await axios.post(`${API_BASE_URL}/start-job`, {
        gemini_key: geminiKey,
        github_token: githubToken || null,
        repo_url: repoUrl,
        include_patterns: includePatterns,
        exclude_patterns: excludePatterns,
        max_file_size: maxFileSize * 1024, // Convert KB to bytes
      });

      if ((response.status === 202 || response.status === 200)) {
        // Job was accepted and queued for processing
        setGeneratedTutorialLink(`/output/${repoUrl.split('/').pop()}`);
        navigate(`/output/${repoUrl.split('/').pop()}`);
      } else {
        setError('Job submission failed. Please try again later.');
      }
    } catch (err) {
      console.error("Job submission failed:", err);
      const errorMsg = err.response?.data?.details || err.response?.data?.error || err.message || 'An unknown error occurred during submission.';
      setError(`Job Submission Failed: ${errorMsg}`);
      if (err.message.includes('Network Error') || err.message.includes('CORS')) {
        setError(`Job Submission Failed: Network or CORS error. Ensure backend is running and accessible at ${API_BASE_URL}. Check browser console for details.`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Get included and excluded patterns based on patternStatus
  const includedPatterns = patternSuggestions.filter(p => patternStatus[p.pattern] === 'include');
  const excludedPatterns = patternSuggestions.filter(p => patternStatus[p.pattern] === 'exclude');

  return (
    <div className="container">
      <AppHeader />
      <div className="form-container">
        <form onSubmit={(e) => {
          e.preventDefault();
          if (patternSuggestions.length > 0) {
            handleSubmit(e);
          } else {
            fetchPatterns();
          }
        }}>
          <div className="form-group">
            <label htmlFor="geminiKey">Gemini API Key *</label>
            <input
              type="password"
              id="geminiKey"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>
          <div className="form-group">
            <label htmlFor="githubToken">GitHub Token (Optional, for private repos)</label>
            <input
              type="password"
              id="githubToken"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div className="form-group">
            <label htmlFor="repoUrl">GitHub Repo URL *</label>
            <div className="url-input-group">
              <input
                type="url"
                id="repoUrl"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/user/repo"
                required
              />
              {!patternSuggestions.length && (
                <button
                  type="submit"
                  disabled={isFetchingPatterns || !repoUrl}
                  className="secondary-button"
                >
                  {isFetchingPatterns ? 'Fetching...' : 'Submit'}
                </button>
              )}
            </div>
          </div>

          {patternSuggestions.length > 0 && (
            <>
              <div className="form-group">
                <label htmlFor="maxFileSize">Maximum File Size (KB)</label>
                <div className="size-input-container">
                  <div className="number-input-container">
                    <button
                      type="button"
                      className="number-input-button"
                      onClick={() => handleMaxFileSizeChange(Math.max(1, maxFileSize - 10))}
                      aria-label="Decrease file size"
                    >
                      <span className="button-icon">−</span>
                    </button>
                    <input
                      type="number"
                      id="maxFileSize"
                      min="1"
                      max="10000"
                      value={maxFileSize}
                      onChange={(e) => handleMaxFileSizeChange(parseInt(e.target.value) || 100)}
                      className="number-input"
                      aria-label="Maximum file size in kilobytes"
                    />
                    <button
                      type="button"
                      className="number-input-button"
                      onClick={() => handleMaxFileSizeChange(Math.min(10000, maxFileSize + 10))}
                      aria-label="Increase file size"
                    >
                      <span className="button-icon">+</span>
                    </button>
                  </div>

                  <div className="file-size-slider-container">
                    <input
                      type="range"
                      min="1"
                      max="1000"
                      step="10"
                      value={maxFileSize}
                      onChange={(e) => handleMaxFileSizeChange(parseInt(e.target.value))}
                      className="file-size-slider"
                      aria-label="Adjust maximum file size using slider"
                    />
                    <div className="slider-labels">
                      <span>1KB</span>
                      <span>500KB</span>
                      <span>1000KB</span>
                    </div>
                  </div>
                </div>
                <small className="form-hint">Files larger than this will be skipped (default: 100KB)</small>
              </div>
            </>
          )}

          {patternError && <div className="error" style={{ marginBottom: '15px' }}>{patternError}</div>}

          {patternSuggestions.length > 0 && (
            <div className="patterns-container">
              <div className="patterns-header">
                <h3>File Patterns ({fileCount} files found)</h3>
                <p className="patterns-explanation">
                  <strong>What are patterns?</strong> Patterns are filters like "*.py" (all Python files) or "src/**" (all files in src folder).
                  <br />
                  <strong>Include:</strong> Files that will be analyzed for the tutorial.
                  <br />
                  <strong>Exclude:</strong> Files that will be skipped.
                  <br />
                  Click on any pattern to move it between the Include and Exclude columns.
                </p>
              </div>

              <div className="patterns-columns">
                <div className="patterns-column">
                  <h4>Include ({includedPatterns.length} patterns, {includedFilesCount} total files)</h4>
                  <div className="patterns-list">
                    {includedPatterns.map((pattern, index) => (
                      <div
                        key={`include-${index}`}
                        className="pattern-item pattern-item-movable"
                        onClick={() => movePattern(pattern.pattern)}
                      >
                        <div className="pattern-content">
                          <span className="pattern-icon">→</span>
                          <span className="pattern-label">{pattern.label}</span>
                          <span className="pattern-count">
                            ({pattern.count} files, {pattern.formatted_size})
                          </span>
                        </div>
                      </div>
                    ))}
                    {includedPatterns.length === 0 && (
                      <div className="pattern-empty">No patterns included</div>
                    )}
                  </div>
                </div>

                <div className="patterns-column">
                  <h4>Exclude ({excludedPatterns.length} patterns, {excludedFilesCount} total files)</h4>
                  <div className="patterns-list">
                    {excludedPatterns.map((pattern, index) => (
                      <div
                        key={`exclude-${index}`}
                        className="pattern-item pattern-item-movable"
                        onClick={() => movePattern(pattern.pattern)}
                      >
                        <div className="pattern-content">
                          <span className="pattern-icon">←</span>
                          <span className="pattern-label">{pattern.label}</span>
                          <span className="pattern-count">
                            ({pattern.count} files, {pattern.formatted_size})
                          </span>
                        </div>
                      </div>
                    ))}
                    {excludedPatterns.length === 0 && (
                      <div className="pattern-empty">No patterns excluded</div>
                    )}
                  </div>
                </div>
              </div>

              <button type="submit" disabled={isLoading} className="generate-button">
                {isLoading ? 'Generating...' : 'Generate Tutorial'}
              </button>
            </div>
          )}

          {generatedTutorialLink && (
            <div className="success-message">
              <p>Job accepted! Your tutorial is now being generated.</p>
              <p>The tutorial will be available in a few minutes at:</p>
              <div className="tutorial-link-container">
                <a
                  href={generatedTutorialLink}
                  className="tutorial-link"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {window.location.origin}{generatedTutorialLink}
                </a>
              </div>
            </div>
          )}
        </form>
        {error && <div className="error" style={{ marginTop: '15px' }}>{error}</div>}
      </div>
    </div>
  );
}

export default InputForm;