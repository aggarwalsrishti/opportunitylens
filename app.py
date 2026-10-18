import streamlit as st
from dotenv import load_dotenv
from services.tinyfish import TinyFishClient, TinyFishError
from utils.matching import score_opportunity
from data.database import init_db, save_opportunity, get_saved, update_status, remove_saved
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

def urlparse_host(url):
    try:
        return urlparse(url).netloc or "Web result"
    except Exception:
        return "Web result"

load_dotenv()
st.set_page_config(page_title="OpportunityLens", page_icon="🔎", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1180px;}
.hero {padding: 1.5rem 1.7rem; border-radius: 18px; background: linear-gradient(120deg,#102a43,#176b72); color: white; margin-bottom: 1rem;}
.hero h1 {color:white; margin:0;}
.hero p {color:#e1f3f3; margin:.45rem 0 0 0;}
.small-muted {color:#64748b; font-size:.9rem;}
</style>
<div class="hero">
  <h1>🔎 OpportunityLens</h1>
  <p>Find opportunities. Understand your fit. Follow the original source.</p>
</div>
""", unsafe_allow_html=True)

init_db()
api_key = os.getenv("TINYFISH_API_KEY", "").strip()
client = TinyFishClient(api_key) if api_key else None
with st.sidebar:
    st.header("Your profile")
    degree = st.selectbox("Degree / background", ["B.Tech / Engineering", "BCA / Computer Applications", "B.Sc", "BA / Humanities", "MBA / Management", "Other"])
    year = st.selectbox("Current year", ["1st year", "2nd year", "3rd year", "4th year", "Graduate / Fresher", "Other"])
    skills_text = st.text_input("Skills (comma-separated)", "Python, problem solving, communication")
    interests_text = st.text_input("Interests (comma-separated)", "software development, AI, research")
    location = st.text_input("Preferred location", "India")
    categories = st.multiselect("Opportunity types", ["Internships", "Hackathons", "Scholarships", "Fellowships", "Graduate jobs"], default=["Internships", "Hackathons"])
    st.caption("Matching is a heuristic aid, not an official eligibility decision.")

tab_search, tab_saved, tab_about = st.tabs(["Discover", "Saved opportunities", "About"])

with tab_search:
    left, right = st.columns([3, 1])
    with left:
        query = st.text_input("What are you looking for?", "software engineering internships for second year students in India")
    with right:
        st.write("")
        st.write("")
        max_results = st.slider("Results to inspect", 3, 8, 5)
    search_clicked = st.button("Search live opportunities", type="primary", use_container_width=False)

    if search_clicked:
        if not client:
            st.error("TINYFISH_API_KEY is missing. Copy .env.example to .env and add a newly generated TinyFish API key.")
        elif not query.strip():
            st.warning("Enter a search query first.")
        else:
            try:
                with st.spinner("Searching the live web with TinyFish…"):
                    results = client.search(
                        query=f"{query} {' '.join(categories)} {location}",
                        location="IN", language="en",
                        purpose="Find internships, hackathons, scholarships and other student opportunities relevant to this profile",
                    )
                items = results[:max_results]
                if not items:
                    st.info("No search results returned. Try a broader query.")
                else:
                    st.session_state["opportunity_results"] = items
                    st.session_state["search_query"] = query
                    st.session_state["last_search"] = datetime.now(timezone.utc).isoformat()
            except TinyFishError as exc:
                st.error(f"TinyFish Search failed: {exc}")

    items = st.session_state.get("opportunity_results", [])
    if items:
        st.caption(f"Search: {st.session_state.get('search_query','')} · Last checked: {st.session_state.get('last_search','')}")
        for idx, item in enumerate(items):
            title = item.get("title") or "Untitled opportunity"
            url = item.get("url", "")
            snippet = item.get("snippet", "")
            score, reasons = score_opportunity(
                title=title, snippet=snippet, degree=degree, year=year,
                skills=skills_text, interests=interests_text, location=location
            )
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.subheader(title)
                    st.write(snippet or "TinyFish returned no summary for this result.")
                    if url:
                        st.markdown(f"[Open original source]({url})")
                    st.caption(f"Source: {item.get('site_name') or urlparse_host(url)}" + (f" · Date: {item.get('date')}" if item.get("date") else ""))
                with c2:
                    st.metric("Profile match", f"{score}%")
                    if st.button("Save", key=f"save_{idx}"):
                        save_opportunity(title, url, snippet, score, "; ".join(reasons))
                        st.success("Saved")
                st.write("**Why it may fit:** " + (", ".join(reasons) if reasons else "General relevance based on your search."))
                if st.button("Fetch source details", key=f"fetch_{idx}"):
                    if not client:
                        st.error("Add TINYFISH_API_KEY to .env to fetch source details.")
                    elif not url.startswith("https://") and not url.startswith("http://"):
                        st.warning("This result has no valid URL to fetch.")
                    else:
                        try:
                            with st.spinner("Fetching source content with TinyFish…"):
                                pages = client.fetch([url])
                            if not pages:
                                st.warning("TinyFish did not return readable page content. Open the original source to verify details.")
                            else:
                                page = pages[0]
                                st.markdown(f"**Fetched title:** {page.get('title') or title}")
                                page_text = page.get("text") or "No readable text returned."
                                st.text_area("Source content (first 8,000 characters)", page_text[:8000], height=220, key=f"source_{idx}")
                                st.caption("Check deadlines and eligibility against the original page before applying.")
                        except TinyFishError as exc:
                            st.error(f"TinyFish Fetch failed: {exc}")

with tab_saved:
    st.subheader("Your saved opportunities")
    saved = get_saved()
    if not saved:
        st.info("No saved opportunities yet. Run a search and save a result.")
    for row in saved:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(f"**{row['title']}**")
                if row["url"]:
                    st.markdown(f"[Open source]({row['url']})")
                st.caption(f"Match: {row['score']}% · Saved: {row['saved_at']}")
                if row["reason"]:
                    st.write(row["reason"])
            with c2:
                status = st.selectbox("Status", ["Interested", "Applied", "Not pursuing"], index=["Interested", "Applied", "Not pursuing"].index(row["status"]), key=f"status_{row['id']}")
                if status != row["status"]:
                    update_status(row["id"], status)
                    st.rerun()
            with c3:
                if st.button("Remove", key=f"remove_{row['id']}"):
                    remove_saved(row["id"])
                    st.rerun()

with tab_about:
    st.subheader("How OpportunityLens works")
    st.markdown("""
1. **TinyFish Search** discovers current opportunity pages on the live web.
2. **TinyFish Fetch** retrieves clean page content when you inspect a result.
3. A transparent rule-based matcher estimates relevance from your profile and the result text.
4. You can save opportunities and track your application status locally.

**Responsible-use note:** Match scores are heuristic relevance indicators, not verified eligibility decisions. Websites can change, search snippets may be incomplete, and deadlines must be checked on the original source. This MVP does not submit applications automatically.
""")
    st.info("Data storage: saved opportunities are stored locally in opportunitylens.db on this computer. There is no account system or cloud sync in this MVP.")

