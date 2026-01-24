import { Link } from 'react-router-dom';

/**
 * AboutPage Component
 * Club history, mission, vision, and executive committee information
 */
const AboutPage = () => {
    // Executive Committee Members
    const executiveCommittee = [
        {
            name: "Ahmed Rahman",
            role: "President",
            image: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300",
            department: "International Relations",
        },
        {
            name: "Fatima Akter",
            role: "Vice President",
            image: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=300",
            department: "Political Science",
        },
        {
            name: "Mohammad Hasan",
            role: "Secretary General",
            image: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300",
            department: "Law",
        },
        {
            name: "Nusrat Jahan",
            role: "Deputy Secretary",
            image: "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=300",
            department: "Economics",
        },
        {
            name: "Karim Khan",
            role: "Treasurer",
            image: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300",
            department: "Business Administration",
        },
        {
            name: "Shirin Sultana",
            role: "Director of Training",
            image: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300",
            department: "English",
        },
    ];

    // Timeline milestones
    const milestones = [
        { year: "2015", event: "JKKNIU MUN Club Founded", description: "Started with 20 founding members" },
        { year: "2016", event: "First National Conference", description: "Hosted JKKNIU MUN 2016 with 50 delegates" },
        { year: "2018", event: "Regional Recognition", description: "Won Best Delegation at National MUN Dhaka" },
        { year: "2020", event: "Virtual MUN Adaptation", description: "Successfully transitioned to online conferences" },
        { year: "2022", event: "500+ Member Milestone", description: "Grew to over 500 active members" },
        { year: "2025", event: "10 Year Anniversary", description: "Celebrating a decade of excellence" },
    ];

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

            {/* History/Story Section */}
            <section className="section-container bg-gray-50">
                <div className="text-center mb-12">
                    <h2 className="section-title">Our Story</h2>
                    <p className="section-subtitle">
                        A decade of empowering future diplomats and global leaders.
                    </p>
                </div>

                <div className="max-w-4xl mx-auto">
                    <div className="grid gap-8">
                        <p className="text-gray-600 leading-relaxed text-lg">
                            The JKKNIU Model United Nations Club was founded in 2015 by a group of passionate
                            students who believed in the power of diplomatic education. Starting with just 20
                            members in a small classroom, we have grown into one of the most active and
                            recognized MUN clubs in Bangladesh.
                        </p>
                        <p className="text-gray-600 leading-relaxed text-lg">
                            Over the years, our members have represented JKKNIU at national and international
                            conferences, winning numerous awards and bringing recognition to our university.
                            We have hosted over 15 conferences, trained hundreds of delegates, and built a
                            strong alumni network of professionals working in diplomacy, law, journalism,
                            and public service.
                        </p>
                    </div>
                </div>
            </section>

            {/* Timeline Section */}
            <section className="section-container">
                <div className="text-center mb-12">
                    <h2 className="section-title">Our Journey</h2>
                    <p className="section-subtitle">
                        Key milestones that shaped our club's history.
                    </p>
                </div>

                <div className="max-w-4xl mx-auto">
                    <div className="relative">
                        {/* Timeline Line */}
                        <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-0.5 bg-primary-200 transform md:-translate-x-1/2" />

                        {/* Timeline Items */}
                        {milestones.map((milestone, index) => (
                            <div
                                key={index}
                                className={`relative flex items-start gap-6 mb-8 ${index % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'
                                    }`}
                            >
                                {/* Dot */}
                                <div className="absolute left-4 md:left-1/2 w-4 h-4 bg-primary-600 rounded-full transform -translate-x-1/2 z-10 border-4 border-white" />

                                {/* Content */}
                                <div className={`ml-12 md:ml-0 md:w-1/2 ${index % 2 === 0 ? 'md:pr-12 md:text-right' : 'md:pl-12'}`}>
                                    <div className="card">
                                        <span className="inline-block px-3 py-1 bg-primary-100 text-primary-600 text-sm font-semibold rounded-full mb-2">
                                            {milestone.year}
                                        </span>
                                        <h3 className="font-heading font-semibold text-lg text-primary-700 mb-1">
                                            {milestone.event}
                                        </h3>
                                        <p className="text-gray-600 text-sm">{milestone.description}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Executive Committee Section */}
            <section className="section-container bg-gray-50">
                <div className="text-center mb-12">
                    <h2 className="section-title">Executive Committee</h2>
                    <p className="section-subtitle">
                        Meet the dedicated team leading our club to new heights.
                    </p>
                </div>

                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {executiveCommittee.map((member, index) => (
                        <div key={index} className="card text-center group">
                            <div className="relative w-32 h-32 mx-auto mb-4">
                                <img
                                    src={member.image}
                                    alt={member.name}
                                    className="w-full h-full object-cover rounded-full border-4 border-primary-100 group-hover:border-primary-400 transition-all duration-300"
                                />
                                <div className="absolute inset-0 rounded-full bg-primary-600/0 group-hover:bg-primary-600/10 transition-all duration-300" />
                            </div>
                            <h3 className="font-heading font-semibold text-lg text-primary-700">
                                {member.name}
                            </h3>
                            <p className="text-accent-500 font-medium text-sm mb-1">{member.role}</p>
                            <p className="text-gray-500 text-xs">{member.department}</p>
                        </div>
                    ))}
                </div>
            </section>

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
