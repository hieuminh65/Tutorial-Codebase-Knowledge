import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './AppHeader.css';

function AppHeader() {
  const [starCount, setStarCount] = useState(null);
  const [isStarHovered, setIsStarHovered] = useState(false);
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

  const handleHeaderClick = () => {
    navigate('/');
  };

  const handleExamplesClick = () => {
    // Navigate to examples section or page
    // For now, we'll just navigate to home
    navigate('/');
  };

  return (
    <div className="app-header-wrapper">
      <div className="app-header">
        <div className="app-header-title" onClick={handleHeaderClick}>
          <h1>Tutorial-Codebase-Knowledge</h1>
          <div className="app-header-subtitle">Convert your codebase into comprehensive tutorials</div>
        </div>
        <div className="header-controls">
          <button
            className="examples-button"
            onClick={handleExamplesClick}
          >
            <span className="examples-icon">📚</span>
            Examples
          </button>

          {starCount !== null && (
            <a
              href="https://github.com/The-Pocket/Tutorial-Codebase-Knowledge"
              target="_blank"
              rel="noopener noreferrer"
              className={`github-stats ${isStarHovered ? 'github-stats-hover' : ''}`}
              onMouseEnter={() => setIsStarHovered(true)}
              onMouseLeave={() => setIsStarHovered(false)}
            >
              <div className="github-star-container">
                <svg className="github-icon" width="24" height="24" viewBox="0 0 16 16" fill="currentColor">
                  <path fillRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
                <svg className="github-star" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25z"></path>
                </svg>
              </div>
              <div className="star-info">
                <span className="github-star-label">Star</span>
                <span className="github-star-count">{starCount}</span>
              </div>
              {isStarHovered && <div className="star-tooltip">Star us on GitHub!</div>}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default AppHeader;