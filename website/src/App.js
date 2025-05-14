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
        
        // Primary data file is grants-data.json - contains actual grant data
        const dataFile = 'grants-data.json';
        console.log('Fetching from:', `${pathPrefix}/${dataFile}?v=${timestamp}`);

        const response = await fetch(`${pathPrefix}/${dataFile}?v=${timestamp}`);

        if (!response.ok) {
          console.error('First fetch attempt failed, trying fallback paths');
          
          // Try the original sample-data.json for backward compatibility
          let fallbackResponse;
          try {
            fallbackResponse = await fetch(`${pathPrefix}/sample-data.json?v=${timestamp}`);
            if (!fallbackResponse.ok) {
              // If that fails too, try relative path as final fallback
              fallbackResponse = await fetch(`./grants-data.json?v=${timestamp}`);
              if (!fallbackResponse.ok) {
                fallbackResponse = await fetch(`./sample-data.json?v=${timestamp}`);
              }
            }
          } catch (fallbackError) {
            // Final attempt with the most basic path
            fallbackResponse = await fetch(`./sample-data.json?v=${timestamp}`);
          }

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
      
      {/* Consolidated Chart - Compare Across Sources */}
      <div className="consolidated-chart">
        <h2>Source Comparison</h2>
        <Bar
          options={{
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
              x: {
                beginAtZero: true,
                stacked: false
              },
              y: {
                stacked: false
              }
            },
            plugins: {
              legend: {
                position: 'top',
              },
              title: {
                display: true,
                text: 'Grants by Source'
              }
            },
          }}
          data={{
            labels: data.sites.map(site => site.site),
            datasets: [
              {
                label: 'Grants in Database',
                data: data.sites.map(site => site.grant_count),
                backgroundColor: 'rgba(54, 162, 235, 0.7)',
              },
              {
                label: 'Pending Details',
                data: data.sites.map(site => site.grants_without_details),
                backgroundColor: 'rgba(255, 99, 132, 0.7)',
              }
            ],
          }}
        />
      </div>
      
      {/* Pending Grants Section */}
      {data.summary.pending_grants && data.summary.pending_grants.length > 0 && (
        <div className="pending-grants">
          <h2>Pending Grants</h2>
          <p>These grants have been detected but full details have not yet been collected:</p>
          <div className="pending-grants-list">
            {data.summary.pending_grants.map((grant, index) => (
              <div key={grant.id} className="pending-grant-item">
                <h3>{grant.title}</h3>
                <div className="pending-grant-details">
                  <div className="pending-grant-source">{grant.source}</div>
                  <div className="pending-grant-id">ID: {grant.id}</div>
                  <a 
                    href={grant.url} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="pending-grant-link"
                  >
                    View Original
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
              <div className="pull-stats-title">Grant Status Distribution</div>
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
                    labels: ['Complete Grants', 'Pending Details', 'New Grants'],
                    datasets: [
                      {
                        data: [
                          site.grant_count,
                          site.grants_without_details || 0,
                          site.latest_pull?.new_grants || 0
                        ],
                        backgroundColor: [
                          'rgba(54, 162, 235, 0.7)',
                          'rgba(255, 159, 64, 0.7)',
                          'rgba(255, 99, 132, 0.7)'
                        ],
                        borderColor: [
                          'rgba(54, 162, 235, 1)',
                          'rgba(255, 159, 64, 1)',
                          'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1,
                      },
                    ],
                  }}
                />
              </div>
            </div>
            
            {/* Pending Grants for this Source */}
            {site.pending_grants && site.pending_grants.length > 0 && (
              <div className="site-pending-grants">
                <h4>Pending Grants for {site.site}</h4>
                <ul className="site-pending-grants-list">
                  {site.pending_grants.map(grant => (
                    <li key={grant.id}>
                      <a 
                        href={grant.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                      >
                        {grant.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
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