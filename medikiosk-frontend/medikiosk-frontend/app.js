/* ============================================================
   MediKiosk frontend — plain JS, no build step.
   Talks to the FastAPI backend at API_BASE (see config.js).
   Narration uses the browser's real built-in Web Speech API
   (window.speechSynthesis) — not mocked, works offline, but
   voice availability/quality depends on the device's installed
   voices (Hindi voices aren't present on every OS by default).
   ============================================================ */

const COPY = {
  en: {
    welcome_title: "Welcome to MediKiosk",
    welcome_lead: "A quick health check-in before you see the doctor.",
    start: "Start check-in",
    phone_title: "Enter your phone number",
    phone_lead: "We'll use this to find or create your health record.",
    phone_placeholder: "10-digit mobile number",
    send_code: "Send code",
    otp_title: "Enter the code",
    otp_lead: "We sent a 6-digit code to your phone.",
    otp_demo_hint: "Demo mode — no real SMS is sent, so we've filled in the code for you:",
    verify: "Verify",
    back: "Back",
    home_greeting: "You're checked in.",
    home_lead: "Next, we'll take a few quick measurements.",
    begin_vitals: "Begin health check",
    docs_title: "Any old records?",
    docs_lead: "If you have an old prescription or lab report, show it to the camera. This helps the doctor know your history.",
    docs_upload: "Take a photo",
    docs_skip: "I don't have any",
    docs_scanning: "Reading your document…",
    docs_found_title: "Found in your document",
    docs_conditions: "Conditions",
    docs_medications: "Medications",
    docs_none_found: "Nothing specific detected — that's okay.",
    docs_continue: "Continue",
    vitals_title: "Your vitals",
    vitals_lead: "Enter your latest readings. Ask staff for help with the devices.",
    spo2: "Oxygen level (SpO2 %)",
    hr: "Pulse (beats/min)",
    sbp: "Blood pressure — top number",
    dbp: "Blood pressure — bottom number",
    temp: "Temperature (°C)",
    glucose: "Blood sugar (mg/dL)",
    glucose_context: "When was this measured?",
    fasting: "Fasting",
    random: "Random / after eating",
    submit_vitals: "Check my results",
    checking: "Checking your vitals…",
    result_title: "Your result",
    action_label: "What to do next",
    see_summary: "Continue to summary",
    summary_title: "Visit summary",
    summary_lead: "This has been saved to your health record.",
    finish: "Finish",
    risk: { low: "All normal", moderate: "Worth a review", high: "Please see a doctor soon", critical: "Urgent — see a doctor now" },
  },
  hi: {
    welcome_title: "मेडीकियोस्क में आपका स्वागत है",
    welcome_lead: "डॉक्टर से मिलने से पहले एक त्वरित स्वास्थ्य जांच।",
    start: "जांच शुरू करें",
    phone_title: "अपना फोन नंबर दर्ज करें",
    phone_lead: "हम इसका उपयोग आपका स्वास्थ्य रिकॉर्ड खोजने के लिए करेंगे।",
    phone_placeholder: "10 अंकों का मोबाइल नंबर",
    send_code: "कोड भेजें",
    otp_title: "कोड दर्ज करें",
    otp_lead: "हमने आपके फोन पर 6 अंकों का कोड भेजा है।",
    otp_demo_hint: "डेमो मोड — कोई वास्तविक SMS नहीं भेजा गया, इसलिए हमने कोड भर दिया है:",
    verify: "सत्यापित करें",
    back: "वापस",
    home_greeting: "आप चेक-इन कर चुके हैं।",
    home_lead: "अब हम कुछ त्वरित माप लेंगे।",
    begin_vitals: "स्वास्थ्य जांच शुरू करें",
    docs_title: "कोई पुराना रिकॉर्ड?",
    docs_lead: "यदि आपके पास पुराना प्रिस्क्रिप्शन या लैब रिपोर्ट है, तो कैमरे को दिखाएं। इससे डॉक्टर को आपका इतिहास पता चलेगा।",
    docs_upload: "फोटो लें",
    docs_skip: "मेरे पास नहीं है",
    docs_scanning: "आपका दस्तावेज़ पढ़ा जा रहा है…",
    docs_found_title: "आपके दस्तावेज़ में मिला",
    docs_conditions: "स्थितियां",
    docs_medications: "दवाएं",
    docs_none_found: "कुछ खास नहीं मिला — कोई बात नहीं।",
    docs_continue: "जारी रखें",
    vitals_title: "आपके वाइटल्स",
    vitals_lead: "अपनी नवीनतम रीडिंग दर्ज करें। मशीनों के लिए स्टाफ से मदद लें।",
    spo2: "ऑक्सीजन स्तर (SpO2 %)",
    hr: "नब्ज़ (बीट्स/मिनट)",
    sbp: "ब्लड प्रेशर — ऊपरी संख्या",
    dbp: "ब्लड प्रेशर — निचली संख्या",
    temp: "तापमान (°C)",
    glucose: "ब्लड शुगर (mg/dL)",
    glucose_context: "यह कब मापा गया था?",
    fasting: "खाली पेट",
    random: "खाने के बाद",
    submit_vitals: "मेरे परिणाम जांचें",
    checking: "आपके वाइटल्स जांचे जा रहे हैं…",
    result_title: "आपका परिणाम",
    action_label: "आगे क्या करें",
    see_summary: "सारांश पर जाएं",
    summary_title: "विज़िट सारांश",
    summary_lead: "यह आपके स्वास्थ्य रिकॉर्ड में सहेज लिया गया है।",
    finish: "समाप्त",
    risk: { low: "सब सामान्य", moderate: "जांच योग्य", high: "जल्द डॉक्टर से मिलें", critical: "तत्काल — अभी डॉक्टर से मिलें" },
  },
};

const state = {
  language: "en",
  voiceOn: true,
  screen: "welcome",
  sessionId: null,
  debugOtp: null,
  phone: null,
  patientId: null,
  token: null,
  vitalsReadingId: null,
  triage: null,
  history: { conditions: [], medications: [] },
};

const SCREEN_ORDER = ["welcome", "phone", "otp", "home", "documents", "vitals", "result", "summary"];

function t(key) {
  return COPY[state.language][key];
}

/* ---------------- Voice narration (real Web Speech API) ---------------- */
function speak(text) {
  if (!state.voiceOn || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = state.language === "hi" ? "hi-IN" : "en-IN";
  window.speechSynthesis.speak(utter);
}

/* ---------------- API helper ---------------- */
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json();
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => { toast.hidden = true; }, 4000);
}

/* ---------------- Rendering helpers ---------------- */
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child) node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }
  return node;
}

function renderProgress() {
  const track = document.getElementById("progress-track");
  track.innerHTML = "";
  const idx = SCREEN_ORDER.indexOf(state.screen);
  SCREEN_ORDER.forEach((s, i) => {
    const dot = el("span", {
      class: "progress-dot",
      "data-state": i < idx ? "done" : i === idx ? "current" : "upcoming",
      role: "listitem",
    });
    track.appendChild(dot);
  });
}

function mount(node, narrate) {
  const screen = document.getElementById("screen");
  screen.innerHTML = "";
  screen.appendChild(node);
  renderProgress();
  if (narrate) speak(narrate);
  const heading = screen.querySelector("h1, h2");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus();
  }
}

/* ---------------- Screens ---------------- */
function screenWelcome() {
  const node = el("div", {}, [
    el("h1", { text: t("welcome_title") }),
    el("p", { class: "lead", text: t("welcome_lead") }),
    el("button", { class: "btn btn-primary", type: "button", onclick: () => { state.screen = "phone"; renderScreen(); } }, t("start")),
  ]);
  mount(node, `${t("welcome_title")}. ${t("welcome_lead")}`);
}

function screenPhone() {
  const errorBox = el("p", { class: "error-text", hidden: "true" });
  const input = el("input", { type: "tel", inputmode: "numeric", placeholder: t("phone_placeholder"), "aria-label": t("phone_title"), id: "phone-input" });

  async function submit() {
    const phone = input.value.trim();
    errorBox.hidden = true;
    if (!/^\d{10}$/.test(phone)) {
      errorBox.textContent = "Please enter a valid 10-digit phone number.";
      errorBox.hidden = false;
      return;
    }
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending…";
    try {
      const resp = await api("/auth/otp/request", {
        method: "POST",
        body: JSON.stringify({ identifier: phone, purpose: "login" }),
      });
      state.phone = phone;
      state.sessionId = resp.session_id;
      state.debugOtp = resp.debug_otp || null;
      state.screen = "otp";
      renderScreen();
    } catch (err) {
      errorBox.textContent = err.message || "Couldn't send the code. Check the backend is running.";
      errorBox.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t("send_code");
    }
  }

  const submitBtn = el("button", { class: "btn btn-primary", type: "button", onclick: submit }, t("send_code"));

  const node = el("div", {}, [
    el("h1", { text: t("phone_title") }),
    el("p", { class: "lead", text: t("phone_lead") }),
    el("label", { for: "phone-input", text: t("phone_title") }),
    input,
    errorBox,
    submitBtn,
    el("button", { class: "btn btn-ghost", type: "button", onclick: () => { state.screen = "welcome"; renderScreen(); } }, t("back")),
  ]);
  mount(node, `${t("phone_title")}. ${t("phone_lead")}`);
}

function screenOtp() {
  const errorBox = el("p", { class: "error-text", hidden: "true" });
  const input = el("input", { class: "otp-input", type: "text", inputmode: "numeric", maxlength: "6", "aria-label": t("otp_title"), id: "otp-input", value: state.debugOtp || "" });

  async function submit() {
    const code = input.value.trim();
    errorBox.hidden = true;
    if (!/^\d{6}$/.test(code)) {
      errorBox.textContent = "Enter the 6-digit code.";
      errorBox.hidden = false;
      return;
    }
    verifyBtn.disabled = true;
    verifyBtn.textContent = "Verifying…";
    try {
      const resp = await api("/auth/otp/verify", {
        method: "POST",
        body: JSON.stringify({ session_id: state.sessionId, otp_code: code }),
      });
      state.patientId = resp.patient_id;
      state.token = resp.access_token;
      state.screen = "home";
      renderScreen();
    } catch (err) {
      errorBox.textContent = err.message || "That code didn't work. Try again.";
      errorBox.hidden = false;
    } finally {
      verifyBtn.disabled = false;
      verifyBtn.textContent = t("verify");
    }
  }

  const verifyBtn = el("button", { class: "btn btn-primary", type: "button", onclick: submit }, t("verify"));

  const children = [
    el("h1", { text: t("otp_title") }),
    el("p", { class: "lead", text: t("otp_lead") }),
  ];
  if (state.debugOtp) {
    children.push(el("p", { class: "hint", text: `${t("otp_demo_hint")} ${state.debugOtp}` }));
  }
  children.push(
    el("label", { for: "otp-input", text: t("otp_title") }),
    input,
    errorBox,
    verifyBtn,
    el("button", { class: "btn btn-ghost", type: "button", onclick: () => { state.screen = "phone"; renderScreen(); } }, t("back")),
  );
  mount(el("div", {}, children), `${t("otp_title")}. ${t("otp_lead")}`);
}

function screenHome() {
  const node = el("div", {}, [
    el("h1", { text: t("home_greeting") }),
    el("p", { class: "lead", text: t("home_lead") }),
    el("button", { class: "btn btn-primary", type: "button", onclick: () => { state.screen = "documents"; renderScreen(); } }, t("begin_vitals")),
  ]);
  mount(node, `${t("home_greeting")} ${t("home_lead")}`);
}

function screenDocuments() {
  const errorBox = el("p", { class: "error-text", hidden: "true" });
  const resultsBox = el("div", { class: "stack" });
  const fileInput = el("input", {
    type: "file", accept: "image/*", capture: "environment",
    id: "doc-file-input", class: "sr-only",
  });

  async function handleFile(file) {
    if (!file) return;
    errorBox.hidden = true;
    uploadBtn.disabled = true;
    resultsBox.innerHTML = "";
    resultsBox.appendChild(el("div", { class: "spinner-row" }, [el("span", { class: "spinner", "aria-hidden": "true" }), t("docs_scanning")]));

    const formData = new FormData();
    formData.append("patient_id", state.patientId);
    formData.append("image", file);

    try {
      const res = await fetch(`${API_BASE}/documents/scan`, { method: "POST", body: formData });
      if (!res.ok) throw new Error(`Scan failed (${res.status})`);
      const scan = await res.json();

      state.history.conditions = Array.from(new Set([...state.history.conditions, ...scan.extracted_conditions]));
      state.history.medications = Array.from(new Set([...state.history.medications, ...scan.extracted_medications]));

      resultsBox.innerHTML = "";
      resultsBox.appendChild(el("h2", { text: t("docs_found_title") }));
      if (scan.extracted_conditions.length === 0 && scan.extracted_medications.length === 0) {
        resultsBox.appendChild(el("p", { class: "hint", text: t("docs_none_found") }));
      } else {
        if (scan.extracted_conditions.length) {
          resultsBox.appendChild(row(t("docs_conditions"), scan.extracted_conditions.join(", ")));
        }
        if (scan.extracted_medications.length) {
          resultsBox.appendChild(row(t("docs_medications"), scan.extracted_medications.join(", ")));
        }
      }
      speak(`${t("docs_found_title")}. ${[...scan.extracted_conditions, ...scan.extracted_medications].join(", ") || t("docs_none_found")}`);
    } catch (err) {
      errorBox.textContent = err.message || "Couldn't read that document. You can skip this step.";
      errorBox.hidden = false;
      resultsBox.innerHTML = "";
    } finally {
      uploadBtn.disabled = false;
    }
  }

  fileInput.addEventListener("change", (e) => handleFile(e.target.files[0]));

  const uploadBtn = el("button", {
    class: "btn btn-secondary", type: "button",
    onclick: () => fileInput.click(),
  }, t("docs_upload"));

  const node = el("div", {}, [
    el("h1", { text: t("docs_title") }),
    el("p", { class: "lead", text: t("docs_lead") }),
    fileInput,
    uploadBtn,
    errorBox,
    resultsBox,
    el("button", { class: "btn btn-primary", type: "button", onclick: () => { state.screen = "vitals"; renderScreen(); } }, t("docs_continue")),
    el("button", { class: "btn btn-ghost", type: "button", onclick: () => { state.screen = "vitals"; renderScreen(); } }, t("docs_skip")),
  ]);
  mount(node, `${t("docs_title")}. ${t("docs_lead")}`);
}

function numberField(id, labelKey, opts = {}) {
  const label = el("label", { for: id, text: t(labelKey) });
  const input = el("input", { type: "number", id, inputmode: "decimal", ...opts });
  return { wrap: el("div", { class: "vital-field" }, [label, input]), input };
}

function screenVitals() {
  const errorBox = el("p", { class: "error-text", hidden: "true" });

  const spo2 = numberField("f-spo2", "spo2", { min: "50", max: "100" });
  const hr = numberField("f-hr", "hr", { min: "30", max: "220" });
  const sbp = numberField("f-sbp", "sbp", { min: "60", max: "260" });
  const dbp = numberField("f-dbp", "dbp", { min: "40", max: "160" });
  const temp = numberField("f-temp", "temp", { step: "0.1", min: "30", max: "43" });
  const glucose = numberField("f-glucose", "glucose", { min: "30", max: "500" });

  let glucoseContext = "random";
  const fastingBtn = el("button", { class: "choice-btn", type: "button", "aria-pressed": "false" }, t("fasting"));
  const randomBtn = el("button", { class: "choice-btn", type: "button", "aria-pressed": "true" }, t("random"));
  function setContext(ctx) {
    glucoseContext = ctx;
    fastingBtn.setAttribute("aria-pressed", ctx === "fasting" ? "true" : "false");
    randomBtn.setAttribute("aria-pressed", ctx === "random" ? "true" : "false");
  }
  fastingBtn.addEventListener("click", () => setContext("fasting"));
  randomBtn.addEventListener("click", () => setContext("random"));

  async function submit() {
    errorBox.hidden = true;
    submitBtn.disabled = true;
    submitBtn.textContent = t("checking");
    try {
      const payload = {
        patient_id: state.patientId,
        source: "manual",
        spo2_percent: numOrNull(spo2.input.value),
        heart_rate_bpm: numOrNull(hr.input.value),
        systolic_bp: numOrNull(sbp.input.value),
        diastolic_bp: numOrNull(dbp.input.value),
        temperature_c: numOrNull(temp.input.value),
        glucose_mg_dl: numOrNull(glucose.input.value),
        glucose_context: glucose.input.value ? glucoseContext : null,
      };
      const reading = await api("/vitals", { method: "POST", body: JSON.stringify(payload) });
      state.vitalsReadingId = reading.id;

      const triage = await api("/triage/run", {
        method: "POST",
        body: JSON.stringify({ patient_id: state.patientId, vitals_reading_id: reading.id }),
      });
      state.triage = triage;
      state.screen = "result";
      renderScreen();
    } catch (err) {
      errorBox.textContent = err.message || "Couldn't save your vitals. Check the backend is running.";
      errorBox.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t("submit_vitals");
    }
  }

  const submitBtn = el("button", { class: "btn btn-primary", type: "button", onclick: submit }, t("submit_vitals"));

  const node = el("div", {}, [
    el("h1", { text: t("vitals_title") }),
    el("p", { class: "lead", text: t("vitals_lead") }),
    el("div", { class: "vitals-grid" }, [spo2.wrap, hr.wrap, sbp.wrap, dbp.wrap, temp.wrap, glucose.wrap]),
    el("label", { text: t("glucose_context") }),
    el("div", { class: "choice-list" }, [fastingBtn, randomBtn]),
    errorBox,
    submitBtn,
  ]);
  mount(node, `${t("vitals_title")}. ${t("vitals_lead")}`);
}

function numOrNull(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

const RISK_ICON = { low: "✅", moderate: "🟡", high: "🟠", critical: "🔴" };

function screenResult() {
  const triage = state.triage;
  const riskClass = `risk-${triage.risk_level}`;
  const riskLabel = t("risk")[triage.risk_level] || triage.risk_level;

  const banner = el("div", { class: `risk-banner ${riskClass}` }, [
    el("span", { class: "risk-icon", "aria-hidden": "true" }, RISK_ICON[triage.risk_level] || "•"),
    el("span", { text: riskLabel }),
  ]);

  const flagItems = (triage.rationale && triage.rationale.length ? triage.rationale : ["No specific concerns flagged."])
    .map((r) => el("li", { text: r }));

  const node = el("div", {}, [
    el("h1", { text: t("result_title") }),
    banner,
    el("ul", { class: "flag-list" }, flagItems),
    el("label", { text: t("action_label") }),
    el("p", { class: "lead", text: triage.recommended_action }),
    el("button", { class: "btn btn-primary", type: "button", onclick: () => { state.screen = "summary"; renderScreen(); } }, t("see_summary")),
  ]);
  mount(node, `${t("result_title")}. ${riskLabel}. ${triage.recommended_action}`);
}

async function screenSummary() {
  const node = el("div", {}, [
    el("h1", { text: t("summary_title") }),
    el("p", { class: "lead", text: t("summary_lead") }),
    el("div", { class: "spinner-row" }, [el("span", { class: "spinner", "aria-hidden": "true" }), "Preparing your record…"]),
  ]);
  mount(node, `${t("summary_title")}. ${t("summary_lead")}`);

  try {
    const bundle = await api(`/fhir/patient/${state.patientId}/bundle`, { method: "POST" });
    const riskLabel = t("risk")[state.triage.risk_level] || state.triage.risk_level;

    const summaryNode = el("div", {}, [
      el("h1", { text: t("summary_title") }),
      el("p", { class: "lead", text: t("summary_lead") }),
      el("div", { class: "stack" }, [
        row("Phone", state.phone),
        row("Risk level", riskLabel),
        row("Next step", state.triage.recommended_action),
        ...(state.history.conditions.length ? [row(t("docs_conditions"), state.history.conditions.join(", "))] : []),
        ...(state.history.medications.length ? [row(t("docs_medications"), state.history.medications.join(", "))] : []),
        row("Records saved", `${bundle.entry ? bundle.entry.length : 0} items`),
      ]),
      el("button", { class: "btn btn-primary", type: "button", onclick: resetToWelcome }, t("finish")),
    ]);
    mount(summaryNode, `${t("summary_title")}. ${t("summary_lead")}`);
  } catch (err) {
    showToast(err.message || "Couldn't generate the summary.");
  }
}

function row(label, value) {
  return el("div", { class: "summary-row" }, [
    el("span", { class: "summary-label", text: label }),
    el("span", { class: "summary-value", text: String(value) }),
  ]);
}

function resetToWelcome() {
  Object.assign(state, {
    screen: "welcome", sessionId: null, debugOtp: null, phone: null,
    patientId: null, token: null, vitalsReadingId: null, triage: null,
    history: { conditions: [], medications: [] },
  });
  renderScreen();
}

/* ---------------- Router ---------------- */
const RENDERERS = {
  welcome: screenWelcome,
  phone: screenPhone,
  otp: screenOtp,
  home: screenHome,
  documents: screenDocuments,
  vitals: screenVitals,
  result: screenResult,
  summary: screenSummary,
};

function renderScreen() {
  const render = RENDERERS[state.screen];
  if (render) render();
}

/* ---------------- Top bar controls ---------------- */
document.getElementById("lang-select").addEventListener("change", (e) => {
  state.language = e.target.value;
  renderScreen();
});

document.getElementById("mute-btn").addEventListener("click", (e) => {
  state.voiceOn = !state.voiceOn;
  const btn = e.currentTarget;
  btn.setAttribute("aria-pressed", String(state.voiceOn));
  document.getElementById("mute-icon").textContent = state.voiceOn ? "🔊" : "🔇";
  document.getElementById("mute-label").textContent = state.voiceOn ? "Voice guidance on" : "Voice guidance off";
  if (!state.voiceOn && "speechSynthesis" in window) window.speechSynthesis.cancel();
});

renderScreen();
