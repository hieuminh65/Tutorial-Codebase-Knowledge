import React from 'react';
import './SkeletonLoader.css';

const SkeletonLoader = () => {
  return (
    <div className="skeleton-content">
      {/* Title section */}
      <div className="skeleton-loader skeleton-title"></div>

      {/* Introduction paragraph section */}
      <div className="skeleton-loader skeleton-paragraph long"></div>
      <div className="skeleton-loader skeleton-paragraph long"></div>
      <div className="skeleton-loader skeleton-paragraph medium"></div>

      {/* Section heading */}
      <div className="skeleton-loader skeleton-subtitle"></div>

      {/* Content paragraphs */}
      <div className="skeleton-loader skeleton-paragraph long"></div>
      <div className="skeleton-loader skeleton-paragraph medium"></div>
      <div className="skeleton-loader skeleton-paragraph long"></div>

      {/* Code block skeleton */}
      <div className="skeleton-code-block">
        <div className="skeleton-loader skeleton-code-line short"></div>
        <div className="skeleton-loader skeleton-code-line medium"></div>
        <div className="skeleton-loader skeleton-code-line long"></div>
        <div className="skeleton-loader skeleton-code-line medium"></div>
        <div className="skeleton-loader skeleton-code-line short"></div>
      </div>

      {/* More content */}
      <div className="skeleton-loader skeleton-paragraph long"></div>
      <div className="skeleton-loader skeleton-paragraph medium"></div>

      {/* Another section heading */}
      <div className="skeleton-loader skeleton-subtitle"></div>

      {/* More paragraphs */}
      <div className="skeleton-loader skeleton-paragraph medium"></div>
      <div className="skeleton-loader skeleton-paragraph long"></div>
      <div className="skeleton-loader skeleton-paragraph short"></div>

      {/* List skeleton */}
      <div className="skeleton-list">
        <div className="skeleton-loader skeleton-list-item"></div>
        <div className="skeleton-loader skeleton-list-item"></div>
        <div className="skeleton-loader skeleton-list-item"></div>
      </div>
    </div>
  );
};

export default SkeletonLoader;