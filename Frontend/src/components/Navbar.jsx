import { useState, useEffect } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';

/**
 * Navbar Component
 * Sticky navigation bar with logo, menu links, and mobile hamburger menu
 */
const Navbar = () => {
    const [openLocation, setOpenLocation] = useState(null);
    const [isScrolled, setIsScrolled] = useState(() => window.scrollY > 20);
    const location = useLocation();
    const isOpen = openLocation === location.key;
    const hasLightBackground = location.pathname !== '/' || isScrolled || isOpen;

    // Navigation links configuration
    const navLinks = [
        { name: 'Home', path: '/' },
        { name: 'About', path: '/about' },
        { name: 'Events', path: '/events' },
        { name: 'Gallery', path: '/gallery' },
        { name: 'Contact', path: '/contact' },
    ];

    // Handle scroll effect for navbar background
    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <nav
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${hasLightBackground
                ? 'bg-white/95 backdrop-blur-md shadow-soft py-3'
                : 'bg-transparent py-5'
                }`}
        >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between">
                    {/* Logo */}
                    <Link to="/" className="flex items-center space-x-3 group">
                        {/* MUN Club Logo */}
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center overflow-hidden transition-all duration-300 ${hasLightBackground ? 'bg-white' : 'bg-white'
                            } group-hover:scale-105`}>
                            <img
                                src="/mun-logo.png"
                                alt="JKKNIU MUN Club Logo"
                                className="w-full h-full object-contain p-1"
                            />
                        </div>
                        {/* Logo Text */}
                        <div className="hidden sm:block">
                            <span className={`font-heading font-bold text-xl transition-colors duration-300 ${hasLightBackground ? 'text-primary-700' : 'text-white'
                                }`}>
                                JKKNIU MUN
                            </span>
                            <span className={`block text-xs font-medium transition-colors duration-300 ${hasLightBackground ? 'text-primary-700' : 'text-white/80'
                                }`}>
                                Model United Nations Club
                            </span>
                        </div>
                    </Link>

                    {/* Desktop Navigation Links */}
                    <div className="hidden md:flex items-center space-x-8">
                        {navLinks.map((link) => (
                            <NavLink
                                key={link.name}
                                to={link.path}
                                onClick={() => setOpenLocation(null)}
                                className={({ isActive }) =>
                                    `relative font-medium transition-all duration-300 ${hasLightBackground
                                        ? isActive
                                            ? 'text-primary-600'
                                            : 'text-gray-700 hover:text-primary-600'
                                        : isActive
                                            ? 'text-accent-400'
                                            : 'text-white hover:text-accent-300'
                                    } after:absolute after:left-0 after:bottom-[-4px] after:w-0 after:h-0.5 after:transition-all after:duration-300 hover:after:w-full ${isActive ? 'after:w-full' : ''
                                    } ${hasLightBackground ? 'after:bg-primary-600' : 'after:bg-accent-400'}`
                                }
                            >
                                {link.name}
                            </NavLink>
                        ))}
                        {/* Join Button */}
                        <Link
                            to="/contact"
                            className={`px-5 py-2.5 rounded-full font-semibold transition-all duration-300 transform hover:-translate-y-0.5 ${hasLightBackground
                                ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-soft hover:shadow-glow'
                                : 'bg-accent-400 text-primary-900 hover:bg-accent-300 shadow-soft'
                                }`}
                        >
                            Join Us
                        </Link>
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        onClick={() => setOpenLocation(isOpen ? null : location.key)}
                        className={`md:hidden p-2 rounded-lg transition-colors duration-300 ${hasLightBackground ? 'text-primary-600' : 'text-white'
                            }`}
                        aria-label="Toggle menu"
                        aria-expanded={isOpen}
                        aria-controls="mobile-navigation"
                    >
                        <svg
                            className="w-7 h-7"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            {isOpen ? (
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            ) : (
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M4 6h16M4 12h16M4 18h16"
                                />
                            )}
                        </svg>
                    </button>
                </div>

                {/* Mobile Menu */}
                <div
                    id="mobile-navigation"
                    inert={!isOpen}
                    className={`md:hidden overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? 'max-h-96 opacity-100 mt-4' : 'max-h-0 opacity-0'
                        }`}
                >
                    <div className={`rounded-2xl p-4 space-y-2 ${hasLightBackground ? 'bg-gray-50' : 'bg-white/10 backdrop-blur-lg'
                        }`}>
                        {navLinks.map((link) => (
                            <NavLink
                                key={link.name}
                                to={link.path}
                                onClick={() => setOpenLocation(null)}
                                className={({ isActive }) =>
                                    `block px-4 py-3 rounded-xl font-medium transition-all duration-300 ${hasLightBackground
                                        ? isActive
                                            ? 'bg-primary-100 text-primary-700'
                                            : 'text-gray-700 hover:bg-gray-100'
                                        : isActive
                                            ? 'bg-white/20 text-white'
                                            : 'text-white hover:bg-white/10'
                                    }`
                                }
                            >
                                {link.name}
                            </NavLink>
                        ))}
                        <Link
                            to="/contact"
                            className="block w-full mt-4 px-4 py-3 bg-primary-600 text-white text-center font-semibold rounded-xl hover:bg-primary-700 transition-colors duration-300"
                        >
                            Join Us
                        </Link>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
