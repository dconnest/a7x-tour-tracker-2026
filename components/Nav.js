import Link from 'next/link';
export default function Nav(){return <header className="siteHeader"><div className="shell nav">
<Link className="brand" href="/"><span className="brandMark">A7X</span><span>Tour Tracker <b>2026</b></span></Link>
<nav><Link href="/shows">Shows</Link><Link href="/songs">Songs</Link><Link href="/stats">Statistics</Link><Link href="/heatmap">Heat map</Link><Link href="/compare">Compare</Link></nav>
</div></header>}