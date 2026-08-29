import React, { useState, useEffect, useRef } from 'react';

export interface CustomDropdownOption<T> {
  value: T;
  label: string;
  icon?: string;
  sublabel?: string;
}

interface CustomSelectProps<T extends string | number> {
  label?: string;
  options: CustomDropdownOption<T>[];
  value: T;
  onChange: (val: T) => void;
  disabled?: boolean;
}

export function CustomSelect<T extends string | number>({
  label,
  options,
  value,
  onChange,
  disabled = false,
}: CustomSelectProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value) || options[0];

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  return (
    <div className="control-field custom-dropdown-container" ref={containerRef}>
      {label && <label className="field-label">{label}</label>}
      <div className="custom-dropdown-relative">
        <button
          type="button"
          className={`custom-select-trigger ${isOpen ? 'is-open' : ''}`}
          onClick={() => !disabled && setIsOpen((prev) => !prev)}
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={isOpen}
        >
          <div className="trigger-content">
            {selectedOption?.icon && <span className="trigger-icon">{selectedOption.icon}</span>}
            <span className="trigger-label">{selectedOption?.label}</span>
            {selectedOption?.sublabel && <span className="trigger-sublabel">{selectedOption.sublabel}</span>}
          </div>
          <span className="trigger-arrow">{isOpen ? '▴' : '▾'}</span>
        </button>

        {isOpen && (
          <div className="custom-select-menu" role="listbox">
            {options.map((opt) => {
              const isSelected = opt.value === value;
              return (
                <div
                  key={String(opt.value)}
                  className={`custom-select-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => {
                    onChange(opt.value);
                    setIsOpen(false);
                  }}
                  role="option"
                  aria-selected={isSelected}
                >
                  <div className="item-left">
                    {opt.icon && <span className="item-icon">{opt.icon}</span>}
                    <div className="item-text">
                      <span className="item-label">{opt.label}</span>
                      {opt.sublabel && <span className="item-sublabel">{opt.sublabel}</span>}
                    </div>
                  </div>
                  {isSelected && <span className="item-check">✓</span>}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
