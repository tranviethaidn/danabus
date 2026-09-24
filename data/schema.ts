/**
 * TypeScript Schema Definitions for Danangbus PWA
 */

export type RouteCategory =
  | 'subsidized'       // Tuyến trợ giá (Phương Trang FUTA Bus Lines)
  | 'non_subsidized'   // Tuyến không trợ giá
  | 'interprovincial'  // Tuyến buýt liền kề / liên tỉnh (Đà Nẵng - Huế, Hội An, Tam Kỳ)
  | 'tourist'          // Tuyến buýt phục vụ du lịch
  | 'suspended';       // Tuyến tạm dừng hoạt động

export type RouteStatus = 'active' | 'suspended';

export type StopConfidence = 'high' | 'medium' | 'low' | 'unresolved';
export type StopStatus = 'verified' | 'unresolved';

export interface BusStop {
  order: number;
  name: string;
  street?: string;
  lat?: number | null;
  lng?: number | null;
  source?: string | null;
  confidence?: StopConfidence;
  status?: StopStatus;
}

export interface DirectionStops {
  outbound: BusStop[];
  inbound: BusStop[];
}

export interface RoutePathDirection {
  text: string;
  streets: string[];
}

export interface RoutePaths {
  outbound: RoutePathDirection;
  inbound: RoutePathDirection;
}

export interface OperatingHours {
  start: string;       // "HH:mm"
  end: string;         // "HH:mm"
  raw: string;         // "từ 05h30 đến 19h00..."
}

export interface Frequency {
  peakMinutes?: number | null;
  offPeakMinutes?: number | null;
  raw: string;
}

export interface DistanceKm {
  average?: number | null;
  outbound?: number | null;
  inbound?: number | null;
  raw?: string;
}

export interface Terminals {
  origin: string;
  destination: string;
}

export interface FareInfo {
  singleTicket?: number | null;
  monthlyRegular?: number | null;
  monthlyPriority?: number | null;
  rawSummary?: string;
}

export interface TimetableTrip {
  trip: number;
  departureTime?: string;
  timeline?: Record<string, string>;
}

export interface Timetable {
  outbound?: TimetableTrip[];
  inbound?: TimetableTrip[];
}

export interface RouteGeometryProvenance {
  source: string;
  pointsCount: number;
  verified: boolean;
  generatedAt?: string;
}

export interface RouteGeometry {
  outbound?: [number, number][] | null;
  inbound?: [number, number][] | null;
  provenance?: {
    outbound?: RouteGeometryProvenance;
    inbound?: RouteGeometryProvenance;
  };
}

/**
 * Full Bus Route Entity
 */
export interface BusRoute {
  id: string;                    // "05", "LK01", "21", "TKY-TMY"
  routeNumber: string;           // "05", "LK01", "21"
  name: string;                  // "Khu Chung cư Hòa Hiệp Nam – Công viên Biển Đông"
  shortName: string;             // "Hòa Hiệp Nam – CV Biển Đông"
  formerName?: string | null;    // "Xuân Diệu - Bến xe phía Nam"
  aliases?: string[];            // ["17", "R17A"]
  category: RouteCategory;
  status: RouteStatus;
  statusNote?: string | null;
  operator: string;
  terminals: Terminals;
  operatingHours: OperatingHours;
  frequency: Frequency;
  distanceKm: DistanceKm;
  fares: FareInfo;
  routePaths: RoutePaths;
  stops: DirectionStops;
  geometry?: RouteGeometry;
  timetable?: Timetable;
  vehicleInfo?: string;
  pdfUrls: string[];
}

/**
 * Lightweight Route Model for initial PWA load and fast search
 */
export interface BusRouteCompact {
  id: string;
  routeNumber: string;
  name: string;
  shortName: string;
  category: RouteCategory;
  status: RouteStatus;
  operator: string;
  terminals: Terminals;
  operatingHours: OperatingHours;
  frequency: Frequency;
  distanceKm?: number | null;
  singleFare?: number | null;
  totalStops: {
    outbound: number;
    inbound: number;
  };
  hasGeometry?: {
    outbound: boolean;
    inbound: boolean;
  };
  streets: string[];
  pdfUrls: string[];
}

/**
 * Normalized Bus Stop Entity
 */
export interface NormalizedBusStop {
  id: string;                    // "stop_0001"
  name: string;                  // "Bến xe Trung tâm"
  street?: string;               // "Cao Sơn Pháo"
  lat?: number | null;
  lng?: number | null;
  source?: string | null;
  confidence?: StopConfidence;
  status?: StopStatus;
  routes: Array<{
    routeId: string;
    routeNumber: string;
    direction: 'outbound' | 'inbound';
    stopOrder?: number;
  }>;
}

/**
 * Street Index: Street name to list of route numbers passing through it
 */
export type StreetRoutesIndex = Record<string, string[]>;
