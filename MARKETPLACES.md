# Marketplace evaluation — 2026-09-10, measured

| source | reachable | rendering | rate | budgets | account to apply | verdict |
|---|---|---|---|---|---|---|
| PeoplePerHour | 200, ~1s, 3 hits ok | server-rendered, JSON in page (title/budget/posted_dt/currency) | ~67/day (17 on p1 over 6.1h) | median $75, USD/GBP/EUR | yes (20 login gates on index) | **viable** |
| Twine | 200 | SEO landing pages by category/country; zero job cards even fully rendered | — | — | listings behind sign-in | not viable |
| Contra | 200 → sign-up wall | /opportunities redirects to /sign-up | — | — | fully gated | not viable |
| Freelancermap | 200, 1.3MB | server-rendered, 22 project links/page | ? | none on index | 2 login links | marginal — UK IT contracting via agencies, mostly on-site, no rates |
| Guru | 403 | — | — | — | — | blocked, no API |
| Workana | 403 Cloudflare | — | — | — | — | blocked, no API |
| Malt | 403 Cloudflare | — | — | — | — | blocked, no API |
| Truelancer | 429 Vercel checkpoint, persists | — | — | — | — | blocked |
| Behance | 200 | listings under /joblist/fulltime/ | — | 9 | — | wrong kind — salaried creative jobs |
| Hubstaff Talent | 200 shell only | Cloudflare JS challenge; listings only after it, 584 jobs at $7.50-20/hr VA and staffing work | — | hourly rates | — | not viable — bot-gated, and low-rate staffing behind it (checked in a browser 2026-09-11) |
| Outsourcely | 000 | connection failed | — | — | — | retry later |

## Conclusion
The open, structured, project-based supply is Freelancer.com and PeoplePerHour. Every other
marketplace probed is a walled garden (sign-in, bot protection, no API) or is actually a job board.
