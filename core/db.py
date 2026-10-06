"""All app data lives in a local SQLite file. Every query is scoped to the logged-in user."""
from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Any

from core import config
from core.auth import current_user_id

log = logging.getLogger("pivio.db")

STATUSES = ["Applied", "Interview", "Offer", "Rejected"]

SCHEMA = """
create table if not exists resumes (
  id text primary key, user_id text not null, label text not null, filename text not null,
  file_hash text not null, extracted_text text not null, file_path text, uploaded_at text not null,
  unique (user_id, file_hash)
);
create table if not exists applications (
  id text primary key, user_id text not null,
  resume_id text references resumes(id) on delete set null,
  company text not null, role text not null, job_description text not null default '',
  applied_on text not null,
  status text not null default 'Applied' check (status in ('Applied','Interview','Offer','Rejected')),
  notes text default ''
);
create table if not exists interview_sessions (
  id text primary key, user_id text not null,
  application_id text not null references applications(id) on delete cascade,
  persona text not null, transcript text not null default '[]', evaluations text not null default '[]',
  report text not null default '{}', overall_score real, created_at text not null
);
create index if not exists idx_resumes_user on resumes(user_id);
create index if not exists idx_applications_user on applications(user_id);
create index if not exists idx_sessions_user on interview_sessions(user_id);
create index if not exists idx_sessions_application on interview_sessions(application_id);
"""


class DatabaseError(Exception):
    """Raised with a friendly message when a database call fails."""


def _run(action: str, fn):
    try:
        return fn()
    except DatabaseError:
        raise
    except Exception as exc:
        log.exception("DB failure while trying to %s", action)
        print("[DB ERROR]", action, repr(exc), flush=True)
        raise DatabaseError("Could not " + action + ". Please try again. (" + str(exc)[:160] + ")") from exc


@contextlib.contextmanager
def _conn():
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("pragma foreign_keys = on")
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rows(con: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args).fetchall()]


# ---------------------------------------------------------------- resumes
def list_resumes() -> list[dict]:
    uid = current_user_id()

    def q():
        with _conn() as con:
            return _rows(con, "select id,label,filename,file_hash,file_path,uploaded_at from resumes "
                              "where user_id=? order by uploaded_at desc", (uid,))

    return _run("load resumes", q)


def get_resume(resume_id: str) -> dict | None:
    uid = current_user_id()

    def q():
        with _conn() as con:
            return _rows(con, "select * from resumes where user_id=? and id=?", (uid, resume_id))

    rows = _run("load the resume", q)
    return rows[0] if rows else None


def find_resume_by_hash(file_hash: str) -> dict | None:
    uid = current_user_id()

    def q():
        with _conn() as con:
            return _rows(con, "select id,label,filename from resumes where user_id=? and file_hash=?", (uid, file_hash))

    rows = _run("check for duplicates", q)
    return rows[0] if rows else None


def _file_dir():
    return config.data_dir() / "files"


def upload_original(data: bytes, file_hash: str) -> str:
    rel = f"{current_user_id()}/{file_hash}.pdf"

    def save():
        target = _file_dir() / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    _run("store the original file", save)
    return rel


def read_original(path: str) -> bytes | None:
    try:
        uid = current_user_id()
        if not path.startswith(uid + "/") or ".." in path:
            return None
        target = (_file_dir() / path).resolve()
        if _file_dir().resolve() not in target.parents or not target.is_file():
            return None
        return target.read_bytes()
    except Exception:
        return None


def add_resume(label: str, filename: str, file_hash: str, text: str, file_path: str | None) -> dict:
    row = {"id": str(uuid.uuid4()), "user_id": current_user_id(), "label": label, "filename": filename,
           "file_hash": file_hash, "extracted_text": text, "file_path": file_path, "uploaded_at": _now()}

    def q():
        with _conn() as con:
            con.execute("insert into resumes (id,user_id,label,filename,file_hash,extracted_text,file_path,uploaded_at) "
                        "values (:id,:user_id,:label,:filename,:file_hash,:extracted_text,:file_path,:uploaded_at)", row)
        return row

    return _run("save the resume", q)


def delete_resume(resume_id: str) -> None:
    resume = get_resume(resume_id)
    uid = current_user_id()

    def q():
        with _conn() as con:
            con.execute("delete from resumes where user_id=? and id=?", (uid, resume_id))
        if resume and resume.get("file_path"):
            with contextlib.suppress(OSError):
                (_file_dir() / resume["file_path"]).unlink()

    _run("delete the resume", q)


# ----------------------------------------------------------- applications
def list_applications() -> list[dict]:
    uid = current_user_id()

    def q():
        with _conn() as con:
            return _rows(con, "select a.*, r.label as resume_label from applications a "
                              "left join resumes r on r.id = a.resume_id "
                              "where a.user_id=? order by a.applied_on desc, a.rowid desc", (uid,))

    return _run("load applications", q)


def get_application(app_id: str) -> dict | None:
    return next((a for a in list_applications() if a["id"] == app_id), None)


def _app_row(company: str, role: str, jd: str, applied_on: date, status: str, notes: str, resume_id: str | None) -> dict[str, Any]:
    return {"company": company.strip(), "role": role.strip(), "job_description": jd, "applied_on": applied_on.isoformat(),
            "status": status, "notes": notes, "resume_id": resume_id}


def add_application(company: str, role: str, jd: str, applied_on: date, status: str, notes: str, resume_id: str | None) -> dict:
    row = {"id": str(uuid.uuid4()), "user_id": current_user_id(),
           **_app_row(company, role, jd, applied_on, status, notes, resume_id)}

    def q():
        with _conn() as con:
            con.execute("insert into applications (id,user_id,resume_id,company,role,job_description,applied_on,status,notes) "
                        "values (:id,:user_id,:resume_id,:company,:role,:job_description,:applied_on,:status,:notes)", row)
        return row

    return _run("save the application", q)


def update_application(app_id: str, company: str, role: str, jd: str, applied_on: date, status: str, notes: str, resume_id: str | None) -> None:
    uid = current_user_id()
    row = {**_app_row(company, role, jd, applied_on, status, notes, resume_id), "id": app_id, "uid": uid}

    def q():
        with _conn() as con:
            con.execute("update applications set company=:company, role=:role, job_description=:job_description, "
                        "applied_on=:applied_on, status=:status, notes=:notes, resume_id=:resume_id "
                        "where id=:id and user_id=:uid", row)

    _run("update the application", q)


def delete_application(app_id: str) -> None:
    uid = current_user_id()

    def q():
        with _conn() as con:
            con.execute("delete from applications where user_id=? and id=?", (uid, app_id))

    _run("delete the application", q)


# --------------------------------------------------------------- sessions
def _session_out(r: dict) -> dict:
    for key, empty in (("transcript", []), ("evaluations", []), ("report", {})):
        try:
            r[key] = json.loads(r[key]) if r.get(key) else empty
        except json.JSONDecodeError:
            r[key] = empty
    return r


def save_session(application_id: str, persona: str, transcript: list, evaluations: list, report: dict) -> dict:
    row = {"id": str(uuid.uuid4()), "user_id": current_user_id(), "application_id": application_id, "persona": persona,
           "transcript": json.dumps(transcript), "evaluations": json.dumps(evaluations), "report": json.dumps(report),
           "overall_score": report.get("overall_score"), "created_at": _now()}

    def q():
        with _conn() as con:
            con.execute("insert into interview_sessions (id,user_id,application_id,persona,transcript,evaluations,report,"
                        "overall_score,created_at) values (:id,:user_id,:application_id,:persona,:transcript,:evaluations,"
                        ":report,:overall_score,:created_at)", row)
        return _session_out(dict(row))

    return _run("save the interview", q)


def list_sessions(application_id: str | None = None) -> list[dict]:
    uid = current_user_id()

    def q():
        with _conn() as con:
            sql, args = "select * from interview_sessions where user_id=?", [uid]
            if application_id:
                sql += " and application_id=?"
                args.append(application_id)
            return [_session_out(r) for r in _rows(con, sql + " order by created_at, rowid", tuple(args))]

    return _run("load history", q)


def delete_session(session_id: str) -> None:
    uid = current_user_id()

    def q():
        with _conn() as con:
            con.execute("delete from interview_sessions where user_id=? and id=?", (uid, session_id))

    _run("delete the session", q)


# ---------------------------------------------------------------- privacy
def delete_all_user_data() -> None:
    uid = current_user_id()

    def q():
        with _conn() as con:
            for table in ("interview_sessions", "applications", "resumes"):
                con.execute(f"delete from {table} where user_id=?", (uid,))
        folder = _file_dir() / uid
        if folder.is_dir():
            for f in folder.glob("*"):
                with contextlib.suppress(OSError):
                    f.unlink()

    _run("delete your data", q)