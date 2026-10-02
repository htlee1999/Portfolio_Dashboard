# Portfolio — web app

Next.js frontend for the Portfolio Dashboard. See the repository root README for setup; in short, run `../dev.sh`, or start the FastAPI backend on port 8000 and then run `npm run dev` here.

- `src/app/globals.css`: design tokens (Apple system colors for light and dark, type scale with inverse tracking, translucent materials, squircle corners)
- `src/lib/motion.ts`: spring presets used by every animation
- `src/components/ui`: primitives (buttons, segmented control, sheets, switches, sliders)
- `src/components/charts`: Recharts wrappers that follow one set of chart rules (validated categorical palette, single y-axis, hairline grids)
- `src/app/(app)/*`: pages; `src/app/(auth)/*`: sign in and sign up
