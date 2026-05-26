import streamlit as st
import sqlite3
import pandas as pd
import re
import os
import shutil
from datetime import date, timedelta, datetime

st.set_page_config(page_title="Insurance Register", page_icon="📋", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
html, body, .stApp { font-size: 22px !important; }

.big-title {
    font-size: 82px !important;
    font-weight: 1000 !important;
    color: #0f172a;
    margin-bottom: 10px;
}

h1 { font-size: 68px !important; font-weight: 900 !important; }
h2, h3 { font-size: 34px !important; font-weight: 800 !important; }

label, p, div, span { font-size: 22px !important; }
input, textarea, select { font-size: 22px !important; }

.stButton > button {
    font-size: 21px !important;
    height: 58px;
    border-radius: 14px;
    font-weight: 800;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #0f172a;
    box-shadow: 0px 3px 10px rgba(15,23,42,0.08);
}

.stButton > button:hover {
    border: 2px solid #2563eb;
    color: #2563eb;
    background: #f8fafc;
}

.stDownloadButton > button {
    font-size: 22px !important;
    height: 56px;
    border-radius: 12px;
    font-weight: 800;
}

.nav-box {
    background: #f8fafc;
    padding: 18px;
    border-radius: 18px;
    border: 1px solid #e2e8f0;
    box-shadow: 0px 4px 16px rgba(15,23,42,0.08);
    margin-bottom: 18px;
}

.kpi-card {
    background-color: white;
    padding: 28px;
    border-radius: 18px;
    box-shadow: 0px 4px 16px rgba(0,0,0,0.12);
    border-left: 8px solid #1f77b4;
    margin-bottom: 20px;
}

.kpi-title { color: #555; font-size: 24px !important; font-weight: 800; }
.kpi-value { color: #111; font-size: 50px !important; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

# =========================
# DATABASE
# =========================
DB_FILE = "insurance.db"
BACKUP_FOLDER = "backups"

if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS policies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_date TEXT,
    to_date TEXT,
    name TEXT,
    address TEXT,
    mobile_no TEXT,
    policy_type TEXT,
    policy_prefix TEXT,
    policy_mode TEXT,
    policy_no TEXT UNIQUE,
    renewal_policy_no TEXT,
    premium REAL,
    sum_insured REAL,
    detail TEXT,
    remark TEXT,
    renewal_of TEXT,
    renewed_by TEXT
)
""")
conn.commit()

def add_column_if_missing(column_name, column_type):
    c.execute("PRAGMA table_info(policies)")
    existing_columns = [col[1] for col in c.fetchall()]
    if column_name not in existing_columns:
        c.execute("ALTER TABLE policies ADD COLUMN {} {}".format(column_name, column_type))
        conn.commit()

required_columns = {
    "from_date": "TEXT",
    "to_date": "TEXT",
    "name": "TEXT",
    "address": "TEXT",
    "mobile_no": "TEXT",
    "policy_type": "TEXT",
    "policy_prefix": "TEXT",
    "policy_mode": "TEXT",
    "policy_no": "TEXT",
    "renewal_policy_no": "TEXT",
    "premium": "REAL",
    "sum_insured": "REAL",
    "detail": "TEXT",
    "remark": "TEXT",
    "renewal_of": "TEXT",
    "renewed_by": "TEXT"
}

for col, typ in required_columns.items():
    add_column_if_missing(col, typ)

# =========================
# HELPERS
# =========================
POLICY_PREFIX = {
    "Fire": "11",
    "Misc": "48",
    "Motor": "31"
}

EXPIRING_OPTIONS = {
    "Today": 0,
    "1 Day": 1,
    "7 Days": 7,
    "15 Days": 15,
    "30 Days": 30,
    "45 Days": 45,
    "60 Days": 60,
    "90 Days": 90
}

DISPLAY_COLUMNS = [
    "from_date",
    "to_date",
    "name",
    "address",
    "mobile_no",
    "policy_type",
    "policy_prefix",
    "policy_mode",
    "policy_no",
    "renewal_policy_no",
    "premium",
    "sum_insured",
    "detail",
    "remark"
]

def create_backup():
    conn.commit()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_FOLDER, "insurance_backup_{}.db".format(timestamp))

    shutil.copy2(DB_FILE, backup_file)

    return backup_file

def default_to_date():
    return date.today() + timedelta(days=364)

def validate_policy(policy_type, policy_no):
    prefix = POLICY_PREFIX[policy_type]
    pattern = r"^{}/\d{{4}}/\d{{3,5}}$".format(prefix)
    return bool(re.match(pattern, str(policy_no).strip()))

def validate_mobile(mobile_no):
    return bool(re.match(r"^\d{10}$", str(mobile_no).strip()))

def get_all_policies():
    return pd.read_sql_query("SELECT * FROM policies ORDER BY to_date ASC", conn)

def clean_dates(df):
    if not df.empty:
        df["from_date_dt"] = pd.to_datetime(df["from_date"], errors="coerce").dt.date
        df["to_date_dt"] = pd.to_datetime(df["to_date"], errors="coerce").dt.date
    return df

def prepare_display(df):
    cols = [col for col in DISPLAY_COLUMNS if col in df.columns]
    return df[cols]

def show_table(df, height=550):
    st.dataframe(df, width=1800, height=height)

def export_csv(df, file_name):
    if not df.empty:
        st.download_button(
            "⬇ Export CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=file_name,
            mime="text/csv"
        )

def display_kpi(title, value):
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-title">{}</div>
        <div class="kpi-value">{}</div>
    </div>
    """.format(title, value), unsafe_allow_html=True)

def filter_and_select_policy(page_key):
    df = clean_dates(get_all_policies())

    if df.empty:
        st.info("No policies found.")
        return None

    search_text = st.text_input("Search by Policy No or Name", key=page_key + "_search")
    use_date_filter = st.checkbox("Apply Date Filter", key=page_key + "_date_filter")

    filtered = df.copy()

    if search_text:
        filtered = filtered[
            filtered["name"].astype(str).str.contains(search_text, case=False, na=False) |
            filtered["policy_no"].astype(str).str.contains(search_text, case=False, na=False)
        ]

    if use_date_filter:
        start_date = st.date_input(
            "From Date Filter",
            value=date.today() - timedelta(days=365),
            key=page_key + "_start"
        )
        end_date = st.date_input(
            "To Date Filter",
            value=default_to_date(),
            key=page_key + "_end"
        )

        filtered = filtered[
            (filtered["from_date_dt"] >= start_date) &
            (filtered["to_date_dt"] <= end_date)
        ]

    filtered = filtered.sort_values(by="to_date_dt", ascending=True)
    display_filtered = prepare_display(filtered)

    if display_filtered.empty:
        st.warning("No matching policies found.")
        return None

    st.markdown("### Matching Policies")
    show_table(display_filtered, 420)
    export_csv(display_filtered, page_key + "_matching_policies.csv")

    options = ["-- Select Policy --"]

    for _, row in filtered.iterrows():
        options.append("{} | {} | To: {}".format(row["policy_no"], row["name"], row["to_date"]))

    selected_option = st.selectbox("Select Policy", options, key=page_key + "_select")

    if selected_option == "-- Select Policy --":
        return None

    selected_policy_no = selected_option.split(" | ")[0]
    selected_df = filtered[filtered["policy_no"] == selected_policy_no]

    if selected_df.empty:
        return None

    return selected_df.iloc[0]

# =========================
# HEADER
# =========================
st.markdown('<div class="big-title">📋 Insurance Policy Register</div>', unsafe_allow_html=True)

# =========================
# ENTERPRISE HORIZONTAL NAVIGATION
# =========================
if "show_menu" not in st.session_state:
    st.session_state.show_menu = False

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if st.button("☰ Menu"):
    st.session_state.show_menu = not st.session_state.show_menu

if st.session_state.show_menu:
    st.markdown('<div class="nav-box">', unsafe_allow_html=True)

    nav_cols = st.columns(6)

    with nav_cols[0]:
        if st.button("📊 Dashboard"):
            st.session_state.page = "Dashboard"

    with nav_cols[1]:
        if st.button("➕ Add Policy"):
            st.session_state.page = "Add Policy"

    with nav_cols[2]:
        if st.button("📄 View Policies"):
            st.session_state.page = "View Policies"

    with nav_cols[3]:
        if st.button("🔁 Renew Policy"):
            st.session_state.page = "Renew Policy"

    with nav_cols[4]:
        if st.button("✏️ Update Policy"):
            st.session_state.page = "Update Policy"

    with nav_cols[5]:
        if st.button("🗑 Delete Policy"):
            st.session_state.page = "Delete Policy"

    st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.page

st.markdown("---")

# =========================
# DASHBOARD
# =========================
if page == "Dashboard":
    st.subheader("📊 Dashboard")

    df = clean_dates(get_all_policies())

    if df.empty:
        st.info("No policies found.")
    else:
        filter_policy_type = st.selectbox("Policy Type", ["All", "Fire", "Misc", "Motor"])

        expiring_label = st.selectbox(
            "Expiring Soon Window",
            list(EXPIRING_OPTIONS.keys()),
            index=1
        )

        expiring_days = EXPIRING_OPTIONS[expiring_label]
        filtered_df = df.copy()

        if filter_policy_type != "All":
            filtered_df = filtered_df[filtered_df["policy_type"] == filter_policy_type]

        today = date.today()
        expiring_limit = today + timedelta(days=expiring_days)

        expiring_df = filtered_df[
            (filtered_df["to_date_dt"] >= today) &
            (filtered_df["to_date_dt"] <= expiring_limit)
        ]

        expired_not_renewed_df = filtered_df[
            (filtered_df["to_date_dt"] < today) &
            ((filtered_df["renewed_by"].isna()) | (filtered_df["renewed_by"] == ""))
        ]

        k1, k2, k3 = st.columns(3)

        with k1:
            display_kpi("Total Policies", len(filtered_df))
        with k2:
            display_kpi("Expiring Soon", len(expiring_df))
        with k3:
            display_kpi("Expired Not Renewed", len(expired_not_renewed_df))

        st.markdown("---")

        st.markdown("### 💾 Database Backup")

        if st.button("Create Backup"):
            backup_path = create_backup()
            st.success("Backup created successfully: {}".format(backup_path))

        st.markdown("---")

        st.markdown("### ⏳ Policies About to Expire")
        expiring_display = prepare_display(expiring_df)

        if expiring_display.empty:
            st.success("No policies expiring in selected window.")
        else:
            show_table(expiring_display, 520)
            export_csv(expiring_display, "policies_about_to_expire.csv")

        st.markdown("### ⚠️ Expired Not Renewed Policies")
        expired_display = prepare_display(expired_not_renewed_df)

        if expired_display.empty:
            st.success("No expired not renewed policies.")
        else:
            show_table(expired_display, 520)
            export_csv(expired_display, "expired_not_renewed.csv")

        st.markdown("### 📄 Recent Policies")
        recent_display = prepare_display(filtered_df.sort_values(by="to_date_dt", ascending=True))
        show_table(recent_display, 600)
        export_csv(recent_display, "recent_policies.csv")

# =========================
# ADD POLICY
# =========================
elif page == "Add Policy":
    st.subheader("➕ Add Policy")

    policy_type = st.selectbox("Policy Type", ["Fire", "Misc", "Motor"])
    prefix = POLICY_PREFIX[policy_type]

    st.info("{} policy must start with {}. Format example: {}/XXXX/435".format(policy_type, prefix, prefix))

    with st.form("add_form"):
        from_date = st.date_input("From Date", value=date.today())
        to_date = st.date_input("To Date", value=default_to_date())

        name = st.text_input("Name")
        address = st.text_area("Address")
        mobile_no = st.text_input("Mobile No", max_chars=10)

        policy_prefix = st.text_input("Policy Prefix", value=prefix)
        policy_mode = st.text_input("Policy Mode", value="New")
        policy_no = st.text_input("Policy No", value=prefix + "/", help="Format: 48/XXXX/435")

        premium = st.number_input("Premium", min_value=0.0, step=100.0)
        sum_insured = st.number_input("Sum Insured", min_value=0.0, step=1000.0)
        detail = st.text_area("Detail")
        remark = st.text_area("Remark")

        submit = st.form_submit_button("Save Policy")

        if submit:
            if policy_prefix != prefix:
                st.error("Policy prefix must be {} for {} policy.".format(prefix, policy_type))
            elif not validate_policy(policy_type, policy_no):
                st.error("{} policy must follow format {}/XXXX/435.".format(policy_type, prefix))
            elif not validate_mobile(mobile_no):
                st.error("Mobile number must be exactly 10 digits.")
            else:
                try:
                    c.execute("""
                    INSERT INTO policies (
                        from_date, to_date, name, address, mobile_no,
                        policy_type, policy_prefix, policy_mode, policy_no,
                        renewal_policy_no, premium, sum_insured, detail,
                        remark, renewal_of, renewed_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(from_date),
                        str(to_date),
                        name,
                        address,
                        mobile_no,
                        policy_type,
                        policy_prefix,
                        policy_mode,
                        policy_no.strip(),
                        "",
                        premium,
                        sum_insured,
                        detail,
                        remark,
                        "",
                        ""
                    ))
                    conn.commit()
                    create_backup()
                    st.success("Policy added successfully. Backup also created.")
                except sqlite3.IntegrityError:
                    st.error("Policy number already exists.")

# =========================
# VIEW POLICIES
# =========================
elif page == "View Policies":
    st.subheader("📄 View Policies")

    df = clean_dates(get_all_policies())

    if df.empty:
        st.info("No policies found.")
    else:
        search_text = st.text_input("Search by Policy No or Name")
        use_date_filter = st.checkbox("Apply Date Filter")

        filtered = df.copy()

        if search_text:
            filtered = filtered[
                filtered["name"].astype(str).str.contains(search_text, case=False, na=False) |
                filtered["policy_no"].astype(str).str.contains(search_text, case=False, na=False)
            ]

        if use_date_filter:
            start_date = st.date_input("From Date Filter", value=date.today() - timedelta(days=365))
            end_date = st.date_input("To Date Filter", value=default_to_date())

            filtered = filtered[
                (filtered["from_date_dt"] >= start_date) &
                (filtered["to_date_dt"] <= end_date)
            ]

        filtered = filtered.sort_values(by="to_date_dt", ascending=True)
        final_df = prepare_display(filtered)

        if final_df.empty:
            st.warning("No records found.")
        else:
            show_table(final_df, 600)
            export_csv(final_df, "all_policies.csv")

# =========================
# RENEW POLICY
# =========================
elif page == "Renew Policy":
    st.subheader("🔁 Renew Policy")

    selected_row = filter_and_select_policy("renew")

    if selected_row is not None:
        old_policy_no = selected_row["policy_no"]
        st.success("Selected Policy: {}".format(old_policy_no))

        policy_type = st.selectbox(
            "Policy Type",
            ["Fire", "Misc", "Motor"],
            index=["Fire", "Misc", "Motor"].index(selected_row["policy_type"])
        )

        prefix = POLICY_PREFIX[policy_type]
        st.info("New renewal policy must start with {}. Format example: {}/XXXX/435".format(prefix, prefix))

        with st.form("renew_form"):
            from_date = st.date_input("From Date", value=date.today())
            to_date = st.date_input("To Date", value=default_to_date())

            name = st.text_input("Name", value=selected_row["name"])
            address = st.text_area("Address", value=selected_row["address"] or "")
            mobile_no = st.text_input("Mobile No", value=str(selected_row["mobile_no"]), max_chars=10)

            policy_prefix = st.text_input("Policy Prefix", value=prefix)
            policy_mode = st.text_input("Policy Mode", value="Renewal")
            new_policy_no = st.text_input("Policy No", value=prefix + "/", help="Format: 48/XXXX/435")
            renewal_policy_no = st.text_input("Renewal Policy No", value=old_policy_no)

            premium = st.number_input("Premium", value=float(selected_row["premium"] or 0), step=100.0)
            sum_insured = st.number_input("Sum Insured", value=float(selected_row["sum_insured"] or 0), step=1000.0)
            detail = st.text_area("Detail", value=selected_row["detail"] or "")
            remark = st.text_area("Remark", value=selected_row["remark"] or "")

            submit = st.form_submit_button("Save Renewal")

            if submit:
                if policy_prefix != prefix:
                    st.error("Policy prefix must be {} for {} policy.".format(prefix, policy_type))
                elif not validate_policy(policy_type, new_policy_no):
                    st.error("Invalid renewal policy number format. Example: {}/XXXX/435".format(prefix))
                elif not validate_mobile(mobile_no):
                    st.error("Mobile number must be exactly 10 digits.")
                else:
                    try:
                        c.execute("""
                        INSERT INTO policies (
                            from_date, to_date, name, address, mobile_no,
                            policy_type, policy_prefix, policy_mode, policy_no,
                            renewal_policy_no, premium, sum_insured, detail,
                            remark, renewal_of, renewed_by
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(from_date),
                            str(to_date),
                            name,
                            address,
                            mobile_no,
                            policy_type,
                            policy_prefix,
                            policy_mode,
                            new_policy_no.strip(),
                            renewal_policy_no.strip(),
                            premium,
                            sum_insured,
                            detail,
                            remark,
                            old_policy_no,
                            ""
                        ))

                        c.execute("""
                        UPDATE policies
                        SET renewed_by = ?
                        WHERE policy_no = ?
                        """, (new_policy_no.strip(), old_policy_no))

                        conn.commit()
                        create_backup()
                        st.success("Policy renewed successfully. Backup also created.")
                    except sqlite3.IntegrityError:
                        st.error("Renewal policy number already exists.")

# =========================
# UPDATE POLICY
# =========================
elif page == "Update Policy":
    st.subheader("✏️ Update Policy")

    selected_row = filter_and_select_policy("update")

    if selected_row is not None:
        selected_policy_no = selected_row["policy_no"]
        st.success("Selected Policy: {}".format(selected_policy_no))

        policy_type = st.selectbox(
            "Policy Type",
            ["Fire", "Misc", "Motor"],
            index=["Fire", "Misc", "Motor"].index(selected_row["policy_type"])
        )

        prefix = POLICY_PREFIX[policy_type]

        with st.form("update_form"):
            from_date = st.date_input("From Date", value=pd.to_datetime(selected_row["from_date"]).date())
            to_date = st.date_input("To Date", value=pd.to_datetime(selected_row["to_date"]).date())

            name = st.text_input("Name", value=selected_row["name"])
            address = st.text_area("Address", value=selected_row["address"] or "")
            mobile_no = st.text_input("Mobile No", value=str(selected_row["mobile_no"]), max_chars=10)

            policy_prefix = st.text_input("Policy Prefix", value=selected_row["policy_prefix"] or prefix)
            policy_mode = st.text_input("Policy Mode", value=selected_row["policy_mode"] or "")

            premium = st.number_input("Premium", value=float(selected_row["premium"] or 0), step=100.0)
            sum_insured = st.number_input("Sum Insured", value=float(selected_row["sum_insured"] or 0), step=1000.0)
            detail = st.text_area("Detail", value=selected_row["detail"] or "")
            remark = st.text_area("Remark", value=selected_row["remark"] or "")

            submit = st.form_submit_button("Update Policy")

            if submit:
                if policy_prefix != prefix:
                    st.error("Policy prefix must be {} for {} policy.".format(prefix, policy_type))
                elif not validate_mobile(mobile_no):
                    st.error("Mobile number must be exactly 10 digits.")
                else:
                    c.execute("""
                    UPDATE policies
                    SET
                        from_date = ?,
                        to_date = ?,
                        name = ?,
                        address = ?,
                        mobile_no = ?,
                        policy_type = ?,
                        policy_prefix = ?,
                        policy_mode = ?,
                        premium = ?,
                        sum_insured = ?,
                        detail = ?,
                        remark = ?
                    WHERE policy_no = ?
                    """, (
                        str(from_date),
                        str(to_date),
                        name,
                        address,
                        mobile_no,
                        policy_type,
                        policy_prefix,
                        policy_mode,
                        premium,
                        sum_insured,
                        detail,
                        remark,
                        selected_policy_no
                    ))
                    conn.commit()
                    create_backup()
                    st.success("Policy updated successfully. Backup also created.")

# =========================
# DELETE POLICY
# =========================
elif page == "Delete Policy":
    st.subheader("🗑 Delete Policy")

    selected_row = filter_and_select_policy("delete")

    if selected_row is not None:
        selected_policy_no = selected_row["policy_no"]
        st.warning("Selected Policy for Delete: {}".format(selected_policy_no))

        if st.button("Delete Selected Policy"):
            create_backup()
            c.execute("DELETE FROM policies WHERE policy_no = ?", (selected_policy_no,))
            conn.commit()
            st.success("Policy deleted successfully. Backup was created before delete.")