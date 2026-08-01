import './globals.css';import Nav from '../components/Nav';import Footer from '../components/Footer';
export const metadata={title:'A7X Tour Tracker 2026',description:'Every show. Every song. Every change.'};
export default function RootLayout({children}){return <html lang="en"><body><Nav/><main>{children}</main><Footer/></body></html>}