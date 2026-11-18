(() => {
  const navigation = document.querySelector(".navigation");
  const desktop = window.matchMedia("(min-width: 64rem)");
  const syncNavigation = () => { navigation.open = desktop.matches; };
  syncNavigation();
  desktop.addEventListener("change", syncNavigation);

  const form = document.querySelector("#site-search");
  if (!form) return;
  const field = document.querySelector("#query");
  const status = document.querySelector("#search-status");
  const results = document.querySelector("#search-results");
  let index;
  const search = async (event) => {
    if (event) event.preventDefault();
    const query = field.value.trim();
    results.replaceChildren();
    if (!query) {
      status.textContent = "Enter a search term.";
      return;
    }
    status.textContent = "Searching...";
    try {
      if (!index) {
        const script = document.querySelector("script[src$='/assets/site.js']");
        const response = await fetch(new URL("../search-index.json", script.src));
        if (!response.ok) throw new Error("Search index unavailable");
        index = await response.json();
      }
      const words = query.toLocaleLowerCase().split(/\s+/);
      const matches = index.filter((item) =>
        words.every((word) => `${item.title} ${item.text}`.toLocaleLowerCase().includes(word)));
      for (const match of matches) {
        const item = document.createElement("li");
        const title = document.createElement("h2");
        const link = document.createElement("a");
        link.href = match.url;
        link.textContent = match.title;
        const excerpt = document.createElement("p");
        excerpt.textContent = match.text.slice(0, 220) + (match.text.length > 220 ? "..." : "");
        title.append(link);
        item.append(title, excerpt);
        results.append(item);
      }
      status.textContent = `${matches.length} result${matches.length === 1 ? "" : "s"} for "${query}".`;
      const url = new URL(window.location.href);
      url.searchParams.set("q", query);
      window.history.replaceState(null, "", url);
    } catch {
      status.textContent = "Search is unavailable. Use the navigation or all-pages link below.";
    }
  };
  form.addEventListener("submit", search);
  field.value = new URLSearchParams(window.location.search).get("q") || "";
  if (field.value) search();
})();
