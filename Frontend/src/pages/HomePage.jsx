import { Link } from 'react-router-dom';
import HeroVideo from '../components/HeroVideo';
import { organizationInfo } from '../data/organization';

/**
 * HomePage Component
 * Landing page with hero section and introduction to MUN club
 */
const HomePage = () => {
    // Features/Benefits of joining MUN
    const features = [
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
            ),
            title: "Global Perspective",
            description: "Gain understanding of international relations, diplomacy, and global challenges facing our world today.",
        },
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
            ),
            title: "Public Speaking",
            description: "Develop confidence and eloquence through debates, speeches, and diplomatic negotiations.",
        },
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
            ),
            title: "Networking",
            description: "Connect with like-minded students from across Bangladesh and build lasting professional relationships.",
        },
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
            ),
            title: "Critical Thinking",
            description: "Analyze complex issues from multiple perspectives and develop innovative solutions.",
        },
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
            ),
            title: "Research Skills",
            description: "Master research methodologies and learn to synthesize information from diverse sources.",
        },
        {
            icon: (
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
            ),
            title: "Leadership",
            description: "Take on leadership roles and learn to guide teams towards common goals.",
        },
    ];

    // Statistics to showcase
    const stats = [
        { number: "500+", label: "Active Members" },
        { number: "15+", label: "Conferences Hosted" },
        { number: "50+", label: "Awards Won" },
        { number: organizationInfo.foundedYear, label: "Founded" },
    ];

    return (
        <div>
            {/* Hero Section with Video Background */}
            <HeroVideo />

            {/* About Preview Section */}
            <section className="section-container bg-gray-50">
                <div className="text-center mb-12">
                    <h2 className="section-title">Welcome to JKKNIU MUN</h2>
                    <p className="section-subtitle">
                        Join a community of future diplomats, leaders, and changemakers at
                        Jatiya Kabi Kazi Nazrul Islam University.
                    </p>
                </div>

                <div className="grid md:grid-cols-2 gap-8 items-center">
                    <div className="space-y-6">
                        <p className="text-gray-600 leading-relaxed">
                            The JKKNIU Model United Nations Club is the premier platform for students
                            passionate about international affairs, diplomacy, and global governance.
                            Through simulations of United Nations committees, we provide hands-on
                            experience in diplomatic negotiation and problem-solving.
                        </p>
                        <p className="text-gray-600 leading-relaxed">
                            Our members develop essential skills including public speaking, research,
                            critical thinking, and collaboration. Whether you're a first-time delegate
                            or an experienced MUNer, there's a place for you in our community.
                        </p>
                        <Link
                            to="/about"
                            className="inline-flex items-center gap-2 text-primary-600 font-semibold hover:text-primary-700 transition-colors group"
                        >
                            Learn More About Us
                            <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                            </svg>
                        </Link>
                    </div>
                    <div className="relative">
                        <img
                            src="https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=600"
                            alt="MUN Conference"
                            className="rounded-2xl shadow-soft-lg"
                        />
                        <div className="absolute -bottom-6 -left-6 bg-primary-600 text-white p-6 rounded-2xl shadow-lg">
                            <p className="font-heading font-bold text-3xl">Since {organizationInfo.foundedYear}</p>
                            <p className="text-sm opacity-90">Building Future Leaders</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features/Benefits Section */}
            <section className="section-container">
                <div className="text-center mb-12">
                    <h2 className="section-title">Why Join MUN?</h2>
                    <p className="section-subtitle">
                        Discover the skills and experiences that await you as a member of our club.
                    </p>
                </div>

                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, index) => (
                        <div
                            key={index}
                            className="card group hover:border-primary-200 border border-transparent"
                        >
                            <div className="w-14 h-14 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center mb-4 group-hover:bg-primary-600 group-hover:text-white transition-all duration-300">
                                {feature.icon}
                            </div>
                            <h3 className="font-heading font-semibold text-xl text-primary-700 mb-2">
                                {feature.title}
                            </h3>
                            <p className="text-gray-600 text-sm leading-relaxed">
                                {feature.description}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Stats Section */}
            <section className="bg-gradient-to-r from-primary-700 to-primary-900 py-16">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
                        {stats.map((stat, index) => (
                            <div key={index} className="text-center">
                                <p className="font-heading font-bold text-4xl md:text-5xl text-accent-400 mb-2">
                                    {stat.number}
                                </p>
                                <p className="text-white/80 text-sm md:text-base">
                                    {stat.label}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="section-container bg-gray-50">
                <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-3xl p-8 md:p-12 text-center text-white">
                    <h2 className="font-heading font-bold text-3xl md:text-4xl mb-4">
                        Ready to Begin Your Diplomatic Journey?
                    </h2>
                    <p className="text-white/90 max-w-2xl mx-auto mb-8">
                        Join hundreds of students who have discovered their potential through
                        Model United Nations. Take the first step towards becoming a global leader.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <Link
                            to="/contact"
                            className="px-8 py-4 bg-accent-400 text-primary-900 font-semibold rounded-full hover:bg-accent-300 transition-all duration-300 transform hover:-translate-y-1"
                        >
                            Join Now
                        </Link>
                        <Link
                            to="/events"
                            className="px-8 py-4 bg-transparent border-2 border-white font-semibold rounded-full hover:bg-white hover:text-primary-600 transition-all duration-300 transform hover:-translate-y-1"
                        >
                            View Events
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default HomePage;
