import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8002/pull-requests";
const blank = { title: "", author: "", description: "", files: "", added: 0, deleted: 0, tests: false, lint: false };

function errorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join(" ");
  return "Không thực hiện được thao tác. Vui lòng thử lại.";
}

export function PRForm({ pr, onClose, onSaved }) {
  const [values, setValues] = useState(blank);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    setValues(pr ? {
      title: pr.title, author: pr.author, description: pr.description || "",
      files: (pr.danh_sach_file || []).join(", "), added: pr.so_dong_them,
      deleted: pr.so_dong_xoa, tests: !!pr.quality_checks?.tests_passed,
      lint: !!pr.quality_checks?.lint_passed,
    } : blank);
  }, [pr]);
  const set = (key, value) => setValues(current => ({ ...current, [key]: value }));
  async function submit(event) {
    event.preventDefault();
    setError("");
    const files = values.files.split(",").map(file => file.trim()).filter(Boolean);
    if (!files.length) { setError("Cần nhập ít nhất một file thay đổi."); return; }
    const body = {
      title: values.title.trim(), author: values.author.trim(), description: values.description,
      danh_sach_file: files, so_dong_them: Number(values.added), so_dong_xoa: Number(values.deleted),
      tests_passed: values.tests, lint_passed: values.lint,
    };
    setSaving(true);
    try {
      const response = pr ? await axios.put(`${API}/${pr.id}`, body) : await axios.post(API, body);
      await onSaved(response.data);
    } catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  return <div className="form-backdrop" onMouseDown={onClose}><section className="pr-form-modal" role="dialog" aria-modal="true" aria-label={pr ? "Sửa pull request" : "Tạo pull request"} onMouseDown={event => event.stopPropagation()}>
    <div className="modal-header"><div><span className="eyebrow">QUẢN LÝ PULL REQUEST</span><h2>{pr ? `Chỉnh sửa ${pr.id}` : "Tạo pull request"}</h2><p>{pr ? "Sau khi sửa, PR cần được phê duyệt lại." : "Reviewer và điểm sẽ được tính tự động khi lưu."}</p></div><button className="icon-button" onClick={onClose} aria-label="Đóng">×</button></div>
    <form onSubmit={submit}>
      <div className="form-grid"><label>Tiêu đề <input required value={values.title} onChange={event => set("title", event.target.value)} placeholder="Ví dụ: Cập nhật giao diện quản lý"/></label><label>Tác giả <input required disabled={!!pr} value={values.author} onChange={event => set("author", event.target.value)} placeholder="Tên người tạo PR"/></label></div>
      <label>Mô tả <textarea rows="3" value={values.description} onChange={event => set("description", event.target.value)} placeholder="Mô tả thay đổi..."/></label>
      <label>File thay đổi <textarea rows="2" required value={values.files} onChange={event => set("files", event.target.value)} placeholder="src/app.py, tests/test_app.py"/><small>Ngăn cách các đường dẫn bằng dấu phẩy.</small></label>
      <div className="form-grid"><label>Số dòng thêm <input type="number" min="0" required value={values.added} onChange={event => set("added", event.target.value)}/></label><label>Số dòng xóa <input type="number" min="0" required value={values.deleted} onChange={event => set("deleted", event.target.value)}/></label></div>
      <div className="form-checks"><label><input type="checkbox" checked={values.tests} onChange={event => set("tests", event.target.checked)}/> Tests đạt</label><label><input type="checkbox" checked={values.lint} onChange={event => set("lint", event.target.checked)}/> Lint đạt</label></div>
      {error && <p className="action-error" role="alert">{error}</p>}
      <div className="form-footer"><button type="button" className="secondary" onClick={onClose}>Hủy</button><button type="submit" className="primary" disabled={saving}>{saving ? "Đang lưu..." : pr ? "Lưu thay đổi" : "Tạo PR"}</button></div>
    </form>
  </section></div>;
}

export function PRDrawer({ pr, onClose, onEdit, onChanged }) {
  const [comment, setComment] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const merged = pr.status === "MERGED";
  const unresolved = (pr.comments || []).some(item => !item.resolved);
  async function action(method, path, body) {
    setBusy(true); setError("");
    try {
      const response = await axios({ method, url: `${API}/${pr.id}${path}`, data: body });
      await onChanged(response.data);
      return true;
    } catch (err) { setError(errorMessage(err)); return false; }
    finally { setBusy(false); }
  }
  async function addComment(event) {
    event.preventDefault();
    if (await action("post", "/comments", { content: comment, severity })) setComment("");
  }
  return <div className="drawer-backdrop" onMouseDown={onClose}><aside className="drawer admin-drawer" role="dialog" aria-modal="true" aria-label={`Chi tiết ${pr.id}`} onMouseDown={event => event.stopPropagation()}>
    <div className="drawer-head"><span className="eyebrow">QUẢN LÝ PULL REQUEST</span><button className="icon-button" onClick={onClose} aria-label="Đóng chi tiết">×</button></div>
    <span className="pr-id">{pr.id}</span><h2>{pr.title}</h2><div className="drawer-badges"><span className="drawer-status">{pr.status}</span><span className="drawer-risk">{pr.risk_level} RISK</span></div>
    {error && <p className="action-error" role="alert">{error}</p>}
    <div className="drawer-section"><h3>Thông tin chung</h3><div><span>Tác giả</span><b>{pr.author}</b></div><div><span>Người đánh giá</span><b>{pr.reviewer || "Chưa phân công"}</b></div><div><span>Điểm chất lượng</span><b>{pr.quality_score}/100</b></div><div><span>Điểm rủi ro</span><b>{pr.risk_score}</b></div><div><span>Dòng thêm / xóa</span><b>+{pr.so_dong_them} / -{pr.so_dong_xoa}</b></div></div>
    {pr.description && <div className="drawer-section"><h3>Mô tả</h3><p className="detail-description">{pr.description}</p></div>}
    <div className="drawer-section"><h3>File thay đổi</h3><div className="file-list">{(pr.danh_sach_file || []).map(file => <code key={file}>{file}</code>)}</div></div>
    <div className="drawer-section"><h3>Kiểm tra chất lượng</h3>{[["Tests", pr.quality_checks?.tests_passed], ["Lint", pr.quality_checks?.lint_passed]].map(([name, pass]) => <div key={name}><span>{name}</span><b className={pass ? "pass" : "fail"}>{pass ? "Đạt" : "Chưa đạt"}</b></div>)}</div>
    {!merged && <div className="drawer-section"><h3>Thao tác quản trị</h3><div className="admin-actions"><button disabled={busy} onClick={onEdit}>Sửa thông tin</button><button disabled={busy} onClick={() => action("post", "/reassign")}>Phân công lại reviewer</button><button disabled={busy} onClick={() => action("post", "/request-changes")}>Yêu cầu chỉnh sửa</button><button disabled={busy || !pr.reviewer || unresolved} onClick={() => action("post", "/approve")}>Phê duyệt</button><button className="merge-action" disabled={busy || !pr.approved || unresolved} onClick={() => { if (window.confirm(`Gộp ${pr.id}? Thao tác này không thể chỉnh sửa lại PR.`)) action("post", "/merge"); }}>Gộp PR</button></div>{unresolved && <p className="action-hint">Cần xử lý tất cả nhận xét trước khi phê duyệt hoặc gộp.</p>}</div>}
    <div className="drawer-section"><h3>Nhận xét ({(pr.comments || []).length})</h3><div className="comment-list">{(pr.comments || []).length ? pr.comments.map(item => <div className="comment-item" key={item.id}><div><b>#{item.id} · {item.severity}</b><span className={item.resolved ? "resolved" : "unresolved"}>{item.resolved ? "Đã xử lý" : "Chưa xử lý"}</span></div><p>{item.content}</p>{!item.resolved && !merged && <button disabled={busy} onClick={() => action("patch", `/comments/${item.id}/resolve`)}>Đánh dấu đã xử lý</button>}</div>) : <p className="action-hint">Chưa có nhận xét.</p>}</div>
      {!merged && <form className="comment-form" onSubmit={addComment}><textarea required rows="3" value={comment} onChange={event => setComment(event.target.value)} placeholder="Viết nhận xét đánh giá..."/><div><select value={severity} onChange={event => setSeverity(event.target.value)} aria-label="Mức độ nhận xét"><option value="LOW">Thấp</option><option value="MEDIUM">Trung bình</option><option value="HIGH">Cao</option></select><button className="primary" type="submit" disabled={busy || !comment.trim()}>Thêm nhận xét</button></div></form>}
    </div>
  </aside></div>;
}
