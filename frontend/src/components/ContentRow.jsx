import React from 'react';
import { ChevronRight } from 'lucide-react';
import MovieCard from './MovieCard';
import './ContentRow.css';

const ContentRow = ({ title, items = [], isLoading = false, emptyStateMessage = "Nothing to show right now." }) => {

    // Generate Skeletons
    if (isLoading) {
        return (
            <div className="content-row-container">
                <div className="content-row-header">
                    <h2>{title}</h2>
                </div>
                <div className="content-row-scroll">
                    {[1, 2, 3, 4, 5, 6].map(val => (
                        <MovieCard key={val} isLoading={true} />
                    ))}
                </div>
            </div>
        );
    }

    const safeItems = Array.isArray(items) ? items : [];

    if (!isLoading && safeItems.length === 0) {
        return (
            <div className="content-row-container">
                <div className="content-row-header">
                    <h2>{title}</h2>
                </div>
                <div className="content-row-empty-state">
                    <p>{emptyStateMessage}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="content-row-container">
            <div className="content-row-header">
                <h2>{title}</h2>
                <button className="view-all-btn">
                    See All <ChevronRight size={16} />
                </button>
            </div>

            <div className="content-row-scroll">
                {safeItems.map((item, index) => (
                    <MovieCard key={item?.id || index} movie={item} />
                ))}
            </div>
        </div>
    );
};

export default ContentRow;
