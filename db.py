# db.py
import asyncpg
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=5)

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchrow(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def init_schema(self):
        # users
        await self.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id         BIGINT PRIMARY KEY,
            state           TEXT DEFAULT 'REG_NAME',
            full_name       TEXT,
            xj_id           TEXT,
            join_date_text  TEXT,
            phone           TEXT,
            level           TEXT,
            inviter_id      BIGINT,
            ref_code        TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # stage2 progress (4/4 gate)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage2_progress (
            user_id     BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            matn_done   BOOLEAN DEFAULT FALSE,
            audio_done  BOOLEAN DEFAULT FALSE,
            video_done  BOOLEAN DEFAULT FALSE,
            links_done  BOOLEAN DEFAULT FALSE,
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # stage3 progress
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_progress (
            user_id         BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            confirmed_text  TEXT,
            confirmed_at    TIMESTAMPTZ
        );
        """)

        # stage3 attempts (exact confirm urinishlar)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage3_attempts (
            user_id     BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            attempts    INT DEFAULT 0,
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # leads (20)
        await self.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lead_index  INT NOT NULL,
            name_raw    TEXT NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, lead_index)
        );
        """)

        # counters/indexes for stages 4-7
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage_counters (
            user_id     BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            s4_idx      INT DEFAULT 1,
            s5_idx      INT DEFAULT 1,
            s6_idx      INT DEFAULT 1,
            s7_idx      INT DEFAULT 1,
            s7_pending  INT DEFAULT 0,
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # stage5 meeting notes
        await self.execute("""
        CREATE TABLE IF NOT EXISTS meeting_notes (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lead_index  INT NOT NULL,
            status_text TEXT NOT NULL,
            updated_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, lead_index)
        );
        """)

        # stage6 presentation status
        await self.execute("""
        CREATE TABLE IF NOT EXISTS presentation_status (
            user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lead_index  INT NOT NULL,
            done        BOOLEAN NOT NULL,
            updated_at  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, lead_index)
        );
        """)

        # stage7 followup questions
        await self.execute("""
        CREATE TABLE IF NOT EXISTS followup_questions (
            id            BIGSERIAL PRIMARY KEY,
            user_id       BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            lead_index    INT NOT NULL,
            question_text TEXT NOT NULL,
            status        TEXT DEFAULT 'sent_to_admin',
            admin_answer  TEXT,
            created_at    TIMESTAMPTZ DEFAULT NOW(),
            answered_at   TIMESTAMPTZ
        );
        """)

        # stage8 progress
        await self.execute("""
        CREATE TABLE IF NOT EXISTS stage8_progress (
            user_id      BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            audio_done   BOOLEAN DEFAULT FALSE,
            text_opened  BOOLEAN DEFAULT FALSE,
            video_opened BOOLEAN DEFAULT FALSE,
            links_opened BOOLEAN DEFAULT FALSE,
            updated_at   TIMESTAMPTZ DEFAULT NOW()
        );
        """)

    # ---------- users ----------
    async def ensure_user(self, user_id: int, inviter_id: Optional[int] = None):
        row = await self.fetchrow("SELECT user_id, inviter_id FROM users WHERE user_id=$1", user_id)
        if row is None:
            await self.execute(
                "INSERT INTO users(user_id, state, ref_code, inviter_id) VALUES($1, 'REG_NAME', md5(random()::text), $2)",
                user_id,
                inviter_id
            )
        else:
            # inviter_id faqat birinchi marta (NULL bo‘lsa) set qilamiz
            if inviter_id is not None and row["inviter_id"] is None:
                await self.execute("UPDATE users SET inviter_id=$2 WHERE user_id=$1", user_id, inviter_id)

        # dependent rows
        await self.execute(
            "INSERT INTO stage2_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id
        )
        await self.execute(
            "INSERT INTO stage3_attempts(user_id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id
        )
        await self.execute(
            "INSERT INTO stage_counters(user_id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id
        )
        await self.execute(
            "INSERT INTO stage8_progress(user_id) VALUES($1) ON CONFLICT DO NOTHING",
            user_id
        )

    async def get_state(self, user_id: int) -> str:
        row = await self.fetchrow("SELECT state FROM users WHERE user_id=$1", user_id)
        return row["state"] if row else "REG_NAME"

    async def set_state(self, user_id: int, state: str):
        await self.execute("UPDATE users SET state=$2 WHERE user_id=$1", user_id, state)

    async def set_user_field(self, user_id: int, field: str, value: Any):
        if field not in {"full_name", "xj_id", "join_date_text", "phone", "level"}:
            raise ValueError("Invalid field")
        await self.execute(f"UPDATE users SET {field}=$2 WHERE user_id=$1", user_id, value)

    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = await self.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None

    # ---------- referral ----------
    async def get_user_id_by_ref_code(self, code: str) -> Optional[int]:
        row = await self.fetchrow("SELECT user_id FROM users WHERE ref_code=$1", code)
        return int(row["user_id"]) if row else None

    async def get_ref_code(self, user_id: int) -> str:
        row = await self.fetchrow("SELECT ref_code FROM users WHERE user_id=$1", user_id)
        if row and row["ref_code"]:
            return row["ref_code"]
        await self.execute("UPDATE users SET ref_code=md5(random()::text) WHERE user_id=$1", user_id)
        row2 = await self.fetchrow("SELECT ref_code FROM users WHERE user_id=$1", user_id)
        return row2["ref_code"]

    # ---------- stage2 ----------
    async def mark_stage2(self, user_id: int, key: str):
        if key not in {"matn_done", "audio_done", "video_done", "links_done"}:
            raise ValueError("Invalid stage2 key")
        await self.execute(
            f"UPDATE stage2_progress SET {key}=TRUE, updated_at=NOW() WHERE user_id=$1",
            user_id
        )

    async def get_stage2(self, user_id: int) -> Dict[str, bool]:
        row = await self.fetchrow("SELECT * FROM stage2_progress WHERE user_id=$1", user_id)
        if not row:
            return {"matn_done": False, "audio_done": False, "video_done": False, "links_done": False}
        return {
            "matn_done": row["matn_done"],
            "audio_done": row["audio_done"],
            "video_done": row["video_done"],
            "links_done": row["links_done"],
        }

    # ---------- stage3 ----------
    async def set_stage3_confirm(self, user_id: int, text: str):
        await self.execute("""
            INSERT INTO stage3_progress(user_id, confirmed_text, confirmed_at)
            VALUES($1, $2, NOW())
            ON CONFLICT (user_id)
            DO UPDATE SET confirmed_text=EXCLUDED.confirmed_text, confirmed_at=EXCLUDED.confirmed_at
        """, user_id, text)

    async def inc_stage3_attempt(self, user_id: int) -> int:
        await self.execute("""
            INSERT INTO stage3_attempts(user_id, attempts)
            VALUES($1, 1)
            ON CONFLICT (user_id)
            DO UPDATE SET attempts=stage3_attempts.attempts+1, updated_at=NOW()
        """, user_id)
        row = await self.fetchrow("SELECT attempts FROM stage3_attempts WHERE user_id=$1", user_id)
        return int(row["attempts"]) if row else 1

    async def reset_stage3_attempts(self, user_id: int):
        await self.execute("UPDATE stage3_attempts SET attempts=0, updated_at=NOW() WHERE user_id=$1", user_id)

    # ---------- leads ----------
    async def set_lead(self, user_id: int, idx: int, name_raw: str):
        await self.execute("""
            INSERT INTO leads(user_id, lead_index, name_raw)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, lead_index)
            DO UPDATE SET name_raw=EXCLUDED.name_raw
        """, user_id, idx, name_raw)

    async def get_leads(self, user_id: int) -> List[Dict[str, Any]]:
        rows = await self.fetch("SELECT lead_index, name_raw FROM leads WHERE user_id=$1 ORDER BY lead_index", user_id)
        return [dict(r) for r in rows]

    # ---------- counters ----------
    async def _get_counter(self, user_id: int, col: str, default: int) -> int:
        row = await self.fetchrow(f"SELECT {col} FROM stage_counters WHERE user_id=$1", user_id)
        if not row or row[col] is None:
            return default
        return int(row[col])

    async def _set_counter(self, user_id: int, col: str, value: int):
        await self.execute(f"UPDATE stage_counters SET {col}=$2, updated_at=NOW() WHERE user_id=$1", user_id, value)

    async def get_s4_idx(self, user_id: int) -> int:
        return await self._get_counter(user_id, "s4_idx", 1)

    async def set_s4_idx(self, user_id: int, idx: int):
        await self._set_counter(user_id, "s4_idx", idx)

    async def get_s5_idx(self, user_id: int) -> int:
        return await self._get_counter(user_id, "s5_idx", 1)

    async def set_s5_idx(self, user_id: int, idx: int):
        await self._set_counter(user_id, "s5_idx", idx)

    async def get_s6_idx(self, user_id: int) -> int:
        return await self._get_counter(user_id, "s6_idx", 1)

    async def set_s6_idx(self, user_id: int, idx: int):
        await self._set_counter(user_id, "s6_idx", idx)

    async def get_s7_idx(self, user_id: int) -> int:
        return await self._get_counter(user_id, "s7_idx", 1)

    async def set_s7_idx(self, user_id: int, idx: int):
        await self._set_counter(user_id, "s7_idx", idx)

    async def get_s7_pending(self, user_id: int) -> int:
        return await self._get_counter(user_id, "s7_pending", 0)

    async def set_s7_pending(self, user_id: int, idx: int):
        await self._set_counter(user_id, "s7_pending", idx)

    # ---------- stage5 ----------
    async def set_meeting_note(self, user_id: int, idx: int, text: str):
        await self.execute("""
            INSERT INTO meeting_notes(user_id, lead_index, status_text)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, lead_index)
            DO UPDATE SET status_text=EXCLUDED.status_text, updated_at=NOW()
        """, user_id, idx, text)

    # ---------- stage6 ----------
    async def set_presentation(self, user_id: int, idx: int, done: bool):
        await self.execute("""
            INSERT INTO presentation_status(user_id, lead_index, done)
            VALUES($1, $2, $3)
            ON CONFLICT (user_id, lead_index)
            DO UPDATE SET done=EXCLUDED.done, updated_at=NOW()
        """, user_id, idx, done)

    # ---------- stage7 ----------
    async def add_followup_question(self, user_id: int, idx: int, question_text: str) -> int:
        row = await self.fetchrow("""
            INSERT INTO followup_questions(user_id, lead_index, question_text)
            VALUES($1, $2, $3)
            RETURNING id
        """, user_id, idx, question_text)
        return int(row["id"])

    async def answer_followup_question(self, qid: int, answer: str):
        await self.execute("""
            UPDATE followup_questions
            SET status='answered', admin_answer=$2, answered_at=NOW()
            WHERE id=$1
        """, qid, answer)

    async def get_followup_question(self, qid: int) -> Optional[Dict[str, Any]]:
        row = await self.fetchrow("SELECT * FROM followup_questions WHERE id=$1", qid)
        return dict(row) if row else None

    async def list_pending_followups(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = await self.fetch("""
            SELECT id, user_id, lead_index, question_text, created_at
            FROM followup_questions
            WHERE status='sent_to_admin'
            ORDER BY created_at ASC
            LIMIT $1
        """, limit)
        return [dict(r) for r in rows]

    # ---------- stage8 ----------
    async def set_stage8_audio_done(self, user_id: int):
        await self.execute("""
            UPDATE stage8_progress
            SET audio_done=TRUE, updated_at=NOW()
            WHERE user_id=$1
        """, user_id)

    async def mark_stage8_opened(self, user_id: int, key: str):
        if key not in {"text_opened", "video_opened", "links_opened"}:
            raise ValueError("Invalid stage8 key")
        await self.execute(f"""
            UPDATE stage8_progress
            SET {key}=TRUE, updated_at=NOW()
            WHERE user_id=$1
        """, user_id)

    async def get_stage8(self, user_id: int) -> Dict[str, bool]:
        row = await self.fetchrow("SELECT * FROM stage8_progress WHERE user_id=$1", user_id)
        if not row:
            return {"audio_done": False, "text_opened": False, "video_opened": False, "links_opened": False}
        return {
            "audio_done": row["audio_done"],
            "text_opened": row["text_opened"],
            "video_opened": row["video_opened"],
            "links_opened": row["links_opened"],
        }


# =========================
# Module-level singleton API
# =========================
_DB: Optional[Database] = None


def _db() -> Database:
    if _DB is None:
        raise RuntimeError("DB is not initialized. Call await db.init(DATABASE_URL) in main.py")
    return _DB


async def init(dsn: str):
    global _DB
    _DB = Database(dsn)
    await _DB.connect()
    await _DB.init_schema()


async def close():
    global _DB
    if _DB is not None:
        await _DB.close()
        _DB = None


# ---- wrappers used by main.py ----
async def ensure_user(user_id: int, inviter_id: Optional[int] = None):
    return await _db().ensure_user(user_id, inviter_id)

async def get_state(user_id: int) -> str:
    return await _db().get_state(user_id)

async def set_state(user_id: int, state: str):
    return await _db().set_state(user_id, state)

async def set_user_field(user_id: int, field: str, value: Any):
    return await _db().set_user_field(user_id, field, value)

async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    return await _db().get_user_profile(user_id)

async def get_user_id_by_ref_code(code: str) -> Optional[int]:
    return await _db().get_user_id_by_ref_code(code)

async def get_ref_code(user_id: int) -> str:
    return await _db().get_ref_code(user_id)

async def mark_stage2(user_id: int, key: str):
    return await _db().mark_stage2(user_id, key)

async def get_stage2(user_id: int) -> Dict[str, bool]:
    return await _db().get_stage2(user_id)

async def set_stage3_confirm(user_id: int, text: str):
    return await _db().set_stage3_confirm(user_id, text)

async def inc_stage3_attempt(user_id: int) -> int:
    return await _db().inc_stage3_attempt(user_id)

async def reset_stage3_attempts(user_id: int):
    return await _db().reset_stage3_attempts(user_id)

async def set_lead(user_id: int, idx: int, name_raw: str):
    return await _db().set_lead(user_id, idx, name_raw)

async def get_leads(user_id: int) -> List[Dict[str, Any]]:
    return await _db().get_leads(user_id)

async def get_s4_idx(user_id: int) -> int:
    return await _db().get_s4_idx(user_id)

async def set_s4_idx(user_id: int, idx: int):
    return await _db().set_s4_idx(user_id, idx)

async def get_s5_idx(user_id: int) -> int:
    return await _db().get_s5_idx(user_id)

async def set_s5_idx(user_id: int, idx: int):
    return await _db().set_s5_idx(user_id, idx)

async def get_s6_idx(user_id: int) -> int:
    return await _db().get_s6_idx(user_id)

async def set_s6_idx(user_id: int, idx: int):
    return await _db().set_s6_idx(user_id, idx)

async def get_s7_idx(user_id: int) -> int:
    return await _db().get_s7_idx(user_id)

async def set_s7_idx(user_id: int, idx: int):
    return await _db().set_s7_idx(user_id, idx)

async def get_s7_pending(user_id: int) -> int:
    return await _db().get_s7_pending(user_id)

async def set_s7_pending(user_id: int, idx: int):
    return await _db().set_s7_pending(user_id, idx)

async def set_meeting_note(user_id: int, idx: int, text: str):
    return await _db().set_meeting_note(user_id, idx, text)

async def set_presentation(user_id: int, idx: int, done: bool):
    return await _db().set_presentation(user_id, idx, done)

async def add_followup_question(user_id: int, idx: int, question_text: str) -> int:
    return await _db().add_followup_question(user_id, idx, question_text)

async def answer_followup_question(qid: int, answer: str):
    return await _db().answer_followup_question(qid, answer)

async def get_followup_question(qid: int) -> Optional[Dict[str, Any]]:
    return await _db().get_followup_question(qid)

async def list_pending_followups(limit: int = 20) -> List[Dict[str, Any]]:
    return await _db().list_pending_followups(limit)

async def set_stage8_audio_done(user_id: int):
    return await _db().set_stage8_audio_done(user_id)

async def mark_stage8_opened(user_id: int, key: str):
    return await _db().mark_stage8_opened(user_id, key)

async def get_stage8(user_id: int) -> Dict[str, bool]:
    return await _db().get_stage8(user_id)
