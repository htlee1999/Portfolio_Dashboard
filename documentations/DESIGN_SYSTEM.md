# Design system

The interface follows Apple's Human Interface Guidelines:

- **Clarity:** content comes first.
- **Deference:** chrome recedes, through translucent materials and quiet controls.
- **Depth:** layered surfaces and spring physics make the UI feel like direct manipulation.

Tokens live in `web/src/app/globals.css`, motion presets in `web/src/lib/motion.ts`, and components in `web/src/components/`.

## Principles

1. **Content first.** Numbers are the largest thing on screen. Chrome uses secondary labels, hairlines and fills, never borders or heavy shadows.
2. **Semantic color only.** Every color is a role token (`--label`, `--tint`, `--positive` …) that has a light and a dark value. Accent color appears only where it guides or invites action: the tint for buttons, links, selection and the active nav item; positive and negative for signed values.
3. **Never color alone.** Every signed value carries a sign and an arrow (`Delta`). Status badges carry text, and charts carry legends.
4. **Spring motion.** Animations use mass, stiffness and damping instead of fixed durations, so they can be interrupted and they carry momentum.
5. **44pt targets.** Every interactive element is at least 44×44px. Small visual controls (`size="sm"` buttons, segments, chips) expand their hit area with an invisible pseudo-element.

## Color

The app uses Apple's system colors. On light backgrounds, the text-safe variants are used for status (for example `#248A3D` green rather than `#34C759`).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F2F2F7` | `#000000` | Grouped page background |
| `--bg-elevated` | `#FFFFFF` | `#1C1C1E` | Cards, sheets |
| `--fill` / `--fill-secondary` / `--fill-strong` | gray at 12% / 8% / 20% | 24% / 16% / 36% | Control fills, tracks, hover |
| `--label` | `#000` | `#FFF` | Primary text |
| `--label-secondary` | 60% gray-blue | 60% | Secondary text |
| `--label-tertiary` | 30% | 30% | Placeholders, chevrons |
| `--separator` | hairline gray | hairline gray | 0.5px dividers |
| `--tint` | `#007AFF` | `#0A84FF` | Actions, selection |
| `--positive` | `#248A3D` | `#30D158` | Gains, success |
| `--negative` | `#D70015` | `#FF453A` | Losses, destructive |
| `--warning` | `#B25000` | `#FFD60A` | Cautions |

Each token is exposed to Tailwind as a color (`bg-elevated`, `text-label-2`, `bg-tint-fill`, `text-positive` …).

**Appearance:** `data-theme` on `<html>` is `light` or `dark`. It is resolved from the user's choice in Settings (Automatic, Light or Dark), and an inline script sets it before first paint. Tailwind's `dark:` variant keys off this attribute, not the media query, so the user's choice always wins.

## Typography

The font stack is SF Pro (`-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display"`), falling back to `system-ui`. Hierarchy comes from **weight, size and inverse tracking**: large type tracks tighter, small type tracks looser.

| Utility | Size / line height | Weight | Tracking |
|---|---|---|---|
| `text-hero` | 40–56px fluid / 1.05 | 700 | −0.035em |
| `text-large-title` | 34 / 41 | 700 | −0.026em |
| `text-title-1` | 28 / 34 | 700 | −0.022em |
| `text-title-2` | 22 / 28 | 700 | −0.018em |
| `text-title-3` | 20 / 25 | 600 | −0.014em |
| `text-headline` | 17 / 22 | 600 | −0.012em |
| `text-body` | 15 / 22 | 400 | −0.009em |
| `text-callout` | 14 / 20 | 400 | −0.006em |
| `text-footnote` | 13 / 18 | 400 | −0.002em |
| `text-caption` | 12 / 16 | 400 | +0.004em |
| `text-overline` | 11 / 13, uppercase | 600 | +0.06em |

Use `tabular` (tabular figures) for numbers that line up in columns: tables, axes, stat grids.

## Geometry

- **Squircles:** the `squircle` utility applies `corner-shape: superellipse(1.6)` where supported, giving continuous corners like Apple's. Browsers without support fall back to an ordinary radius.
- **Radii:** cards and lists 20px, sheets 22px, buttons and inputs 12–14px, segmented controls 10px (8px for the inner pill), chips and badges fully rounded.
- **Spacing:** pages use a 16 / 24 / 40px gutter (phone, tablet, desktop) and 20px gaps between cards, with a maximum content width of 1200px.

## Materials and depth

| Utility | Recipe | Used for |
|---|---|---|
| `material-chrome` | 72% surface + `saturate(180%) blur(24px)` | Sidebar, toolbar (once scrolled), tab bar |
| `material-thick` | 82% surface + `blur(32px)` + soft shadow | Toasts, chart tooltips, sign-in card |
| `--shadow-card` | 0.5px ring + 1px shadow | Cards on the grouped background |
| `--shadow-raised` | ring + 16px shadow | Sheets |

Layering, from back to front: grouped background → cards → sticky translucent chrome → sheets with a dimmed backdrop → toasts.

## Motion

Presets live in `src/lib/motion.ts`.

| Preset | Stiffness / damping / mass | Use |
|---|---|---|
| `snappy` | 520 / 38 / 0.8 | Presses, toggles, selection pills, chevrons |
| `smooth` | 300 / 32 / 1 | Content entering, layout changes, page transitions |
| `sheet` | 260 / 30 / 1.1 | Sheets and large surfaces |
| `bouncy` | 400 / 18 / 0.9 | Confirmations: toasts, recommendation icon, tab icon |

Patterns:

- **Press feedback:** buttons scale to 0.96 (`whileTap`).
- **Shared-element selection:** the active sidebar item, segmented-control pill and research tab slide between positions with `layoutId`.
- **Sheets** rise from the bottom on phones and can be dragged down to dismiss (rubber-banded upward). On larger screens they float centered.
- **Large title → inline title:** when a page's large title scrolls under the toolbar, a compact title fades into the toolbar and the toolbar turns translucent.
- **Numbers spring to new values** (`AnimatedNumber`) instead of jumping.
- **Lists and grids stagger in** (`stagger`, `staggerItem`). Rows animate out when deleted.

`MotionConfig reducedMotion="user"` disables transform animations when the OS "Reduce Motion" setting is on.

## Components

| Component | Notes |
|---|---|
| `Button` | Variants: `filled`, `tinted`, `gray`, `plain`, `destructive`. Sizes: `sm` (32px visual, 44px hit area), `md` (44px), `lg` (50px). Has a `loading` state |
| `IconButton` | 44px round, requires `label` (aria-label and tooltip) |
| `Segmented` | Radio group with a sliding pill. Use for 2–6 mutually exclusive options, such as periods |
| `TextField`, `Select`, `Switch`, `Slider` | 44px controls. `Select` is native, so phones get the platform picker |
| `Card`, `Section`, `CardHeader` | Inset-grouped containers |
| `List`, `ListRow` | Settings-style rows with inset hairlines, optional leading icon tile, trailing value and chevron |
| `Sheet` | Modal with focus on open, Escape to close and body scroll lock |
| `Disclosure` | Expandable row with a spring height animation |
| `Banner` | Info, warning or error, each with an icon |
| `Stat`, `StatGrid`, `Delta`, `AnimatedNumber` | Metric display |
| `EmptyState`, `Skeleton`, `Spinner`, `LoadingBlock` | Loading and empty states |
| `Toast` | `useToast()(message, tone)`. Swipe up to dismiss |

## Data visualization

Charts are in `src/components/charts/charts.tsx` (built on Recharts).

- **Categorical palette:** eight slots (`--series-1…8`), with separate light and dark steps. The palette has been checked for colorblind separation and lightness on these surfaces. Slots are **assigned in fixed order and never cycled.** Past seven series, the rest fold into a muted "Other".
- **Color follows the entity.** On Performance, a pinned holding keeps its slot when others are added or removed.
- **One y-axis per chart.** Different measures get separate charts, such as Usage's tokens and cost.
- **Marks:**
  - lines 2px with round caps; areas a 10% wash
  - bars up to 24px wide, with 4px rounded ends at the top and square at the baseline
  - gridlines horizontal hairlines only
  - active dots ringed in the surface color
- **Legend** whenever there are two or more series. Labels and values use text tokens, never the series color.
- **Tooltip:** a crosshair and tooltip on every line chart, a per-bar tooltip on bars, all rendered on `material-thick`.
- **Signed data** (gains, MACD histogram) uses `--positive` / `--negative`, and the values carry signs.
- Several light-mode slots fall below 3:1 contrast against white, so charts rely on legends and the adjacent tables rather than color alone.

## Accessibility checklist

- Semantic landmarks: `nav` with `aria-label`, `main#main`, and a skip link
- `aria-current` on the active nav item; `role="radiogroup"` / `radio` on segmented controls; `role="switch"`; `role="meter"` on gauges
- Figures carry `aria-label`s. The radar also renders its scores as a screen-reader-only list
- Focus rings use `:focus-visible` with a 3px tinted outline
- `forced-colors` mode drops translucency for solid backgrounds
