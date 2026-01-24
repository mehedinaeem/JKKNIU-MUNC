import { useState } from 'react';
import { Link } from 'react-router-dom';
import { upcomingEvents, pastEvents, eventTypes } from '../data/events';

/**
 * EventsPage Component
 * Display upcoming and past MUN events with filtering
 */
const EventsPage = () => {
    const [activeTab, setActiveTab] = useState('upcoming');
    const [selectedType, setSelectedType] = useState('All');

    // Filter events based on type
    const filterEvents = (events) => {
        if (selectedType === 'All') return events;
        return events.filter((event) => event.type === selectedType);
    };

    // Format date to readable string
    const formatDate = (dateString) => {
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        return new Date(dateString).toLocaleDateString('en-US', options);
    };

    // Get date range display
    const getDateRange = (startDate, endDate) => {
        if (startDate === endDate) {
            return formatDate(startDate);
        }
        const start = new Date(startDate);
        const end = new Date(endDate);
        const startMonth = start.toLocaleDateString('en-US', { month: 'long' });
        const endMonth = end.toLocaleDateString('en-US', { month: 'long' });

        if (startMonth === endMonth) {
            return `${start.getDate()} - ${end.getDate()} ${startMonth}, ${start.getFullYear()}`;
        }
        return `${formatDate(startDate)} - ${formatDate(endDate)}`;
    };

    return (
        <div className="pt-24">
            {/* Hero Section */}
            <section className="bg-gradient-to-br from-primary-700 to-primary-900 text-white py-16 md:py-24">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h1 className="font-heading font-bold text-4xl md:text-5xl lg:text-6xl mb-6">
                        Events
                    </h1>
                    <p className="text-xl md:text-2xl text-white/90 max-w-3xl mx-auto">
                        Discover our upcoming conferences, workshops, and training sessions.
                    </p>
                </div>
            </section>

            {/* Events Content */}
            <section className="section-container">
                {/* Tab Navigation */}
                <div className="flex justify-center mb-8">
                    <div className="inline-flex bg-gray-100 rounded-full p-1">
                        <button
                            onClick={() => setActiveTab('upcoming')}
                            className={`px-6 py-2.5 rounded-full font-medium transition-all duration-300 ${activeTab === 'upcoming'
                                    ? 'bg-primary-600 text-white shadow-soft'
                                    : 'text-gray-600 hover:text-primary-600'
                                }`}
                        >
                            Upcoming Events
                        </button>
                        <button
                            onClick={() => setActiveTab('past')}
                            className={`px-6 py-2.5 rounded-full font-medium transition-all duration-300 ${activeTab === 'past'
                                    ? 'bg-primary-600 text-white shadow-soft'
                                    : 'text-gray-600 hover:text-primary-600'
                                }`}
                        >
                            Past Events
                        </button>
                    </div>
                </div>

                {/* Type Filter */}
                <div className="flex flex-wrap justify-center gap-2 mb-12">
                    {eventTypes.map((type) => (
                        <button
                            key={type}
                            onClick={() => setSelectedType(type)}
                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${selectedType === type
                                    ? 'bg-accent-400 text-primary-900'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {type}
                        </button>
                    ))}
                </div>

                {/* Upcoming Events Grid */}
                {activeTab === 'upcoming' && (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filterEvents(upcomingEvents).map((event) => (
                            <div key={event.id} className="card group overflow-hidden">
                                {/* Event Image */}
                                <div className="relative h-48 -mx-6 -mt-6 mb-6 overflow-hidden">
                                    <img
                                        src={event.image}
                                        alt={event.title}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                    <div className="absolute top-4 left-4">
                                        <span className="px-3 py-1 bg-primary-600 text-white text-xs font-semibold rounded-full">
                                            {event.type}
                                        </span>
                                    </div>
                                    {event.registrationOpen && (
                                        <div className="absolute top-4 right-4">
                                            <span className="px-3 py-1 bg-green-500 text-white text-xs font-semibold rounded-full">
                                                Registration Open
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {/* Event Details */}
                                <h3 className="font-heading font-semibold text-xl text-primary-700 mb-3 group-hover:text-primary-600 transition-colors">
                                    {event.title}
                                </h3>

                                <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    <span>{getDateRange(event.date, event.endDate)}</span>
                                </div>

                                <div className="flex items-center gap-2 text-gray-500 text-sm mb-4">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    <span>{event.location}</span>
                                </div>

                                <p className="text-gray-600 text-sm mb-6 line-clamp-2">
                                    {event.description}
                                </p>

                                <Link
                                    to="/contact"
                                    className="inline-flex items-center gap-2 text-primary-600 font-semibold hover:text-primary-700 transition-colors group/link"
                                >
                                    Register Now
                                    <svg className="w-4 h-4 group-hover/link:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                                    </svg>
                                </Link>
                            </div>
                        ))}
                    </div>
                )}

                {/* Past Events Grid */}
                {activeTab === 'past' && (
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filterEvents(pastEvents).map((event) => (
                            <div key={event.id} className="card group overflow-hidden opacity-90">
                                {/* Event Image */}
                                <div className="relative h-48 -mx-6 -mt-6 mb-6 overflow-hidden">
                                    <img
                                        src={event.image}
                                        alt={event.title}
                                        className="w-full h-full object-cover grayscale-[30%] group-hover:grayscale-0 group-hover:scale-105 transition-all duration-500"
                                    />
                                    <div className="absolute top-4 left-4">
                                        <span className="px-3 py-1 bg-gray-600 text-white text-xs font-semibold rounded-full">
                                            {event.type}
                                        </span>
                                    </div>
                                </div>

                                {/* Event Details */}
                                <h3 className="font-heading font-semibold text-xl text-primary-700 mb-3">
                                    {event.title}
                                </h3>

                                <div className="flex items-center gap-2 text-gray-500 text-sm mb-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    <span>{getDateRange(event.date, event.endDate)}</span>
                                </div>

                                <div className="flex items-center gap-2 text-gray-500 text-sm mb-4">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                    </svg>
                                    <span>{event.location}</span>
                                </div>

                                <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                                    {event.description}
                                </p>

                                {/* Highlights */}
                                {event.highlights && (
                                    <div className="flex flex-wrap gap-2">
                                        {event.highlights.map((highlight, idx) => (
                                            <span
                                                key={idx}
                                                className="px-2 py-1 bg-primary-50 text-primary-600 text-xs rounded-full"
                                            >
                                                {highlight}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                {/* Empty State */}
                {((activeTab === 'upcoming' && filterEvents(upcomingEvents).length === 0) ||
                    (activeTab === 'past' && filterEvents(pastEvents).length === 0)) && (
                        <div className="text-center py-12">
                            <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            <h3 className="text-xl font-semibold text-gray-500 mb-2">No Events Found</h3>
                            <p className="text-gray-400">Try selecting a different category</p>
                        </div>
                    )}
            </section>

            {/* CTA Section */}
            <section className="section-container bg-gray-50">
                <div className="bg-gradient-to-br from-primary-600 to-primary-800 rounded-3xl p-8 md:p-12 text-center text-white">
                    <h2 className="font-heading font-bold text-3xl md:text-4xl mb-4">
                        Want to Host an Event with Us?
                    </h2>
                    <p className="text-white/90 max-w-2xl mx-auto mb-8">
                        We're always looking for partners and speakers. Get in touch to collaborate
                        on conferences, workshops, or training sessions.
                    </p>
                    <Link
                        to="/contact"
                        className="inline-block px-8 py-4 bg-accent-400 text-primary-900 font-semibold rounded-full hover:bg-accent-300 transition-all duration-300 transform hover:-translate-y-1"
                    >
                        Contact Us
                    </Link>
                </div>
            </section>
        </div>
    );
};

export default EventsPage;
