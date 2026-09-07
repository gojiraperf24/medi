# MediKiosk Frontend (basic, accessible)

A minimal kiosk UI for the patient-facing check-in flow: login → vitals →
triage result → summary. Plain HTML/CSS/JS — **no npm, no build step** —
so there's nothing to install beyond a browser.

## Run it

1. Make sure the backend is running first (`uvicorn app.main:app --reload`
   in the `medikiosk-backend` project, on `http://localhost:8000`).
2. Open `index.html` directly in a browser — double-click it, or drag it
   into a browser window.
   - If your browser blocks the API calls when opened as a `file://` URL,
     serve the folder instead: `python -m http.server 5500` from inside
     this folder, then visit `http://localhost:5500`.
3. Walk through the flow: enter any 10-digit number → the OTP screen
   auto-fills the demo code (real SMS isn't wired up, see backend README)
   → enter vitals → see your risk result → see the summary.

If your backend runs somewhere other than `localhost:8000`, edit
`config.js`.

## What's actually here

- `index.html` — page shell, top bar (language switch + voice mute), skip link
- `styles.css` — all design tokens and styling, no framework
- `config.js` — one line: where the backend lives
- `app.js` — the whole app: a tiny screen router (`welcome → phone → otp →
  home → documents → vitals → result → summary`), the API calls, and voice
  narration

## Accessibility choices made on purpose

- **Atkinson Hyperlegible** font — designed by the Braille Institute
  specifically for low-vision readability, not a generic UI font.
- **Real voice narration** via the browser's built-in `speechSynthesis` —
  every screen is read aloud automatically (mutable with the speaker icon
  top-right). This is genuinely functional, unlike the backend's mocked
  Bhashini endpoints — it just depends on what voices your OS/browser has
  installed (Hindi voice quality varies by device).
- **Large touch targets** — every button is at least 60px tall.
- **One task per screen**, a progress-dot tracker, big "Back" options.
- **Color is never the only signal** — every risk level pairs a color with
  an icon and a plain-language label.
- **Visible focus rings**, skip-to-content link, semantic headings that
  receive focus on screen change (helps both keyboard and screen-reader
  users track where they are), `aria-live` regions for dynamic content.
- **Bilingual UI copy** (English/Hindi) via the language switcher — covers
  the core flow's labels; extending `COPY` in `app.js` covers more screens
  or languages later.

## What this doesn't do (be aware)

- No real device integration — vitals are typed in manually, standing in
  for what a paired pulse oximeter/BP cuff/etc. would auto-fill.
- The "old records" screen sends whatever image you pick to the backend's
  mocked OCR — it doesn't actually read the photo's contents client-side,
  so any image works for testing (the backend returns a random canned
  extraction regardless of what's actually in the photo).
- No medicine-scan or telemedicine screens yet — covers intake → old
  records → vitals → triage → summary. Structurally easy to add as new
  screens following the same pattern (`screenDocuments` is a good template
  for a file-upload-based screen, `screenVitals` for a form-based one).
- Not a kiosk-mode/fullscreen app — for an actual kiosk deployment you'd
  run this in a browser's kiosk mode (e.g. Chrome `--kiosk` flag) on the
  device.

## Extending it

Every screen follows the same shape: a `screenX()` function that builds
DOM nodes with `el(...)`, wires up one `async submit()` that calls `api(...)`,
and calls `mount(node, spokenText)` to render + narrate it. Copy the
`screenVitals` function as a template for a new screen (e.g. medicine scan).
