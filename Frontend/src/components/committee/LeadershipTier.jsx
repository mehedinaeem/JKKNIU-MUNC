import ExecutiveMemberCard from './ExecutiveMemberCard';

export default function LeadershipTier({ tier, members, index }) {
    const headingId = `leadership-tier-${index}`;
    return <li className="leadership-tier" data-committee-reveal>
        <section aria-labelledby={headingId}>
            <div className="leadership-tier-heading">
                <h3 id={headingId}>{tier.label}</h3>
            </div>
            <div className={`leadership-tier-cards leadership-row-${members.length}`}>
                {members.map((member, memberIndex) => <ExecutiveMemberCard key={member.id} index={memberIndex} member={member} featured={tier.featured} president={member.position === 'President'} />)}
            </div>
        </section>
    </li>;
}
