import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

// --- Dynamically set API Base URL ---
const getApiBaseUrl = () => {
    const currentHostname = window.location.hostname;
    const currentPort = window.location.port;
    const currentProtocol = window.location.protocol;

    // In Cloud Workstations, the backend often runs on a different port but the same base hostname
    if (currentHostname.includes('cloudworkstations.dev')) {
        const baseHostname = currentHostname.split('-').slice(1).join('-'); // Attempt to get base hostname
        return `${currentProtocol}//5001-${baseHostname}/api`; // Construct backend URL on port 5001
    }
    // Fallback for local development
    return 'http://localhost:5001/api';
};

const API_BASE_URL = getApiBaseUrl();
console.log("Using API Base URL:", API_BASE_URL);
// -------------------------------------

// --- Input Form Component ---
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
    const [starCount, setStarCount] = useState(null);
    const navigate = useNavigate();

    // Fetch GitHub repository stars when component mounts
    useEffect(() => {
        const fetchRepoStats = async () => {
            try {
                // Use the main repository URL
                const repoUrl = "https://github.com/The-Pocket/Tutorial-Codebase-Knowledge";
                const [, , , owner, repo] = repoUrl.split('/');

                const response = await axios.get(`https://api.github.com/repos/${owner}/${repo}`);
                if (response.status === 200) {
                    setStarCount(response.data.stargazers_count);
                }
            } catch (err) {
                console.error("Failed to fetch repository stats:", err);
                // Silently fail - stars display is not critical functionality
            }
        };

        fetchRepoStats();
    }, []);

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
            console.log(`Sending request to: ${API_BASE_URL}/generate`);
            const response = await axios.post(`${API_BASE_URL}/generate`, {
                gemini_key: geminiKey,
                github_token: githubToken || null,
                repo_url: repoUrl,
                include_patterns: includePatterns,
                exclude_patterns: excludePatterns,
                max_file_size: maxFileSize * 1024, // Convert KB to bytes
            });

            if (response.status === 200 && response.data.repo_name) {
                // Instead of navigating, set the link for the user to click
                setGeneratedTutorialLink(`/output/${response.data.repo_name}`);
            } else {
                setError('Generation started but failed to get repo name.');
            }
        } catch (err) {
            console.error("Generation failed:", err);
            const errorMsg = err.response?.data?.details || err.response?.data?.error || err.message || 'An unknown error occurred during generation.';
            setError(`Generation Failed: ${errorMsg}`);
            if (err.message.includes('Network Error') || err.message.includes('CORS')) {
                setError(`Generation Failed: Network or CORS error. Ensure backend is running and accessible at ${API_BASE_URL}. Check browser console for details.`);
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
            <div className="app-header-wrapper">
                <div className="app-header">
                    <div className="app-header-title">
                        <h1>Tutorial-Codebase-Knowledge</h1>
                        <div className="app-header-subtitle">Convert your codebase into comprehensive tutorials</div>
                    </div>
                    {starCount !== null && (
                        <a
                            href="https://github.com/The-Pocket/Tutorial-Codebase-Knowledge"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="github-stats"
                        >
                            <svg className="github-icon" width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                                <path fillRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                            </svg>
                            <span className="github-star-count">{starCount}</span>
                        </a>
                    )}
                </div>
            </div>
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
                                <div className="number-input-container">
                                    <button
                                        type="button"
                                        className="number-input-button"
                                        onClick={() => handleMaxFileSizeChange(Math.max(1, maxFileSize - 10))}
                                        aria-label="Decrease file size"
                                    >
                                        −
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
                                        +
                                    </button>
                                    <span className="size-unit">KB</span>
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
                            <p>Tutorial generated successfully!</p>
                            <div className="tutorial-link-container">
                                <a
                                    href={generatedTutorialLink}
                                    className="tutorial-link"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Click here to view your tutorial
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

// --- Output Display Component ---
function OutputDisplay() {
    const { repoName } = useParams();
    const [structure, setStructure] = useState(null);
    const [selectedContent, setSelectedContent] = useState('');
    const [selectedPath, setSelectedPath] = useState(null);
    const [isLoadingStructure, setIsLoadingStructure] = useState(true);
    const [isLoadingContent, setIsLoadingContent] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchStructure = async () => {
            setIsLoadingStructure(true);
            setError(null);
            try {
                console.log(`Fetching structure from: ${API_BASE_URL}/output-structure/${repoName}`); // Debug log
                const response = await axios.get(`${API_BASE_URL}/output-structure/${repoName}`);
                setStructure(response.data);
                // Automatically load the first lesson of the first chapter if available
                if (response.data?.chapters?.[0]?.lessons?.[0]?.path) {
                    fetchContent(response.data.chapters[0].lessons[0].path);
                }
            } catch (err) {
                console.error("Failed to fetch structure:", err);
                setError(err.response?.data?.error || err.message || 'Failed to load tutorial structure.');
            } finally {
                setIsLoadingStructure(false);
            }
        };
        fetchStructure();
    }, [repoName]);

    const fetchContent = async (filePath) => {
        if (!filePath) return;
        setIsLoadingContent(true);
        setError(null);
        setSelectedContent(''); // Clear previous content
        setSelectedPath(filePath); // Track selected path
        try {
            // Encode the file path part of the URL to handle special characters like spaces or #
            const encodedFilePath = encodeURIComponent(filePath);
            console.log(`Fetching content from: ${API_BASE_URL}/output-content/${repoName}/${filePath}`); // Debug log
            // IMPORTANT: Axios might double-encode if we pass the full URL. Let axios handle encoding of path segments.
            // We need to be careful here. Let's try fetching with the raw path first, assuming Flask/Werkzeug handles decoding.
            const response = await axios.get(`${API_BASE_URL}/output-content/${repoName}/${filePath}`); // Pass raw path
            setSelectedContent(response.data.content);
        } catch (err) {
            console.error("Failed to fetch content:", err);
            setError(err.response?.data?.description || err.message || 'Failed to load lesson content.');
        } finally {
            setIsLoadingContent(false);
        }
    };

    return (
        <div className="container output-container">
            <aside className="sidebar">
                <h3>{repoName} Tutorial</h3>
                {isLoadingStructure && <p>Loading structure...</p>}
                {!isLoadingStructure && error && !selectedContent && <p className="error">{error}</p>} {/* Show structure error only if no content loaded*/}
                {!isLoadingStructure && structure && structure.chapters && (
                    <ul>
                        {structure.chapters.map((chapter, chapIndex) => (
                            <li key={chapIndex}>
                                <div className="chapter-title">{chapter.title}</div>
                                {chapter.lessons && chapter.lessons.length > 0 && (
                                    <ul>
                                        {chapter.lessons.map((lesson, lessonIndex) => (
                                            <li key={lessonIndex}>
                                                <a
                                                    href="#"
                                                    className={`lesson-link ${lesson.path === selectedPath ? 'active' : ''}`}
                                                    onClick={(e) => { e.preventDefault(); fetchContent(lesson.path); }}
                                                    style={{ fontWeight: lesson.path === selectedPath ? 'bold' : 'normal' }} // Highlight active
                                                >
                                                    {lesson.title}
                                                </a>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </li>
                        ))}
                    </ul>
                )}
                {!isLoadingStructure && (!structure || !structure.chapters || structure.chapters.length === 0) && !error && (
                    <p>No tutorial structure found.</p>
                )}
            </aside>
            <main className="content">
                {isLoadingContent && <div className="loading">Loading content...</div>}
                {/* Show content-specific error if content loading failed */}
                {!isLoadingContent && error && selectedPath && <div className="error">Error loading {selectedPath}: {error}</div>}
                {!isLoadingContent && selectedContent && (
                    <div className="markdown-content">
                        <ReactMarkdown>{selectedContent}</ReactMarkdown>
                    </div>
                )}
                {/* Initial state message */}
                {!isLoadingStructure && !isLoadingContent && !selectedPath && !error && (
                    <p>Select a lesson from the sidebar to view its content.</p>
                )}
            </main>
        </div>
    );
}

// --- Main App Component ---
function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<InputForm />} />
                <Route path="/output/:repoName" element={<OutputDisplay />} />
                {/* Add other routes as needed */}
            </Routes>
        </Router>
    );
}

export default App;
