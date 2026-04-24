/*
  Anchorage OBS Overlay Baseline

  IMPORTANT:
  If overlay.html, overlay.js, style.css, and feed.xml are all hosted in the same
  GitHub Pages repo/folder, keep FEED_URL as "feed.xml".

  If you use your custom domain in OBS, use:
    const FEED_URL = "https://akpulselive.com/feed.xml";

  If you use the GitHub Pages URL in OBS, use:
    const FEED_URL = "https://fritoburrito.github.io/anchorage/feed.xml";
*/
const FEED_URL = "feed.xml";
const REFRESH_MS = 5 * 60 * 1000;
const MAX_ITEMS = 15;
const DEBUG = true;

let animId = null;
let x = 0;
let scrollSpeed = 0.8;

function debug(message) {
  console.log(message);
  if (!DEBUG) return;

  const panel = document.getElementById("debug-panel");
  if (!panel) return;

  panel.classList.remove("hidden");
  panel.textContent = String(message);
}

function clearDebug() {
  const panel = document.getElementById("debug-panel");
  if (!panel) return;
  panel.classList.add("hidden");
  panel.textContent = "";
}

function getBadgeClass(category) {
  const c = (category || "").toLowerCase();
  if (["breaking", "weather", "top", "world", "business", "local"].includes(c)) {
    return c;
  }
  return "general";
}

function getBadgeLabel(category) {
  const c = (category || "").toLowerCase();
  const labels = {
    breaking: "BREAKING",
    weather: "WEATHER",
    top: "TOP",
    world: "WORLD",
    business: "BUSINESS",
    local: "LOCAL",
    general: "GENERAL"
  };
  return labels[c] || "GENERAL";
}

function setSingleMessage(label, message) {
  const track = document.getElementById("ticker-track");
  if (!track) return;

  track.innerHTML = "";

  const wrap = document.createElement("span");
  wrap.className = "item";

  const badge = document.createElement("span");
  badge.className = "badge general";
  badge.textContent = label;

  const textNode = document.createElement("span");
  textNode.className = "headline-text";
  textNode.textContent = message;

  wrap.appendChild(badge);
  wrap.appendChild(textNode);
  track.appendChild(wrap);

  startScroll();
}

function startScroll() {
  const track = document.getElementById("ticker-track");
  if (!track) return;

  cancelAnimationFrame(animId);
  x = window.innerWidth;

  function step() {
    const width = track.scrollWidth || 1;
    x -= scrollSpeed;

    if (x < -width) {
      x = window.innerWidth;
    }

    track.style.transform = `translateX(${x}px)`;
    animId = requestAnimationFrame(step);
  }

  step();
}

async function loadFeed() {
  const track = document.getElementById("ticker-track");
  if (!track) return;

  try {
    debug(`Loading feed: ${FEED_URL}`);

    const response = await fetch(FEED_URL + "?t=" + Date.now(), {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`Feed fetch failed: HTTP ${response.status}`);
    }

    const text = await response.text();

    if (!text.trim()) {
      throw new Error("Feed file was empty");
    }

    const xml = new DOMParser().parseFromString(text, "text/xml");

    const parserError = xml.querySelector("parsererror");
    if (parserError) {
      throw new Error("XML parser error: " + parserError.textContent.slice(0, 180));
    }

    const items = [...xml.querySelectorAll("item")];

    if (!items.length) {
      throw new Error("No <item> entries found in feed");
    }

    track.innerHTML = "";
    let rendered = 0;

    items.slice(0, MAX_ITEMS).forEach((item, index) => {
     const title = item.querySelector("title")?.textContent?.trim() || "";
     const description = item.querySelector("description")?.textContent?.trim() || "";
     const category = item.querySelector("category")?.textContent?.trim() || "general";

   // For weather, combine title + description
   let displayText = title;

  if (category.toLowerCase() === "weather" && description) {
  // strip basic HTML if present
  const temp = document.createElement("div");
  temp.innerHTML = description;
  const cleanDesc = temp.textContent || temp.innerText || "";

  //displayText = `${title}: ${cleanDesc}`;
  const shortDesc = cleanDesc.length > 120
  ? cleanDesc.slice(0, 117) + "..."
  : cleanDesc;

   displayText = `${title}: ${shortDesc}`;  
}

      if (!title) return;

      const wrap = document.createElement("span");
      wrap.className = "item";

      if (category.toLowerCase() === "breaking") {
        wrap.style.fontWeight = "900";
        wrap.style.textTransform = "uppercase";
      }

      const badge = document.createElement("span");
      badge.className = `badge ${getBadgeClass(category)}`;
      badge.textContent = getBadgeLabel(category);

      const textNode = document.createElement("span");
      textNode.className = "headline-text";
      // textNode.textContent = title;
      textNode.textContent = displayText;

      wrap.appendChild(badge);
      wrap.appendChild(textNode);
      track.appendChild(wrap);
      rendered++;

      if (index < Math.min(items.length, MAX_ITEMS) - 1) {
        const separator = document.createElement("span");
        separator.className = "separator";
        separator.textContent = "•";
        track.appendChild(separator);
      }
    });

    if (!rendered) {
      throw new Error("Items existed, but none had usable titles");
    }

    clearDebug();
    startScroll();
  } catch (error) {
    console.error("Failed to load feed:", error);
    const msg = `Feed unavailable: ${error.message}`;
    debug(msg);

   setSingleMessage("ERROR", msg);
  }
}

function updateClock() {
  const now = new Date();
  const clock = document.getElementById("ticker-clock");
  if (!clock) return;

  clock.textContent = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
}

window.addEventListener("resize", () => {
  startScroll();
});

updateClock();
setInterval(updateClock, 1000);

loadFeed();
setInterval(loadFeed, REFRESH_MS);
