---
name: Danabus Modern Transit
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#3f4850'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#707881'
  outline-variant: '#bfc7d2'
  surface-tint: '#006398'
  primary: '#006194'
  on-primary: '#ffffff'
  primary-container: '#007bb9'
  on-primary-container: '#fdfcff'
  inverse-primary: '#93ccff'
  secondary: '#9d4300'
  on-secondary: '#ffffff'
  secondary-container: '#fd761a'
  on-secondary-container: '#5c2400'
  tertiary: '#00628d'
  on-tertiary: '#ffffff'
  tertiary-container: '#007cb1'
  on-tertiary-container: '#fcfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cce5ff'
  primary-fixed-dim: '#93ccff'
  on-primary-fixed: '#001d31'
  on-primary-fixed-variant: '#004b73'
  secondary-fixed: '#ffdbca'
  secondary-fixed-dim: '#ffb690'
  on-secondary-fixed: '#341100'
  on-secondary-fixed-variant: '#783200'
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#89ceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004c6e'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Be Vietnam Pro
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Be Vietnam Pro
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: 0em
  headline-md:
    fontFamily: Be Vietnam Pro
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: 0em
  headline-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: 0em
  body-xl:
    fontFamily: Be Vietnam Pro
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 30px
    letterSpacing: 0em
  body-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0em
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  label-lg:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Be Vietnam Pro
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 1.5rem
  gutter-desktop: 2rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.375rem
  space-sm: 0.75rem
  space-md: 1.25rem
  space-lg: 1.75rem
  space-xl: 2.5rem
---

## Brand & Style

This design system expresses a bright, coastal civic utility tailored for central Vietnam's urban transit corridor between Da Nang and Hoi An. The design language marries civic clarity with seaside freshness: calm, open, and instantly parseable under direct tropical sunlight.

### Personality & Demographics
- **Audience:** Everyday commuters, multi-generational families (including elderly passengers needing effortless legibility), and domestic/international tourists navigating cross-city journeys.
- **Tone:** Inviting, reliable, sunny, and stress-free. It removes the friction of transit schedules through immediate optical hierarchy.
- **Design Movement:** Modern Minimalist with tactile utility. It balances clean open whitespace with touch-friendly, physical affordances—avoiding decorative fluff while providing large, comforting interactive targets.

## Colors

The palette draws directly from Da Nang’s maritime identity and iconic intercity fleet markings:
- **Primary (`#0284C7` - Ocean Bus Blue):** Represents civic trust, clear skies, and primary navigation corridors. Used for top application bars, active transit routes, and primary actions.
- **Secondary (`#F97316` - Energetic Fleet Orange):** Evokes the recognizable express buses (FUTA / Kim Long lines), transfer warnings, live tracking indicators, and real-time transit highlights.
- **Tertiary (`#0EA5E9` - Coastal Cyan):** Supporting accent for interactive map pins, water transport links, and secondary interactive states.
- **Neutral Surface & Base (`#0F172A` - Deep Abyssal Slate):** Provides AAA contrast for high-noon readability on phone displays. Paired with clean off-white tinted canvas backgrounds (`#F8FAFC` to `#FFFFFF`) to reduce glare while preserving crisp line definition.

## Typography

The design system exclusively adopts **Be Vietnam Pro** across all typographic applications. Engineered for Vietnamese diacritics and complex tone marks, it avoids tone-clipping while offering exceptional legibility for both Latin and Vietnamese text.

Type sizing leans intentionally large to ensure elderly users and hurried transit travelers can glean route numbers, stop names, and countdown timers at arm's length without eye strain.

## Layout & Spacing

A fluid grid system built to accommodate dynamic mobile transit scenarios:
- **Mobile (<768px):** Single-column layout with 16px (`1rem`) outer margins and high-density, touch-prioritized card arrangements. Floating sticky bottom drawers accommodate one-handed operation.
- **Tablet (768px–1024px):** Split-view orientation with a persistent route list pane (360px) and an adaptive live map canvas.
- **Desktop (>1024px):** Centered operational shell (max-width 1280px) flanked by 48px (`3rem`) safety margins.

Spacing embraces generous breathing room around text blocks and schedule timelines, preventing tap accidents on crowded moving vehicles.

## Elevation & Depth

Visual hierarchy uses **tonal layering and warm ambient diffusion** rather than harsh outlines or muddy shadows:
- **Canvas Base:** Soft warm mist (`#F8FAFC`).
- **Cards & Surfaces:** Pure crisp white (`#FFFFFF`) with a subtle 1px border (`#E2E8F0`) paired with an ambient tinted drop shadow: `0 8px 24px -4px rgba(2, 132, 199, 0.07)` to convey a floating, airy coastal feel.
- **Tactile Depth:** Actionable components use physical press depth. Floating bottom action sheets and live GPS badges sit at an elevated plane (`0 12px 32px -6px rgba(15, 23, 42, 0.12)`), clearly demarcating interaction from the background map canvas.

## Shapes

The interface embraces a gentle, human-centric geometry with standard `rounded-2xl` (1rem / 16px) foundations across card modules, bottom sheets, and route cards. Status pills, route identifiers, and floating control buttons transition into full pill-shapes (`rounded-full`) to communicate direct clickability and avoid sharp edges in rapid-scan environments.

## Components

### Buttons
- **Primary:** High-profile pill or rounded-2xl block, filled with Ocean Bus Blue (`#0284C7`), text in pure white (`#FFFFFF`), minimum target height of 52px. Active press transitions with a 2px downward transform and a subtle inner shadow.
- **Accent (Live Tracking / Quick Book):** Bus Orange (`#F97316`) filled with high-contrast white text, used for critical alerts and express routes.
- **Secondary / Ghost:** White background, 1.5px solid border in `#CBD5E1`, text in Slate (`#0F172A`).

### Route Cards & Transit Modules
- Generously padded surfaces (20px internal padding) using soft borders (`#E2E8F0`).
- Route badges display large condensed numbers (e.g., **R16**, **01**) inside a distinct color-coded pill with generous horizontal padding (16px).
- Arrival indicators feature prominent ETA numerals (`3 phút`) styled with `headline-md` weight.

### Chips & Filters
- Compact pill-shaped tags (`rounded-full`) for transit modes: "Xe Buýt Trợ Giá", "Tuyến Liên Tỉnh", "Đang Hoạt Động".
- Selected state fills with solid Ocean Bus Blue or Bus Orange; unselected state retains a light neutral slate background (`#F1F5F9`) with dark slate typography.

### Input Fields & Search Bars
- Search stops feature 56px minimum height, pre-fixed with recognizable transit icons (bus, location pin).
- Background uses soft surface white with a 1.5px boundary in `#CBD5E1`. On focus, transitions cleanly to a 2px `#0284C7` ring with soft blue glow.

### Real-Time Bus Arrival & Stop Timeline
- Step-indicator list with 24px circular nodes connected by a 3px continuous guide line (`#E2E8F0` for passed stops, `#0284C7` for upcoming path).
- Moving bus vehicle icons animate smoothly along the vector path using the secondary Orange badge for immediate glanceability.