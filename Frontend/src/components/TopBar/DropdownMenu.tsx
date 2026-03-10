import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './DropdownMenu.css';

interface DropdownMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

const DropdownMenu = ({ isOpen, onClose }: DropdownMenuProps) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div ref={menuRef} className="dropdown-menu">
      <Link to="/profile" className="dropdown-item" onClick={onClose}>
        Profile
      </Link>
      <Link to="/metrics" className="dropdown-item" onClick={onClose}>
        Metrics
      </Link>
<<<<<<< HEAD
=======
      
      {/* Seb- Added login to dropdown menu temp for easy access, can be removed as needed */}
      <Link to="/login" className="dropdown-item" onClick={onClose}>
        Login
      </Link>
>>>>>>> 98124e8777c05699532414f1f992ced32eca24bd
    </div>
  );
};

export default DropdownMenu;
