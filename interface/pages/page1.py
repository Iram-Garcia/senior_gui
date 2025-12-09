import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import os
import shutil
import datetime
from pathlib import Path


def maybe_rerun():
    """Try to rerun the Streamlit script; fall back to stopping execution if unavailable."""
    try:
        st.experimental_rerun()
    except Exception:
        try:
            st.stop()
        except Exception:
            pass


def get_tables(conn: sqlite3.Connection):
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def load_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM \"{table}\"", conn)


def replace_table(conn: sqlite3.Connection, table: str, df: pd.DataFrame):
    # replace the table with the edited dataframe
    df.to_sql(table, conn, if_exists="replace", index=False)


def parse_log_file(log_path: str) -> pd.DataFrame:
    rows = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            data = {}
            for p in parts:
                if p.startswith("Image:"):
                    data["image"] = p.split("Image:", 1)[1].strip()
                elif p.startswith("Timestamp:"):
                    data["timestamp"] = p.split("Timestamp:", 1)[1].strip()
                elif p.startswith("Execution Time:"):
                    val = p.split("Execution Time:", 1)[1].strip()
                    if val.endswith("s"):
                        val = val[:-1]
                    try:
                        data["execution_time"] = float(val)
                    except Exception:
                        data["execution_time"] = None
                elif p.startswith("Text:"):
                    data["text"] = p.split("Text:", 1)[1].strip()
                elif p.startswith("Confidence:"):
                    try:
                        data["confidence"] = float(p.split("Confidence:", 1)[1].strip())
                    except Exception:
                        data["confidence"] = None
            rows.append(data)
    df = pd.DataFrame(rows)
    for c in ["image", "timestamp", "execution_time", "text", "confidence"]:
        if c not in df.columns:
            df[c] = None
    return df[["image", "timestamp", "execution_time", "text", "confidence"]]


def import_log_to_db(log_path: str, db_path: str, table_name: str = "results"):
    df = parse_log_file(log_path)
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    except Exception:
        pass
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()


def main():
    st.title("Database Viewer & Editor — Page 1")
    st.markdown("Upload an SQLite database file, or provide a path to one on the server.")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader("Upload SQLite file (.db/.sqlite)")
        db_path = st.text_input("Or enter a path to an SQLite file on this machine:")
    with col2:
        open_mode = st.radio("Open as:", ["Read-only", "Read / Write"]) 

    pages_dir = Path(__file__).resolve().parent
    interface_dir = pages_dir.parent
    default_db = str(interface_dir / "data.db")
    default_log = str(interface_dir / "license_plate_results.txt")

    if os.path.exists(default_db):
        st.info(f"Detected DB at `{default_db}` — it will be used by default.")
        if not db_path:
            db_path = default_db
    if not db_path and os.path.exists(default_log):
        st.info(f"No DB provided. Found log at `{default_log}` — you can import it to a DB or edit the parsed log.")

    db_file = None
    conn = None
    if uploaded is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp.write(uploaded.getbuffer())
        tmp.flush()
        tmp.close()
        db_file = tmp.name
        st.success(f"Uploaded and opened temp DB: {os.path.basename(db_file)}")
    elif db_path:
        if os.path.exists(db_path):
            db_file = db_path
        else:
            st.warning("Path does not exist yet. Please upload a DB or provide an existing path.")

    # parsed log actions
    if not db_file and os.path.exists(default_log):
        st.subheader("Parsed Log (no DB found)")
        df_log = parse_log_file(default_log)
        try:
            edited_log = st.experimental_data_editor(df_log, num_rows="dynamic")
        except Exception:
            st.dataframe(df_log)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Import log to DB (create data.db)"):
                try:
                    if os.path.exists(default_db):
                        bak = f"{default_db}.{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.bak"
                        shutil.copy2(default_db, bak)
                        st.info(f"Backed up existing DB to {bak}")
                    import_log_to_db(default_log, default_db)
                    st.success(f"Imported log into DB: {default_db}")
                    maybe_rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")
        with c2:
            if st.button("Export parsed log CSV"):
                csv = df_log.to_csv(index=False).encode("utf-8")
                st.download_button("Download CSV", data=csv, file_name="parsed_log.csv")

    # open DB
    if db_file:
        try:
            if open_mode == "Read-only":
                conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
            else:
                conn = sqlite3.connect(db_file)
        except Exception as e:
            st.error(f"Could not open DB: {e}")

    if conn:
        try:
            tables = get_tables(conn)
            if not tables:
                st.info("No tables found in this database.")
                return

            table = st.selectbox("Choose a table to view/edit:", tables)
            if table:
                df = load_table(conn, table)
                st.markdown(f"**Preview — table `{table}`**")

                # editor area
                editor_key = f"data_editor_{table}"
                use_editor = True
                try:
                    if editor_key not in st.session_state:
                        st.session_state[editor_key] = df.copy()
                    edited = st.experimental_data_editor(st.session_state[editor_key], num_rows="dynamic", key=editor_key)
                    st.session_state[editor_key] = edited
                except Exception:
                    use_editor = False
                    edited = df.copy()

                # Add row UI
                if use_editor:
                    if st.button("Add empty row"):
                        cols = list(st.session_state[editor_key].columns)
                        empty = {c: None for c in cols}
                        st.session_state[editor_key] = pd.concat([st.session_state[editor_key], pd.DataFrame([empty])], ignore_index=True, sort=False)
                        maybe_rerun()
                else:
                    st.info("Editable table not available in this environment. Use the form below to add a single row.")
                    with st.form(key=f"add_row_form_{table}"):
                        new_vals = {}
                        for col in df.columns:
                            new_vals[col] = st.text_input(f"{col}")
                        submit = st.form_submit_button("Add row")
                        if submit:
                            try:
                                cols = ",".join([f'"{c}"' for c in df.columns])
                                placeholders = ",".join(["?" for _ in df.columns])
                                values = []
                                for c in df.columns:
                                    v = new_vals[c]
                                    if c in ("execution_time", "confidence"):
                                        try:
                                            v = float(v) if v not in (None, "") else None
                                        except Exception:
                                            v = None
                                    values.append(v)
                                conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
                                conn.commit()
                                st.success("Row added.")
                            except Exception as e:
                                st.error(f"Failed to add row: {e}")

                # Save mode
                try:
                    save_mode = st.selectbox("Save mode:", ["Replace table (default)", "Append rows — add edited rows to existing table"], index=0)
                except Exception:
                    save_mode = "Replace table (default)"

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Save changes"):
                        if open_mode == "Read-only":
                            st.error("Database opened read-only. Switch to Read / Write to save changes.")
                        else:
                            try:
                                if os.path.exists(db_file):
                                    bak = f"{db_file}.{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.bak"
                                    shutil.copy2(db_file, bak)
                                    st.info(f"Backed up DB to {bak}")
                                if save_mode.startswith("Replace"):
                                    replace_table(conn, table, edited)
                                    st.success("Table saved successfully (replaced).")
                                else:
                                    try:
                                        if not isinstance(edited, pd.DataFrame):
                                            st.error("No editable DataFrame available to append.")
                                        else:
                                            edited.to_sql(table, conn, if_exists="append", index=False)
                                            st.success("Rows appended successfully.")
                                    except Exception as _e:
                                        st.error(f"Failed to append rows: {_e}")
                            except Exception as e:
                                st.error(f"Error saving table: {e}")

                with c2:
                    if st.button("Export CSV"):
                        csv = df.to_csv(index=False).encode("utf-8")
                        st.download_button("Download CSV", data=csv, file_name=f"{table}.csv")

                with c3:
                    if st.button("Refresh"):
                        maybe_rerun()

                st.markdown("---")
                st.markdown("**Run SQL** — run a query against this DB (SELECT queries show results).")
                sql = st.text_area("SQL", value=f"SELECT * FROM \"{table}\" LIMIT 100")
                if st.button("Run SQL"):
                    if not sql.strip():
                        st.warning("Enter a SQL query first.")
                    else:
                        try:
                            cur = conn.cursor()
                            cur.execute(sql)
                            if sql.strip().lower().startswith("select"):
                                res = cur.fetchall()
                                cols = [d[0] for d in cur.description] if cur.description else []
                                res_df = pd.DataFrame(res, columns=cols)
                                st.dataframe(res_df)
                            else:
                                if open_mode == "Read-only":
                                    st.error("Non-SELECT queries require write access.")
                                else:
                                    conn.commit()
                                    st.success("Query executed and changes committed.")
                        except Exception as e:
                            st.error(f"SQL error: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
