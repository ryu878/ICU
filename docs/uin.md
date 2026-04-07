# UIN (User Identification Number) generation

Addendum to the specification: unique numeric user identifier.

---

## UIN requirement

UIN is assigned **sequentially**.

### Rules

- The first registered user receives **UIN = 1**.
- Each subsequent user receives **UIN = previous + 1**.
- UIN is:
  - **unique**
  - **immutable** after creation
  - the **primary public** user identifier

### Requirements

- **No duplicates.**
- **No gaps** in the business sense: see **Gaps** (depends on the PostgreSQL mechanism chosen).
- Generation is **atomic** and **safe** under concurrent registration.
- UIN is **never reused**, including after user deletion (the counter only increases).

### Constraints

- Do **not** use **random** or **UUID** values as the primary UIN.
- A separate **internal technical ID** (`users.id`, etc.) is allowed alongside UIN.

---

## Role in the system

- **UIN** is the only public numeric identifier (API, lookup, display like classic messenger UINs).
- The database may use a **surrogate PK** (`id` bigint/uuid) for FKs; externally always expose **UIN**.

### Conceptual data model

```text
users:
  id            BIGSERIAL PRIMARY KEY   -- internal PK, FKs from other tables
  uin           BIGINT NOT NULL UNIQUE  -- public identifier
  ...
```

- External routes and search: `/users/{uin}`, lookup by **UIN**.
- Internal FKs (`messages`, `sessions`, …) — prefer **`users.id`** (or `uin` by team convention; UIN stays immutable).

---

## PostgreSQL implementation options

### Option A — `SEQUENCE` (`nextval`)

- **Pros:** simple, fast, atomic, no duplicates, issued numbers are not reused.
- **Gaps:** after a **transaction rollback** following `nextval()`, that number is already consumed — **rare gaps** in the sequence. If “no gaps” only means no duplicates, `SEQUENCE` plus documented rollback gaps is often enough.

**Example:**

```sql
CREATE SEQUENCE users_uin_seq START WITH 1 INCREMENT BY 1;

-- In INSERT:
INSERT INTO users (uin, email, ...)
VALUES (nextval('users_uin_seq'), ...);
```

(Or `DEFAULT nextval('users_uin_seq')` on `uin`.)

---

### Option B — single-row counter + `SELECT … FOR UPDATE`

Strictly **no gaps** from failed registration: the counter increments in the **same transaction** as the user `INSERT`; on rollback the counter rolls back too.

**Schema:**

- Table `uin_counter` with one row; `value` starts at `0` (next UIN = `value + 1` after increment).

**Logic in one transaction:**

1. `SELECT value FROM uin_counter WHERE id = 1 FOR UPDATE`
2. `new_uin = value + 1`
3. `UPDATE uin_counter SET value = value + 1 WHERE id = 1`
4. `INSERT INTO users (uin, ...) VALUES (new_uin, ...)`
5. `COMMIT`

**Pros:** transaction rollback restores the counter — **no gaps** from registration failure.  
**Cons:** higher serialization under concurrent signups (usually fine for MVP).

---

## Recommendation

- For **strictly no gaps** — **option B**.
- If rare gaps on `SEQUENCE` rollback are acceptable — **option A** + document in runbooks.

---

## User deletion and UIN reuse

- Prefer **soft delete** (`deleted_at`) or avoid physical delete in MVP for referential consistency.
- The counter **never decreases** — an old UIN is **never** reissued.

---

## Atomicity and races

- **Option A:** `nextval` prevents duplicates under concurrency.
- **Option B:** `FOR UPDATE` on the counter row yields exactly one next UIN per successful registration and no duplicates.

---

## Short specification wording

**UIN** is a monotonic public integer identifier issued in strict order starting at **1**, immutable after creation, unique, and not reused after account deletion. Generation is atomic at user creation; an internal surrogate `id` in the database is allowed. For **no gaps**, use a **single-row counter locked in the registration transaction** (option B), or document **rare gaps** with **SEQUENCE** and transaction rollbacks (option A).
