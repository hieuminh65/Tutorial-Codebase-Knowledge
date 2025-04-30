import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import mermaid from 'mermaid';
import { API_BASE_URL } from '../../utils/apiConfig';
import AppHeader from '../common/AppHeader';
import SkeletonLoader from '../common/SkeletonLoader';
import SidebarSkeletonLoader from '../common/SidebarSkeletonLoader';
import './OutputDisplay.css';

// Initialize mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark',
  securityLevel: 'loose',
  fontSize: 16,
  fontFamily: '"Fira Code", monospace',
});

// Custom component for Mermaid diagrams
const MermaidDiagram = ({ content }) => {
  const ref = useRef(null);
  const [svg, setSvg] = useState('');
  const [key, setKey] = useState(0);

  useEffect(() => {
    if (ref.current) {
      const renderDiagram = async () => {
        try {
          // Generate a unique ID for this diagram
          const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
          // Render the diagram
          const { svg } = await mermaid.render(id, content);
          setSvg(svg);
        } catch (error) {
          console.error('Failed to render Mermaid diagram:', error);
          // Set error message
          setSvg(`<pre style="color:#f38ba8">Mermaid diagram error: ${error.message}</pre>`);
        }
      };

      renderDiagram();
    }
  }, [content, key]);

  // This useEffect will re-render diagrams on window resize
  useEffect(() => {
    const handleResize = () => setKey(prev => prev + 1);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div
      ref={ref}
      className="mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

function OutputDisplay() {
  const { repoName, lessonPath } = useParams();
  const navigate = useNavigate();
  const [structure, setStructure] = useState(null);
  const [selectedContent, setSelectedContent] = useState('');
  const [selectedPath, setSelectedPath] = useState(null);
  const [isLoadingStructure, setIsLoadingStructure] = useState(true);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [error, setError] = useState(null);

  // Track content transition state for smooth fading
  const [contentTransitionState, setContentTransitionState] = useState('idle'); // 'idle', 'fadeOut', 'fadeIn'
  const previousContentRef = useRef('');
  const fadeTimeoutRef = useRef(null);

  useEffect(() => {
    const fetchStructure = async () => {
      setIsLoadingStructure(true);
      setError(null);
      try {
        console.log(`Fetching structure from: ${API_BASE_URL}/output-structure/${repoName}`); // Debug log
        const response = await axios.get(`${API_BASE_URL}/output-structure/${repoName}`);
        setStructure(response.data);

        // If lessonPath is provided in URL, load that content
        if (lessonPath) {
          fetchContent(decodeURIComponent(lessonPath), false);
        }
        // Automatically load the first lesson of the first chapter if available
        else if (response.data?.chapters?.[0]?.lessons?.[0]?.path) {
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
  }, [repoName, lessonPath]);

  const fetchContent = async (filePath, updateURL = true) => {
    if (!filePath) return;

    // Start fade out transition
    setContentTransitionState('fadeOut');
    // Store current content so we can keep displaying it during the transition
    previousContentRef.current = selectedContent;
    setIsLoadingContent(true);
    setError(null);
    setSelectedPath(filePath); // Track selected path

    // Update the URL if updateURL is true
    if (updateURL) {
      navigate(`/output/${repoName}/${encodeURIComponent(filePath)}`);
    }

    // Clear any existing fade timeout
    if (fadeTimeoutRef.current) {
      clearTimeout(fadeTimeoutRef.current);
    }

    // Wait for fade out animation to complete
    fadeTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/output-content/${repoName}/${filePath}`);
        setSelectedContent(response.data.content);
        // Begin fade in transition
        setContentTransitionState('fadeIn');
      } catch (err) {
        console.error("Failed to fetch content:", err);
        setError(err.response?.data?.description || err.message || 'Failed to load lesson content.');
        setContentTransitionState('idle'); // Reset in case of error
      } finally {
        setIsLoadingContent(false);
      }
    }, 150); // Match this with the CSS transition time
  };

  return (
    <div className="output-page">
      <AppHeader />
      <div className="container output-container">
        <aside className="sidebar">
          {isLoadingStructure && <SidebarSkeletonLoader />}
          {!isLoadingStructure && error && !selectedContent && (
            <div className="generating-message">
              {/* <p className="error">{error}</p> */}
              <p>The tutorial for this repository might be generated, which might take a few minutes to complete.</p>
              <p>Please check back soon or refresh the page to see the latest content.</p>
            </div>
          )}
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
                            style={{ fontWeight: lesson.path === selectedPath ? 'bold' : 'normal' }}
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
        {structure && <main className="content">
          {/* Content container with transition classes */}
          <div className={`content-transition ${contentTransitionState}`}>
            {/* Show loading skeleton only on first load or when we have no content */}
            {isLoadingContent && !previousContentRef.current && <SkeletonLoader />}

            {/* Show previous content during fadeOut for a smooth transition */}
            {contentTransitionState === 'fadeOut' && previousContentRef.current && (
              <div className="markdown-content">
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      if (!inline && match && match[1] === 'mermaid') {
                        return <MermaidDiagram content={String(children).replace(/\n$/, '')} />;
                      }
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {previousContentRef.current}
                </ReactMarkdown>
              </div>
            )}

            {/* Show new content during fadeIn or when idle */}
            {(contentTransitionState === 'fadeIn' || contentTransitionState === 'idle') &&
              !isLoadingContent && selectedContent && (
                <div className="markdown-content">
                  <ReactMarkdown
                    rehypePlugins={[rehypeRaw]}
                    components={{
                      code({ node, inline, className, children, ...props }) {
                        const match = /language-(\w+)/.exec(className || '');
                        if (!inline && match && match[1] === 'mermaid') {
                          return <MermaidDiagram content={String(children).replace(/\n$/, '')} />;
                        }
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {selectedContent}
                  </ReactMarkdown>
                </div>
              )}

            {/* Error message */}
            {!isLoadingContent && error && selectedPath && (
              <div className="error">Error loading {selectedPath}: {error}</div>
            )}

            {/* Initial state message */}
            {!isLoadingStructure && !isLoadingContent && !selectedPath && !error && (
              <p>Select a lesson from the sidebar to view its content.</p>
            )}
          </div>
        </main>}
      </div>
    </div>
  );
}

export default OutputDisplay;