import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../../utils/apiConfig';
import AppHeader from '../common/AppHeader';
import './OutputDisplay.css';

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
    <div className="output-page">
      <AppHeader />
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
    </div>
  );
}

export default OutputDisplay;