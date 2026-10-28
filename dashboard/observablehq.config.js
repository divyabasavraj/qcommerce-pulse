// Q-Commerce Pulse dashboard. Data loaders in src/data/ are Python, run through uv in the parent project,
// so every number comes from the same SQL as the reports (../sql).
export default {
  title: "Q-Commerce Pulse",
  root: "src",
  pages: [
    {name: "This week", path: "/"},
    {name: "Trends", path: "/trends"},
    {name: "Compare apps", path: "/compare"},
    {name: "What to fix", path: "/fixes"},
    {name: "How it works", path: "/method"}
  ],
  sidebar: false,
  pager: false,
  toc: false,
  search: false,
  style: "style.css",
  head: `<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Anek+Devanagari:wght@400;600&family=Anek+Latin:wdth,wght@75..125,300..800&display=swap"><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Cpath d='M1 9h4l2-6 2 10 2-4h4' fill='none' stroke='%231F2A44' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/%3E%3C/svg%3E">`,
  header: ({path}) => {
    const links = [["/", "This week"], ["/trends", "Trends"], ["/compare", "Compare apps"], ["/fixes", "What to fix"], ["/method", "How it works"]];
    const here = path === "/index" ? "/" : path;
    const nav = links.map(([p, name]) => `<a href=".${p === "/" ? "/" : p}"${p === here ? ` aria-current="page"` : ""}>${name}</a>`).join("");
    return `<div class="site-header"><a class="wordmark" href="./">Q-Commerce Pulse</a><nav class="site-nav" aria-label="Pages">${nav}</nav></div>`;
  },
  footer: `Independent project built from public Google Play reviews. Not affiliated with Blinkit, Zepto, Swiggy Instamart or BigBasket. <a href="https://github.com/divyabasavraj/qcommerce-pulse">Code and method on GitHub</a>.`,
  interpreters: {".py": ["uv", "run", "--quiet", "python"]}
};
