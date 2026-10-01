import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import "./style.css";
import { PRDrawer, PRForm } from "./ManagePR.jsx";

const API_URL = "http://127.0.0.1:8002/dashboard/overview";
const statuses = { OPEN: ["Đang mở", "blue"], IN_REVIEW: ["Đang đánh giá", "blue"], REQUEST_CHANGES: ["Cần chỉnh sửa", "amber"], APPROVED: ["Đã phê duyệt", "green"], REJECTED: ["Từ chối", "red"], MERGED: ["Đã gộp", "purple"] };
const risks = { LOW: ["Thấp", "green"], MEDIUM: ["Trung bình", "amber"], HIGH: ["Cao", "red"] };
const chartStatus = [{ key: "open", name: "Đang mở", color: "#5675ed" }, { key: "approved", name: "Đã duyệt", color: "#28b089" }, { key: "rejected", name: "Từ chối", color: "#eb7378" }, { key: "merged", name: "Đã gộp", color: "#a478df" }];

function Icon({ name, size = 19 }) {
  const icons = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    git: <><circle cx="6" cy="3" r="2"/><path d="M6 5v11a4 4 0 0 0 4 4h4"/><circle cx="16" cy="20" r="2"/><circle cx="18" cy="5" r="2"/><path d="M18 7v5a4 4 0 0 1-4 4H6"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    refresh: <><path d="M20 11a8 8 0 1 0-2 6"/><path d="M20 4v7h-7"/></>,
    arrow: <><path d="m7 17 10-10M8 7h9v9"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
    alert: <><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v4M12 17h.01"/></>,
    layers: <><path d="m12 2 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 17l9 5 9-5"/></>,
    close: <path d="M18 6 6 18M6 6l12 12"/>,
    download: <><path d="M12 3v12m-4-4 4 4 4-4M4 17v4h16v-4"/></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

function Badge({ value, risk = false }) {
  const [label, tone] = (risk ? risks : statuses)[value] || [value || "Chưa rõ", "gray"];
  return <span className={`badge ${tone}`}><i/>{label}</span>;
}

function Quality({ value }) {
  const score = Math.max(0, Math.min(100, Number(value) || 0));
  return <div className="quality"><div><span className={score >= 75 ? "good" : score >= 50 ? "mid" : "low"} style={{ width: `${score}%` }}/></div><b>{score}</b></div>;
}

function PrTable({ prs, onSelect }) {
  if (!prs.length) return <div className="empty"><Icon name="search" size={27}/><h3>Không tìm thấy pull request</h3><p>Thử từ khóa hoặc bộ lọc khác.</p></div>;
  return <div className="table-scroll"><table><thead><tr><th>Pull request</th><th>Người đánh giá</th><th>Trạng thái</th><th>Chất lượng</th><th>Rủi ro</th><th/></tr></thead><tbody>{prs.map(pr => <tr key={pr.id} onClick={() => onSelect(pr)}><td><div className="pr-title"><span className="pr-id">{pr.id}</span><b>{pr.title}</b></div></td><td><div className="reviewer-cell"><span className="tiny-avatar">{(pr.reviewer || "?").charAt(0).toUpperCase()}</span>{pr.reviewer || "Chưa phân công"}</div></td><td><Badge value={pr.status}/></td><td><Quality value={pr.quality_score}/></td><td><Badge value={pr.risk_level} risk/></td><td><button className="row-arrow" onClick={event => { event.stopPropagation(); onSelect(pr); }} aria-label={`Xem ${pr.id}`}><Icon name="chevron" size={16}/></button></td></tr>)}</tbody></table></div>;
}

function exportCsv(prs) {
  const rows = [["ID", "Tiêu đề", "Người đánh giá", "Trạng thái", "Chất lượng", "Điểm rủi ro", "Mức rủi ro"], ...prs.map(pr => [pr.id, pr.title, pr.reviewer, pr.status, pr.quality_score, pr.risk_score, pr.risk_level])];
  const csv = "\uFEFF" + rows.map(row => row.map(value => `"${String(value ?? "").replaceAll('"', '""')}"`).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = "pull-requests.csv"; link.click(); URL.revokeObjectURL(url);
}

function App() {
  const [data, setData] = useState(null), [error, setError] = useState(""), [page, setPage] = useState("overview"), [query, setQuery] = useState(""), [filter, setFilter] = useState("all"), [selected, setSelected] = useState(null), [form, setForm] = useState(null), [menuOpen, setMenuOpen] = useState(false), [refreshing, setRefreshing] = useState(false);
  const refresh = useCallback(async () => {
    setRefreshing(true);
    try { const response = await axios.get(API_URL); setData(response.data); setError(""); }
    catch { setError("Không kết nối được API. Hãy khởi động backend ở cổng 8002."); }
    finally { setRefreshing(false); }
  }, []);
  useEffect(() => { refresh(); const timer = setInterval(refresh, 5000); return () => clearInterval(timer); }, [refresh]);
  useEffect(() => { if (data) setSelected(current => current ? data.pull_requests.find(pr => pr.id === current.id) || current : null); }, [data]);

  const prs = data?.pull_requests || [];
  const shown = useMemo(() => prs.filter(pr => {
    const matchesText = `${pr.id} ${pr.title} ${pr.reviewer}`.toLocaleLowerCase("vi").includes(query.trim().toLocaleLowerCase("vi"));
    const matchesFilter = filter === "all" || (filter === "open" ? ["OPEN", "IN_REVIEW", "REQUEST_CHANGES"].includes(pr.status) : filter === "HIGH_RISK" ? pr.risk_level === "HIGH" : pr.status === filter);
    return matchesText && matchesFilter;
  }), [prs, query, filter]);
  const stats = data?.statistics || { total_pr: 0, open: 0, approved: 0, rejected: 0, merged: 0 };
  const risk = data?.risk_score || { low: 0, medium: 0, high: 0 };
  const metrics = data?.metrics || { approval_rate: 0, average_quality_score: 0 };
  const reviewers = Object.entries(data?.reviewer || {}).sort((a, b) => b[1].reviews - a[1].reviews);
  const statusData = chartStatus.map(item => ({ ...item, value: stats[item.key] || 0 }));
  const riskData = [{ name: "Thấp", value: risk.low, color: "#28b089" }, { name: "Trung bình", value: risk.medium, color: "#efad57" }, { name: "Cao", value: risk.high, color: "#eb7378" }];
  const today = new Intl.DateTimeFormat("vi-VN", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
  const navigate = next => { setPage(next); setMenuOpen(false); };
  const goPrs = nextFilter => { setFilter(nextFilter || "all"); navigate("prs"); };
  const changed = async pr => { setSelected(pr); await refresh(); };
  const saved = async pr => { setForm(null); goPrs(); await changed(pr); };

  return <div className="shell">
    {menuOpen && <button className="scrim" aria-label="Đóng menu" onClick={() => setMenuOpen(false)}/>}
    <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
      <div className="brand"><span className="brand-mark"><Icon name="git" size={22}/></span><div><b>ReviewFlow</b><small>PR Management</small></div></div>
      <span className="side-label">WORKSPACE</span>
      <nav aria-label="Điều hướng chính">
        <button className={page === "overview" ? "active" : ""} onClick={() => navigate("overview")}><Icon name="grid"/>Tổng quan</button>
        <button className={page === "prs" ? "active" : ""} onClick={() => goPrs()}><Icon name="git"/>Pull requests <span className="nav-count">{stats.total_pr}</span></button>
        <button className={page === "reviewers" ? "active" : ""} onClick={() => navigate("reviewers")}><Icon name="users"/>Người đánh giá</button>
      </nav>
      <div className="side-bottom"><div className="system"><i className={error ? "offline" : ""}/><div><b>{error ? "Mất kết nối" : "Hệ thống hoạt động"}</b><small>{error ? "Kiểm tra backend" : "Cập nhật mỗi 5 giây"}</small></div></div><div className="side-profile"><span>AD</span><div><b>Quản trị viên</b><small>Workspace admin</small></div></div></div>
    </aside>
    <main>
      <header className="topbar"><div><button className="menu-button" aria-label="Mở menu" onClick={() => setMenuOpen(true)}><Icon name="menu"/></button><span>Workspace</span><Icon name="chevron" size={14}/><b>{page === "overview" ? "Tổng quan" : page === "prs" ? "Pull requests" : "Người đánh giá"}</b></div><div><span className="today">{today}</span><span className="top-avatar">AD</span></div></header>
      <div className="content">
        {error && <div className="error" role="alert"><Icon name="alert" size={18}/>{error}<button onClick={refresh}>Thử lại</button></div>}
        {!data && !error ? <div className="loading"><span/>Đang tải dữ liệu dashboard...</div> : <>
          {page === "overview" && <>
            <div className="intro"><div><span className="eyebrow">DASHBOARD / TỔNG QUAN</span><h1>Tổng quan dự án <em>✳</em></h1><p>Theo dõi chất lượng, tiến độ và rủi ro của các pull request.</p></div><div className="intro-actions"><button className="secondary" onClick={() => goPrs()}>Xem danh sách</button><button className="primary" onClick={() => setForm({ type: "create" })}>+ Tạo PR</button></div></div>
            <div className="stats">
              {[["Tổng pull request", stats.total_pr, "Tất cả yêu cầu trong dự án", "layers", "blue", "all"], ["Đang xử lý", stats.open, "Cần theo dõi và đánh giá", "clock", "amber", "open"], ["Đã phê duyệt", stats.approved, "Sẵn sàng cho bước tiếp theo", "check", "green", "APPROVED"], ["Rủi ro cao", risk.high, "Ưu tiên kiểm tra kỹ", "shield", "red", "HIGH_RISK"]].map(([name, value, hint, icon, tone, target]) => <button className="stat" key={name} onClick={() => goPrs(target)}><span className="stat-top"><span className={`stat-icon ${tone}`}><Icon name={icon}/></span><Icon name="arrow" size={16}/></span><strong>{value}</strong><b>{name}</b><small>{hint}</small></button>)}
            </div>
            <div className="insights">
              <section className="panel chart-panel"><div className="panel-head"><div><span className="eyebrow">PHÂN BỐ</span><h2>Trạng thái pull request</h2></div><small>Tổng {stats.total_pr} PR</small></div><div className="status-body"><div className="donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={statusData} dataKey="value" nameKey="name" innerRadius={73} outerRadius={98} paddingAngle={statusData.filter(item => item.value).length > 1 ? 3 : 0} stroke="none">{statusData.map(item => <Cell key={item.key} fill={item.color}/>)}</Pie><Tooltip formatter={(value, name) => [`${value} PR`, name]}/></PieChart></ResponsiveContainer><div className="donut-text"><b>{stats.total_pr}</b><span>Pull request</span></div></div><div className="legend">{statusData.map(item => <div key={item.key}><i style={{ background: item.color }}/><span>{item.name}</span><b>{item.value}</b></div>)}</div></div></section>
              <section className="panel chart-panel"><div className="panel-head"><div><span className="eyebrow">PHÂN TÍCH</span><h2>Mức độ rủi ro</h2></div><small>Theo số lượng PR</small></div><div className="risk-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={riskData} layout="vertical" margin={{ top: 4, right: 18, left: 0, bottom: 4 }} barSize={18}><CartesianGrid horizontal={false} stroke="#edf0f5"/><XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "#96a1b2", fontSize: 11 }}/><YAxis type="category" dataKey="name" tickLine={false} axisLine={false} width={80} tick={{ fill: "#647188", fontSize: 11 }}/><Tooltip formatter={value => [`${value} PR`, "Số lượng"]}/><Bar dataKey="value" radius={[0, 6, 6, 0]}>{riskData.map(item => <Cell key={item.name} fill={item.color}/>)}</Bar></BarChart></ResponsiveContainer></div><div className="risk-note"><span><Icon name="shield" size={18}/></span><div><b>{risk.high ? `${risk.high} PR cần chú ý` : "Không có PR rủi ro cao"}</b><small>{risk.high ? "Hãy ưu tiên đánh giá các thay đổi này." : "Các pull request đang ở mức an toàn."}</small></div></div></section>
            </div>
            <div className="insights lower">
              <section className="panel metric-panel"><div className="panel-head"><div><span className="eyebrow">HIỆU SUẤT</span><h2>Chỉ số chất lượng</h2></div></div>{[["Tỷ lệ phê duyệt", metrics.approval_rate, "%", "blue"], ["Điểm chất lượng trung bình", metrics.average_quality_score, "/100", "purple"]].map(([name, value, suffix, tone]) => <div className="metric" key={name}><div><span>{name}</span><b>{value}<small>{suffix}</small></b></div><div className={`track ${tone}`}><span style={{ width: `${Math.min(100, Math.max(0, Number(value) || 0))}%` }}/></div></div>)}</section>
              <section className="panel quick-panel"><div><span className="eyebrow">ĐIỀU HƯỚNG NHANH</span><h2>Quản lý công việc</h2><p>Đi đến danh sách PR hoặc xem hiệu suất người đánh giá.</p></div><div className="quick-actions"><button onClick={() => goPrs()}><Icon name="git" size={17}/>Danh sách pull request<Icon name="chevron" size={16}/></button><button onClick={() => navigate("reviewers")}><Icon name="users" size={17}/>Người đánh giá<Icon name="chevron" size={16}/></button></div></section>
            </div>
            <section className="panel table-panel"><div className="panel-head"><div><span className="eyebrow">HOẠT ĐỘNG</span><h2>Pull request gần đây</h2></div><button className="text-button" onClick={() => goPrs()}>Xem tất cả <Icon name="chevron" size={16}/></button></div><PrTable prs={prs.slice(0, 5)} onSelect={setSelected}/></section>
          </>}
          {page === "prs" && <><div className="intro"><div><span className="eyebrow">WORKSPACE / PULL REQUESTS</span><h1>Pull requests</h1><p>Tạo, đánh giá và quản lý tất cả yêu cầu thay đổi trong dự án.</p></div><div className="intro-actions"><button className="secondary" onClick={() => exportCsv(shown)}><Icon name="download" size={17}/> Xuất CSV</button><button className="primary" onClick={() => setForm({ type: "create" })}>+ Tạo PR</button></div></div><section className="panel list-panel"><div className="toolbar"><label className="search"><Icon name="search"/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Tìm theo mã, tiêu đề, người đánh giá..." aria-label="Tìm pull request"/></label><div><select value={filter} onChange={event => setFilter(event.target.value)} aria-label="Lọc danh sách"><option value="all">Tất cả PR</option><option value="open">Đang xử lý</option><option value="APPROVED">Đã phê duyệt</option><option value="MERGED">Đã gộp</option><option value="REJECTED">Từ chối</option><option value="HIGH_RISK">Rủi ro cao</option></select><button className={`icon-button ${refreshing ? "spinning" : ""}`} onClick={refresh} aria-label="Làm mới"><Icon name="refresh"/></button></div></div><div className="result-count">Hiển thị <b>{shown.length}</b> / {prs.length} pull request</div><PrTable prs={shown} onSelect={setSelected}/></section></>}
          {page === "reviewers" && <><div className="intro"><div><span className="eyebrow">WORKSPACE / NGƯỜI ĐÁNH GIÁ</span><h1>Người đánh giá</h1><p>Tổng hợp số lượt đánh giá và chất lượng PR theo từng người.</p></div></div><div className="reviewer-summary"><div className="panel"><span className="stat-icon blue"><Icon name="users"/></span><div><b>{reviewers.length}</b><span>Người đánh giá</span></div></div><div className="panel"><span className="stat-icon green"><Icon name="check"/></span><div><b>{reviewers.reduce((sum, [, value]) => sum + value.reviews, 0)}</b><span>Lượt đánh giá</span></div></div></div><section className="panel reviewer-panel"><div className="panel-head"><div><span className="eyebrow">ĐỘI NGŨ</span><h2>Hiệu suất đánh giá</h2></div><small>Sắp xếp theo số lượt</small></div>{reviewers.length ? reviewers.map(([name, value], index) => <div className="reviewer-row" key={name}><span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="reviewer-avatar">{name.charAt(0).toUpperCase()}</span><div className="reviewer-name"><b>{name}</b><small>Người đánh giá</small></div><div className="reviewer-number"><b>{value.reviews}</b><small>Lượt đánh giá</small></div><div className="reviewer-number"><b>{value.average_score}</b><small>Điểm TB / 100</small></div></div>) : <div className="empty"><Icon name="users" size={27}/><h3>Chưa có người đánh giá</h3><p>Dữ liệu sẽ hiển thị khi có PR được phân công.</p></div>}</section></>}
        </>}
      </div>
    </main>
    {selected && <PRDrawer pr={selected} onClose={() => setSelected(null)} onEdit={() => { setForm({ type: "edit", pr: selected }); setSelected(null); }} onChanged={changed}/>}
    {form && <PRForm pr={form.type === "edit" ? form.pr : null} onClose={() => setForm(null)} onSaved={saved}/>}
  </div>;
}

export default App;
