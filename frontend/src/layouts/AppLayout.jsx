import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";
import MobileNavbar from "../components/MobileNavbar";
import "./AppLayout.css";

const AppLayout = () => {
    const location = useLocation();

    // When navigating away from /music, ensure any background music playback is stopped
    useEffect(() => {
        if (location.pathname !== '/music') {
            if (window.stopAllStreamHubAudio) {
                window.stopAllStreamHubAudio();
            }
        }
    }, [location.pathname]);

    return (
        <div className="app-container">
            <Navbar />

            <main className="page-content">
                <Outlet />
            </main>

            <MobileNavbar />
        </div>
    );
};

export default AppLayout;
