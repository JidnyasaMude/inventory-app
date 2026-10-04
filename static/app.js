const API = "/api";
const COLORS = ["#7c5cff", "#ff4fa3", "#22d3ee", "#f59e0b", "#22c55e", "#f97316", "#a78bfa", "#38bdf8"];
const $ = (sel) => document.querySelector(sel);

const state = {
  token: localStorage.getItem("token"),
  user: localStorage.getItem("user"),
  products: [],
  editingId: null,
  low: 10,
  timer: null,
};

const inr = (n, d = 2) =>
  "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });

// XSS defence: always escape user data before putting it in HTML
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function toast(message, type = "success") {
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = message;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function countUp(el, to, fmt) {
  const start = performance.now();
  const step = (t) => {
    const k = Math.min((t - start) / 700, 1);
    el.textContent = fmt(to * k);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---------- API helper (Fetch + JSON + JWT header) ----------
async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : null });
  let data = {};
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (res.status === 401 && state.token) {
    logout();
    toast("Session expired. Please login again.", "error");
    throw new Error("Unauthorized");
  }
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

// ---------- Auth ----------
function saveSession(d) {
  state.token = d.token;
  state.user = d.username;
  localStorage.setItem("token", d.token);
  localStorage.setItem("user", d.username);
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  $("#app-view").classList.add("hidden");
  $("#auth-view").classList.remove("hidden");
}

function enterApp() {
  $("#auth-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  $("#user-chip").textContent = "👤 " + state.user;
  loadAll();
}

document.querySelectorAll(".tab").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const isLogin = btn.dataset.tab === "login";
    $("#login-form").classList.toggle("hidden", !isLogin);
    $("#register-form").classList.toggle("hidden", isLogin);
    $("#auth-error").textContent = "";
  })
);

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#auth-error").textContent = "";
  const username = $("#login-user").value.trim();
  const password = $("#login-pass").value;
  if (!username || !password) return ($("#auth-error").textContent = "Enter username and password");
  try {
    saveSession(await api("/login", "POST", { username, password }));
    toast("Welcome back, " + state.user + "! 👋");
    enterApp();
  } catch (err) { $("#auth-error").textContent = err.message; }
});

$("#register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#auth-error").textContent = "";
  const username = $("#reg-user").value.trim();
  const password = $("#reg-pass").value;
  if (!/^[A-Za-z0-9_]{3,20}$/.test(username))
    return ($("#auth-error").textContent = "Username: 3-20 letters, digits or underscore");
  if (password.length < 6 || !/[A-Za-z]/.test(password) || !/\d/.test(password))
    return ($("#auth-error").textContent = "Password: 6+ characters with a letter and a digit");
  try {
    saveSession(await api("/register", "POST", { username, password }));
    toast("Account created! 🎉");
    enterApp();
  } catch (err) { $("#auth-error").textContent = err.message; }
});

$("#logout-btn").addEventListener("click", () => { logout(); toast("Logged out"); });

// ---------- Load & render ----------
async function loadAll() {
  try {
    const q = encodeURIComponent($("#search").value.trim());
    const cat = encodeURIComponent($("#cat-filter").value);
    const [stats, products] = await Promise.all([
      api("/stats"),
      api(`/products?q=${q}&category=${cat}`),
    ]);
    state.products = products;
    state.low = stats.low_threshold;
    renderStats(stats);
    renderCategories(stats.categories);
    renderTable(products);
  } catch (err) { if (err.message !== "Unauthorized") toast(err.message, "error"); }
}

function renderStats(s) {
  countUp($("#stat-total"), s.total_products, (v) => Math.round(v));
  countUp($("#stat-units"), s.total_units, (v) => Math.round(v).toLocaleString("en-IN"));
  countUp($("#stat-value"), s.total_value, (v) => inr(v, 0));
  countUp($("#stat-low"), s.low_stock_count, (v) => Math.round(v));

  $("#alerts").innerHTML = s.low_stock.length
    ? s.low_stock.map((p) => `
        <div class="alert-item">
          <div class="alert-top"><span>${esc(p.name)} <small>(${esc(p.product_id)})</small></span>
          <b>${p.quantity === 0 ? "Out of stock" : p.quantity + " left"}</b></div>
          <div class="bar"><i style="width:${Math.max(4, Math.min(100, (p.quantity / s.low_threshold) * 100))}%"></i></div>
        </div>`).join("")
    : `<p class="all-good">✅ All products are well stocked.</p>`;

  // donut chart made with CSS conic-gradient
  const total = s.categories.reduce((a, c) => a + c.units, 0);
  if (total > 0) {
    let acc = 0;
    const parts = s.categories.map((c, i) => {
      const from = (acc / total) * 100;
      acc += c.units;
      return `${COLORS[i % COLORS.length]} ${from}% ${(acc / total) * 100}%`;
    });
    $("#donut").style.background = `conic-gradient(${parts.join(",")})`;
  } else {
    $("#donut").style.background = "#333";
  }
  $("#legend").innerHTML = s.categories.map((c, i) =>
    `<li><i style="background:${COLORS[i % COLORS.length]}"></i>${esc(c.category)} — <b>${c.units}</b></li>`).join("");
}

function renderCategories(cats) {
  const sel = $("#cat-filter");
  const current = sel.value;
  sel.innerHTML = `<option value="">All categories</option>` +
    cats.map((c) => `<option value="${esc(c.category)}">${esc(c.category)}</option>`).join("");
  sel.value = current;
}

function renderTable(list) {
  $("#empty").classList.toggle("hidden", list.length > 0);
  $("#tbody").innerHTML = list.map((p) => {
    const st = p.quantity === 0 ? ["Out of stock", "out"]
      : p.quantity <= state.low ? ["Low stock", "low"] : ["In stock", "ok"];
    return `<tr>
      <td><span class="code">${esc(p.product_id)}</span></td>
      <td class="name">${esc(p.name)}</td>
      <td><span class="cat">${esc(p.category)}</span></td>
      <td><div class="qty">
        <button class="icon-btn" data-action="dec" data-id="${p.id}">−</button>
        <b>${p.quantity}</b>
        <button class="icon-btn" data-action="inc" data-id="${p.id}">+</button></div></td>
      <td>${inr(p.price)}</td>
      <td>${inr(p.price * p.quantity)}</td>
      <td><span class="pill ${st[1]}">${st[0]}</span></td>
      <td class="actions">
        <button class="icon-btn" data-action="edit" data-id="${p.id}" title="Edit">✏️</button>
        <button class="icon-btn danger" data-action="delete" data-id="${p.id}" title="Delete">🗑️</button></td>
    </tr>`;
  }).join("");
}

// ---------- Table actions (event delegation) ----------
$("#tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const action = btn.dataset.action;
  try {
    if (action === "inc" || action === "dec") {
      await api(`/products/${id}/stock`, "PUT", { change: action === "inc" ? 1 : -1 });
      loadAll();
    } else if (action === "edit") {
      openModal(state.products.find((p) => p.id === id));
    } else if (action === "delete") {
      const p = state.products.find((x) => x.id === id);
      if (confirm(`Delete "${p.name}"? This cannot be undone.`)) {
        await api(`/products/${id}`, "DELETE");
        toast("Product deleted 🗑️");
        loadAll();
      }
    }
  } catch (err) { if (err.message !== "Unauthorized") toast(err.message, "error"); }
});

// ---------- Search & filter (no page reload) ----------
$("#search").addEventListener("input", () => {
  clearTimeout(state.timer);
  state.timer = setTimeout(loadAll, 300);
});
$("#cat-filter").addEventListener("change", loadAll);

// ---------- Modal (add / edit) ----------
function openModal(product = null) {
  state.editingId = product ? product.id : null;
  $("#modal-title").textContent = product ? "Edit Product" : "Add Product";
  $("#f-pid").value = product ? product.product_id : "";
  $("#f-pid").readOnly = !!product;
  $("#f-name").value = product ? product.name : "";
  $("#f-cat").value = product ? product.category : "";
  $("#f-qty").value = product ? product.quantity : "";
  $("#f-price").value = product ? product.price : "";
  $("#form-error").textContent = "";
  $("#modal").classList.remove("hidden");
  (product ? $("#f-name") : $("#f-pid")).focus();
}
function closeModal() { $("#modal").classList.add("hidden"); }

$("#add-btn").addEventListener("click", () => openModal());
$("#cancel-btn").addEventListener("click", closeModal);
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

$("#product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    product_id: $("#f-pid").value.trim(),
    name: $("#f-name").value.trim(),
    category: $("#f-cat").value.trim(),
    quantity: $("#f-qty").value,
    price: $("#f-price").value,
  };
  // client-side validation (server validates again)
  if (!/^[A-Za-z0-9-]{2,20}$/.test(body.product_id)) return ($("#form-error").textContent = "Product ID: 2-20 letters, digits or hyphens");
  if (body.name.length < 2) return ($("#form-error").textContent = "Enter a valid product name");
  if (body.category.length < 2) return ($("#form-error").textContent = "Enter a category");
  if (body.quantity === "" || !Number.isInteger(Number(body.quantity)) || Number(body.quantity) < 0)
    return ($("#form-error").textContent = "Quantity must be a whole number, 0 or more");
  if (body.price === "" || Number(body.price) < 0)
    return ($("#form-error").textContent = "Price must be 0 or more");
  try {
    if (state.editingId) {
      await api(`/products/${state.editingId}`, "PUT", body);
      toast("Product updated ✅");
    } else {
      await api("/products", "POST", body);
      toast("Product added 🎉");
    }
    closeModal();
    loadAll();
  } catch (err) { $("#form-error").textContent = err.message; }
});

// ---------- Start ----------
if (state.token) enterApp();