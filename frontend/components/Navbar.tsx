// "use client";

// import Link from "next/link";
// import { usePathname } from "next/navigation";

// const links = [
//   { href: "/", label: "Dashboard" },
//   { href: "/create-job", label: "Create Job" },
//   { href: "/upload", label: "Upload" },
//   { href: "/results", label: "Results" },
//   { href: "/copilot", label: "Copilot" },
// ];

// export default function Navbar() {
//   const pathname = usePathname();

//   return (
//     <nav className="sticky top-0 z-40 w-full border-b border-slate-700/60 bg-slate-900/80 backdrop-blur-md">
//       <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
//         {/* Brand */}
//         <Link href="/" className="flex items-center gap-2 text-sm font-semibold text-white">
//           <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-xs font-bold text-white">
//             AI
//           </span>
//           <span className="hidden sm:inline">Hiring Co-Recruiter</span>
//         </Link>

//         {/* Links */}
//         <ul className="flex items-center gap-1">
//           {links.map(({ href, label }) => {
//             const active = pathname === href;
//             return (
//               <li key={href}>
//                 <Link
//                   href={href}
//                   className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
//                     active
//                       ? "bg-slate-700 text-white"
//                       : "text-slate-400 hover:bg-slate-800 hover:text-white"
//                   }`}
//                 >
//                   {label}
//                 </Link>
//               </li>
//             );
//           })}
//         </ul>
//       </div>
//     </nav>
//   );
// }
