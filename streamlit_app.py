import streamlit as st
import requests
import time
from datetime import datetime, timezone
from dateutil import parser as date_parser

# Page config
st.set_page_config(
    page_title="Service Status Dashboard", page_icon="🔍", layout="centered"
)

# Session state
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "services_data" not in st.session_state:
    st.session_state.services_data = {}


def get_status_emoji(status):
    return {"operational": "🟢", "degraded": "🟡", "outage": "🔴"}.get(status, "⚪")


def parse_indicator_block(data):
    # Generic Statuspage-like parsing
    ind = data.get("status", {}).get("indicator", "none")
    desc = data.get("status", {}).get("description", "")
    if ind == "none":
        status = "operational"
    elif ind in ("minor", "major"):
        status = "degraded"
    else:
        status = "outage"
    # Gather active incidents if present
    incidents = []
    for inc in data.get("incidents", []):
        name = inc.get("name") or inc.get("shortlink") or "Unnamed incident"
        incidents.append(name)
    return status, desc, incidents


def map_indicator(indicator: str):
    if indicator in ("none", "operational"):
        return "operational"
    if indicator in ("minor", "major", "partial_outage"):
        return "degraded"
    return "outage"


def check_gcp_component(component_name: str, incidents_url: str):
    """
    Fetches all GCP incidents, filters for active ones in North America
    affecting exactly the given component_name.
    """
    try:
        resp = requests.get(incidents_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()  # list of incident objects
        now = datetime.now(timezone.utc)
        active_inc = []
        for inc in data:
            # Skip if incident has an end time in the past
            end_ts = inc.get("end")
            if end_ts and date_parser.isoparse(end_ts) < now:
                continue
            # Check component names
            comps = [c.get("name", "") for c in inc.get("components", [])]
            # Only North America:
            desc = inc.get("external_desc", "")
            updates = [u.get("text", "") for u in inc.get("updates", [])]
            region_ok = "North America" in desc or any(
                "North America" in u for u in updates
            )
            if component_name in comps and region_ok:
                active_inc.append(
                    inc.get("external_desc") or updates[-1] or "No details"
                )
        if active_inc:
            return (
                "outage",
                (
                    f"{len(active_inc)} incident(s) affecting {component_name} in North America"
                ),
                active_inc,
            )
        else:
            return (
                "operational",
                (f"No active North America incidents for {component_name}"),
                [],
            )
    except Exception as e:
        return "outage", f"Error fetching GCP incidents: {e}", []


def check_openai_component(comp_key: str, proxy_url: str):
    """
    Fetches the OpenAI proxy URL, looks for a component whose name
    contains comp_key, and returns its status, description, and active incidents.
    Falls back to the global status if no matching component is found.
    """
    try:
        resp = requests.get(
            proxy_url, timeout=10, headers={"Accept": "application/json"}
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return "outage", f"Error fetching/parsing OpenAI status: {e}", []

    # Try new root‐level 'components' key, or fall back to nested 'page'
    components = data.get("components") or data.get(
        "page", {}).get("components", [])
    incidents = data.get("incidents") or data.get(
        "page", {}).get("incidents", [])

    # Find our target component
    comp = next(
        (c for c in components if comp_key.lower()
         in c.get("name", "").lower()), None
    )
    if comp:
        # Some APIs call it 'status', others 'indicator'
        raw_ind = comp.get("status") or comp.get("indicator", "none")
        status = map_indicator(raw_ind)
        desc = comp.get("description", "").strip(
        ) or "No description available"

        # Gather all incidents that list this component ID
        comp_id = comp.get("id")
        active = []
        for inc in incidents:
            # incidents might list affected components under 'components' or 'affected_components'
            affected = inc.get("components") or inc.get(
                "affected_components") or []
            affected_ids = [c.get("id") for c in affected]
            if comp_id in affected_ids:
                active.append(inc.get("name", "Unnamed incident"))

        return status, desc, active

    # — No matching component: fall back to global status block —
    root_status = data.get("status") or data.get("page", {}).get("status", {})
    raw_ind = root_status.get("indicator") or root_status.get("status", "none")
    status = map_indicator(raw_ind)
    desc = root_status.get(
        "description", "").strip() or "No global description"

    return status, desc, []


def refresh_all_services():
    services = {
        # GCP sub-services
        "GCP: Cloud Run": {
            "url": "https://status.cloud.google.com/products/adnGEDEt9zWzs8uF1oKA/history",
            "checker": lambda: check_gcp_component(
                "Cloud Run", "https://status.cloud.google.com/incidents.json"
            ),
        },
        "GCP: Cloud Scheduler": {
            "url": "https://status.cloud.google.com/products/XXXscheduler/history",
            "checker": lambda: check_gcp_component(
                "Cloud Scheduler", "https://status.cloud.google.com/incidents.json"
            ),
        },
        "GCP: Firebase": {
            "url": "https://status.cloud.google.com/products/YYYfirebase/history",
            "checker": lambda: check_gcp_component(
                "Firebase", "https://status.cloud.google.com/incidents.json"
            ),
        },
        "GCP: Cloud Storage": {
            "url": "https://status.cloud.google.com/products/ZZZstorage/history",
            "checker": lambda: check_gcp_component(
                "Cloud Storage", "https://status.cloud.google.com/incidents.json"
            ),
        },
        "GCP: Compute Engine": {
            "url": "https://status.cloud.google.com/products/DixAowEQm45KgqXKP5tR/history",
            "checker": lambda: check_gcp_component(
                "Compute Engine", "https://status.cloud.google.com/incidents.json"
            ),
        },
        "GCP: IAM": {
            "url": "https://status.cloud.google.com/products/adnGEDEt9zWzs8uF1oKA/history",
            "checker": lambda: check_gcp_component(
                "Identity and Access Management",
                "https://status.cloud.google.com/incidents.json",
            ),
        },
        # OpenAI components
        # OpenAI components, via your proxy URL
        "OpenAI: Chat": {
            "url": "https://status.openai.com/",
            "checker": lambda: check_openai_component(
                "chat", "https://status.openai.com/proxy/status.openai.com"
            ),
        },
        "OpenAI: Embedding": {
            "url": "https://status.openai.com/",
            "checker": lambda: check_openai_component(
                "embedding", "https://status.openai.com/proxy/status.openai.com"
            ),
        },
        # legacy services
        "Netlify": {
            "url": "https://www.netlifystatus.com/",
            "api_url": "https://www.netlifystatus.com/api/v2/summary.json",
        },
        "Cloudflare": {
            "url": "https://www.cloudflarestatus.com/",
            "api_url": "https://www.cloudflarestatus.com/api/v2/status.json",
        },
    }

    prog = st.progress(0)
    info = st.empty()
    total = len(services)
    for i, (name, cfg) in enumerate(services.items()):
        info.text(f"Checking {name}...")
        if "checker" in cfg:
            status, msg, incs = cfg["checker"]()
        else:
            # fallback to generic statuspage parsing
            resp = requests.get(cfg["api_url"], headers={
                                "Accept": "application/json"})
            status, msg, incs = parse_indicator_block(resp.json())
        st.session_state.services_data[name] = {
            "status": status,
            "message": msg,
            "incidents": incs,
            "url": cfg.get("url"),
            "last_checked": datetime.now(),
        }
        prog.progress((i + 1) / total)
        time.sleep(0.2)
    prog.empty()
    info.empty()
    st.session_state.last_refresh = datetime.now()


# UI
st.title("🔍 Detailed Service Status Dashboard")
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Refresh All"):
        refresh_all_services()
        st.rerun()

if st.session_state.last_refresh is None:
    with st.spinner("Loading statuses..."):
        refresh_all_services()

st.caption(f"Last updated: {st.session_state.last_refresh:%Y-%m-%d %H:%M:%S}")

# overall banner
statuses = [d["status"] for d in st.session_state.services_data.values()]
if all(s == "operational" for s in statuses):
    st.success("🟢 All Systems Fully Operational")
elif any(s == "outage" for s in statuses):
    st.error("🔴 One or more services are down")
else:
    st.warning("🟡 Some services are reporting degraded performance")

# show cards two-column
cols = st.columns(2)
for idx, (svc, data) in enumerate(st.session_state.services_data.items()):
    c = cols[idx % 2]
    with c:
        emo = get_status_emoji(data["status"])
        st.markdown(f"### {emo} {svc}")
        if data["status"] == "operational":
            st.success(data["message"])
        elif data["status"] == "degraded":
            st.warning(data["message"])
        else:
            st.error(data["message"])
        if data["incidents"]:
            st.markdown("**Active Incident Details:**")
            for inc in data["incidents"]:
                st.markdown(f"- {inc}")
        st.caption(f"Last checked: {data['last_checked']:%H:%M:%S}")
        if data["url"]:
            st.markdown(f"[🔗 Official Status Page]({data['url']})")
        st.divider()

st.info(
    """
💡 **Live Status Information**

This dashboard displays **actual current outage data** based on real-time monitoring of official status pages.
The status shown reflects genuine service disruptions happening right now.

**Official Status Pages:**
- Google Cloud: https://status.cloud.google.com/
- OpenAI: https://status.openai.com/
- Netlify: https://www.netlifystatus.com/
- Cloudflare: https://www.cloudflarestatus.com/

**Note:** For production use, implement a backend proxy to fetch status data and avoid CORS limitations.
"""
)

st.markdown("---")
st.markdown(
    "<small>Tracks individual GCP products (North America only) and OpenAI sub-systems for chat & embeddings, plus Netlify & Cloudflare.</small>",
    unsafe_allow_html=True,
)
