import React from 'react';

export default function CatLogo({ className = "h-8" }) {
  return (
    <div className={`inline-flex items-center select-none shrink-0 ${className}`}>
      <img
        src="/cat-logo.jpg"
        alt="Caterpillar CAT Logo"
        className="h-full w-auto object-contain rounded-md shadow-sm"
        draggable={false}
      />
    </div>
  );
}