import type {
  AreaType,
  FurnishingType,
  HousePredictionRequest,
  OwnershipType,
  ParkingType,
  StatusType,
  TransactionType,
} from "../types/api";

export const DEFAULT_PREDICTION_REQUEST: HousePredictionRequest = {
  location: "bangalore",
  area_sqft: 1500,
  area_type: "carpet",
  bhk: 3,
  bathroom: 3,
  balcony: 2,
  floor_number: 5,
  total_floors: 12,
  transaction: "New Property",
  status: "Ready to Move",
  furnishing: "Semi-Furnished",
  ownership: "Freehold",
  facing: "East",
  parking_count: 1,
  parking_type: "Covered",
  society: "Missing",
  overlooking: "Missing",
};

export const AREA_TYPE_OPTIONS: { value: AreaType; label: string; hint: string }[] = [
  { value: "carpet", label: "Carpet Area", hint: "Usable inner floor area" },
  { value: "super", label: "Super Area", hint: "Built-up + common share" },
];

export const TRANSACTION_OPTIONS: TransactionType[] = ["Resale", "New Property"];

export const STATUS_OPTIONS: { value: StatusType; label: string }[] = [
  { value: "Ready to Move", label: "Ready to Move" },
  { value: "Missing", label: "Not Specified (Missing)" },
];

export const FURNISHING_OPTIONS: { value: FurnishingType; label: string }[] = [
  { value: "Unfurnished", label: "Unfurnished" },
  { value: "Semi-Furnished", label: "Semi-Furnished" },
  { value: "Furnished", label: "Furnished" },
  { value: "Missing", label: "Not Specified (Missing)" },
];

export const OWNERSHIP_OPTIONS: { value: OwnershipType; label: string }[] = [
  { value: "Freehold", label: "Freehold" },
  { value: "Leasehold", label: "Leasehold" },
  { value: "Co-operative Society", label: "Co-operative Society" },
  { value: "Power Of Attorney", label: "Power Of Attorney" },
  { value: "Missing", label: "Not Specified (Missing)" },
];

// Matches the 9 normalized compass categories learned by CategoricalEncoder in the trained pipeline
export const FACING_OPTIONS: { value: string; label: string }[] = [
  { value: "East", label: "East" },
  { value: "North-East", label: "North-East" },
  { value: "North", label: "North" },
  { value: "North-West", label: "North-West" },
  { value: "West", label: "West" },
  { value: "South-West", label: "South-West" },
  { value: "South", label: "South" },
  { value: "South-East", label: "South-East" },
  { value: "Missing", label: "Not Specified (Missing)" },
];

export const PARKING_TYPE_OPTIONS: { value: ParkingType; label: string }[] = [
  { value: "Covered", label: "Covered" },
  { value: "Open", label: "Open" },
  { value: "Other", label: "Other" },
  { value: "Missing", label: "None / Not Specified (Missing)" },
];

// All 81 Indian cities from Data/house_prices.csv used when training LocationEncoder
export const FALLBACK_TRAINED_CITIES: string[] = [
  "agra",
  "ahmadnagar",
  "ahmedabad",
  "allahabad",
  "aurangabad",
  "badlapur",
  "bangalore",
  "belgaum",
  "bhiwadi",
  "bhiwandi",
  "bhopal",
  "bhubaneswar",
  "chandigarh",
  "chennai",
  "coimbatore",
  "dehradun",
  "durgapur",
  "ernakulam",
  "faridabad",
  "ghaziabad",
  "goa",
  "greater-noida",
  "guntur",
  "gurgaon",
  "guwahati",
  "gwalior",
  "haridwar",
  "hyderabad",
  "indore",
  "jabalpur",
  "jaipur",
  "jamshedpur",
  "jodhpur",
  "kalyan",
  "kanpur",
  "kochi",
  "kolkata",
  "kozhikode",
  "lucknow",
  "ludhiana",
  "madurai",
  "mangalore",
  "mohali",
  "mumbai",
  "mysore",
  "nagpur",
  "nashik",
  "navi-mumbai",
  "navsari",
  "nellore",
  "new-delhi",
  "noida",
  "palakkad",
  "palghar",
  "panchkula",
  "patna",
  "pondicherry",
  "pune",
  "raipur",
  "rajahmundry",
  "ranchi",
  "satara",
  "shimla",
  "siliguri",
  "solapur",
  "sonipat",
  "surat",
  "thane",
  "thrissur",
  "tirupati",
  "trichy",
  "trivandrum",
  "udaipur",
  "udupi",
  "vadodara",
  "vapi",
  "varanasi",
  "vijayawada",
  "visakhapatnam",
  "vrindavan",
  "zirakpur",
];

export interface PropertyPreset {
  name: string;
  subtitle: string;
  payload: HousePredictionRequest;
}

export const PROPERTY_PRESETS: PropertyPreset[] = [
  {
    name: "Bangalore 3 BHK",
    subtitle: "1,500 sqft carpet · New Property",
    payload: {
      ...DEFAULT_PREDICTION_REQUEST,
    },
  },
  {
    name: "New Delhi 2 BHK",
    subtitle: "1,050 sqft carpet · Resale",
    payload: {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "new-delhi",
      area_sqft: 1050,
      area_type: "carpet",
      bhk: 2,
      bathroom: 2,
      balcony: 1,
      floor_number: 2,
      total_floors: 4,
      transaction: "Resale",
      furnishing: "Unfurnished",
      facing: "North-East",
    },
  },
  {
    name: "Mumbai 3 BHK",
    subtitle: "1,400 sqft carpet · Furnished",
    payload: {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "mumbai",
      area_sqft: 1400,
      area_type: "carpet",
      bhk: 3,
      bathroom: 3,
      balcony: 2,
      floor_number: 11,
      total_floors: 22,
      transaction: "Resale",
      furnishing: "Furnished",
      facing: "West",
      society: "Provided",
      overlooking: "Garden/Park",
    },
  },
  {
    name: "Pune 2 BHK",
    subtitle: "980 sqft super · Semi-Furnished",
    payload: {
      ...DEFAULT_PREDICTION_REQUEST,
      location: "pune",
      area_sqft: 980,
      area_type: "super",
      bhk: 2,
      bathroom: 2,
      balcony: 2,
      floor_number: 4,
      total_floors: 10,
      transaction: "New Property",
      furnishing: "Semi-Furnished",
      facing: "East",
    },
  },
];

export const BATCH_MAX_ITEMS = 500;
