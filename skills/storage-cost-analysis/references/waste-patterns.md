# Waste Pattern Classification

Classify each candidate table into the first matching pattern (first-match-wins). If none match, the table is not a waste candidate.

## Patterns (in evaluation order)

### 1. UNREAD

**Definition:** Nobody queries this table.

**Criteria:**
- Zero read queries (total reads = 0)
- No downstream lineage consumers (degree out = 0)
- Zero reading users

**Typical cause:** Table was created for a one-time analysis or migration and never used again.

**Recommendation:** Safe to DROP if safety tier is low. Archive if uncertain.

---

### 2. WRITE_ONLY

**Definition:** ETL writes to this table but nobody reads from it.

**Criteria:**
- Has write queries (total writes > 0)
- Very few reads (total reads < 5)
- Last read was >30 days before last write
- Active write schedule (regular writes)

**Typical cause:** Pipeline output that lost its consumer. ETL still runs but the downstream dashboard or model was decommissioned.

**Recommendation:** Pause the write pipeline first, then DROP after confirming no side effects.

---

### 3. DEAD_END

**Definition:** Receives data from upstream but serves nothing downstream.

**Criteria:**
- Has upstream dependencies (degree in > 0)
- No downstream consumers (degree out = 0)
- Zero reading users

**Typical cause:** Intermediate table in a pipeline that was superseded by a refactored query. Upstream still feeds it but nothing reads from it.

**Recommendation:** Check if upstream pipeline can be simplified to skip this table. Safe to DROP if no readers.

---

### 4. BULK_LOADED

**Definition:** Bulk file loads nobody uses.

**Criteria:**
- Has file-based writes (COPY INTO, file loads)
- File writes are >50% of total writes
- Very few reads (total reads < 5)

**Typical cause:** Data dump from an external system that was loaded once or on schedule but never integrated into analytics.

**Recommendation:** Archive to cold storage if data might be needed later. DROP if confirmed unused.

---

### 5. STATIC_WASTE

**Definition:** Size never changes and nobody reads it.

**Criteria:**
- No volume changes in >90 days
- No reads in >90 days

**Typical cause:** Reference table or snapshot that became obsolete.

**Recommendation:** Archive or DROP.

---

### 6. ZOMBIE

**Definition:** Forgotten table with no activity.

**Criteria:**
- No reads in >90 days
- Low importance score (< 0.3)
- Not monitored

**Typical cause:** Table created during development or experimentation and never cleaned up.

**Recommendation:** Safe to DROP. Low risk.

---

### 7. OTHER_STALE

**Definition:** Stale table that doesn't match a specific pattern above.

**Criteria:** Catch-all for tables with no recent activity that don't fit the categories above.

**Recommendation:** Investigate further before taking action.
