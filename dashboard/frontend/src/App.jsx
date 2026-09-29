import { useEffect, useState } from "react";
import axios from "axios";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from "recharts";
import "./style.css";

const API_URL = "http://127.0.0.1:8002/dashboard/overview";
const STATUS_COLORS = ["#3b82f6", "#22c55e", "#ef4444", "#8b5cf6"];

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const refresh = () => {
      axios.get(API_URL)
        .then((response) => {
          if (active) {
            setDashboard(response.data);
            setError("");
          }
        })
        .catch(() => {
          if (active) setError("Không tải được dữ liệu PR. Hãy kiểm tra backend.");
        });
    };
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  if (!dashboard) {
    return <div className="dashboard"><h1>Pull Request Quality Dashboard</h1><p>{error || "Đang tải dữ liệu..."}</p></div>;
  }

  const { statistics: stats, risk_score: risk, reviewer, metrics, pull_requests: prs } = dashboard;
  const statusData = [
    { name: "Open", value: stats.open },
    { name: "Approved", value: stats.approved },
    { name: "Rejected", value: stats.rejected },
    { name: "Merged", value: stats.merged },
  ];
  const riskData = [
    { name: "Low", value: risk.low },
    { name: "Medium", value: risk.medium },
    { name: "High", value: risk.high },
  ];
  const qualityData = prs.map((pr) => ({ name: pr.id, score: pr.quality_score }));

  return (
    <div className="dashboard">
      <h1>Pull Request Quality Dashboard</h1>
      {error && <p role="alert">{error}</p>}

      <div className="cards">
        <div><h3>Total PR</h3><b>{stats.total_pr}</b></div>
        <div><h3>Approved</h3><b>{stats.approved}</b></div>
        <div><h3>Open</h3><b>{stats.open}</b></div>
        <div><h3>Risk High</h3><b>{risk.high}</b></div>
      </div>

      <div className="charts">
        <div className="box">
          <h2>Pull Request Status</h2>
          <PieChart width={400} height={300}>
            <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}>
              {statusData.map((item, index) => <Cell key={item.name} fill={STATUS_COLORS[index]} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </div>
        <div className="box">
          <h2>Risk Level</h2>
          <BarChart width={400} height={300} data={riskData}>
            <CartesianGrid />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        </div>
        <div className="box">
          <h2>Quality Score by PR</h2>
          <BarChart width={400} height={300} data={qualityData}>
            <CartesianGrid />
            <XAxis dataKey="name" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Bar dataKey="score" fill="#22c55e" />
          </BarChart>
        </div>
      </div>

      <div className="box">
        <h2>Pull Requests</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th>ID</th><th>Title</th><th>Reviewer</th><th>Status</th><th>Tests</th><th>Lint</th><th>Quality Score</th><th>Risk Score</th><th>Risk Level</th></tr></thead>
            <tbody>
              {prs.map((pr) => (
                <tr key={pr.id}>
                  <td>{pr.id}</td><td>{pr.title}</td><td>{pr.reviewer}</td>
                  <td>{pr.status}</td>
                  <td>{pr.quality_checks.tests_passed ? "Pass" : "Fail"}</td>
                  <td>{pr.quality_checks.lint_passed ? "Pass" : "Fail"}</td>
                  <td>{pr.quality_score}</td>
                  <td>{pr.risk_score}</td><td>{pr.risk_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="box">
        <h2>PRs by Reviewer</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th>Reviewer</th><th>Reviews</th><th>Average PR Quality Score</th></tr></thead>
            <tbody>
              {Object.entries(reviewer).map(([name, value]) => (
                <tr key={name}><td>{name}</td><td>{value.reviews}</td><td>{value.average_score}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="metrics">
        <div><h3>Approval Rate</h3><b>{metrics.approval_rate}%</b></div>
        <div><h3>Average PR Quality Score</h3><b>{metrics.average_quality_score}</b></div>
      </div>
    </div>
  );
}

export default App;
