"use client";

import React from "react";

interface CustomButtonProps {
  label: string;
  onClick: () => void;
  className?: string;
  disabled?: boolean;
}

const CustomButton: React.FC<CustomButtonProps> = ({
  label,
  onClick,
  className = "",
  disabled = false,
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-xl font-semibold transition-all duration-200 ${
        disabled
          ? "bg-gray-400 cursor-not-allowed text-white"
          : "bg-blue-500 hover:bg-blue-600 text-white"
      } ${className}`}
    >
      {label}
    </button>
  );
};

export default CustomButton;
