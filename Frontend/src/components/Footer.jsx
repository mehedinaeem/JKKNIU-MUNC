import { Link } from 'react-router-dom';

/**
 * Footer Component
 * Professional footer with club info, quick links, social media, and contact info
 */
const Footer = () => {
    const currentYear = new Date().getFullYear();

    // Quick links for navigation
    const quickLinks = [
        { name: 'Home', path: '/' },
        { name: 'About Us', path: '/about' },
        { name: 'Events', path: '/events' },
        { name: 'Gallery', path: '/gallery' },
        { name: 'Contact', path: '/contact' },
    ];

    // Social media links
    const socialLinks = [
        {
            name: 'Facebook',
            url: 'https://facebook.com/jkkniumun',
            icon: (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.77,7.46H14.5v-1.9c0-.9.6-1.1,1-1.1h3V.5L14.17.5C10.24.5,9.5,3.44,9.5,5.32v2.15H6.5v4h3v12h5v-12h3.85l.42-4Z" />
                </svg>
            ),
        },
        {
            name: 'LinkedIn',
            url: 'https://linkedin.com/company/jkkniumun',
            icon: (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19,3H5C3.895,3,3,3.895,3,5v14c0,1.105,0.895,2,2,2h14c1.105,0,2-0.895,2-2V5C21,3.895,20.105,3,19,3z M9,17H6.477v-7H9 V17z M7.694,8.717c-0.771,0-1.286-0.514-1.286-1.2s0.514-1.2,1.371-1.2c0.771,0,1.286,0.514,1.286,1.2S8.551,8.717,7.694,8.717z M18,17h-2.442v-3.826c0-1.058-0.651-1.302-0.895-1.302s-1.058,0.163-1.058,1.302c0,0.163,0,3.826,0,3.826h-2.523v-7h2.523v0.977 C13.93,10.407,14.581,10,15.802,10C17.023,10,18,10.977,18,13.174V17z" />
                </svg>
            ),
        },
        {
            name: 'Instagram',
            url: 'https://instagram.com/jkkniumun',
            icon: (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12,2.162c3.204,0,3.584,0.012,4.849,0.07c1.308,0.06,2.655,0.358,3.608,1.311c0.962,0.962,1.251,2.296,1.311,3.608 c0.058,1.265,0.07,1.645,0.07,4.849s-0.012,3.584-0.07,4.849c-0.06,1.308-0.358,2.655-1.311,3.608 c-0.962,0.962-2.296,1.251-3.608,1.311c-1.265,0.058-1.645,0.07-4.849,0.07s-3.584-0.012-4.849-0.07 c-1.308-0.06-2.655-0.358-3.608-1.311c-0.962-0.962-1.251-2.296-1.311-3.608c-0.058-1.265-0.07-1.645-0.07-4.849 s0.012-3.584,0.07-4.849c0.06-1.308,0.358-2.655,1.311-3.608c0.962-0.962,2.296-1.251,3.608-1.311 C8.416,2.174,8.796,2.162,12,2.162 M12,0C8.741,0,8.332,0.014,7.052,0.072c-1.95,0.089-3.663,0.567-5.038,1.942 C0.639,3.389,0.161,5.102,0.072,7.052C0.014,8.332,0,8.741,0,12s0.014,3.668,0.072,4.948c0.089,1.95,0.567,3.663,1.942,5.038 c1.375,1.375,3.088,1.853,5.038,1.942C8.332,23.986,8.741,24,12,24s3.668-0.014,4.948-0.072c1.95-0.089,3.663-0.567,5.038-1.942 c1.375-1.375,1.853-3.088,1.942-5.038C23.986,15.668,24,15.259,24,12s-0.014-3.668-0.072-4.948c-0.089-1.95-0.567-3.663-1.942-5.038 c-1.375-1.375-3.088-1.853-5.038-1.942C15.668,0.014,15.259,0,12,0z M12,5.838c-3.403,0-6.162,2.759-6.162,6.162 S8.597,18.162,12,18.162s6.162-2.759,6.162-6.162S15.403,5.838,12,5.838z M12,16c-2.209,0-4-1.791-4-4s1.791-4,4-4s4,1.791,4,4 S14.209,16,12,16z M18.406,4.155c-0.796,0-1.441,0.645-1.441,1.441s0.645,1.441,1.441,1.441s1.441-0.645,1.441-1.441 S19.202,4.155,18.406,4.155z" />
                </svg>
            ),
        },
        {
            name: 'Email',
            url: 'mailto:mun@jkkniu.edu.bd',
            icon: (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M20,4H4C2.895,4,2,4.895,2,6v12c0,1.105,0.895,2,2,2h16c1.105,0,2-0.895,2-2V6C22,4.895,21.105,4,20,4z M20,8.236l-8,4.882 L4,8.236V6h16V8.236z" />
                </svg>
            ),
        },
    ];

    return (
        <footer className="bg-primary-900 text-white">
            {/* Main Footer Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-16">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10">
                    {/* Brand Section */}
                    <div className="lg:col-span-1">
                        <Link to="/" className="flex items-center space-x-3 mb-4">
                            <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center overflow-hidden">
                                <img
                                    src="/mun-logo.png"
                                    alt="JKKNIU MUN Club Logo"
                                    className="w-full h-full object-contain p-1"
                                />
                            </div>
                            <div>
                                <span className="font-heading font-bold text-xl text-white">JKKNIU MUN</span>
                                <span className="block text-xs text-gray-400">Model United Nations Club</span>
                            </div>
                        </Link>
                        <p className="text-gray-400 text-sm leading-relaxed mb-6">
                            Empowering future diplomats and global leaders through Model United Nations
                            simulations at Jatiya Kabi Kazi Nazrul Islam University.
                        </p>
                    </div>

                    {/* Quick Links */}
                    <div>
                        <h3 className="font-heading font-semibold text-lg mb-4">Quick Links</h3>
                        <ul className="space-y-3">
                            {quickLinks.map((link) => (
                                <li key={link.name}>
                                    <Link
                                        to={link.path}
                                        className="text-gray-400 hover:text-accent-400 transition-colors duration-300 text-sm"
                                    >
                                        {link.name}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Contact Info */}
                    <div>
                        <h3 className="font-heading font-semibold text-lg mb-4">Contact Us</h3>
                        <ul className="space-y-3 text-sm text-gray-400">
                            <li className="flex items-start space-x-3">
                                <svg className="w-5 h-5 text-accent-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                <span>JKKNIU Campus, Trishal, Mymensingh-2224</span>
                            </li>
                            <li className="flex items-center space-x-3">
                                <svg className="w-5 h-5 text-accent-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                                <span>mun@jkkniu.edu.bd</span>
                            </li>
                            <li className="flex items-center space-x-3">
                                <svg className="w-5 h-5 text-accent-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                                </svg>
                                <span>+880 1234-567890</span>
                            </li>
                        </ul>
                    </div>

                    {/* Social Links & Newsletter */}
                    <div>
                        <h3 className="font-heading font-semibold text-lg mb-4">Follow Us</h3>
                        <div className="flex space-x-3 mb-6">
                            {socialLinks.map((social) => (
                                <a
                                    key={social.name}
                                    href={social.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-10 h-10 rounded-full bg-primary-800 flex items-center justify-center text-gray-400 hover:bg-accent-400 hover:text-primary-900 transition-all duration-300"
                                    aria-label={social.name}
                                >
                                    {social.icon}
                                </a>
                            ))}
                        </div>
                        <p className="text-gray-400 text-sm">
                            Stay updated with our latest events and activities.
                        </p>
                    </div>
                </div>
            </div>

            {/* Bottom Bar */}
            <div className="border-t border-primary-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
                        <p className="text-gray-400 text-sm text-center md:text-left">
                            © {currentYear} JKKNIU MUN Club. All rights reserved.
                        </p>
                        <p className="text-gray-500 text-xs">
                            Crafted with ❤️ for future diplomats
                        </p>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
