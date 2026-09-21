import { useEffect, useRef } from 'react';
import { fourthExecutiveCommittee } from '../../data/executiveCommittee';
import LeadershipTier from './LeadershipTier';
import './committee.css';

const tiers = [
    { roles: ['President'], label: 'President', featured: true },
    { roles: ['Senior Vice President', 'General Secretary'], label: 'Senior Leadership', featured: true },
    { roles: ['Vice President'], label: 'Vice Presidents' },
    { roles: ['Chief of Staff', 'Joint Secretary'], label: 'Secretariat' },
    { roles: ['Organizing Secretary', 'Additional Organizing Secretary'], label: 'Organizing Team' },
    { roles: ['Treasurer'], label: 'Finance' },
].map(tier => ({ ...tier, members: tier.roles.flatMap(role => fourthExecutiveCommittee.filter(member => member.position === role)) }));

export default function ExecutiveCommittee() {
    const section = useRef(null);
    useEffect(() => {
        const media = window.matchMedia('(prefers-reduced-motion: reduce)');
        if (media.matches || !('IntersectionObserver' in window)) return;
        const elements = [...section.current.querySelectorAll('[data-committee-reveal]')];
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                entry.target.classList.remove('committee-pending');
                entry.target.classList.add('committee-visible');
                observer.unobserve(entry.target);
            });
        }, { threshold: .08 });
        elements.forEach(element => { element.classList.add('committee-pending'); observer.observe(element); });
        function disableMotion() {
            if (!media.matches) return;
            observer.disconnect();
            elements.forEach(element => element.classList.remove('committee-pending'));
        }
        media.addEventListener('change', disableMotion);
        return () => { observer.disconnect(); media.removeEventListener('change', disableMotion); };
    }, []);

    return <section ref={section} id="executive-committee" className="executive-committee" aria-labelledby="executive-committee-title">
        <div className="section-container relative">
            <header className="committee-intro" data-committee-reveal>
                <h2 id="executive-committee-title">4th Executive Committee</h2>
                <p className="committee-subtitle">Meet the leadership team of JKKNIU Model United Nations Club.</p>
                <span className="committee-count">{fourthExecutiveCommittee.length} Members</span>
            </header>
            <ol className="committee-hierarchy">
                {tiers.map((tier, index) => <LeadershipTier key={tier.label} tier={tier} members={tier.members} index={index} />)}
            </ol>
        </div>
    </section>;
}
