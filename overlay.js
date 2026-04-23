const FEED_URL = "https://fritoburrito.github.io/anchorage/feed.xml";
const REFRESH_MS = 5 * 60 * 1000;

let animId = null;
let x = 0;
let scrollSpeed = 0.8;

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

function startScroll() {
  const track = document.getElementById("ticker-track");
  if (!track) return;

  cancelAnimationFrame(animId);
  x = window.innerWidth;

  function step() {
    const width = track.scrollWidth;
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
    const response = await fetch(FEED_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const text = await response.text();
    const xml = new DOMParser().parseFromString(text, "text/xml");

    if (xml.querySelector("parsererror")) {
      throw new Error("XML parser error");
    }

    const items = [...xml.querySelectorAll("item")];
    track.innerHTML = "";

    if (!items.length) {
      const empty = document.createElement("span");
      empty.className = "item";
      empty.textContent = "No feed items available.";
      track.appendChild(empty);
      startScroll();
      return;
    }

    let rendered = 0;

    items.slice(0, 15).forEach((item, index) => {
      try {
        const title = item.querySelector("title")?.textContent?.trim() || "";
        const category = item.querySelector("category")?.textContent?.trim() || "general";

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
        textNode.textContent = title;

        wrap.appendChild(badge);
        wrap.appendChild(textNode);
        track.appendChild(wrap);
        rendered++;

        if (index < items.length - 1) {
          const separator = document.createElement("span");
          separator.textContent = "  •  ";
          separator.style.opacity = "0.6";
          separator.style.display = "inline-block";
          separator.style.marginRight = "18px";
          track.appendChild(separator);
        }
      } catch (itemError) {
        console.error("Skipping bad item:", itemError);
      }
    });

    if (!rendered) {
      throw new Error("No valid items rendered");
    }

    startScroll();
  } catch (error) {
    console.error("Failed to load feed:", error);
    track.innerHTML = "";

    const fail = document.createElement("span");
    fail.className = "item";
    fail.textContent = "Feed unavailable.";
    track.appendChild(fail);

    startScroll();
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
