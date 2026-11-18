import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const origin = process.argv[2] || "http://127.0.0.1:8765";
const artifacts = process.argv[3] || path.join(tmpdir(), "digisas-browser-check");
const chrome = process.env.CHROME || (process.platform === "darwin"
  ? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" : "google-chrome");
const profile = await mkdtemp(path.join(tmpdir(), "digisas-preview-"));
await mkdir(artifacts, { recursive: true });
const browser = spawn(chrome, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--remote-debugging-pipe", `--user-data-dir=${profile}`,
], { stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"] });
let sequence = 0;
let buffer = "";
const pending = new Map();
const events = new Map();
const failures = [];
browser.stdio[4].on("data", (chunk) => {
  buffer += chunk.toString();
  let end;
  while ((end = buffer.indexOf("\0")) !== -1) {
    const message = JSON.parse(buffer.slice(0, end));
    buffer = buffer.slice(end + 1);
    if (message.id) {
      const request = pending.get(message.id);
      if (!request) continue;
      pending.delete(message.id);
      clearTimeout(request.timer);
      if (message.error) request.reject(new Error(JSON.stringify(message.error)));
      else request.resolve(message.result);
    } else {
      const key = `${message.sessionId}:${message.method}`;
      const listener = events.get(key);
      if (listener) {
        events.delete(key);
        listener(message.params);
      }
      if (message.method === "Runtime.exceptionThrown") {
        failures.push(message.params.exceptionDetails.text);
      }
    }
  }
});
function call(method, params = {}, sessionId) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`Timed out: ${method}`));
    }, 25000);
    pending.set(id, { resolve, reject, timer });
    browser.stdio[3].write(JSON.stringify({ id, method, params, sessionId }) + "\0");
  });
}
function event(method, session) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Timed out waiting for ${method}`)), 25000);
    events.set(`${session}:${method}`, (params) => { clearTimeout(timer); resolve(params); });
  });
}

try {
  const { targetId } = await call("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await call("Target.attachToTarget", { targetId, flatten: true });
  await call("Page.enable", {}, sessionId);
  await call("Runtime.enable", {}, sessionId);
  const cases = [
    { name: "desktop-home", route: "/", width: 1440, height: 1080 },
    { name: "mobile-home", route: "/", width: 390, height: 844 },
    { name: "mobile-people", route: "/people/", width: 390, height: 844 },
    { name: "desktop-people", route: "/people/", width: 1440, height: 1080 },
    { name: "mobile-sarv", route: "/people/#sarv-girn", width: 390, height: 844 },
    { name: "desktop-sarv", route: "/people/#sarv-girn", width: 1440, height: 1080 },
    { name: "tablet-home", route: "/", width: 820, height: 1180 },
    { name: "mobile-research", route: "/research/", width: 390, height: 844 },
    { name: "mobile-fgea", route: "/fgea-cop/", width: 390, height: 844 },
    { name: "desktop-fgea", route: "/fgea-cop/", width: 1440, height: 1080 },
    { name: "mobile-search", route: "/search/?q=FGEA", width: 390, height: 844 },
    { name: "latest-event", route: "/blog/2026/11/15/fgea-cop-2026-q4-symposium/", width: 390, height: 844 },
    { name: "native-event", route: "/fgea-cop/events/fgea-2026-q4-symposium/", width: 390, height: 844 },
    { name: "desktop-native-event", route: "/fgea-cop/events/fgea-2026-q4-symposium/", width: 1440, height: 1080 },
    { name: "event-gallery", route: "/fgea-cop/news/2025-q4-symposium/", width: 390, height: 844 },
  ];
  const results = [];
  for (const test of cases) {
    const cleared = event("Page.loadEventFired", sessionId);
    await call("Page.navigate", { url: "about:blank" }, sessionId);
    await cleared;
    await call("Emulation.setDeviceMetricsOverride", {
      width: test.width, height: test.height, deviceScaleFactor: 1, mobile: test.width < 600,
    }, sessionId);
    await call("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: test.name === "mobile-sarv" ? "reduce" : "no-preference" }],
    }, sessionId);
    const loaded = event("Page.loadEventFired", sessionId);
    await call("Page.navigate", { url: origin + test.route }, sessionId);
    await loaded;
    await call("Runtime.evaluate", {
      expression: `(async () => {
        await document.fonts.ready;
        if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView({ behavior: "instant", block: "center" });
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        await new Promise(resolve => {
          const deadline = Date.now() + 15000;
          const ready = () => {
            const images = [...document.images].filter(image => {
              const bounds = image.getBoundingClientRect();
              return bounds.bottom > 0 && bounds.top < innerHeight && image.checkVisibility();
            });
            const searching = document.querySelector("#search-status")?.textContent === "Searching...";
            if ((!searching && images.every(image => image.complete)) || Date.now() > deadline) resolve();
            else setTimeout(ready, 100);
          };
          ready();
        });
      })()`, awaitPromise: true,
    }, sessionId);
    const { result } = await call("Runtime.evaluate", {
      expression: `JSON.stringify({
        viewport: innerWidth, width: document.documentElement.scrollWidth,
        menuVisible: getComputedStyle(document.querySelector("summary, .menu-toggle")).display !== "none",
        menuOpen: document.querySelector(".navigation")?.open ?? (document.querySelector(".menu-toggle")?.getAttribute("aria-expanded") === "true"),
        navigationVisible: document.querySelector(".navigation nav, #site-nav").checkVisibility(),
        search: document.querySelector("#search-status")?.textContent,
        portrait: (() => { const i = document.querySelector("#sarv-girn img"); if (!i) return null; const b = i.getBoundingClientRect(); return { src: i.src, width: i.naturalWidth, visible: b.bottom > 0 && b.top < innerHeight }; })(),
        cardImages: document.querySelectorAll("main .card img").length,
        recordImage: document.querySelector(".record-image img")?.naturalWidth,
        reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
        cardTransition: document.querySelector(".cb-profile__post") ? getComputedStyle(document.querySelector(".cb-profile__post")).transitionDuration : null,
        brokenImages: [...document.images].filter(i => { const b = i.getBoundingClientRect(); return b.bottom > 0 && b.top < innerHeight && i.checkVisibility() && (!i.complete || i.naturalWidth === 0); }).map(i => i.src)
      })`, returnByValue: true,
    }, sessionId);
    const metrics = JSON.parse(result.value);
    if (metrics.width > test.width + 1 || metrics.viewport > test.width + 1) failures.push(`${test.name}: horizontal overflow ${JSON.stringify(metrics)}`);
    if (metrics.brokenImages.length) failures.push(`${test.name}: broken visible images`);
    if (test.name.endsWith("-sarv") && (!metrics.portrait?.visible || metrics.portrait?.width !== 400 || !metrics.portrait?.src.endsWith("/Sarv.jpg"))) failures.push(`${test.name}: Sarv's full-size portrait did not display`);
    if (test.name.includes("native-event") && !metrics.recordImage) failures.push(`${test.name}: event picture did not load`);
    if (test.name.includes("home") && metrics.cardImages !== 6) failures.push(`${test.name}: news cards are missing pictures`);
    if (test.name === "mobile-sarv" && (!metrics.reducedMotion || metrics.cardTransition !== "0s")) failures.push("Reduced-motion preference was not respected");
    if (test.width < 600 && (!metrics.menuVisible || metrics.menuOpen)) failures.push(`${test.name}: mobile menu state incorrect`);
    if (test.width < 600 && metrics.navigationVisible) failures.push(`${test.name}: closed navigation is still displayed`);
    if (test.name === "mobile-search" && !/^[1-9]\d* results/.test(metrics.search)) failures.push("Search returned no results");
    if (test.name === "mobile-home") {
      const menu = await call("Runtime.evaluate", {
        expression: `document.querySelector("summary").click(); document.querySelector(".navigation").open`,
        returnByValue: true,
      }, sessionId);
      if (!menu.result.value) failures.push("Mobile menu did not open");
      await call("Runtime.evaluate", { expression: `document.querySelector("summary").click()` }, sessionId);
    }
    if (test.name === "mobile-fgea") {
      const menu = await call("Runtime.evaluate", {
        expression: `(() => { document.querySelector(".menu-toggle").click(); return document.querySelector("#site-nav").getBoundingClientRect().height > 0; })()`,
        returnByValue: true,
      }, sessionId);
      if (!menu.result.value) failures.push("FGEA mobile navigation did not open");
      await call("Runtime.evaluate", { expression: `document.querySelector(".menu-toggle").click()` }, sessionId);
    }
    const screenshot = await call("Page.captureScreenshot", { format: "png" }, sessionId);
    await writeFile(path.join(artifacts, `${test.name}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ ...test, ...metrics });
  }
  await writeFile(path.join(artifacts, "browser-results.json"), JSON.stringify({ results, failures }, null, 2) + "\n");
  console.log(JSON.stringify({ results, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
} finally {
  await call("Browser.close").catch(() => {});
  await new Promise((resolve) => browser.exitCode !== null ? resolve() : browser.once("exit", resolve));
  await rm(profile, { recursive: true });
}
