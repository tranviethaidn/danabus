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

export type FrequencyType = 'fixed' | 'range' | 'peak_offpeak' | 'irregular';

export interface Frequency {
  type?: FrequencyType;
  peakMinutes?: number | null;
  offPeakMinutes?: number | null;
  minMinutes?: number | null;
  maxMinutes?: number | null;
  exactHeadway?: boolean;
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

export type FareType = 'flat' | 'distance_tiered' | 'unknown';

export interface FareTier {
  name: string;
  distanceMaxKm?: number | null;
  price: number;
  targetGroup?: 'all' | 'standard' | 'student';
}

export interface FareProvenance {
  source: 'subsidized_policy' | 'official_fare_table' | 'operator_notice' | 'unknown';
  verifiedAt?: string;
  note?: string;
}

export interface FareInfo {
  type?: FareType;
  flatPrice?: number | null;
  singleTicket?: number | null;
  minPrice?: number | null;
  maxPrice?: number | null;
  studentPrice?: number | null;
  tiers?: FareTier[];
  monthlyRegular?: number | null;
  monthlyPriority?: number | null;
  provenance?: FareProvenance;
  rawSummary?: string;
}

export type ScheduleStatus =
  | 'before_service'
  | 'in_service'
  | 'after_service'
  | 'next_day'
  | 'unknown';

export interface ScheduleDepartureResult {
  status: ScheduleStatus;
  timeStr: string | null;
  minutesUntilDeparture: number | null;
  minutesLeft: number | null;
  isOperating: boolean;
  isNextDay: boolean;
  source: 'timetable' | 'frequency' | 'unknown';
  message: string;
  trip?: TimetableTrip | null;
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
 * Task 8: Data Quality Contract & Planner Readiness Interfaces
 */
export interface DirectionStopMetrics {
  total: number;
  verified: number;
  unresolved: number;
}

export interface DirectionDataQuality {
  stopsReady: boolean;
  geometryReady: boolean;
  eligibleForPlanning: boolean;
  reason?: string | null;
}

export interface DataQuality {
  hasOutboundStops: boolean;
  hasInboundStops: boolean;
  hasOutboundGeometry: boolean;
  hasInboundGeometry: boolean;
  hasFareModel: boolean;
  tripPlanningReady: boolean;
  directions: {
    outbound: DirectionDataQuality;
    inbound: DirectionDataQuality;
  };
  stopMetrics: {
    outbound: DirectionStopMetrics;
    inbound: DirectionStopMetrics;
  };
  ineligibilityReasons?: string[];
  evaluatedAt?: string;
}

export interface NearbyStopCandidate extends BusStop {
  id?: string;
  distanceMeters: number;
}

export interface NearbyStopsOptions {
  maxDistanceMeters?: number;
  limit?: number;
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
  dataQuality?: DataQuality;
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
