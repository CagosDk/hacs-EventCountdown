const TYPE_LABELS = {
  fødselsdag: "Birthday 🎂",
  bryllup: "Anniversary 💍",
  begivenhed: "Event 📅",
};

const MONTH_NAMES = [
  "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

class EventCountdownPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._loaded = false;
    this._editIndex = null;
    this._hasChanges = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded) {
      this._loaded = true;
      this._init();
    }
  }

  set narrow(val) { this._narrow = val; }
  set panel(val) { this._panel = val; }

  async _init() {
    this._setHtml(`<div class="loading"><div class="spinner"></div><span>Loading…</span></div>`);
    try {
      this._config = await this._hass.callWS({ type: "event_countdown/get_config" });
      this._render();
    } catch (err) {
      this._setHtml(`<div class="error">Could not load configuration: ${err.message}</div>`);
    }
  }

  _setHtml(inner) {
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${inner}`;
  }

  // ── Full render ────────────────────────────────────────────────────────────

  _render() {
    if (!this._config) return;
    const { events = [], max_sensors = 4 } = this._config;

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <div class="panel">

        <div class="toolbar">
          <span class="toolbar-title">Event Countdown</span>
          <button class="save-btn ${this._hasChanges ? "dirty" : ""}" id="save-btn">
            ${this._hasChanges ? "● Save changes" : "Saved"}
          </button>
        </div>

        <div class="content">

          <!-- Sensor count -->
          <div class="card">
            <div class="card-header">Number of sensors</div>
            <div class="card-content">
              <div class="number-control">
                <button class="num-btn" id="dec-btn" ${max_sensors <= 1 ? "disabled" : ""}>−</button>
                <span class="num-value" id="sensor-count">${max_sensors}</span>
                <button class="num-btn" id="inc-btn" ${max_sensors >= 20 ? "disabled" : ""}>+</button>
              </div>
              <p class="hint" id="sensor-hint">
                Creates <code>sensor.event_countdown_event_1</code>
                ${max_sensors > 1 ? `… <code>event_${max_sensors}</code>` : ""}
              </p>
            </div>
          </div>

          <!-- Events -->
          <div class="card">
            <div class="card-header">
              <span>Events <span class="badge">${events.length}</span></span>
              <button class="add-btn" id="add-btn">+ Add event</button>
            </div>
            <div id="event-list">
              ${events.length === 0
                ? `<p class="empty">No events yet — click <strong>+ Add event</strong> to get started.</p>`
                : events.map((e, i) => this._rowHtml(e, i)).join("")}
            </div>
          </div>

        </div><!-- /content -->

        <!-- Modal overlay -->
        <div class="overlay" id="overlay" hidden>
          <div class="modal" role="dialog">
            <div class="modal-header">
              <span id="modal-title">Add event</span>
              <button class="close-btn" id="modal-close" aria-label="Close">✕</button>
            </div>
            <div class="modal-body" id="modal-body">
              ${this._formHtml()}
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" id="modal-cancel">Cancel</button>
              <button class="btn-primary" id="modal-confirm">Save event</button>
            </div>
          </div>
        </div>

        <div class="toast" id="toast" hidden></div>
      </div>
    `;

    this._bind();
  }

  // ── Event row HTML ─────────────────────────────────────────────────────────

  _rowHtml(ev, i) {
    const typeLabel = TYPE_LABELS[ev.type] || "📅 " + (ev.type || "event");
    const recurring = ev.recurring !== undefined ? ev.recurring : (ev.type !== "begivenhed");
    const tags = [
      `${ev.day} ${MONTH_NAMES[ev.month] || ev.month}${ev.year ? ` ${ev.year}` : ""}`,
      typeLabel,
      recurring ? "↻ repeats" : "once",
      ev.soon !== undefined ? `soon: ${ev.soon}d` : null,
    ].filter(Boolean);

    return `
      <div class="event-row ${ev.disabled ? "row-disabled" : ""}">
        <div class="row-info">
          <div class="row-name">${this._esc(ev.name)}${ev.disabled ? ' <span class="chip chip-off">disabled</span>' : ""}</div>
          <div class="row-tags">${tags.map(t => `<span class="chip">${t}</span>`).join("")}</div>
        </div>
        <div class="row-actions">
          <button class="icon-btn" data-action="edit" data-i="${i}" title="Edit">✏️</button>
          <button class="icon-btn" data-action="delete" data-i="${i}" title="Delete">🗑️</button>
        </div>
      </div>`;
  }

  // ── Form HTML ──────────────────────────────────────────────────────────────

  _formHtml(ev = {}) {
    const recurring = ev.recurring !== undefined ? ev.recurring : (ev.type !== "begivenhed");
    const types = ["fødselsdag", "bryllup", "begivenhed"];
    return `
      <div class="form-field">
        <label>Name <span class="req">*</span></label>
        <input id="f-name" type="text" value="${this._esc(ev.name || "")}" placeholder="e.g. Frederik's birthday" />
      </div>

      <div class="form-row-3">
        <div class="form-field">
          <label>Day <span class="req">*</span></label>
          <input id="f-day" type="number" value="${ev.day || ""}" min="1" max="31" />
        </div>
        <div class="form-field">
          <label>Month <span class="req">*</span></label>
          <input id="f-month" type="number" value="${ev.month || ""}" min="1" max="12" />
        </div>
        <div class="form-field">
          <label>Year</label>
          <input id="f-year" type="number" value="${ev.year || ""}" placeholder="e.g. 1990" />
        </div>
      </div>

      <div class="form-field">
        <label>Type</label>
        <select id="f-type">
          ${types.map(t => `<option value="${t}" ${(ev.type || "fødselsdag") === t ? "selected" : ""}>${TYPE_LABELS[t]}</option>`).join("")}
        </select>
      </div>

      <div class="form-field">
        <label>Days before marked as "soon" (default 30)</label>
        <input id="f-soon" type="number" value="${ev.soon !== undefined ? ev.soon : 30}" min="1" max="365" />
      </div>

      <div class="form-field">
        <label>Picture path <span class="hint-inline">(optional)</span></label>
        <input id="f-picture" type="text" value="${this._esc(ev.picture || "")}" placeholder="/local/pic/name.jpg" />
      </div>

      <div class="form-checks">
        <label class="check-label">
          <input id="f-recurring" type="checkbox" ${recurring ? "checked" : ""} />
          <span>Repeats every year</span>
        </label>
        <label class="check-label">
          <input id="f-disabled" type="checkbox" ${ev.disabled ? "checked" : ""} />
          <span>Disabled (skip this event)</span>
        </label>
      </div>
    `;
  }

  // ── Bind listeners ─────────────────────────────────────────────────────────

  _bind() {
    const $ = id => this.shadowRoot.getElementById(id);

    // Save
    $("save-btn").addEventListener("click", () => this._save());

    // +/- sensor count
    $("dec-btn").addEventListener("click", () => this._adjustSensors(-1));
    $("inc-btn").addEventListener("click", () => this._adjustSensors(1));

    // Add event
    $("add-btn").addEventListener("click", () => this._openModal());

    // Edit / delete via delegation
    $("event-list").addEventListener("click", e => {
      const btn = e.target.closest("[data-action]");
      if (!btn) return;
      const i = parseInt(btn.dataset.i);
      if (btn.dataset.action === "edit") this._openModal(i);
      if (btn.dataset.action === "delete") this._deleteEvent(i);
    });

    // Modal
    $("modal-close").addEventListener("click", () => this._closeModal());
    $("modal-cancel").addEventListener("click", () => this._closeModal());
    $("modal-confirm").addEventListener("click", () => this._saveEvent());
    $("overlay").addEventListener("click", e => {
      if (e.target === $("overlay")) this._closeModal();
    });
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  _adjustSensors(delta) {
    const newVal = Math.max(1, Math.min(20, this._config.max_sensors + delta));
    this._config.max_sensors = newVal;
    this._hasChanges = true;
    this._render();
  }

  _openModal(editIndex = null) {
    this._editIndex = editIndex;
    const root = this.shadowRoot;
    const ev = editIndex !== null ? this._config.events[editIndex] : {};
    root.getElementById("modal-title").textContent = editIndex !== null ? "Edit event" : "Add event";
    root.getElementById("modal-body").innerHTML = this._formHtml(ev);
    root.getElementById("overlay").removeAttribute("hidden");
    root.getElementById("f-name").focus();
  }

  _closeModal() {
    this.shadowRoot.getElementById("overlay").setAttribute("hidden", "");
    this._editIndex = null;
  }

  _saveEvent() {
    const $ = id => this.shadowRoot.getElementById(id);
    const name = $("f-name").value.trim();
    const day = parseInt($("f-day").value);
    const month = parseInt($("f-month").value);
    const yearStr = $("f-year").value.trim();
    const type = $("f-type").value;
    const soon = parseInt($("f-soon").value) || 30;
    const picture = $("f-picture").value.trim();
    const recurring = $("f-recurring").checked;
    const disabled = $("f-disabled").checked;

    if (!name || !day || !month || day < 1 || day > 31 || month < 1 || month > 12) {
      this._showError("Name, day (1–31) and month (1–12) are required.");
      return;
    }

    const ev = { name, day, month, type, soon, recurring };
    if (yearStr) ev.year = parseInt(yearStr);
    if (picture) ev.picture = picture;
    if (disabled) ev.disabled = true;

    if (this._editIndex !== null) {
      this._config.events[this._editIndex] = ev;
    } else {
      this._config.events.push(ev);
    }

    this._hasChanges = true;
    this._closeModal();
    this._render();
  }

  _deleteEvent(index) {
    this._config.events.splice(index, 1);
    this._hasChanges = true;
    this._render();
  }

  async _save() {
    const btn = this.shadowRoot.getElementById("save-btn");
    btn.disabled = true;
    btn.textContent = "Saving…";
    try {
      await this._hass.callWS({
        type: "event_countdown/save_config",
        entry_id: this._config.entry_id,
        events: this._config.events,
        max_sensors: this._config.max_sensors,
      });
      this._hasChanges = false;
      this._showToast("Configuration saved ✓");
      this._render();
    } catch (err) {
      this._showToast("Error: " + err.message, true);
      btn.disabled = false;
      btn.textContent = "● Save changes";
    }
  }

  _showToast(msg, isError = false) {
    const t = this.shadowRoot.getElementById("toast");
    t.textContent = msg;
    t.className = "toast" + (isError ? " toast-error" : "");
    t.removeAttribute("hidden");
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => t.setAttribute("hidden", ""), 3000);
  }

  _showError(msg) {
    const t = this.shadowRoot.getElementById("toast");
    if (t) {
      t.textContent = msg;
      t.className = "toast toast-error";
      t.removeAttribute("hidden");
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => t.setAttribute("hidden", ""), 4000);
    }
  }

  _esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Styles ─────────────────────────────────────────────────────────────────

  _styles() {
    return `
      :host { display: block; background: var(--primary-background-color); min-height: 100%; }

      /* ── Toolbar ── */
      .toolbar {
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, #fff);
        display: flex; align-items: center;
        padding: 0 16px; height: 56px; gap: 12px;
      }
      .toolbar-title { flex: 1; font-size: 20px; font-weight: 400; }
      .save-btn {
        border: none; border-radius: 4px; padding: 8px 16px;
        cursor: pointer; font-size: 14px; font-weight: 500;
        background: rgba(255,255,255,0.15); color: inherit;
        transition: background 0.2s;
      }
      .save-btn:hover { background: rgba(255,255,255,0.25); }
      .save-btn.dirty { background: #f57c00; color: #fff; }
      .save-btn.dirty:hover { background: #ef6c00; }

      /* ── Layout ── */
      .content { padding: 16px; max-width: 760px; margin: 0 auto; }

      /* ── Card ── */
      .card {
        background: var(--card-background-color, #fff);
        border-radius: 8px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,.12));
        margin-bottom: 16px; overflow: hidden;
      }
      .card-header {
        padding: 14px 16px; font-size: 15px; font-weight: 500;
        color: var(--primary-text-color);
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        display: flex; align-items: center; justify-content: space-between;
      }
      .card-content { padding: 16px; }

      /* ── Number control ── */
      .number-control {
        display: flex; align-items: center; gap: 20px; margin-bottom: 8px;
      }
      .num-btn {
        width: 40px; height: 40px; border-radius: 50%;
        border: 2px solid var(--primary-color, #03a9f4);
        background: transparent; color: var(--primary-color, #03a9f4);
        font-size: 22px; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        transition: background 0.15s, color 0.15s;
      }
      .num-btn:hover:not([disabled]) { background: var(--primary-color, #03a9f4); color: #fff; }
      .num-btn[disabled] { opacity: 0.3; cursor: default; }
      .num-value { font-size: 28px; font-weight: 500; min-width: 36px; text-align: center; }
      .hint { color: var(--secondary-text-color); font-size: 13px; margin: 0; }
      code { background: var(--secondary-background-color); padding: 1px 4px; border-radius: 3px; font-size: 12px; }

      /* ── Add button ── */
      .add-btn {
        background: var(--primary-color, #03a9f4); color: #fff;
        border: none; border-radius: 4px; padding: 6px 14px;
        cursor: pointer; font-size: 13px; font-weight: 500;
      }
      .add-btn:hover { opacity: 0.9; }

      /* ── Badge ── */
      .badge {
        display: inline-flex; align-items: center; justify-content: center;
        background: var(--secondary-background-color);
        color: var(--secondary-text-color);
        border-radius: 10px; padding: 0 7px; font-size: 12px;
        font-weight: 400; margin-left: 6px;
      }

      /* ── Event rows ── */
      .event-row {
        display: flex; align-items: center; gap: 12px;
        padding: 12px 16px;
        border-bottom: 1px solid var(--divider-color, #e8e8e8);
      }
      .event-row:last-child { border-bottom: none; }
      .event-row.row-disabled { opacity: 0.45; }
      .row-info { flex: 1; min-width: 0; }
      .row-name { font-weight: 500; color: var(--primary-text-color); margin-bottom: 4px; }
      .row-tags { display: flex; flex-wrap: wrap; gap: 4px; }
      .chip {
        font-size: 11px; padding: 2px 7px; border-radius: 10px;
        background: var(--secondary-background-color);
        color: var(--secondary-text-color);
      }
      .chip-off { background: #ffcdd2; color: #b71c1c; }
      .row-actions { display: flex; gap: 4px; flex-shrink: 0; }
      .icon-btn {
        background: none; border: none; cursor: pointer;
        font-size: 16px; padding: 5px 7px; border-radius: 4px; line-height: 1;
      }
      .icon-btn:hover { background: var(--secondary-background-color); }
      .empty { padding: 24px 16px; color: var(--secondary-text-color); text-align: center; }

      /* ── Modal overlay ── */
      .overlay {
        position: fixed; inset: 0; background: rgba(0,0,0,.5);
        z-index: 9999; display: flex; align-items: center; justify-content: center;
        padding: 16px;
      }
      .overlay[hidden] { display: none; }
      .modal {
        background: var(--card-background-color, #fff);
        border-radius: 10px; width: 100%; max-width: 460px;
        max-height: 90vh; overflow-y: auto;
        box-shadow: 0 12px 40px rgba(0,0,0,.35);
        display: flex; flex-direction: column;
      }
      .modal-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 16px 14px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        font-size: 17px; font-weight: 500;
      }
      .close-btn {
        background: none; border: none; cursor: pointer;
        font-size: 18px; color: var(--secondary-text-color); padding: 4px 6px;
        border-radius: 4px; line-height: 1;
      }
      .close-btn:hover { background: var(--secondary-background-color); }
      .modal-body { padding: 16px; flex: 1; }
      .modal-footer {
        display: flex; gap: 8px; justify-content: flex-end;
        padding: 12px 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }

      /* ── Form ── */
      .form-field { margin-bottom: 14px; }
      .form-field label {
        display: block; font-size: 13px;
        color: var(--secondary-text-color); margin-bottom: 5px;
      }
      .req { color: var(--error-color, #c62828); }
      .hint-inline { font-weight: 400; opacity: 0.7; }
      .form-field input,
      .form-field select {
        width: 100%; box-sizing: border-box;
        padding: 8px 10px; border-radius: 4px;
        border: 1px solid var(--divider-color, #ccc);
        background: var(--primary-background-color);
        color: var(--primary-text-color); font-size: 14px;
      }
      .form-field input:focus,
      .form-field select:focus {
        outline: none;
        border-color: var(--primary-color, #03a9f4);
        box-shadow: 0 0 0 2px rgba(3,169,244,.2);
      }
      .form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 14px; }
      .form-row-3 .form-field { margin-bottom: 0; }
      .form-checks { display: flex; flex-direction: column; gap: 10px; }
      .check-label {
        display: flex; align-items: center; gap: 10px;
        cursor: pointer; font-size: 14px; color: var(--primary-text-color);
      }
      .check-label input[type=checkbox] {
        width: 16px; height: 16px; cursor: pointer;
        accent-color: var(--primary-color, #03a9f4);
      }

      /* ── Buttons ── */
      .btn-secondary {
        background: none; border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px; padding: 8px 18px; cursor: pointer;
        font-size: 14px; color: var(--primary-text-color);
      }
      .btn-primary {
        background: var(--primary-color, #03a9f4); border: none;
        border-radius: 4px; padding: 8px 18px; cursor: pointer;
        font-size: 14px; font-weight: 500; color: #fff;
      }
      .btn-primary:hover { opacity: 0.9; }

      /* ── Toast ── */
      .toast {
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        background: #323232; color: #fff;
        padding: 11px 22px; border-radius: 5px; font-size: 14px;
        z-index: 10000; box-shadow: 0 4px 14px rgba(0,0,0,.3);
        white-space: nowrap;
      }
      .toast[hidden] { display: none; }
      .toast-error { background: #c62828; }

      /* ── Loading ── */
      .loading {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; height: 200px; gap: 16px;
        color: var(--secondary-text-color);
      }
      .spinner {
        width: 32px; height: 32px; border: 3px solid var(--divider-color);
        border-top-color: var(--primary-color, #03a9f4);
        border-radius: 50%; animation: spin 0.8s linear infinite;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      .error { padding: 32px; text-align: center; color: var(--error-color, #c62828); }
    `;
  }
}

customElements.define("event-countdown-panel", EventCountdownPanel);
