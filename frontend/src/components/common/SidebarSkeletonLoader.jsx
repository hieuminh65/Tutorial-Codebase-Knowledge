import React from 'react';
import './SkeletonLoader.css';

const SidebarSkeletonLoader = () => {
  return (
    <div className="skeleton-sidebar">
      <div className="skeleton-loader skeleton-chapter-title"></div>

      {/* First chapter */}
      <div className="skeleton-loader skeleton-chapter-title"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>

      {/* Second chapter */}
      <div className="skeleton-loader skeleton-chapter-title"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>

      {/* Third chapter */}
      <div className="skeleton-loader skeleton-chapter-title"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
      <div className="skeleton-loader skeleton-lesson"></div>
    </div>
  );
};

export default SidebarSkeletonLoader;