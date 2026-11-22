"""Talk or Type to your Database: Streamlit + OpenAI + Supabase (Postgres), no n8n."""

import hashlib
import json
import re

import pandas as pd
import psycopg2
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Talk or Type to your Database", page_icon="🎙️")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
DB_URL = st.secrets["DATABASE_URL"]
MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_ROWS = 200
MAX_STEPS = 5


# ---------- Database ----------

def get_conn():
    # A fresh connection per query: Supabase's pooler drops idle connections,
    # so a long-lived cached connection would go stale on Streamlit Cloud.
    return psycopg2.connect(DB_URL, connect_timeout=10, sslmode="require")


@st.cache_data(ttl=600)
def load_schema() -> str:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    tables: dict[str, list[str]] = {}
    for table, column, dtype in rows:
        tables.setdefault(table, []).append(f"{column} ({dtype})")
    return "\n".join(f"- {t}: {', '.join(cols)}" for t, cols in tables.items())


def run_select(query: str) -> pd.DataFrame:
    q = query.strip().rstrip(";").strip()
    # Second line of defence; the first is the read-only database user.
    if ";" in q or not re.match(r"(?is)^(select|with)\b", q):
        raise ValueError("Only a single SELECT (or WITH ... SELECT) statement is allowed.")
    conn = get_conn()
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '10s'")
            cur.execute(q)
            columns = [d.name for d in cur.description]
            rows = cur.fetchmany(MAX_ROWS)
        return pd.DataFrame(rows, columns=columns)
    finally:
        conn.close()


# ---------- AI ----------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run one read-only PostgreSQL SELECT query and return the rows as JSON.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "A single SELECT statement."}},
                "required": ["query"],
            },
        },
    }
]


def answer(question: str, history: list[dict]) -> tuple[str, list[dict]]:
    system = (
        "You are a data assistant for a PostgreSQL database.\n"
        f"Schema (public):\n{load_schema()}\n\n"
        "Always call run_sql to get real data before answering a question about the data. "
        "Write valid PostgreSQL. Answer in 1-3 short sentences that sound natural read aloud, "
        "You have read-only access. If asked to delete, insert, update or change data, "
        "say clearly that this assistant can only read data and cannot modify it. "
        "in the same language the user wrote in. If a query fails, read the error, fix the SQL "
        "and try again. If it still fails, tell the user the exact error instead of a vague apology."
    )
    messages = [{"role": "system", "content": system}, *history[-10:], {"role": "user", "content": question}]
    steps: list[dict] = []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content or "", steps

        messages.append(msg.model_dump(exclude_none=True))
        for call in msg.tool_calls:
            query = call.function.arguments
            try:
                query = json.loads(call.function.arguments)["query"]
                df = run_select(query)
                result = df.to_json(orient="records", date_format="iso", default_handler=str)
                steps.append({"sql": query, "df": df})
            except Exception as e:  # sent back to the model so it can fix its SQL
                result = f"ERROR: {e}"
                steps.append({"sql": query, "error": str(e)})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result[:8000]})

    return f"I couldn't finish that in {MAX_STEPS} steps. Try rephrasing the question.", steps


def transcribe(audio_file) -> str:
    return client.audio.transcriptions.create(
        model="whisper-1", file=("question.wav", audio_file.getvalue())
    ).text


def speak(text: str) -> bytes | None:
    try:
        return client.audio.speech.create(model="tts-1", voice="alloy", input=text[:4000]).content
    except Exception:
        return None  # the text answer still shows if speech fails


# ---------- UI ----------

st.session_state.setdefault("messages", [])
st.session_state.setdefault("last_audio", None)

with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.last_audio = None
        st.rerun()

st.title("Talk or Type to your Database 🎙️⌨️📊")
st.write("Click the microphone to speak, or type your question in the chat box below.")


def render(m: dict) -> None:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        for step in m.get("steps", []):
            with st.expander("SQL used"):
                st.code(step["sql"], language="sql")
                if "error" in step:
                    st.error(step["error"])
                else:
                    st.dataframe(step["df"], use_container_width=True)
        if m.get("audio"):
            st.audio(m["audio"], format="audio/mp3")


for m in st.session_state.messages:
    render(m)

audio = st.audio_input("🎙️ Ask with your voice")
typed = st.chat_input("Or type your question here...")

question = None
if typed:
    question = typed
elif audio is not None:
    # st.audio_input keeps its value across reruns; only handle a new recording once.
    digest = hashlib.md5(audio.getvalue()).hexdigest()
    if digest != st.session_state.last_audio:
        st.session_state.last_audio = digest
        with st.spinner("Transcribing..."):
            question = transcribe(audio)

if question:
    user_msg = {"role": "user", "content": question}
    render(user_msg)
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    with st.spinner("Querying the database..."):
        try:
            text, steps = answer(question, history)
        except Exception as e:
            text, steps = f"Something went wrong: {e}", []
        bot_msg = {"role": "assistant", "content": text, "steps": steps, "audio": speak(text)}

    render(bot_msg)
    st.session_state.messages += [user_msg, bot_msg]
