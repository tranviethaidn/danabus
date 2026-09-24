---
name: Urban Transit Pulse
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
  on-surface-variant: '#3d4a42'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#6d7a72'
  outline-variant: '#bccac0'
  surface-tint: '#006c4a'
  primary: '#006948'
  on-primary: '#ffffff'
  primary-container: '#00855d'
  on-primary-container: '#f5fff7'
  inverse-primary: '#68dba9'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#825100'
  on-tertiary: '#ffffff'
  tertiary-container: '#a36700'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#85f8c4'
  primary-fixed-dim: '#68dba9'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#005137'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 36px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '700'
    lineHeight: 24px
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-route-badge:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '800'
    lineHeight: 22px
  label-eta-countdown:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '700'
    lineHeight: 20px
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

### Personality & Emotional Response
The design system embodies the reliability, clarity, and vitality of next-generation urban mobility. It delivers a calming, stress-free transit experience for users of all ages—from daily commuters and students to senior citizens navigating public transit. The interface feels prompt, civic-minded, and environmentally conscious, instilling trust through real-time accuracy and crystal-clear route guidance.

### Design Movement
**Modern Utility & Clean Transit Humanism**: Combining the functional legibility of civic signage with contemporary digital fluidity. The system leverages crisp neutral canvas layers, soft rounded contours, high-contrast typography, and purposeful real-time visual anchors (live pulse pings, route badges, countdown indicators). It prioritizes effortless readability under direct sunlight and high-stress on-the-go scenarios.

## Colors

### Palette Philosophy
- **Primary (`#059669` / `#10B981`) - Eco Transit Emerald**: Anchors core navigation, active route paths, on-time statuses, and primary call-to-actions. Represents green, sustainable urban transport.
- **Secondary (`#0284C7`) - Transit Ocean Blue**: Used for hubs, interchange stations, multi-modal connections (metro, ferry, bus), and informational route layers.
- **Tertiary / Live Accent (`#F59E0B` / `#D97706`) - Dynamic Alert Amber**: Dedicated strictly to urgency—approaching vehicle alerts, traffic delays, crowd congestion warnings, and live countdown timers under 3 minutes.
- **Neutrals**:
  - Main Text / Headings: Slate 900 (`#0F172A`) for maximum contrast and glare legibility.
  - Secondary Text / Timestamps: Slate 500 (`#64748B`).
  - Dividers & Subdued Borders: Slate 200 (`#E2E8F0`).
  - App Canvas Surface: Slate 50 (`#F8FAFC`).
  - Card & Modal Elevations: Pure White (`#FFFFFF`).

## Typography

### Rationale & Rules
- **Vietnamese Diacritics Fidelity**: **Plus Jakarta Sans** provides open counters, balanced ascenders/descenders, and full tone mark balance, preventing clipping on stacked accents (`ấ`, `ở`, `ễ`).
- **Route Badges (`label-route-badge`)**: Uses extra-bold weights (`800`) with tabular numeral alignments (`font-variant-numeric: tabular-nums`) so bus identifiers (e.g., `01`, `109`, `BRT01`) retain uniform spacing on maps and lists.
- **Live ETA & Timers (`label-eta-countdown`)**: Prominently emphasized to ensure passengers catching moving buses can grasp countdown metrics in a 200ms glance.

## Layout & Spacing

### Layout Architecture
- **Desktop / Web Split View**: Fixed-width side exploration dock (420px to 480px) on the left paired with a fluid, full-bleed interactive map canvas on the right.
- **Mobile & PWA Bottom-Sheet Pattern**: Sticky map viewport with multi-tier draggable drawer (peek 88px, half 45vh, expanded 90vh) ensuring single-handed reachability on mobile devices.
- **Grid & Safe Margins**: Mobile viewport enforces a 16px lateral margin with 12px card gutters; desktop panels use 24px margins with 16px internal grid gaps.

## Elevation & Depth

### Depth Model
The system uses **Tonal Layering with Crisp Atmospheric Shadows** to preserve instant hierarchy above complex vector maps.

1. **Level 0 (Map & Canvas Ground)**: `#F8FAFC`, non-elevated.
2. **Level 1 (Station Panels, List Items)**: `#FFFFFF` with border `1px solid #E2E8F0` and `box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05)`.
3. **Level 2 (Active Trip Cards, Search Bars, Modals)**: `#FFFFFF` with `box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.08), 0 2px 4px -1px rgba(15, 23, 42, 0.04)`.
4. **Level 3 (Floating Map Action Buttons, Live ETA Popovers)**: Pill/Circle shapes with `box-shadow: 0 10px 25px -5px rgba(5, 150, 105, 0.18), 0 8px 10px -6px rgba(15, 23, 42, 0.08)`.

## Shapes

### Shape Language
- Standard interactive elements, cards, and input groups adopt a cohesive `rounded-md` (0.5rem / 8px) to `rounded-lg` (1rem / 16px) contour.
- Floating controls, route badges, transit mode pills, and live ETA tags use full pill borders (`rounded-full` / 9999px) to communicate tap readiness and human friendliness.

## Components

### 1. Bus Number Badges
- **Display**: High-contrast contrast container.
  - Main Routes: Emerald green fill (`#059669`) with pure white text (`#FFFFFF`).
  - Inter-provincial / Express: Ocean blue fill (`#0284C7`) with white text.
  - Night / Specialized: Deep slate (`#0F172A`) with emerald border.
- **Geometry**: Compact rectangular pill, height `32px`, min-width `44px`, horizontal padding `8px`, centered text with tabular figures.

### 2. Live Countdown & ETA Indicator
- **Normal Status (< 10 mins)**: Emerald badge with subtle pulse ping dot (`#10B981`).
- **Urgent (< 3 mins / Approaching)**: Amber background (`#FEF3C7`), text color Amber 800 (`#92400E`), icon alert indicator with active rhythm ripple.
- **Delayed / Off-schedule**: Rose 50 background (`#FFF1F2`), text Rose 700 (`#BE123C`).

### 3. Step-by-Step Wayfinding Card (Chỉ dẫn từng bước)
- Continuous vertical progress rail connecting nodes with 2px dashed/solid lines.
- Walk segments render in neutral slate dots; bus segments render in solid emerald green line.
- Node icons: Walking man, Transfer interchange hub badge, Bus arrival icon.

### 4. Interactive Input & Quick Route Search
- Full-width tactile input container with dual-icon triggers (Origin pin green `#059669`, Destination flag blue `#0284C7`).
- Includes clear button ("X") and real-time reverse direction toggle button (`SwapVertical`).
- Focused state: 2px ring in Emerald 500 (`#10B981`) with zero layout shift.

### 5. Quick Filter Chips
- Horizontal sliding group: "Gần bạn nhất", "Xe sắp đến (< 5p)", "Tuyến có máy lạnh", "Tuyến điện tử (E-bus)".
- Unselected: White surface with Slate 200 border, Slate 700 text.
- Selected: Emerald 50 surface, Emerald 700 text, 1.5px solid Emerald 600 border.

### 6. Station Stop Card (Thẻ trạm dừng)
- Contains station code, Vietnamese station title, distance (e.g., `Cách 180m`), and an inline horizontal carousel of upcoming buses with real-time countdown badges.