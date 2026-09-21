import { Link } from 'react-router-dom';
import ClubHistory from '../components/ClubHistory';
import ExecutiveCommittee from '../components/committee/ExecutiveCommittee';

/**
 * AboutPage Component
 * Club history, mission, vision, and executive committee information
 */
const AboutPage = () => {
    return (
        <div className="pt-24">
            {/* Hero Section */}
            <section className="bg-gradient-to-br from-primary-700 to-primary-900 text-white py-16 md:py-24">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h1 className="font-heading font-bold text-4xl md:text-5xl lg:text-6xl mb-6">
                        About Us
                    </h1>
                    <p className="text-xl md:text-2xl text-white/90 max-w-3xl mx-auto">
                        Learn about our journey, mission, and the passionate team behind
                        JKKNIU Model United Nations Club.
                    </p>
                </div>
            </section>

            {/* Mission & Vision Section */}
            <section className="section-container">
                <div className="grid md:grid-cols-2 gap-12">
                    {/* Mission */}
                    <div className="card border-l-4 border-primary-600">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="w-12 h-12 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <h2 className="font-heading font-bold text-2xl text-primary-700">Our Mission</h2>
                        </div>
                        <p className="text-gray-600 leading-relaxed">
                            To provide a platform for students to develop diplomatic skills, global awareness,
                            and leadership qualities through Model United Nations simulations. We aim to create
                            informed global citizens who understand the complexities of international relations
                            and are equipped to make meaningful contributions to society.
                        </p>
                    </div>

                    {/* Vision */}
                    <div className="card border-l-4 border-accent-400">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="w-12 h-12 rounded-xl bg-accent-100 text-accent-600 flex items-center justify-center">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                            </div>
                            <h2 className="font-heading font-bold text-2xl text-primary-700">Our Vision</h2>
                        </div>
                        <p className="text-gray-600 leading-relaxed">
                            To be the leading platform for diplomatic education in Bangladesh, recognized for
                            producing future leaders, diplomats, and changemakers. We envision a community
                            where every student has the opportunity to understand global issues and develop
                            the skills to address them.
                        </p>
                    </div>
                </div>
            </section>

            <ClubHistory />

            <ExecutiveCommittee />

            {/* CTA Section */}
            <section className="section-container">
                <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-3xl p-8 md:p-12 text-center text-white">
                    <h2 className="font-heading font-bold text-3xl md:text-4xl mb-4">
                        Want to Be Part of Our Story?
                    </h2>
                    <p className="text-white/90 max-w-2xl mx-auto mb-8">
                        Join our growing community and start your journey as a future diplomat today.
                    </p>
                    <Link
                        to="/contact"
                        className="inline-block px-8 py-4 bg-accent-400 text-primary-900 font-semibold rounded-full hover:bg-accent-300 transition-all duration-300 transform hover:-translate-y-1"
                    >
                        Join Our Club
                    </Link>
                </div>
            </section>
        </div>
    );
};

export default AboutPage;
