Fix the WS-2 dashboard CSS issue before adding new UI.

Problem:
The dashboard routes work, but Tailwind CSS is not applying. The page is rendering with browser default styles.

Inspect:
- apps/web/src/app/globals.css
- apps/web/tailwind.config.ts
- apps/web/package.json
- Next.js config

Expected fix:
- Add the missing PostCSS configuration for Tailwind.
- Add missing frontend dev dependencies if needed: postcss and autoprefixer.
- Keep the fix scoped to apps/web CSS/build config.
- Do not redesign the dashboard yet.
- Do not touch backend services.
- Do not commit or push automatically.

After fixing:
- Restart the frontend dev server.
- Verify /dashboard/card renders with Tailwind styles.
- Run the frontend typecheck/build command if available.
- Tell me exactly which files changed.