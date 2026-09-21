// Display-only framing for the supplied portraits; source images remain unchanged.
const portraitFrames = {
    'exec-06': { size: '370%', top: '-12%' },
    'exec-08': { size: '220%', top: '-22%' },
    'exec-09': { size: '350%', top: '-10%' },
    'exec-11': { size: '125%', top: '-3%' },
    'exec-12': { size: '370%', top: '-10%' },
};

export default function ExecutiveMemberCard({ member, featured = false, president = false, index = 0 }) {
    const frame = portraitFrames[member.id] || { size: '220%', top: '-10%' };
    return <article className={`executive-member ${featured ? 'executive-member-featured' : ''} ${president ? 'executive-member-president' : ''}`} aria-labelledby={`${member.id}-name`} style={{ '--member-delay': `${index * 75}ms`, '--portrait-size': frame.size, '--portrait-top': frame.top }}>
        <div className="executive-portrait">
            <img src={member.image} alt={member.name} width="600" height="600" loading="lazy" decoding="async" />
        </div>
        <div className="executive-member-info">
            <h4 id={`${member.id}-name`}>{member.name}</h4>
            <p>{member.position}</p>
        </div>
    </article>;
}
