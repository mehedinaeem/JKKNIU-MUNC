/**
 * Sample Events Data
 * Contains upcoming and past MUN events for the EventsPage
 */

export const upcomingEvents = [
    {
        id: 1,
        title: "JKKNIU MUN 2026",
        date: "2026-03-15",
        endDate: "2026-03-17",
        location: "JKKNIU Main Auditorium",
        description: "Our flagship annual Model United Nations conference bringing together delegates from universities across Bangladesh to debate pressing global issues.",
        type: "Conference",
        registrationOpen: true,
        image: "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=600",
    },
    {
        id: 2,
        title: "Delegate Training Workshop",
        date: "2026-02-20",
        endDate: "2026-02-20",
        location: "Room 301, Academic Building",
        description: "A comprehensive training session for new delegates covering parliamentary procedures, speech writing, and negotiation skills.",
        type: "Workshop",
        registrationOpen: true,
        image: "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=600",
    },
    {
        id: 3,
        title: "Mock Session: UNSC",
        date: "2026-02-10",
        endDate: "2026-02-10",
        location: "Seminar Hall B",
        description: "Practice your diplomacy skills in this mock United Nations Security Council session focusing on international peace and security.",
        type: "Mock Session",
        registrationOpen: true,
        image: "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600",
    },
];

export const pastEvents = [
    {
        id: 4,
        title: "JKKNIU MUN 2025",
        date: "2025-03-10",
        endDate: "2025-03-12",
        location: "JKKNIU Main Auditorium",
        description: "Our successful 2025 conference with 200+ delegates debating in 6 different committees.",
        type: "Conference",
        highlights: ["200+ Delegates", "6 Committees", "Best Delegate Awards"],
        image: "https://images.unsplash.com/photo-1511578314322-379afb476865?w=600",
    },
    {
        id: 5,
        title: "National MUN Dhaka 2024",
        date: "2024-11-15",
        endDate: "2024-11-17",
        location: "Dhaka, Bangladesh",
        description: "Our delegation represented JKKNIU at the National MUN in Dhaka, winning multiple awards.",
        type: "External Conference",
        highlights: ["Best Delegation Award", "3 Best Delegate Awards"],
        image: "https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=600",
    },
    {
        id: 6,
        title: "Inter-University Debate Competition",
        date: "2024-09-05",
        endDate: "2024-09-05",
        location: "JKKNIU Campus",
        description: "A regional debate competition hosted by our club featuring teams from 10 universities.",
        type: "Competition",
        highlights: ["10 Universities", "40+ Debaters"],
        image: "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=600",
    },
];

export const eventTypes = ["All", "Conference", "Workshop", "Mock Session", "Competition", "External Conference"];
