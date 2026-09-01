export const siteGeofences = [
  { 
    siteId: "S003", 
    name: "Bangalore Metro & Quarry Hub", 
    center: [12.9716, 77.5946], 
    radius: 800 
  },
  { 
    siteId: "S001", 
    name: "Delhi Highway Corridor Site", 
    center: [28.6139, 77.2090], 
    radius: 900 
  },
  { 
    siteId: "S002", 
    name: "Mumbai Coastal Expressway Site", 
    center: [19.0760, 72.8777], 
    radius: 750 
  },
  { 
    siteId: "S006", 
    name: "Ahmedabad Industrial Park Hub", 
    center: [23.0225, 72.5714], 
    radius: 850 
  }
];

export const initialAssets = [
  {
    id: "EQX1001",
    name: "Cat 320 Hydraulic Excavator",
    type: "Excavator",
    siteId: "S003",
    siteName: "Bangalore Metro & Quarry Hub",
    status: "ACTIVE",
    checkOutDate: "2026-08-01",
    checkInDate: "2026-09-01",
    engineHours: 1149.2,
    idleHours: 191.4,
    fuelLevel: 80.2,
    tiltAngle: 12.7,
    speedKmH: 8.5,
    coords: [12.9716, 77.5946],
    isAnomaly: false,
    hoursSinceMaintenance: 242.2,
    trail: [
      [12.9710, 77.5940],
      [12.9713, 77.5943],
      [12.9716, 77.5946]
    ]
  },
  {
    id: "EQX1002",
    name: "Cat 777 Heavy Crane",
    type: "Crane",
    siteId: "S003",
    siteName: "Bangalore Metro & Quarry Hub",
    status: "CRITICAL_ALERT",
    checkOutDate: "2026-08-01",
    checkInDate: "2026-08-25",
    engineHours: 850.0,
    idleHours: 320.5,
    fuelLevel: 42.0,
    tiltAngle: 34.8,
    speedKmH: 22.0,
    coords: [12.9745, 77.5985], // Breaching edge of geofence
    isAnomaly: true,
    anomaly: "Critical Tilt Hazard (34.8°) & Boundary Exit",
    hoursSinceMaintenance: 410.0,
    trail: [
      [12.9720, 77.5950],
      [12.9735, 77.5970],
      [12.9745, 77.5985]
    ]
  },
  {
    id: "EQX1003",
    name: "Cat D6 Track Bulldozer",
    type: "Bulldozer",
    siteId: "S003",
    siteName: "Bangalore Metro & Quarry Hub",
    status: "ACTIVE",
    checkOutDate: "2026-08-05",
    checkInDate: "2026-09-10",
    engineHours: 920.4,
    idleHours: 45.2,
    fuelLevel: 88.5,
    tiltAngle: 3.1,
    speedKmH: 6.2,
    coords: [12.9698, 77.5925],
    isAnomaly: false,
    hoursSinceMaintenance: 110.5,
    trail: [
      [12.9685, 77.5910],
      [12.9692, 77.5918],
      [12.9698, 77.5925]
    ]
  },
  {
    id: "EQX1004",
    name: "Cat 140 Motor Grader",
    type: "Grader",
    siteId: "S003",
    siteName: "Bangalore Metro & Quarry Hub",
    status: "IDLE_WARNING",
    checkOutDate: "2026-08-10",
    checkInDate: "2026-08-30",
    engineHours: 450.0,
    idleHours: 310.0,
    fuelLevel: 51.0,
    tiltAngle: 4.8,
    speedKmH: 0.0,
    coords: [12.9728, 77.5932],
    isAnomaly: false,
    anomaly: "Excessive Idling Ratio Flagged",
    hoursSinceMaintenance: 310.0,
    trail: [
      [12.9728, 77.5932]
    ]
  }
];