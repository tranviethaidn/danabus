/**
 * Danabus SVG Icon System
 * Eliminates font-loading delays, ligature failures, and offline rendering issues.
 */

const DanabusIcons = {
  directions_bus: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>`,
  
  headset_mic: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 1a9 9 0 0 0-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h4v1h-7v2h7c1.66 0 3-1.34 3-3V10a9 9 0 0 0-9-9z"/></svg>`,
  
  my_location: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0 0 13 3.06V1h-2v2.06A8.994 8.994 0 0 0 3.06 11H1v2h2.06A8.994 8.994 0 0 0 11 20.94V23h2v-2.06A8.994 8.994 0 0 0 20.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>`,
  
  location_on: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>`,
  
  swap_vert: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M16 17.01V10h-2v7.01h-3L15 21l4-3.99h-3zM9 3L5 6.99h3V14h2V6.99h3L9 3z"/></svg>`,
  
  swap_horiz: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M6.99 11L3 15l3.99 4v-3H14v-2H6.99v-3zM21 9l-3.99-4v3H10v2h7.01v3L21 9z"/></svg>`,
  
  mic: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/></svg>`,
  
  arrow_forward: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>`,
  
  arrow_back: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>`,
  
  north_east: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M9 5v2h6.59L4 18.59 5.41 20 17 8.41V15h2V5H9z"/></svg>`,
  
  home: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>`,
  
  alt_route: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M19.5 4a3.5 3.5 0 0 0-3.5 3.5c0 1.15.56 2.16 1.42 2.79l-4.42 4.42-2.12-2.12c.57-.68.91-1.56.91-2.52 0-2.17-1.76-3.93-3.93-3.93A3.93 3.93 0 0 0 3.93 10.07 3.93 3.93 0 0 0 7.86 14c.96 0 1.84-.34 2.52-.91l2.12 2.12-3.13 3.13c-.23-.1-.48-.16-.74-.16a1.86 1.86 0 1 0 1.86 1.86c0-.26-.06-.51-.16-.74l3.13-3.13 4.42 4.42c-.63.86-.71 1.99-.08 2.92.74 1.09 2.22 1.37 3.31.63 1.09-.74 1.37-2.22.63-3.31a2.49 2.49 0 0 0-3.31-.63l-4.14-4.14 4.14-4.14c.54.34 1.19.54 1.88.54 1.93 0 3.5-1.57 3.5-3.5S21.43 4 19.5 4z"/></svg>`,
  
  support_agent: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M21 12.22C21 6.73 16.74 3 12 3c-4.69 0-9 3.65-9 9.28-.6.34-1 .98-1 1.72v2c0 1.1.9 2 2 2h1v-6.1c0-3.87 3.13-7 7-7s7 3.13 7 7V19h-8v2h8c1.1 0 2-.9 2-2v-1.22c.59-.31 1-.92 1-1.64v-2.3c0-.7-.41-1.31-1-1.62z"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M18 11.03C17.52 8.18 15.04 6 12.05 6c-3.03 0-6.29 2.51-6.03 6.45 2.47-.14 4.73-1.42 5.98-3.45 1.25 2.1 3.58 3.53 6 3.03z"/></svg>`,
  
  temple_buddhist: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 2L9 6h6l-3-4zm7 5H5v2h14V7zm-2 3H7v7h10v-7zm-4 5h-2v-3h2v3zm9 3H2v2h20v-2z"/></svg>`,
  
  waves: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 18c-3.11 0-5.26-1.5-7.23-2.88C3.12 13.97 1.56 13 0 13v-2c2.06 0 3.96 1.32 5.92 2.69C7.88 15.06 9.77 16 12 16s4.12-.94 6.08-2.31C20.04 12.32 21.94 11 24 11v2c-1.56 0-3.12.97-4.77 2.12C17.26 16.5 15.11 18 12 18zM12 12c-3.11 0-5.26-1.5-7.23-2.88C3.12 7.97 1.56 7 0 7V5c2.06 0 3.96 1.32 5.92 2.69C7.88 9.06 9.77 10 12 10s4.12-.94 6.08-2.31C20.04 6.32 21.94 5 24 5v2c-1.56 0-3.12.97-4.77 2.12C17.26 10.5 15.11 12 12 12z"/></svg>`,
  
  landscape: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M14 6l-3.75 5 2.85 3.8-1.6 1.2C9.81 13.75 7 10 7 10l-6 8h22L14 6z"/></svg>`,
  
  tour: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M21 4H7V2H5v20h2v-8h14l-2-5 2-5zm-3.86 5.82l.73 1.83-8.87.35V5.98l8.87.35-.73 1.83 1.05 1.66z"/></svg>`,
  
  flight: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/></svg>`,
  
  attractions: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>`,
  
  local_hospital: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M19 3H5c-1.1 0-1.99.9-1.99 2L3 19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-1 11h-4v4h-4v-4H6v-4h4V6h4v4h4v4z"/></svg>`,
  
  schedule: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/></svg>`,
  
  search: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>`,
  
  close: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>`,
  
  chevron_right: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>`,
  
  call: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M20.01 15.38c-1.23 0-2.42-.2-3.53-.56a.977.977 0 0 0-1.01.24l-2.2 2.2a15.053 15.053 0 0 1-6.59-6.59l2.2-2.21a.96.96 0 0 0 .25-1.01A11.36 11.36 0 0 1 8.5 3.99c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1 0 9.39 7.61 17 17 17 .55 0 1-.45 1-1v-3.5c0-.55-.45-1-1-1-.01-.11.01-.11.01-.11z"/></svg>`,
  
  eco: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M16 3c-4.42 0-8 3.58-8 8 0 1.95.7 3.73 1.86 5.14L3 23h3.5l5.14-5.14C13.05 18.57 14.47 19 16 19c4.42 0 8-3.58 8-8s-3.58-8-8-8zm0 14c-1.63 0-3.11-.65-4.22-1.71L16 11V5c3.31 0 6 2.69 6 6s-2.69 6-6 6z"/></svg>`,
  
  bolt: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.9 17.55 11 21 11 21z"/></svg>`,
  
  electric_bolt: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M15 2H9c-1.1 0-2 .9-2 2v7h2V4h6v7h2V4c0-1.1-.9-2-2-2zm-3 9l-4 7h3v6l4-7h-3v-6z"/></svg>`,
  
  timelapse: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M16.24 7.76A5.974 5.974 0 0 0 12 6v6l-4.24 4.24c2.34 2.34 6.14 2.34 8.49 0a5.99 5.99 0 0 0-.01-8.48zM12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>`,
  
  straighten: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M21 6H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 10H3V8h2v4h2V8h2v4h2V8h2v4h2V8h2v4h2V8h3v8z"/></svg>`,
  
  confirmation_number: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M22 10V6c0-1.11-.9-2-2-2H4c-1.1 0-1.99.89-1.99 2v4c1.1 0 1.99.9 1.99 2s-.89 2-2 2v4c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2v-4c-1.1 0-2-.9-2-2s.9-2 2-2zm-9 7.5h-2v-2h2v2zm0-4.5h-2v-2h2v2zm0-4.5h-2v-2h2v2z"/></svg>`,
  
  route: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M19 15.18V7c0-2.21-1.79-4-4-4s-4 1.79-4 4v10c0 1.1-.9 2-2 2s-2-.9-2-2V8.82C8.16 8.4 9 7.3 9 6c0-1.66-1.34-3-3-3S3 4.34 3 6c0 1.3.84 2.4 2 2.82V17c0 2.21 1.79 4 4 4s4-1.79 4-4V7c0-1.1.9-2 2-2s2 .9 2 2v8.18c-1.16.41-2 1.51-2 2.82 0 1.66 1.34 3 3 3s3-1.34 3-3c0-1.31-.84-2.41-2-2.82z"/></svg>`,
  
  timeline: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M23 8c0 1.1-.9 2-2 2-.18 0-.35-.02-.51-.07l-3.56 3.55c.05.16.07.34.07.52 0 1.1-.9 2-2 2s-2-.9-2-2c0-.18.02-.36.07-.52l-2.55-2.55c-.16.05-.34.07-.52.07s-.36-.02-.52-.07l-4.55 4.56c.05.16.07.33.07.51 0 1.1-.9 2-2 2s-2-.9-2-2 .9-2 2-2c.18 0 .35.02.51.07l4.56-4.55C8.02 9.36 8 9.18 8 9c0-1.1.9-2 2-2s2 .9 2 2c0 .18-.02.36-.07.52l2.55 2.55c.16-.05.34-.07.52-.07s.36.02.52.07l3.55-3.56C18.02 8.35 18 8.18 18 8c0-1.1.9-2 2-2s2 .9 2 2z"/></svg>`,
  
  map: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/></svg>`,
  
  picture_as_pdf: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 4.5h1v-2h-1v2z"/></svg>`,
  
  radar: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><circle cx="12" cy="12" r="2"/><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm0-14c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm0 10c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z"/></svg>`,
  
  payments: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M19 14V6c0-1.1-.9-2-2-2H3c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zm-9-1c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm13-6v11c0 1.1-.9 2-2 2H4v-2h17V7h2z"/></svg>`,
  
  electric_car: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M18.92 2.01C18.72 1.42 18.16 1 17.5 1h-11c-.66 0-1.21.42-1.42 1.01L3 8v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1V8l-2.08-5.99zM6.5 12c-.83 0-1.5-.67-1.5-1.5S5.67 9 6.5 9s1.5.67 1.5 1.5S7.33 12 6.5 12zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 7l1.5-4.5h11L19 7H5z"/></svg>`,
  
  notifications: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>`,
  
  trip_origin: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><circle cx="12" cy="12" r="8"/></svg>`,
  
  check: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
  
  check_circle: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>`,

  search_off: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14zM2.81 2.81L1.39 4.22l2.27 2.27C2.61 8.07 2 9.96 2 12c0 5.52 4.48 10 10 10 2.04 0 3.93-.61 5.51-1.66l2.27 2.27 1.41-1.41L2.81 2.81z"/></svg>`,

  expand_more: `<svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M16.59 8.59L12 13.17 7.41 8.59 6 10l6 6 6-6z"/></svg>`
};

function renderIcon(name, customClass = 'w-5 h-5') {
  const svg = DanabusIcons[name] || DanabusIcons['directions_bus'];
  return `<span class="inline-flex items-center justify-center shrink-0 ${customClass}">${svg}</span>`;
}

// Export to window
window.renderIcon = renderIcon;
window.DanabusIcons = DanabusIcons;
