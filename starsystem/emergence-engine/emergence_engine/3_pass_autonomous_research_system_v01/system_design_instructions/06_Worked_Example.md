# Worked Example: Restaurant Reservation System

This example demonstrates applying the systems design workflow to a restaurant reservation system, showing all three passes.

## Starting Point

Let's design a restaurant reservation system to illustrate how the workflow applies to a different domain than autobiographies.

---

## Pass 1: CONCEPTUALIZE (What IS a restaurant reservation?)

### Phase 0: Abstract Goal
Understanding the essential nature of restaurant reservations as coordinated time-space allocations between diners and restaurants.

### Phase 1: Systems Design

#### (1a) Purpose Capture
A reservation serves to:
- Guarantee future access to limited resources (tables)
- Allow planning for both diners and restaurants
- Create mutual commitment
- Manage uncertainty

#### (1b) Context Map
- Social context: Dining as social experience
- Economic context: Revenue optimization for restaurants
- Cultural context: Varies by cuisine, formality
- Temporal context: Time-sensitive coordination

#### (1c) Stakeholder Goals
- **Diners**: Certainty, convenience, special experiences
- **Restaurants**: Capacity optimization, revenue, predictability
- **Staff**: Manageable workflow, fair treatment
- **Other diners**: Fair access, pleasant environment

#### (1d) Success Metrics
- Reservation fulfilled as promised
- Optimal table utilization
- Satisfied diners and staff
- Fair access to reservations

#### (1i) Concept Model
Core concepts:
- **Reservation**: A mutual commitment for future service
- **Table**: Physical resource being reserved
- **Time Slot**: When reservation occurs
- **Party**: Group making reservation
- **Confirmation**: Proof of mutual agreement

#### (1j) Ontology Sketch
```
Reservation
├── Time Properties
│   ├── Date
│   ├── Time
│   └── Duration
├── Space Properties
│   ├── Table Assignment
│   ├── Location (indoor/outdoor)
│   └── Capacity
├── Party Properties
│   ├── Size
│   ├── Contact Info
│   └── Special Needs
├── State
│   ├── Requested
│   ├── Confirmed
│   ├── Arrived
│   ├── Seated
│   ├── Completed
│   └── Cancelled
└── Constraints
    ├── Restaurant Hours
    ├── Table Availability
    └── Party Requirements
```

### Phase 3: DSL (Domain Vocabulary)

#### Concepts:
- **Booking Window**: How far in advance reservations accepted
- **No-show**: Confirmed reservation not honored by diner
- **Walk-in**: Diner without reservation
- **Turn Time**: Duration from seating to table available again
- **Cover**: Individual diner
- **Service Period**: Lunch, dinner, etc.

#### Relationships:
- Reservations occupy Tables for Duration
- Parties make Reservations
- Tables have Capacity constraints
- Time Slots have Availability

### Phase 4: Topology

The essential network:
```
Diner ←→ Reservation ←→ Table
           ↓
      Time Slot
```

### Key Pass 1 Insights:
1. A reservation is fundamentally about coordinating future access to scarce resources
2. Trust and commitment are essential (not just data)
3. Time is as important as space
4. Fairness and optimization often conflict

---

## Pass 2: GENERALLY REIFY (How do we BUILD reservation systems?)

### Phase 0: Abstract Goal
Create a system that can manage restaurant reservations efficiently while balancing all stakeholder needs.

### Phase 1: Systems Design

#### (1a) Purpose Capture
Build a system that:
- Accepts and manages reservation requests
- Optimizes table utilization
- Handles modifications and cancellations
- Provides visibility to all stakeholders

#### (1c) Stakeholder Goals
- **Diners**: Easy booking, modifications, reminders
- **Restaurant managers**: Optimization tools, analytics
- **Host staff**: Clear daily views, walk-in management
- **System operators**: Reliability, scalability

#### (1i) Concept Model
System components:
- Booking Engine
- Availability Calculator
- Notification Service
- Analytics Engine
- Admin Interface

### Phase 2: Systems Architecture

#### (2a) Function Decomposition
- F1: Accept reservation requests
- F2: Check availability
- F3: Confirm reservations
- F4: Send notifications
- F5: Handle modifications
- F6: Manage walk-ins
- F7: Generate analytics
- F8: Optimize table assignments

#### (2b) Module Grouping
- **Booking Module**: F1, F2, F3, F5
- **Communication Module**: F4
- **Operations Module**: F6, F8
- **Analytics Module**: F7

### Phase 3: DSL (System Language)

```python
# System vocabulary
class ReservationRequest:
    party_size: int
    preferred_time: datetime
    duration_estimate: int
    special_requirements: List[str]

class AvailabilityCheck:
    time_range: TimeRange
    party_size: int
    constraints: List[Constraint]

class TableAssignment:
    reservation_id: str
    table_id: str
    optimization_score: float
```

### Phase 4: Topology

System network:
```
Web Interface → API Gateway → Booking Service
                                ↓
Database ← Availability Engine ← Analytics
    ↑                           ↑
    └─── Notification Service ──┘
```

### Phase 5: Engineered System

Key implementation decisions:
- Real-time availability checking
- Probabilistic no-show prediction
- Dynamic pricing capabilities
- Multi-channel notifications
- Mobile-first design

---

## Pass 3: SPECIFICALLY REIFY (Build "Chez Marie's" reservation system)

### Phase 0: Abstract Goal
Implement a reservation system for Chez Marie's, a 40-seat French bistro with high demand.

### Phase 1: Systems Design

#### (1a) Purpose Capture
Chez Marie's needs:
- Manage 2-month booking window
- Handle regulars specially
- Optimize for wine service (longer meals)
- Maintain intimate atmosphere

#### (1c) Specific Constraints
- Only 12 tables (4 two-tops, 6 four-tops, 2 six-tops)
- Average meal duration: 2.5 hours
- Peak demand: Friday/Saturday 7-9 PM
- 30% tables held for walk-ins

### Phase 2: Architecture Configuration

Configure the general system:
- Booking window: 60 days
- Time slots: 15-minute intervals
- Maximum party size: 6
- Automatic waitlist for full times
- VIP flag for regulars

### Phase 3: Specific Rules

```python
# Chez Marie's specific rules
PEAK_TIMES = [(FRI, "18:00-21:00"), (SAT, "18:00-21:00")]
REGULAR_CUSTOMER_ADVANCE = 75  # days
WALK_IN_TABLES = {TWO_TOP: 1, FOUR_TOP: 2}
MIN_TURN_TIME = 150  # minutes
```

### Phase 5: Deployment

Specific instance details:
- Integrated with Chez Marie's POS system
- French language support
- SMS preferred over email (older clientele)
- Simple tablet interface for host stand
- Daily printed reservation list backup

### Phase 6: Feedback and Optimization

After 3 months:
- Discovered lunch service different pattern
- Added "counter seating" as special table type
- Implemented "regular's table" recurring reservations
- Adjusted no-show predictions for local market

---

## Key Lessons from This Example

### 1. **Domain Understanding is Crucial**
Pass 1 revealed that reservations are about trust and coordination, not just database records.

### 2. **General Systems Enable Specific Solutions**
Pass 2's flexible system could accommodate Chez Marie's specific needs without custom code.

### 3. **Real Instances Test Design**
Pass 3 revealed needs (like counter seating) not anticipated in earlier passes.

### 4. **Each Pass Has Different Concerns**
- Pass 1: What makes something a reservation?
- Pass 2: How do we build systems that manage reservations?
- Pass 3: How do we configure for Chez Marie's?

### 5. **The Power of Iteration**
Learning from Chez Marie's deployment improves the general system for all restaurants.

## Comparing Domains

Notice how different domains emphasize different aspects:

| Aspect | Autobiography | Restaurant Reservation |
|--------|--------------|----------------------|
| Core Challenge | Meaning extraction | Resource optimization |
| Time Factor | Past reflection | Future coordination |
| Key Relationship | Author ↔ Reader | Diner ↔ Restaurant |
| Success Metric | Narrative coherence | Utilization + satisfaction |
| Main Constraint | Memory/authenticity | Capacity/time |

Yet the same workflow effectively guides both designs!

## Try It Yourself

Apply this workflow to:
- A fitness tracking system
- A team collaboration tool
- A recipe sharing platform
- A pet adoption service

Notice how Pass 1 forces you to think deeply about what these things truly ARE before jumping to features and implementation.
