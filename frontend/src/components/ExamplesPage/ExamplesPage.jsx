import React from 'react';
import { useNavigate } from 'react-router-dom';
import AppHeader from '../common/AppHeader';
import './ExamplesPage.css';

function ExamplesPage() {
  const navigate = useNavigate();

  // Hardcoded repository examples from the screenshot
  const repositories = [
    { name: "AutoGen Core", description: "Explore the AutoGen Core framework for autonomous agents." },
    { name: "Browser Use", description: "Learn about browser automation and interaction techniques." },
    { name: "Celery", description: "Distributed task queue system for Python applications." },
    { name: "Click", description: "Python package for creating command line interfaces." },
    { name: "Codex", description: "A command-line interface for AI-assisted coding and development." },
    { name: "Crawl4AI", description: "Web crawling framework designed for AI data collection." },
    { name: "CrewAI", description: "Framework for orchestrating role-playing autonomous AI agents." },
    { name: "DSPy", description: "Programming language for developing AI-driven systems." },
    { name: "FastAPI", description: "Modern, fast web framework for building APIs with Python." },
    { name: "Flask", description: "Lightweight WSGI web application framework for Python." },
    { name: "Google A2A", description: "Google's Agent-to-Agent communication framework." },
    { name: "hieuminh65", description: "Personal repository showcasing various programming projects." },
    { name: "LangGraph", description: "Framework for building stateful, multi-agent applications with LLMs." },
    { name: "LevelDB", description: "Fast key-value storage library by Google." },
    { name: "MCP Python SDK", description: "Model Context Protocol implementation for Python." },
    { name: "NumPy Core", description: "Fundamental package for scientific computing with Python." },
    { name: "OpenManus", description: "Open-source robotic manipulation framework." },
    { name: "Pydantic Core", description: "Data validation and settings management using Python type annotations." },
    { name: "Requests", description: "Simple HTTP library for Python." },
    { name: "SmolaAgents", description: "Lightweight framework for creating autonomous AI agents." },
  ];

  const handleRepositoryClick = (repoName) => {
    navigate(`/output/${repoName}`);
  };

  return (
    <div className="examples-page">
      <AppHeader />
      <div className="examples-container">
        <h1>Example Repositories</h1>
        <p className="examples-description">
          Browse through these example repositories to see tutorials generated from real codebases.
          Click on any repository to explore its structure and documentation.
        </p>

        <div className="repository-grid">
          {repositories.map((repo, index) => (
            <div
              key={index}
              className="repository-card"
              onClick={() => handleRepositoryClick(repo.name)}
            >
              <h2>{repo.name}</h2>
              <p className="repo-description">{repo.description}</p>
              <div className="card-footer">
                <span className="explore-link">Explore Tutorial →</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default ExamplesPage;