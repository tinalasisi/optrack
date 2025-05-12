import React, { useState, useEffect } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch('/sample-data.json');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        setData(result);
        setLoading(false);
      } catch (e) {
        setError(`Error loading data: ${e.message}`);
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return <div className="app">Loading dashboard data...</div>;
  }

  if (error) {
    return <div className="app">Error: {error}</div>;
  }

  return (
    <div className="app">
      <header>
        <div className="logo">OpTrack Dashboard</div>
        <div>Last updated: {data.summary.last_updated}</div>
      </header>

      <div className="summary-stats">
        <div className="stat-card">
          <div className="stat-value">{data.summary.total_grants}</div>
          <div className="stat-label">Total Grants</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.summary.total_seen_ids}</div>
          <div className="stat-label">Total Seen IDs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.summary.pending_details}</div>
          <div className="stat-label">Pending Details</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.summary.total_sites}</div>
          <div className="stat-label">Sources</div>
        </div>
      </div>

      <h2>Grant Sources</h2>
      <div className="sites-grid">
        {data.sites.map((site) => (
          <div className="site-card" key={site.site}>
            <div className="site-header">
              <div className="site-name">{site.site}</div>
              <div className="site-format">{site.storage_format}</div>
            </div>
            <div className="site-stats">
              <div className="site-stat">
                <div className="site-stat-value">{site.grant_count}</div>
                <div className="site-stat-label">Grants</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">{site.seen_ids_count}</div>
                <div className="site-stat-label">Seen IDs</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">{site.grants_without_details}</div>
                <div className="site-stat-label">Pending</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">
                  {Math.round(site.storage_stats.total_size / 1024 * 10) / 10}
                </div>
                <div className="site-stat-label">Size (MB)</div>
              </div>
            </div>
            <div className="storage-stats">
              <div className="storage-title">Storage Distribution</div>
              <div className="chart-container">
                <Bar
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false,
                      },
                      title: {
                        display: false,
                      },
                    },
                  }}
                  data={{
                    labels: ['Legacy JSON', 'JSONL Data', 'Index', 'CSV'],
                    datasets: [
                      {
                        data: [
                          site.storage_stats.legacy_json_size,
                          site.storage_stats.jsonl_size,
                          site.storage_stats.index_size,
                          site.storage_stats.csv_size,
                        ],
                        backgroundColor: [
                          'rgba(255, 99, 132, 0.5)',
                          'rgba(54, 162, 235, 0.5)',
                          'rgba(255, 206, 86, 0.5)',
                          'rgba(75, 192, 192, 0.5)',
                        ],
                      },
                    ],
                  }}
                />
              </div>
            </div>
            <div className="updated">Last updated: {site.last_updated}</div>
          </div>
        ))}
      </div>

      <footer>
        <p>OpTrack - Opportunity Tracker © 2025</p>
        <p>
          <a href="https://github.com/tinalasisi/optrack" target="_blank" rel="noopener noreferrer">
            GitHub Repository
          </a>
        </p>
      </footer>
    </div>
  );
}

export default App;