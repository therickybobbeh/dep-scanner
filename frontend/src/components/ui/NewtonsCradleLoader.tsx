import React from 'react';
import './NewtonsCradleLoader.css';

interface NewtonsCradleLoaderProps {
  message?: string;
  className?: string;
}

const NewtonsCradleLoader: React.FC<NewtonsCradleLoaderProps> = ({ 
  message = "Processing...", 
  className = "" 
}) => {

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
        <p className="message-text">{message}</p>
      </div>
    </div>
  );
};

export default NewtonsCradleLoader;