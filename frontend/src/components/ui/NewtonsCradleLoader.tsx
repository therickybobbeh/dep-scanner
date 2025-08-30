import React from 'react';
import './NewtonsCradleLoader.css';

interface NewtonsCradleLoaderProps {
  message?: string;
  progress?: number;
  className?: string;
}

const NewtonsCradleLoader: React.FC<NewtonsCradleLoaderProps> = ({ 
  message = "Processing...", 
  progress = 0,
  className = "" 
}) => {
  const getContextualMessage = (progress: number): string => {
    if (progress < 15) return "🔍 Processing your manifest files...";
    if (progress < 40) return "📦 Resolving dependency tree...";
    if (progress < 60) return "🔗 Generating lock files if needed...";
    if (progress < 85) return "🛡️ Querying OSV database for vulnerabilities...";
    if (progress < 95) return "📊 This can take a while - analyzing security data...";
    return "✨ Almost done! Generating your security report...";
  };

  const displayMessage = message === "Processing..." && progress > 0 
    ? getContextualMessage(progress) 
    : message;

  return (
    <div className={`newtons-cradle-loader ${className}`} role="status" aria-live="polite">
      <div className="newtons-cradle">
        <div className="frame-cover"></div>
        <div className="frame">
          <div className="sphere-wrap left">
            <div className="string string-left"></div>
            <div className="sphere"></div>
          </div>
          <div className="sphere center"></div>
          <div className="sphere center"></div>
          <div className="sphere center"></div>
          <div className="sphere-wrap right">
            <div className="string string-right"></div>
            <div className="sphere"></div>
          </div>
        </div>
        <div className="base"></div>
      </div>
      
      <div className="loading-message" aria-live="polite">
        <p className="message-text">{displayMessage}</p>
        {progress > 0 && (
          <p className="progress-text" aria-label={`Progress: ${Math.round(progress)}%`}>
            {Math.round(progress)}% complete
          </p>
        )}
      </div>
    </div>
  );
};

export default NewtonsCradleLoader;