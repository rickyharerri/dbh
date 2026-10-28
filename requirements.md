AquaWise Alberta

Product Requirements Document (PRD)

Version: 1.0
Application: AquaWise Alberta
Application Type: React Web Application
Backend: Python FastAPI
Data Platform: Databricks
AI Integration: Databricks Genie
Primary Dataset: Alberta Water Well Information Database
Deployment: Databricks Apps
Project Type: Microsoft + Databricks Hackathon

⸻

1. Project Overview

1.1 Product Description

AquaWise Alberta is a web application that helps Alberta residents understand historical groundwater conditions around properties they own or intend to purchase.

The application uses Alberta’s Water Well Information Database, hosted in Databricks, to provide groundwater information through a simple and interactive interface.

Users can select a location on a map, explore nearby historical water wells, review groundwater characteristics, compare properties, and ask questions using an AI assistant powered by Databricks Genie.

The application must be understandable to users without technical knowledge of groundwater systems.

1.2 Problem Statement

Many rural Alberta properties depend on private water wells.

When purchasing or maintaining these properties, homeowners may struggle to answer important questions:

* How deep are water wells around my property?
* How much water do nearby wells produce?
* Have neighbouring wells reported water-quality concerns?
* What groundwater information is available in my area?
* How does groundwater information compare between two properties?

Although Alberta maintains historical water-well records, these records can be difficult for ordinary residents to access and interpret.

AquaWise Alberta will simplify this information and make it accessible through an interactive application.

1.3 Project Objectives

The application must:

1. Connect securely to Databricks and retrieve groundwater data.
2. Allow users to select locations using an interactive map.
3. Display nearby historical water wells.
4. Present groundwater statistics in understandable language.
5. Display available water-quality observations.
6. Allow users to compare groundwater conditions between two locations.
7. Integrate Databricks Genie for natural-language questions.
8. Provide a clean, responsive, and intuitive user interface.

The application must not claim to certify water safety or predict the performance of an individual well.

⸻

2. Target Users

2.1 Primary Users

Rural Homeowners

People who own properties supplied by private water wells and want to understand historical groundwater conditions nearby.

Property Buyers

People considering purchasing acreages or rural properties in Alberta.

Real Estate Professionals

Realtors who want to help clients understand publicly available groundwater information.

2.2 Secondary Users

* Water-well drilling contractors
* Environmental consultants
* Municipal planners
* Agricultural landowners
* Groundwater researchers

2.3 User Accessibility

The application must not require users to understand technical groundwater terminology.

Technical measurements should include plain-language descriptions.

For example:

Instead of:

“Median static water level: 24.6 m”

Display:

“Typical recorded water level: 24.6 metres below ground.”

Include an information tooltip explaining what the measurement means.

⸻

3. Application Design Requirements

3.1 General Design Principles

The application must have a simple, modern interface.

Design requirements:

* Clean white background
* Blue and teal accent colours
* Minimal visual clutter
* Large, readable text
* Clear navigation
* Simple icons
* Responsive layouts
* Consistent buttons and cards
* Minimal animations
* No unnecessary visual effects

The application should feel like a practical public-information service rather than a complex enterprise dashboard.

3.2 Application Layout

The application will have a header, navigation, and main content area.

Header

Display:

* AquaWise Alberta logo/name
* Short tagline: “Understand the water beneath your property”
* About button

Navigation

Four main sections:

1. Explore Property
2. Water Quality
3. Compare Properties
4. Ask AquaWise

On desktop, navigation may appear as a horizontal menu.

On mobile, navigation should collapse into a compact menu.

3.3 User Authentication

Authentication is not required for the hackathon MVP.

Users should be able to explore the application without creating an account.

Databricks credentials must remain on the backend and must never be exposed to the browser.

⸻

4. Functional Requirements

FR-001: Property Location Selection

Priority: Must Have

Description

Users must be able to select a location in Alberta.

Requirements

The application must provide:

* Interactive Alberta map
* Search by place name, where a geocoding service is configured
* Ability to click directly on the map
* Latitude and longitude input as a fallback
* Search radius selector

Supported search radii:

* 1 km
* 2 km
* 5 km
* 10 km
* 20 km

Default radius: 5 km.

User Flow

1. User opens Explore Property.
2. User searches for a location or clicks on the map.
3. Application displays a location marker.
4. User selects a search radius.
5. User clicks “Analyze Groundwater.”
6. Application retrieves nearby well information from Databricks.

Acceptance Criteria

* Users can select a location on the map.
* Selected coordinates are displayed.
* Search radius can be changed.
* Analysis can be initiated.
* Invalid coordinates are rejected.
* Loading and error states are displayed.

⸻

FR-002: Nearby Water Wells

Priority: Must Have

Description

Display historical water wells surrounding the selected location.

Requirements

The application must:

* Retrieve well records from Databricks.
* Filter wells by geographic distance.
* Display nearby wells on the map.
* Show the total number of matching wells.
* Allow users to select individual wells.

Well Information

Where available, display:

Field	Description
Well ID	Unique historical well identifier
Location	Latitude and longitude
Well Depth	Recorded drilling depth
Drilling Date	Date the well was drilled
Well Yield	Reported water production
Static Water Level	Recorded water level
Well Status	Recorded status, if available

Actual field names must be mapped after inspecting the Databricks schema.

Map Interaction

When users click a well marker, display a small information panel containing:

* Well identifier
* Well depth
* Recorded yield
* Drilling date
* View Details button

Acceptance Criteria

* Nearby wells are correctly filtered by radius.
* Map markers represent actual dataset locations.
* Clicking a marker displays the corresponding well.
* Missing values display “Not available.”
* The interface clearly distinguishes historical records from current measurements.

⸻

FR-003: Groundwater Overview Dashboard

Priority: Must Have

Description

Display a summary of historical groundwater information around the selected location.

Dashboard Cards

Card 1: Nearby Wells

Total historical wells found within the selected radius.

Card 2: Typical Well Depth

Median depth of wells with available measurements.

Card 3: Typical Well Yield

Median recorded yield of wells with available measurements.

Card 4: Water Quality Records

Number of nearby wells with available water-quality observations.

Additional Visualizations

Display two simple charts:

Well Depth Distribution

Shows the distribution of recorded well depths.

Well Yield Distribution

Shows the distribution of reported well yields.

Charts must include measurement units.

Data Handling

* Exclude missing measurements from statistical calculations.
* Display sample counts.
* Prefer medians for typical values.
* Do not treat missing measurements as zero.
* Preserve the original measurement units or convert them explicitly.

Acceptance Criteria

* Summary cards use actual Databricks query results.
* Statistics update when the selected location changes.
* Charts match the filtered records.
* Missing data does not cause application errors.

⸻

FR-004: Water Quality Explorer

Priority: Must Have, Where Data Is Available

Description

Allow users to explore historical water-quality observations from nearby wells.

Requirements

Display available measurements such as:

* Arsenic
* Nitrate
* Iron
* Manganese
* Total dissolved solids
* Other parameters present in the dataset

The implementation must only expose parameters supported by actual source records.

Water Quality Table

Parameter	Recorded Value	Reference Guideline	Status
Iron	Available measurement	Applicable guideline	Comparison
Nitrate	Available measurement	Applicable guideline	Comparison
Arsenic	Available measurement	Applicable guideline	Comparison

The table must also identify the relevant well and sample date.

Status Indicators

Use:

Within Guideline

The recorded measurement is within the selected reference guideline.

Above Guideline

The recorded measurement exceeds the selected reference guideline.

No Data

No usable measurement is available.

Not Evaluated

No suitable guideline or valid comparison is available.

Guideline values must come from a documented reference source, including units and applicability.

Important Disclaimer

Display:

“Historical water-quality observations do not determine whether water at your property is safe to drink. Laboratory testing of your own water supply is recommended.”

Acceptance Criteria

* Only available measurements are displayed.
* Units are shown.
* Reference guidelines are documented.
* Missing measurements are clearly identified.
* The application never labels a property as safe or unsafe based solely on nearby records.

If the supplied dataset does not contain usable laboratory measurements, the MVP must display the available quality-related observations without inventing results.

⸻

FR-005: Property Comparison

Priority: Must Have

Description

Allow users to compare historical groundwater information around two locations.

Requirements

Users must be able to:

1. Select Property A.
2. Select Property B.
3. Choose a search radius.
4. Click “Compare Properties.”
5. View a side-by-side comparison.

Comparison Metrics

Metric	Property A	Property B
Nearby Wells	Count	Count
Median Well Depth	Metres	Metres
Median Well Yield	Source units	Source units
Quality Records	Count	Count
Low-Yield Records	Count	Count
Data Availability	Summary	Summary

Low-yield thresholds must be clearly defined and configurable.

Comparison Summary

Below the table, display a plain-language summary.

Example:

“Property A has historically shown higher median well yields than Property B. However, these measurements come from neighbouring wells and do not guarantee the performance of either property’s water supply.”

Acceptance Criteria

* Both properties can be selected independently.
* The comparison uses the same measurement definitions.
* The selected radius is clearly displayed.
* Missing values are handled correctly.
* Users can change locations and rerun comparisons.

⸻

FR-006: Databricks Genie AI Assistant

Priority: Must Have

Description

Provide a conversational interface allowing users to ask questions about groundwater data.

Requirements

The assistant must use Databricks Genie to answer supported natural-language questions.

Interface

The Ask AquaWise page must contain:

* Conversation history
* User message input
* Send button
* Loading indicator
* Suggested questions
* Clear conversation button

Suggested Questions

Display clickable examples:

* “How many water wells are near Cochrane?”
* “What is the typical well depth around Okotoks?”
* “Which nearby wells have low recorded yields?”
* “Compare historical groundwater conditions in two areas.”
* “What water-quality information is available?”

Genie Integration

The React application must communicate with Genie through the backend.

The backend must:

1. Receive the user’s question.
2. Identify the configured Genie Space.
3. Start or continue a Genie conversation.
4. Retrieve the response.
5. Return the response to React.
6. Preserve conversation context for follow-up questions.

Response Requirements

Genie responses should display:

* Natural-language answer
* Supporting data table, when available
* Query status
* Error message, if the query fails

Where available, the application should provide a way to inspect the underlying query or source records.

Important Behaviour

The AI must:

* Avoid inventing measurements.
* Clearly identify unavailable information.
* Avoid making unsupported water-safety claims.
* Distinguish historical evidence from current conditions.
* Explain uncertainty when data coverage is limited.

Acceptance Criteria

* Users can submit questions.
* The backend communicates successfully with Genie.
* Answers are displayed in the chat.
* Follow-up questions retain conversation context.
* Failed requests show understandable errors.
* No Databricks secrets are exposed to the browser.

⸻

FR-007: Individual Well Details

Priority: Should Have

Description

Allow users to inspect the details of a historical well.

Requirements

Clicking “View Details” opens a side panel or modal.

Display:

* Well identifier
* Geographic location
* Drilling date
* Well depth
* Recorded yield
* Static water level
* Available geological information
* Available water-quality observations

Fields should only appear when supported by the dataset.

The details panel should also identify the source dataset.

⸻

FR-008: Data Availability and Transparency

Priority: Must Have

Description

The application must explain how much historical data supports each analysis.

Requirements

Display:

* Number of matching wells
* Number of wells with depth measurements
* Number of wells with yield measurements
* Number of wells with water-quality records
* Latest available record date, where possible

When data is insufficient, display:

“Limited historical information is available for this location. Results may not represent current groundwater conditions.”

Do not generate an arbitrary numerical safety score.

⸻

5. Technical Architecture

5.1 Technology Stack

Layer	Technology
Frontend	React
Language	TypeScript
Build Tool	Vite
Styling	Tailwind CSS
UI Components	Simple reusable React components
Maps	React Leaflet
Charts	Recharts
Backend	Python FastAPI
Data Platform	Databricks
Database	Databricks Delta Tables
SQL Execution	Databricks SQL Warehouse
AI	Databricks Genie
Data Governance	Unity Catalog
Deployment	Databricks Apps

5.2 Architecture

                 USER
                   |
                   v
             React Web App
                   |
          HTTPS / REST API
                   |
                   v
             FastAPI Backend
                   |
          +--------+--------+
          |                 |
          v                 v
    Databricks SQL    Databricks Genie
          |                 |
          v                 |
     Unity Catalog          |
          |                 |
          v                 |
      Delta Tables <--------+
          |
          v
  Alberta Water Well Data

5.3 Frontend Responsibilities

React is responsible for:

* User interface
* Navigation
* Map interactions
* Location selection
* Displaying results
* Charts
* Comparison tables
* Chat interface
* Loading and error states

React must not connect directly to Databricks using privileged credentials.

5.4 Backend Responsibilities

FastAPI is responsible for:

* Validating user inputs
* Connecting to Databricks
* Executing parameterized SQL queries
* Performing spatial searches
* Calculating statistics
* Preparing comparison results
* Communicating with Genie
* Formatting API responses
* Handling errors
* Protecting credentials

5.5 Databricks Responsibilities

Databricks is responsible for:

* Hosting groundwater datasets
* Executing SQL queries
* Managing governed tables
* Performing spatial calculations
* Providing data to Genie
* Supporting AI-powered exploration

The backend should query the prepared Delta tables rather than downloading the entire dataset into the application.

⸻

6. Backend API Requirements

All endpoints must use the /api prefix.

API-001: Application Health

Endpoint

GET /api/health

Purpose

Check whether the backend is running.

Example response:

{
  "status": "healthy"
}

⸻

API-002: Search Nearby Wells

Endpoint

GET /api/wells/nearby

Parameters

latitude
longitude
radius_km
limit

Example:

/api/wells/nearby?latitude=51.19&longitude=-114.47&radius_km=5&limit=500

Example response:

{
  "location": {
    "latitude": 51.19,
    "longitude": -114.47
  },
  "radius_km": 5,
  "total_wells": 42,
  "returned_wells": 2,
  "wells": [
    {
      "well_id": "W001",
      "latitude": 51.192,
      "longitude": -114.472,
      "depth_m": 82,
      "yield_gpm": 12,
      "distance_km": 0.3
    },
    {
      "well_id": "W002",
      "latitude": 51.195,
      "longitude": -114.468,
      "depth_m": 95,
      "yield_gpm": 8,
      "distance_km": 0.6
    }
  ]
}

Example values are illustrative.

The total count must represent all matching records, while returned_wells must reflect the paginated or limited result set.

⸻

API-003: Groundwater Summary

Endpoint

GET /api/groundwater/summary

Parameters

latitude
longitude
radius_km

Example response:

{
  "total_wells": 42,
  "median_depth_m": 82,
  "median_yield_gpm": 12,
  "depth_sample_count": 38,
  "yield_sample_count": 35,
  "quality_record_count": 14
}

⸻

API-004: Water Quality

Endpoint

GET /api/water-quality

Parameters

latitude
longitude
radius_km

Example response:

{
  "total_records": 2,
  "measurements": [
    {
      "well_id": "W001",
      "parameter": "Iron",
      "value": 0.4,
      "unit": "mg/L",
      "sample_date": "2024-06-15",
      "guideline_value": 0.3,
      "guideline_unit": "mg/L",
      "guideline_reference": "Configured reference",
      "status": "above_guideline"
    }
  ]
}

This is a response-format example, not a claim about available source measurements or applicable guideline values.

⸻

API-005: Compare Properties

Endpoint

POST /api/properties/compare

Example request:

{
  "property_a": {
    "latitude": 51.19,
    "longitude": -114.47
  },
  "property_b": {
    "latitude": 50.73,
    "longitude": -113.98
  },
  "radius_km": 5
}

The backend must return a consistent set of metrics for both properties.

⸻

API-006: Genie Chat

Endpoint

POST /api/genie/chat

Example request:

{
  "message": "What is the typical well depth near Cochrane?",
  "conversation_id": null,
  "context": {
    "latitude": 51.19,
    "longitude": -114.47,
    "radius_km": 5
  }
}

Example response:

{
  "conversation_id": "conversation-123",
  "message_id": "message-456",
  "status": "completed",
  "answer": "The median recorded well depth is 82 metres.",
  "data": null
}

The backend must manage Genie conversation and message identifiers using the supported Databricks APIs.

If Genie processing is asynchronous, the backend must support polling or another controlled mechanism for retrieving completed responses.

The application must not assume Genie can automatically access the selected map coordinates. Location context must be explicitly passed through supported queries or configured tools.

⸻

API-007: Well Details

Endpoint

GET /api/wells/{well_id}

Returns available details for the selected well.

⸻

7. Databricks Data Requirements

7.1 Source Dataset

Use the Alberta Water Well Information Database provided for the hackathon.

Expected catalog location:

calgary_agent_hackathon.alberta_water_well_data

The application must not assume specific table or column names until the actual schema has been inspected.

7.2 Data Preparation

Create curated Databricks views or tables for:

Well Locations

Contains well identifiers and valid geographic coordinates.

Well Measurements

Contains available well depth, yield, and water-level measurements.

Water Quality

Contains available water-quality observations.

Groundwater Summary

Supports statistical analysis of nearby wells.

These are proposed logical datasets, not confirmed existing tables.

7.3 Spatial Analysis

The application must support finding wells within a selected distance from a location.

Use supported Databricks spatial SQL functions or a validated distance calculation.

Distances must be calculated in kilometres.

Invalid or missing coordinates must be excluded from geographic searches.

7.4 Data Quality

The application must:

* Handle missing coordinates.
* Handle missing measurement values.
* Avoid counting duplicate well records.
* Preserve measurement units.
* Validate geographic coordinates.
* Avoid treating missing values as zero.
* Document assumptions used in calculations.

⸻

8. Databricks Genie Requirements

8.1 Genie Space

Create a dedicated Genie Space named:

AquaWise Alberta Groundwater Intelligence

The Genie Space must use curated groundwater datasets.

8.2 Genie Instructions

Configure Genie with instructions to:

* Use only available groundwater records.
* Explain technical terms simply.
* Include measurement units.
* Identify missing data.
* Avoid unsupported predictions.
* Distinguish historical records from current conditions.
* Avoid declaring drinking water safe or unsafe.
* Prefer medians when describing typical well measurements.

8.3 Genie Data Access

Genie must have access to the required Unity Catalog objects.

The application must use the configured Genie Space ID.

Genie integration must respect Databricks authentication, permissions, and API requirements.

⸻

9. React Application Structure

Use the following project structure:

aquawise-alberta/
|
+-- frontend/
|   |
|   +-- src/
|   |   |
|   |   +-- components/
|   |   |   +-- Header.tsx
|   |   |   +-- Navigation.tsx
|   |   |   +-- LocationSearch.tsx
|   |   |   +-- WellMap.tsx
|   |   |   +-- WellMarker.tsx
|   |   |   +-- SummaryCard.tsx
|   |   |   +-- WellDetails.tsx
|   |   |   +-- LoadingState.tsx
|   |   |
|   |   +-- pages/
|   |   |   +-- ExplorePage.tsx
|   |   |   +-- WaterQualityPage.tsx
|   |   |   +-- ComparePage.tsx
|   |   |   +-- GeniePage.tsx
|   |   |
|   |   +-- services/
|   |   |   +-- api.ts
|   |   |
|   |   +-- types/
|   |   |   +-- groundwater.ts
|   |   |
|   |   +-- App.tsx
|   |   +-- main.tsx
|   |
|   +-- package.json
|   +-- vite.config.ts
|
+-- backend/
|   |
|   +-- main.py
|   +-- routes/
|   |   +-- wells.py
|   |   +-- groundwater.py
|   |   +-- comparison.py
|   |   +-- genie.py
|   |
|   +-- services/
|   |   +-- databricks.py
|   |   +-- spatial.py
|   |   +-- statistics.py
|   |
|   +-- requirements.txt
|
+-- databricks/
|   +-- setup.sql
|   +-- views.sql
|   +-- genie_instructions.md
|
+-- app.yaml
+-- README.md

The project should use a single repository.

For deployment, FastAPI should serve the compiled React application and its API endpoints from one Databricks App.

⸻

10. Non-Functional Requirements

10.1 Performance

Target performance:

* Initial application load: under 3 seconds on a typical broadband connection
* Nearby well search: under 5 seconds for common queries
* Groundwater summary: under 5 seconds
* Property comparison: under 10 seconds
* Genie response: display a loading state while processing

These are target values, not guaranteed Databricks response times.

10.2 Responsiveness

The application must support:

* Desktop browsers
* Tablets
* Mobile browsers

Desktop is the primary target for the hackathon demonstration.

10.3 Security

Requirements:

* Databricks credentials stored server-side.
* No credentials embedded in React.
* SQL inputs validated and parameterized.
* API request parameters validated.
* Genie access restricted to the configured Space.
* Backend permissions limited to required resources.
* No sensitive configuration returned to clients.

10.4 Error Handling

The application must display understandable messages.

Examples:

No nearby wells

“No historical wells were found within the selected radius. Try increasing the search area.”

Databricks unavailable

“We couldn’t retrieve groundwater information right now. Please try again.”

Genie error

“The AI assistant couldn’t complete your question. Please try rephrasing it.”

Missing water-quality data

“No water-quality measurements are available for this selection.”

10.5 Accessibility

Requirements:

* Readable contrast
* Keyboard-accessible navigation
* Labels for input fields
* Clear button text
* Accessible error messages
* Charts supported by text summaries

⸻

11. Application Pages

Page 1: Explore Property

Purpose

Primary landing page for groundwater exploration.

Layout

Top Section

Title: “Explore Groundwater Near Your Property”

Description:

“Select a location in Alberta to explore historical water-well information.”

Location Controls

* Location search
* Search radius
* Analyze Groundwater button

Main Section

* Interactive map
* Nearby well markers

Results Section

Four summary cards:

* Nearby Wells
* Typical Well Depth
* Typical Well Yield
* Water Quality Records

Bottom Section

* Well depth chart
* Well yield chart
* Nearby wells table

⸻

Page 2: Water Quality

Purpose

Display available historical water-quality information.

Layout

Top Section

Title: “Historical Water Quality”

Description:

“Explore available water-quality observations from nearby wells.”

Main Section

* Selected location
* Search radius
* Water-quality summary
* Measurement table

Bottom Section

* Plain-language explanations
* Testing recommendations
* Data limitations

⸻

Page 3: Compare Properties

Purpose

Compare groundwater information between two locations.

Layout

Top Section

Title: “Compare Two Properties”

Location Selection

* Property A
* Property B
* Search radius
* Compare button

Results

* Side-by-side summary cards
* Comparison table
* Simple charts
* Plain-language comparison summary

⸻

Page 4: Ask AquaWise

Purpose

Provide natural-language access to groundwater information.

Layout

Top Section

Title: “Ask AquaWise”

Description:

“Ask questions about Alberta’s historical groundwater information.”

Main Section

* Chat conversation
* Suggested questions
* Message input
* Send button

The interface should resemble a simple messaging application.

⸻

12. MVP Priorities

Phase 1 — Essential Application

Must Have

* React application setup
* FastAPI backend
* Databricks connection
* Navigation
* Interactive map
* Location selection
* Nearby well search
* Groundwater summary cards
* Basic charts
* Loading and error states

Phase 2 — Intelligence Features

Must Have

* Databricks Genie Space
* Genie chat interface
* Property comparison
* Historical water-quality explorer, where supported
* Data availability indicators

Phase 3 — Optional Enhancements

Nice to Have

* PDF groundwater report
* Export nearby well records
* Save favourite locations
* Advanced filtering
* Additional data visualizations
* AI-generated property comparison narrative

These enhancements must not delay delivery of the core MVP.

⸻

13. Testing Requirements

13.1 Frontend Tests

Verify:

* Navigation works.
* Map loads correctly.
* Location selection works.
* Radius selection works.
* Summary cards display returned data.
* Charts handle empty datasets.
* Comparison page works.
* Chat messages render correctly.
* Loading indicators appear.
* Error messages are understandable.

13.2 Backend Tests

Verify:

* Databricks connection handling.
* Coordinate validation.
* Radius validation.
* Nearby well filtering.
* Statistical calculations.
* Missing measurement handling.
* API response formatting.
* Genie conversation handling.
* Backend error handling.

13.3 Data Validation

Verify:

* Well counts match Databricks query results.
* Geographic distances are correct.
* Medians are calculated correctly.
* Missing values are excluded appropriately.
* Measurement units are consistent.
* Comparison metrics use the same definitions.

⸻

14. Definition of Done

The hackathon MVP is complete when:

1. The React application runs successfully.
2. The FastAPI backend connects to Databricks.
3. Users can select an Alberta location.
4. Nearby historical wells appear on the map.
5. Groundwater statistics are calculated from actual data.
6. Users can inspect available well information.
7. Users can compare two locations.
8. Available water-quality observations are displayed accurately.
9. Users can ask questions through Databricks Genie.
10. The application handles missing data and failed requests.
11. Databricks credentials are not exposed.
12. The application can be demonstrated through a deployed Databricks App.

⸻

15. Out of Scope

The following features are excluded from the initial MVP:

* User registration
* User profiles
* Subscription management
* Payment processing
* Real-time groundwater monitoring
* Predictive groundwater modelling
* Automated contamination predictions
* Certified water-quality assessments
* Property purchase recommendations
* Automated well drilling recommendations
* Mobile applications for iOS or Android

⸻

16. Expected Deliverable

A functioning React application called AquaWise Alberta.

The application must allow an ordinary Alberta resident to:

1. Find a location.
2. Explore nearby historical water wells.
3. Understand basic groundwater statistics.
4. Review available water-quality observations.
5. Compare two properties.
6. Ask groundwater questions using Databricks Genie.

The final application should be simple enough that a first-time visitor can use it without instructions.

Product tagline:

“Understand the water beneath your property.”

Product principle:

“Turn complex groundwater data into clear, useful information for Albertans.”

⸻

17. Implementation Notes

Before implementing data-dependent features, developers must inspect the actual Databricks schema and confirm:

* Available tables
* Geographic coordinate fields
* Well identifiers
* Depth measurements
* Yield measurements and units
* Water-quality measurements
* Record dates
* Relationships between tables

Any unavailable data field must be handled gracefully.

The application should be developed against actual Databricks data rather than hardcoded sample values.

Mock data may be used during initial UI development but must be clearly separated from production data.

End of Requirements Document — Version 1.0