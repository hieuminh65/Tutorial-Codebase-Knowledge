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
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    const handleSubmit = async (event) => {
        event.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            console.log(`Sending request to: ${API_BASE_URL}/generate`); // Debug log
            const response = await axios.post(`${API_BASE_URL}/generate`, {
                gemini_key: geminiKey,
                github_token: githubToken || null, // Send null if empty
                repo_url: repoUrl,
                include_patterns: includePatterns,
                exclude_patterns: excludePatterns,
            });

            if (response.status === 200 && response.data.repo_name) {
                navigate(`/output/${response.data.repo_name}`);
            } else {
                setError('Generation started but failed to get repo name.');
            }
        } catch (err) {
            console.error("Generation failed:", err); // Log the full error
            const errorMsg = err.response?.data?.details || err.response?.data?.error || err.message || 'An unknown error occurred during generation.';
            setError(`Generation Failed: ${errorMsg}`);
             if (err.message.includes('Network Error') || err.message.includes('CORS')) {
                setError(`Generation Failed: Network or CORS error. Ensure backend is running and accessible at ${API_BASE_URL}. Check browser console for details.`);
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="container">
            <h1>Generate Tutorial from Codebase</h1>
            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor="geminiKey">Gemini API Key *</label>
                    <input
                        type="password"
                        id="geminiKey"
                        value={geminiKey}
                        onChange={(e) => setGeminiKey(e.target.value)}
                        required
                        autoComplete="new-password" // Prevent browser autofill issues
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
                    <input
                        type="url"
                        id="repoUrl"
                        value={repoUrl}
                        onChange={(e) => setRepoUrl(e.target.value)}
                        placeholder="https://github.com/user/repo"
                        required
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="includePatterns">Include Patterns (Optional, comma-separated)</label>
                    <input
                        type="text"
                        id="includePatterns"
                        value={includePatterns}
                        onChange={(e) => setIncludePatterns(e.target.value)}
                        placeholder="e.g., *.py, src/**/*.js"
                    />
                </div>
                <div className="form-group">
                    <label htmlFor="excludePatterns">Exclude Patterns (Optional, comma-separated)</label>
                    <input
                        type="text"
                        id="excludePatterns"
                        value={excludePatterns}
                        onChange={(e) => setExcludePatterns(e.target.value)}
                        placeholder="e.g., *.test.py, node_modules/**, dist/**"
                    />
                </div>
                <button type="submit" disabled={isLoading}>
                    {isLoading ? 'Generating...' : 'Generate Tutorial'}
                </button>
            </form>
            {error && <div className="error" style={{ marginTop: '15px' }}>{error}</div>}
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
