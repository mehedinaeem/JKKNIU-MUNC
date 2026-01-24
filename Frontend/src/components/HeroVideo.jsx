import { Link } from 'react-router-dom';

/**
 * HeroVideo Component
 * Full-screen hero section with background video, dark overlay, and animated content
 */
const HeroVideo = () => {
    // Demo video URL - using a royalty-free video from Pexels CDN
    const demoVideoUrl = "https://videos.pexels.com/video-files/3129671/3129671-uhd_2560_1440_30fps.mp4";

    return (
        <section className="relative h-screen w-full overflow-hidden">
            {/* Background Video */}
            <video
                autoPlay
                loop
                muted
                playsInline
                className="absolute inset-0 w-full h-full object-cover"
                poster="https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=1920"
            >
                <source src={demoVideoUrl} type="video/mp4" />
                {/* Fallback for browsers that don't support video */}
                Your browser does not support the video tag.
            </video>

            {/* Dark Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-b from-primary-900/70 via-primary-900/60 to-primary-900/80" />

            {/* Animated Background Pattern */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg width=%2260%22 height=%2260%22 viewBox=%220 0 60 60%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cg fill=%22none%22 fill-rule=%22evenodd%22%3E%3Cg fill=%22%23ffffff%22 fill-opacity=%220.4%22%3E%3Cpath d=%22M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z%22/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')]" />
            </div>

            {/* Hero Content */}
            <div className="relative h-full flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 text-center">
                {/* Main Heading */}
                <h1 className="font-heading text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 opacity-0 animate-fade-in-up">
                    <span className="block">JKKNIU</span>
                    <span className="block text-accent-400 mt-2">Model United Nations</span>
                    <span className="block text-2xl sm:text-3xl md:text-4xl font-medium text-white/90 mt-3">Club</span>
                </h1>

                {/* Subtitle */}
                <p className="max-w-2xl text-lg sm:text-xl md:text-2xl text-white/90 mb-10 opacity-0 animate-fade-in-up animation-delay-200">
                    Empowering Future Diplomats and Global Leaders
                </p>

                {/* CTA Buttons */}
                <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 opacity-0 animate-fade-in-up animation-delay-400">
                    <Link
                        to="/contact"
                        className="group px-8 py-4 bg-accent-400 text-primary-900 font-semibold rounded-full shadow-lg hover:bg-accent-300 hover:shadow-glow-gold transform hover:-translate-y-1 transition-all duration-300"
                    >
                        <span className="flex items-center justify-center gap-2">
                            Join MUN
                            <svg
                                className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                        </span>
                    </Link>
                    <Link
                        to="/events"
                        className="group px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-full hover:bg-white hover:text-primary-600 transform hover:-translate-y-1 transition-all duration-300"
                    >
                        <span className="flex items-center justify-center gap-2">
                            Upcoming Events
                            <svg
                                className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-300"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </span>
                    </Link>
                </div>

                {/* Scroll Indicator */}
                <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 opacity-0 animate-fade-in animation-delay-800">
                    <div className="flex flex-col items-center text-white/70 animate-bounce-subtle">
                        <span className="text-sm mb-2">Scroll Down</span>
                        <svg
                            className="w-6 h-6"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                        </svg>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default HeroVideo;
