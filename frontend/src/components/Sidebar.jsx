import { NavLink } from "react-router-dom";
import { Home, Film, Tv, Music, Search, Heart, Clock, User, Bell } from "lucide-react";
import "./Sidebar.css";

const Sidebar = () => {
    const links = [
        { name: "Home", path: "/home", icon: <Home size={20} /> },
        { name: "Search", path: "/search", icon: <Search size={20} /> },
        { name: "Movies", path: "/movies", icon: <Film size={20} /> },
        { name: "TV Shows", path: "/tv", icon: <Tv size={20} /> },
        { name: "Music", path: "/music", icon: <Music size={20} /> },
    ];

    const libraryLinks = [
        { name: "Watchlist", path: "/watchlist", icon: <Heart size={20} /> },
        { name: "History", path: "/history", icon: <Clock size={20} /> },
    ];

    return (
        <aside className="sidebar glass">
            <div className="logo-container">
                <h2>Stream<span className="text-accent">Hub</span></h2>
            </div>

            <div className="menu-section">
                <p className="menu-title">Menu</p>
                <nav className="nav-links">
                    {links.map((link) => (
                        <NavLink
                            key={link.name}
                            to={link.path}
                            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                        >
                            {link.icon}
                            <span>{link.name}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>

            <div className="menu-section">
                <p className="menu-title">Library</p>
                <nav className="nav-links">
                    {libraryLinks.map((link) => (
                        <NavLink
                            key={link.name}
                            to={link.path}
                            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                        >
                            {link.icon}
                            <span>{link.name}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>
        </aside>
    );
};

export default Sidebar;
