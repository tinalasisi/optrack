import React, { useState, useEffect } from 'react';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
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
        // Create a dynamic path that works for both local and GitHub Pages deployment
        // Add a timestamp to prevent browser caching
        const timestamp = new Date().getTime();
        const pathPrefix = process.env.PUBLIC_URL || '';
        console.log('Fetching from:', `${pathPrefix}/sample-data.json?v=${timestamp}`);

        const response = await fetch(`${pathPrefix}/sample-data.json?v=${timestamp}`);

        if (!response.ok) {
          console.error('First fetch attempt failed, trying fallback');
          // If that fails, try the relative path as fallback
          const fallbackResponse = await fetch(`./sample-data.json?v=${timestamp}`);

          if (!fallbackResponse.ok) {
            throw new Error(`HTTP error! status: ${fallbackResponse.status}`);
          }

          const fallbackResult = await fallbackResponse.json();
          console.log('Fallback data:', fallbackResult);
          setData(fallbackResult);
          return setLoading(false);
        }

        const result = await response.json();
        console.log('Data loaded successfully:', result);
        setData(result);
        setLoading(false);
      } catch (e) {
        console.error('Error loading data:', e);
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
          <div className="stat-value">{data.summary.new_grants_last_pull || 0}</div>
          <div className="stat-label">New Grants (Last Pull)</div>
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
            </div>
            <div className="site-stats">
              <div className="site-stat">
                <div className="site-stat-value">{site.grant_count}</div>
                <div className="site-stat-label">Grants in DB</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">{site.seen_ids_count}</div>
                <div className="site-stat-label">Seen IDs</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">
                  {site.latest_pull?.total_found || 0}
                </div>
                <div className="site-stat-label">Latest Pull Count</div>
              </div>
              <div className="site-stat">
                <div className="site-stat-value">
                  {site.latest_pull?.new_grants || 0}
                </div>
                <div className="site-stat-label">New Grants</div>
              </div>
            </div>
            <div className="pull-stats">
              <div className="pull-stats-title">Latest Pull Analysis</div>
              <div className="chart-container">
                <Doughnut
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'right',
                      },
                      title: {
                        display: false,
                      },
                      tooltip: {
                        callbacks: {
                          label: function(context) {
                            return ` ${context.label}: ${context.raw}`;
                          }
                        }
                      }
                    },
                  }}
                  data={{
                    labels: ['Grants in Database', 'New Grants Found'],
                    datasets: [
                      {
                        data: [
                          site.grant_count,
                          site.latest_pull?.new_grants || 0
                        ],
                        backgroundColor: [
                          'rgba(54, 162, 235, 0.7)',
                          'rgba(255, 99, 132, 0.7)'
                        ],
                        borderColor: [
                          'rgba(54, 162, 235, 1)',
                          'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1,
                      },
                    ],
                  }}
                />
              </div>
            </div>
            <div className="pull-comparison">
              <div className="pull-bar-container">
                <Bar
                  options={{
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                      x: {
                        beginAtZero: true,
                        stacked: false,
                        grid: {
                          display: false
                        }
                      },
                      y: {
                        stacked: false,
                        grid: {
                          display: false
                        }
                      }
                    },
                    plugins: {
                      legend: {
                        display: true,
                        position: 'top',
                      },
                      title: {
                        display: true,
                        text: 'Database vs Latest Pull'
                      }
                    },
                  }}
                  data={{
                    labels: ['Grants'],
                    datasets: [
                      {
                        label: 'Grants in Database',
                        data: [site.grant_count],
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                      },
                      {
                        label: 'Latest Pull Total',
                        data: [site.latest_pull?.total_found || 0],
                        backgroundColor: 'rgba(255, 159, 64, 0.7)',
                      }
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