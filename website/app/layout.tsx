import logo from '@/lib/brand/logo.png?url';
import type {Metadata} from 'next';import './globals.css';
export const metadata:Metadata={title:'Custom Steam Achievements',icons:{icon:logo,apple:logo},description:'Explore and share community achievement packs for non-Steam games.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><head><link rel="stylesheet" href="https://store.akamai.steamstatic.com/public/shared/css/motiva_sans.css"/></head><body>{children}</body></html>;}
