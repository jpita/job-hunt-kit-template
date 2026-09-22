// Google "site:" harvest helpers, run through the Claude Chrome extension.
//
// The browser really navigates to each result page and follows the real "Next"
// link, the way a person does. It does not fetch pages in the background and it
// does not build &start= URLs by hand.
//
// Measured once, and the reason it works this way:
//   num does nothing        Google ignores it. A result page is 10 results.
//   background fetch burns  24 rapid fetch() calls returned 429 /sorry/index,
//                           and the block then hit normal browsing too.
//   real navigation is fine Every actual page load that day succeeded.
// Google's Next link carries continuation tokens (ei, ved, sa=N). A hand-made
// &start=20 has none, which is its own bot signal. So: follow the real link.
//
// Usage, one page at a time, ~10s between navigations:
//   0. run `python3 scan/queries.py` and inject its output first. It sets
//      window._GROUPS from GOOGLE_QUERIES in me/search.py.
//   1. navigate to window._queries()[n]
//   2. await window._page()     -> {jobs, next, blocked, count}
//   3. navigate to .next, repeat until next is null
//   4. window._all()            -> every URL collected this session

const HOSTS = [
  'jobs.lever.co',
  'boards.greenhouse.io',
  'job-boards.greenhouse.io',
  'jobs.ashbyhq.com',
];

// Your queries come from GOOGLE_QUERIES in me/search.py, via queries.py.
// Keep each query short, or Google drops terms.
const GROUPS = window._GROUPS || [];
if (!GROUPS.length) throw new Error('window._GROUPS is empty: inject the output of scan/queries.py first');

const JOB_RX = [
  /https?:\/\/jobs\.lever\.co\/[A-Za-z0-9._-]{2,40}\/[0-9a-f-]{16,40}/g,
  /https?:\/\/(?:job-)?boards\.greenhouse\.io\/[A-Za-z0-9._-]{2,40}\/jobs\/\d+/g,
  /https?:\/\/jobs\.ashbyhq\.com\/[A-Za-z0-9._-]{2,40}\/[0-9a-f-]{16,40}/g,
];

window._jobs = window._jobs || new Set();

// One search URL per host and query. Only the first page of each is built by hand; every page
// after that comes from the Next link on the page itself.
window._queries = () => {
  const out = [];
  for (const h of HOSTS) {
    for (const g of GROUPS) {
      out.push('https://www.google.com/search?q=' + encodeURIComponent(`site:${h} ${g}`));
    }
  }
  return out;
};

// Read the page the browser is on now. Adds to the running set, hands back the
// real Next href so the caller can navigate to it.
window._page = () => {
  const blocked = location.href.includes('/sorry/')
    || /Our systems have detected unusual traffic/i.test(document.body.innerText);
  if (blocked) return { blocked: true, jobs: [], next: null, total: window._jobs.size };

  const htmlText = document.documentElement.outerHTML;
  const found = new Set();
  for (const rx of JOB_RX) {
    rx.lastIndex = 0;
    for (const m of htmlText.matchAll(rx)) found.add(m[0].replace(/^http:/, 'https:'));
  }

  let added = 0;
  for (const u of found) if (!window._jobs.has(u)) { window._jobs.add(u); added++; }

  // Google's own pagination link. Absent on the last page.
  const nextEl = document.querySelector('a#pnnext, a[aria-label="Next page"]');

  return {
    blocked: false,
    count: found.size,
    added,
    total: window._jobs.size,
    next: nextEl ? nextEl.href : null,
    title: document.title,
  };
};

window._all = () => ({ total: window._jobs.size, jobs: [...window._jobs] });
window._reset = () => { window._jobs = new Set(); return 'cleared'; };

({ queries: window._queries().length, carried: window._jobs.size });
