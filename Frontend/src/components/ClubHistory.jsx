import { useEffect, useRef } from 'react';
import { organizationInfo, foundingMilestones } from '../data/organization';
import './ClubHistory.css';

export default function ClubHistory() {
    const timeline = useRef(null);
    useEffect(() => {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
        const items = [...timeline.current.querySelectorAll('li')];
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                entry.target.classList.remove('history-pending');
                entry.target.classList.add('history-visible');
                observer.unobserve(entry.target);
            });
        }, { threshold: .15 });
        items.forEach(item => { item.classList.add('history-pending'); observer.observe(item); });
        return () => observer.disconnect();
    }, []);
    return <div className="club-history">
        <section className="section-container bg-gray-50" aria-labelledby="our-beginning">
            <div className="grid lg:grid-cols-[1.6fr_1fr] gap-8 lg:gap-12 items-start">
                <div>
                    <h2 id="our-beginning" className="section-title">Our Beginning</h2>
                    <p className="text-gray-600 leading-relaxed text-base sm:text-lg mt-6">
                        JKKNIU Model United Nations Club began taking shape in {organizationInfo.earlyBeginning}, when its first public activities appeared online. The club formally began its journey on {organizationInfo.officialInauguration} with its inauguration at Jatiya Kabi Kazi Nazrul Islam University.
                    </p>
                    <p className="text-gray-600 leading-relaxed text-base sm:text-lg mt-5">
                        Founded under the leadership of {organizationInfo.founder}, the club was created to provide students with a platform to practise diplomacy, discuss international issues and develop the skills needed to represent themselves and their university beyond campus.
                    </p>
                </div>
                <dl className="card border-t-4 border-accent-400 space-y-6">
                    <div><dt className="text-sm text-gray-500">Founded</dt><dd className="text-3xl font-heading font-bold text-primary-900 mt-1">{organizationInfo.foundedYear}</dd></div>
                    <div><dt className="text-sm text-gray-500">Officially Inaugurated</dt><dd className="text-lg font-semibold text-primary-900 mt-1">{organizationInfo.officialInauguration}</dd></div>
                    <div className="border-t border-gray-100 pt-5"><dt className="text-sm text-gray-500">Founder &amp; President</dt><dd className="text-xl font-heading font-semibold text-primary-900 mt-1">{organizationInfo.founder}</dd></div>
                </dl>
            </div>
        </section>
        <section className="section-container" aria-labelledby="our-journey">
            <div className="text-center mb-10"><h2 id="our-journey" className="section-title">Our Journey</h2><p className="section-subtitle">From an early public presence to our formal beginning.</p></div>
            <ol ref={timeline} className="history-timeline max-w-4xl mx-auto">
                {foundingMilestones.map((milestone, index) => <li key={milestone.title} style={{ '--milestone-delay': `${index * 60}ms` }}>
                    <span className="history-marker" aria-hidden="true" />
                    <div className="card">
                        <p className="text-sm font-semibold text-primary-700 mb-2">{milestone.date}</p>
                        <h3 className="text-lg text-primary-900 mb-2">{milestone.title}</h3>
                        <p className="text-gray-600 leading-relaxed text-sm sm:text-base">{milestone.description}</p>
                        {milestone.source && <a className="inline-flex items-center min-h-11 text-sm font-semibold text-primary-600 mt-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-600 focus-visible:outline-offset-2" href={milestone.source} target="_blank" rel="noopener noreferrer">Facebook Post <span className="ml-2" aria-hidden="true">↗</span></a>}
                    </div>
                </li>)}
            </ol>
        </section>
    </div>;
}
