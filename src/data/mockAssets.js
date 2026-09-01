export const initialAssets = [
  {
    id: "EQX1001",
    name: "Cat 320 Hydraulic Excavator",
    type: "Excavator",
    siteId: "S006",
    siteName: "Ahmedabad Metro Site S006",
    status: "ACTIVE",
    checkOutDate: "2026-08-01",
    checkInDate: "2026-09-01",
    engineHours: 1149.2,
    idleHours: 191.4,
    fuelLevel: 80.2,
    tiltAngle: 12.7,
    speedKmH: 0.0,
    coords: [23.021510, 72.571933],
    isAnomaly: false,
    hoursSinceMaintenance: 242.21,
    trail: [
      [23.021510, 72.571933],
      [23.021875, 72.569955],
      [23.022332, 72.571120]
    ]
  },
  {
    id: "EQX1002",
    name: "Cat 777 Heavy Crane",
    type: "Crane",
    siteId: null,
    siteName: "Unassigned Transit",
    status: "CRITICAL_ALERT",
    checkOutDate: "2026-08-01",
    checkInDate: "2026-08-25",
    engineHours: 850.0,
    idleHours: 320.5,
    fuelLevel: 42.0,
    tiltAngle: 28.5,
    speedKmH: 24.5,
    coords: [19.0760, 72.8777],
    isAnomaly: true,
    hoursSinceMaintenance: 410.0,
    trail: [
      [19.0710, 72.8720],
      [19.0760, 72.8777]
    ]
  },
  {
    id: "EQX1003",
    name: "Cat D6 Track Bulldozer",
    type: "Bulldozer",
    siteId: "S003",
    siteName: "Bangalore Quarry S003",
    status: "ACTIVE",
    checkOutDate: "2026-08-05",
    checkInDate: "2026-09-10",
    engineHours: 920.4,
    idleHours: 45.2,
    fuelLevel: 88.5,
    tiltAngle: 3.1,
    speedKmH: 7.2,
    coords: [12.971575, 77.594675],
    isAnomaly: false,
    hoursSinceMaintenance: 110.5,
    trail: [
      [12.9700, 77.5930],
      [12.971575, 77.594675]
    ]
  },
  {
    id: "EQX1004",
    name: "Cat 140 Motor Grader",
    type: "Grader",
    siteId: "S001",
    siteName: "Delhi Highway S001",
    status: "IDLE_WARNING",
    checkOutDate: "2026-08-10",
    checkInDate: "2026-08-30",
    engineHours: 450.0,
    idleHours: 310.0,
    fuelLevel: 51.0,
    tiltAngle: 4.8,
    speedKmH: 0.0,
    coords: [28.613930, 77.208991],
    isAnomaly: true,
    hoursSinceMaintenance: 310.0,
    trail: [
      [28.6120, 77.2070],
      [28.613930, 77.208991]
    ]
  }
];

export const siteGeofences = [
  { siteId: "S001", name: "Delhi Highway Site", center: [28.613930, 77.208991], radius: 1500 },
  { siteId: "S002", name: "Mumbai Coastal Infra", center: [19.076077, 72.877686], radius: 1200 },
  { siteId: "S003", name: "Bangalore Metro & Quarry", center: [12.971575, 77.594675], radius: 1000 },
  { siteId: "S006", name: "Ahmedabad Express Hub", center: [23.022468, 72.571417], radius: 1100 }
];