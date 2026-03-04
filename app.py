import streamlit as st
import pandas as pd
import smtplib
import ssl
import time
import re
import csv
import io
import base64
import sqlite3
import random
import datetime
import streamlit.components.v1 as components
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid

# --- DATABASE INIT ---
def init_db():
    conn = sqlite3.connect('campaigns.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_email TEXT,
            sender_name TEXT,
            sender_email TEXT,
            sender_password TEXT,
            subject TEXT,
            html_body TEXT,
            send_at DATETIME,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Drip Mailer", page_icon="📧", layout="wide")

# --- CUSTOM CSS (Dark Theme + B2CC40 Green) ---
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #050810;
        background-image: radial-gradient(circle at 50% -20%, #111827, #050810);
        color: #E2E8F0;
    }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF !important; }
    p, span, label { color: #E2E8F0; }
    
    /* Buttons */
    .stButton>button, .stButton>button p, .stButton>button span, .stButton>button div {
        background-color: #B2CC40 !important;
        color: #050810 !important; 
        font-weight: 600 !important;
        border: none;
        border-radius: 6px;
        padding: 0.1rem 0.5rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover, .stButton>button:hover p, .stButton>button:hover span {
        background-color: #9DB535 !important;
        color: #050810 !important;
        box-shadow: 0 4px 10px rgba(178, 204, 64, 0.4);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(255, 255, 255, 0.05);
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #B2CC40;
        box-shadow: 0 0 0 1px #B2CC40;
    }
    
    /* Brand Text Highlight */
    .brand-text {
        color: #B2CC40;
        font-weight: bold;
    }
    
    /* Hide default header */
    header { visibility: hidden; }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        color: #B2CC40 !important;
        border-bottom-color: #B2CC40 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div style="display: flex; align-items: center; gap: 20px; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
    <img src="https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001" style="height: 50px; filter: brightness(0) invert(1);" />
    <div>
        <h1 style="margin: 0; padding: 0; font-size: 32px; line-height: 1.1; color: #FFFFFF;">Drip Mailer</h1>
        <p style="margin: 0; padding: 0; font-size: 15px;">
            <span style="color: #B2CC40; font-weight: 600;">By Trucking BU</span>
            <span style="color: #94A3B8; font-weight: 500;"> - A Sales Toolkit Extension</span>
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if 'env_email' not in st.session_state: st.session_state['env_email'] = ""
if 'env_pass' not in st.session_state: st.session_state['env_pass'] = ""
if 'sig_name' not in st.session_state: st.session_state['sig_name'] = "Jack Yi"
if 'sig_title' not in st.session_state: st.session_state['sig_title'] = "Sales Director"
if 'sig_company' not in st.session_state: st.session_state['sig_company'] = "Streamax Technology"
if 'sig_phone' not in st.session_state: st.session_state['sig_phone'] = "(555) 123-4567"
if 'sig_website' not in st.session_state: st.session_state['sig_website'] = "https://www.streamax.com"
if 'sig_avatar' not in st.session_state: st.session_state['sig_avatar'] = "https://images.unsplash.com/photo-1531831108325-7fe9616bc780?auto=format&fit=crop&fm=jpg&q=60&w=300"
if 'sig_logo' not in st.session_state: st.session_state['sig_logo'] = "https://mail.streamax.com/coremail/s?func=lp:getImg&org_id=&img_id=logo_001"
if 'sig_layout' not in st.session_state: st.session_state['sig_layout'] = "Creative with Avatar"
if 'latest_log_csv' not in st.session_state: st.session_state['latest_log_csv'] = ""

# Follow-up Templates State
for i in range(5):
    if f't_name_{i}' not in st.session_state: st.session_state[f't_name_{i}'] = f"Template {i+1}"
    if f't_subj_{i}' not in st.session_state: st.session_state[f't_subj_{i}'] = f"Checking in - {i+1}"
    if f't_body_{i}' not in st.session_state: st.session_state[f't_body_{i}'] = "Hi {first_name},\n\nJust wanted to float this to the top of your inbox.\n\nBest,"

# Campaign Sequence State
for i in range(5):
    if f'seq_en_{i}' not in st.session_state: st.session_state[f'seq_en_{i}'] = False
    if f'seq_delay_{i}' not in st.session_state: st.session_state[f'seq_delay_{i}'] = (i + 1) * 4

# --- DEFAULTS & TEMPLATES ---
DEFAULT_BODY = """Hi {first_name},

I hope this email finds you well. I noticed that {company} is doing some incredible work lately.

As someone working as a {role}, I thought you might be interested in how our new tools can help streamline your daily operations. We've helped similar teams increase their efficiency by over 20%.

Would you be open to a brief 10-minute chat next week?

Best regards,"""

DISCLAIMER_HTML = (
    '<div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-family: Arial, sans-serif; font-size: 10px; color: #64748b; line-height: 1.4; text-align: justify;">'
    '<strong>Email Disclaimer:</strong> This e-mail is intended only for the person or entity to which it is addressed and may contain confidential and/or privileged material. Any review, retransmission, dissemination or other use of, or taking of any action in reliance upon, the information in this e-mail by persons or entities other than the intended recipient is prohibited and may be unlawful. If you received this e-mail in error, please contact the sender and delete it from any computer.'
    '</div>'
)

def get_signature_html(sig_id, data):
    if sig_id == "Minimalist Professional":
        html = (
            '<div style="font-family: Arial, sans-serif; color: #333; margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px;">'
            f'<p style="margin: 0; font-weight: bold; font-size: 14px; color: #000000;">{data["name"]}</p>'
            f'<p style="margin: 0; font-size: 12px; color: #666;">{data["title"]} | <a href="{data["website"]}" style="color: #666; text-decoration: none;">{data["company"]}</a></p>'
            f'<p style="margin: 0; font-size: 12px; color: #0066cc;">{data["email"]} | {data["phone"]}</p>'
            '</div>'
        )
        return html + DISCLAIMER_HTML
    elif sig_id == "Creative with Avatar":
        html = (
            '<div style="font-family: \'Helvetica Neue\', Helvetica, Arial, sans-serif; margin-top: 20px; display: flex; align-items: center; gap: 15px;">'
            f'<img src="{data["avatarUrl"]}" alt="Avatar" style="width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #e2e8f0;" />'
            '<div>'
            f'<p style="margin: 0; font-weight: 600; font-size: 15px; color: #1e293b;">{data["name"]}</p>'
            f'<p style="margin: 2px 0; font-size: 13px; color: #64748b;">{data["title"]}</p>'
            f'<p style="margin: 2px 0; font-size: 13px; color: #3b82f6;">{data["email"]} <span style="color: #94a3b8;">|</span> <span style="color: #64748b;">{data["phone"]}</span></p>'
            f'<a href="{data["website"]}" style="margin: 0; font-size: 13px; color: #3b82f6; text-decoration: none;">{data["company"]}</a>'
            '</div></div>'
        )
        return html + DISCLAIMER_HTML
    else: # Corporate with Logo
        html = (
            '<div style="font-family: Arial, sans-serif; margin-top: 25px;">'
            f'<p style="margin: 0; font-weight: bold; font-size: 14px; color: #0f172a;">{data["name"]}</p>'
            f'<p style="margin: 2px 0 5px 0; font-size: 12px; color: #475569;">{data["title"]}</p>'
            f'<p style="margin: 0; font-size: 12px; color: #B2CC40;"><strong><a href="{data["website"]}" style="color: #B2CC40; text-decoration: none;">{data["company"]}</a></strong></p>'
            f'<p style="margin: 4px 0 12px 0; font-size: 12px; color: #475569;"><a href="mailto:{data["email"]}" style="color: #B2CC40; text-decoration: none;">{data["email"]}</a> | {data["phone"]}</p>'
            f'<img src="{data["logoUrl"]}" alt="Company Logo" style="height: 45px; border-radius: 4px;" />'
            '</div>'
        )
        return html + DISCLAIMER_HTML

# --- HELPER FUNCTIONS ---
def render_template(template_str, row):
    def replace_var(match):
        key = match.group(1).lower().strip()
        val = row.get(key, "")
        return str(val) if pd.notna(val) and val != "" else f"[{match.group(1)}]"
    return re.sub(r'\{([^}]+)\}', replace_var, template_str)

def create_message(subject, html_body, to_addr, from_name, from_email):
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg

def get_random_business_time(days_ahead):
    """Calculates future date with a random time between 9 AM and 4:59 PM"""
    target_date = datetime.datetime.now() + datetime.timedelta(days=days_ahead)
    random_hour = random.randint(9, 16)
    random_minute = random.randint(0, 59)
    random_second = random.randint(0, 59)
    target_time = target_date.replace(hour=random_hour, minute=random_minute, second=random_second, microsecond=0)
    return target_time.strftime('%Y-%m-%d %H:%M:%S')

# Generate current signature html to share across tabs
sig_data = {
    "name": st.session_state['sig_name'],
    "title": st.session_state['sig_title'],
    "company": st.session_state['sig_company'],
    "phone": st.session_state['sig_phone'],
    "email": st.session_state['env_email'] or "your.email@streamax.com",
    "website": st.session_state['sig_website'],
    "avatarUrl": st.session_state['sig_avatar'],
    "logoUrl": st.session_state['sig_logo']
}
selected_sig_html = get_signature_html(st.session_state['sig_layout'], sig_data)

# --- TABS ---
tab0, tab1, tab2, tab3, tab4 = st.tabs(["0. Setup", "1. Signatures", "2. Compose", "3. Data & Sending", "4. Queue Manager"])

# --- TAB 0: SETUP ---
with tab0:
    st.markdown("<h2>Environment <span class='brand-text'>Setup</span></h2>", unsafe_allow_html=True)
    st.write("To securely send emails from the cloud, enter your Streamax credentials here. They are temporarily held in memory for this session only and are never saved to a database.")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            input_email = st.text_input("Streamax Email", value=st.session_state['env_email'], placeholder="name@streamax.com")
        with col2:
            input_pass = st.text_input("Email Password", value=st.session_state['env_pass'], type="password", placeholder="••••••••")
        
        if st.button("Save Credentials to Session"):
            if input_email.endswith("@streamax.com") and input_pass:
                with st.spinner("Verifying credentials with mail.streamax.com..."):
                    try:
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL("mail.streamax.com", 465, timeout=15, context=context)
                        server.login(input_email, input_pass)
                        server.quit()
                        
                        st.session_state['env_email'] = input_email
                        st.session_state['env_pass'] = input_pass
                        st.success("Credentials verified and saved to active session! You can now proceed to Signatures.")
                    except smtplib.SMTPAuthenticationError:
                        st.error("Email or passwords incorrect.")
                    except Exception as e:
                        if '535' in str(e) or 'authentication failed' in str(e).lower():
                            st.error("Email or passwords incorrect.")
                        else:
                            st.error(f"Could not connect to the mail server: {str(e)}")
            else:
                st.error("Please provide a valid @streamax.com email and password.")

# --- TAB 1: SIGNATURES ---
with tab1:
    st.markdown("<h2>Email <span class='brand-text'>Signature</span></h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.text_input("Full Name", key="sig_name")
        st.text_input("Job Title", key="sig_title")
        st.text_input("Company Name", key="sig_company")
        st.text_input("Phone", key="sig_phone")
        st.text_input("Website", key="sig_website")
        st.text_input("Avatar URL", key="sig_avatar")
        st.text_input("Logo URL", key="sig_logo")
        st.caption(f"Email: {st.session_state['env_email'] or 'Will use Setup Email'}")

    with col2:
        st.radio("Select Layout", ["Minimalist Professional", "Creative with Avatar", "Corporate with Logo"], key="sig_layout")
        st.markdown("<div style='background: white; padding: 20px; border-radius: 8px; border: 1px solid #cbd5e1; color: black; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);'>" + selected_sig_html + "</div>", unsafe_allow_html=True)

# --- TAB 2: COMPOSE ---
with tab2:
    st.markdown("<h2>Compose <span class='brand-text'>Email</span></h2>", unsafe_allow_html=True)
    
    with st.popover("💡 Where do these variables come from?"):
        st.markdown("""
        **Variable Reference Guide:**
        * `{first_name}`, `{last_name}`, `{company}`, `{role}`: These are obtained directly from the **CSV file** you upload in the *Data & Sending* tab.
        * `{your_name}`: This is obtained dynamically from the **Full Name** input in the *Signatures* tab.
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        subject_template = st.text_input("Subject Line", "Streamlining Operations at {company}")
        body_template = st.text_area("Email Body", DEFAULT_BODY, height=350)
    with col2:
        st.caption("Live HTML Preview (Sample Data)")
        sample_row = {
            "first_name": "John", 
            "company": "Acme Corp", 
            "role": "Manager",
            "your_name": st.session_state['sig_name']
        }
        
        rendered_subject = render_template(subject_template, sample_row)
        rendered_body_html = render_template(body_template, sample_row).replace('\n', '<br>')
        
        preview_html = (
            '<div style="background-color: #ffffff; color: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: Arial, sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
            '<div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 20px;">'
            '<span style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Subject:</span>'
            f'<span style="color: #0f172a; font-size: 15px; font-weight: bold; margin-left: 8px;">{rendered_subject}</span>'
            '</div>'
            '<div style="font-size: 14px; line-height: 1.6; color: #334155;">'
            f'{rendered_body_html}'
            '<br><br>'
            f'{selected_sig_html}'
            '</div></div>'
        )
        st.markdown(preview_html, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- Advanced Email Templates Component ---
    with st.expander("⚙️ Advanced: Follow-up Email Templates (Campaign)"):
        st.write("Create up to 5 additional follow-up templates here. You can schedule these to send automatically in the Data & Sending tab.")
        
        template_tabs = st.tabs([st.session_state[f't_name_{i}'] for i in range(5)])
        
        for i, t_tab in enumerate(template_tabs):
            with t_tab:
                st.text_input("Template Name", key=f't_name_{i}')
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.text_input(f"Subject Line", key=f't_subj_{i}')
                    st.text_area(f"Email Body", height=250, key=f't_body_{i}')
                with col_t2:
                    st.caption("Live HTML Preview (Sample Data)")
                    rendered_t_subj = render_template(st.session_state[f't_subj_{i}'], sample_row)
                    rendered_t_body_html = render_template(st.session_state[f't_body_{i}'], sample_row).replace('\n', '<br>')
                    
                    t_preview_html = (
                        '<div style="background-color: #ffffff; color: #1e293b; padding: 24px; border-radius: 8px; border: 1px solid #cbd5e1; font-family: Arial, sans-serif; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">'
                        '<div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 20px;">'
                        '<span style="color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">Subject:</span>'
                        f'<span style="color: #0f172a; font-size: 15px; font-weight: bold; margin-left: 8px;">{rendered_t_subj}</span>'
                        '</div>'
                        '<div style="font-size: 14px; line-height: 1.6; color: #334155;">'
                        f'{rendered_t_body_html}'
                        '<br><br>'
                        f'{selected_sig_html}'
                        '</div></div>'
                    )
                    st.markdown(t_preview_html, unsafe_allow_html=True)

# --- TAB 3: DATA & SENDING ---
with tab3:
    st.markdown("<h2>Data & <span class='brand-text'>Sending</span></h2>", unsafe_allow_html=True)
    
    st.markdown("<h3>📝 Lead List <span class='brand-text'>Template</span></h3>", unsafe_allow_html=True)
    st.write("Ensure your contacts are formatted correctly before uploading below. Here is the required column structure:")
    
    template_df = pd.DataFrame([{"Email": "example@streamax.com", "First_Name": "John", "Last_Name": "Doe", "Company": "Streamax", "Role": "Sales Manager"}])
    st.dataframe(template_df, hide_index=True, use_container_width=True)
    
    CSV_TEMPLATE = "Email,First_Name,Last_Name,Company,Role\nexample@streamax.com,John,Doe,Streamax,Sales Manager\n"
    st.download_button("Download leadList.csv", data=CSV_TEMPLATE, file_name="leadList.csv", mime="text/csv")
    
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1); margin-bottom: 25px;'><br>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload leadList.csv", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [str(c).lower().strip() for c in df.columns]
            required = ['first_name', 'last_name', 'email', 'role', 'company']
            missing = [r for r in required if r not in df.columns]
            
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                st.dataframe(df.head(10), use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Advanced Campaign Settings ---
                with st.expander("⚙️ Advanced: Email Campaign Cycle"):
                    st.write("Set up your automated follow-up sequence. Emails will be scheduled at a random time between **9:00 AM and 5:00 PM** on the target date.")
                    
                    tmpl_options = [st.session_state[f't_name_{j}'] for j in range(5)]
                    
                    for i in range(5):
                        col_s1, col_s2, col_s3 = st.columns([1, 2, 3])
                        with col_s1:
                            st.checkbox(f"Follow-up {i+1}", key=f"seq_en_{i}")
                        with col_s2:
                            st.number_input("Days after T+0", min_value=1, key=f"seq_delay_{i}", disabled=not st.session_state[f"seq_en_{i}"])
                        with col_s3:
                            st.selectbox("Select Template", options=tmpl_options, key=f"seq_tmpl_{i}", disabled=not st.session_state[f"seq_en_{i}"])
                            
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Execution ---
                if st.button("INITIATE BATCH SEND", type="primary"):
                    if not st.session_state['env_email'] or not st.session_state['env_pass']:
                        st.error("Missing Credentials! Please go back to Tab 0 (Setup) and enter your Streamax login.")
                    else:
                        progress_bar = st.progress(0)
                        log_container = st.empty()
                        logs = []
                        
                        # --- Prepare CSV Logging ---
                        log_output = io.StringIO()
                        csv_writer = csv.writer(log_output)
                        
                        csv_writer.writerow(["--- CAMPAIGN CONFIGURATION ---"])
                        csv_writer.writerow(["Type", "Template Name", "Subject", "Body/Details"])
                        csv_writer.writerow(["Main Email", "Original", subject_template, body_template])
                        
                        for j in range(5):
                            if st.session_state[f"seq_en_{j}"]:
                                delay = st.session_state[f"seq_delay_{j}"]
                                tmpl_name = st.session_state[f"seq_tmpl_{j}"]
                                t_subj, t_bod = "", ""
                                for k in range(5):
                                    if st.session_state[f't_name_{k}'] == tmpl_name:
                                        t_subj = st.session_state[f't_subj_{k}']
                                        t_bod = st.session_state[f't_body_{k}']
                                        break
                                csv_writer.writerow(["Follow-up", tmpl_name, t_subj, f"T+{delay} Days | Body: {t_bod}"])
                        
                        csv_writer.writerow([])
                        csv_writer.writerow(["--- EXECUTION LOG ---"])
                        csv_writer.writerow(["Timestamp", "First Name", "Last Name", "Email Address", "Action", "Details"])
                        
                        try:
                            context = ssl.create_default_context()
                            server = smtplib.SMTP_SSL("mail.streamax.com", 465, timeout=30, context=context)
                            server.login(st.session_state['env_email'], st.session_state['env_pass'])
                            
                            # Open local DB connection for queueing
                            conn = sqlite3.connect('campaigns.db')
                            c = conn.cursor()
                            
                            total = len(df)
                            for index, row in df.iterrows():
                                row_dict = row.to_dict()
                                row_dict["your_name"] = st.session_state['sig_name']
                                
                                target_email = row_dict.get('email')
                                first_name = row_dict.get('first_name', '')
                                last_name = row_dict.get('last_name', '')
                                
                                if pd.isna(target_email):
                                    continue
                                    
                                current_timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                                
                                rendered_subj = render_template(subject_template, row_dict)
                                rendered_body = render_template(body_template, row_dict)
                                html_content = rendered_body.replace('\n', '<br>') + f"<br><br>{selected_sig_html}"
                                
                                msg = create_message(rendered_subj, html_content, target_email, st.session_state['sig_name'], st.session_state['env_email'])
                                
                                try:
                                    server.send_message(msg)
                                    logs.append(f"✅ [{time.strftime('%X')}] Sent successfully to {target_email}")
                                    csv_writer.writerow([current_timestamp, first_name, last_name, target_email, "Sent Main Email", "Success"])
                                    
                                    # Schedule Follow-ups
                                    for j in range(5):
                                        if st.session_state[f"seq_en_{j}"]:
                                            delay = st.session_state[f"seq_delay_{j}"]
                                            tmpl_name = st.session_state[f"seq_tmpl_{j}"]
                                            
                                            # Grab specific template
                                            t_subj, t_bod = "", ""
                                            for k in range(5):
                                                if st.session_state[f't_name_{k}'] == tmpl_name:
                                                    t_subj = render_template(st.session_state[f't_subj_{k}'], row_dict)
                                                    t_bod = render_template(st.session_state[f't_body_{k}'], row_dict)
                                                    break
                                            
                                            f_html_content = t_bod.replace('\n', '<br>') + f"<br><br>{selected_sig_html}"
                                            send_at_time = get_random_business_time(delay)
                                            
                                            # Write to database securely
                                            c.execute('''
                                                INSERT INTO scheduled_emails 
                                                (target_email, sender_name, sender_email, sender_password, subject, html_body, send_at)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                            ''', (target_email, st.session_state['sig_name'], st.session_state['env_email'], st.session_state['env_pass'], t_subj, f_html_content, send_at_time))
                                            
                                            logs.append(f"⏳ [{time.strftime('%X')}] Queued '{tmpl_name}' for {target_email} at {send_at_time}")
                                            csv_writer.writerow([current_timestamp, first_name, last_name, target_email, "Scheduled Follow-up", f"{tmpl_name} at {send_at_time}"])
                                            
                                except Exception as e:
                                    logs.append(f"❌ [{time.strftime('%X')}] Failed to send to {target_email}: {str(e)}")
                                    csv_writer.writerow([current_timestamp, first_name, last_name, target_email, "Sent Main Email", f"Failed: {str(e)}"])
                                
                                conn.commit()
                                progress_bar.progress((index + 1) / total)
                                log_container.code('\n'.join(logs[-15:]), language='text')
                                time.sleep(0.5)
                                
                            conn.close()
                            server.quit()
                            st.success("Batch Processing Complete! Your log should begin downloading automatically.")
                            
                            # Finalize CSV
                            final_csv_data = log_output.getvalue()
                            st.session_state['latest_log_csv'] = final_csv_data
                            
                            b64 = base64.b64encode(final_csv_data.encode()).decode()
                            timestamp_file = time.strftime('%Y%m%d_%H%M%S')
                            
                            components.html(
                                f"""
                                <script>
                                    var a = document.createElement('a');
                                    a.href = 'data:text/csv;base64,{b64}';
                                    a.download = 'campaign_log_{timestamp_file}.csv';
                                    a.click();
                                </script>
                                """,
                                height=0
                            )
                            
                        except smtplib.SMTPAuthenticationError:
                            st.error("Email or passwords incorrect. Please return to the Setup tab to re-authenticate.")
                        except Exception as e:
                            if '535' in str(e) or 'authentication failed' in str(e).lower():
                                st.error("Email or passwords incorrect. Please return to the Setup tab to re-authenticate.")
                            else:
                                st.error(f"SMTP Connection Error: {str(e)}")
                
                # --- Persistent Manual Download Button ---
                if st.session_state.get('latest_log_csv'):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button(
                        label="📥 Download Latest Execution Log (CSV)",
                        data=st.session_state['latest_log_csv'],
                        file_name=f"campaign_log_manual.csv",
                        mime="text/csv",
                    )
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")

# --- TAB 4: QUEUE MANAGER ---
with tab4:
    st.markdown("<h2>Queue <span class='brand-text'>Manager</span></h2>", unsafe_allow_html=True)
    st.write("View all scheduled follow-up emails and manually process ones that have reached their target send time.")
    
    # Connect to DB and fetch
    conn = sqlite3.connect('campaigns.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Show all pending
    c.execute("SELECT id, target_email, subject, send_at FROM scheduled_emails WHERE status = 'pending' ORDER BY send_at ASC")
    pending_emails = c.fetchall()
    
    current_time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 2. Show only DUE pending
    c.execute("SELECT * FROM scheduled_emails WHERE status = 'pending' AND send_at <= ?", (current_time_str,))
    due_emails = c.fetchall()
    
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        st.metric("Total Scheduled (Pending)", len(pending_emails))
    with col_q2:
        st.metric("Ready to Send Right Now", len(due_emails), delta_color="off")
        
    st.markdown("### Scheduled Queue")
    if pending_emails:
        df_pending = pd.DataFrame([{
            "ID": r['id'], 
            "Target Email": r['target_email'], 
            "Subject": r['subject'], 
            "Scheduled For": r['send_at']
        } for r in pending_emails])
        st.dataframe(df_pending, use_container_width=True, hide_index=True)
    else:
        st.info("No emails are currently waiting in the queue.")
        
    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1); margin-bottom: 25px;'><br>", unsafe_allow_html=True)
    
    st.markdown("### Execute Due Emails")
    st.write("Clicking this button will dispatch any emails in the queue whose `Scheduled For` time has already passed.")
    
    if st.button("🚀 Process Due Emails Now", type="primary", disabled=len(due_emails) == 0):
        
        q_progress = st.progress(0)
        q_log_container = st.empty()
        q_logs = []
        
        # Group by sender account to minimize logins
        accounts_dict = {}
        for row in due_emails:
            email_key = row['sender_email']
            if email_key not in accounts_dict:
                accounts_dict[email_key] = {
                    'password': row['sender_password'],
                    'emails': []
                }
            accounts_dict[email_key]['emails'].append(row)
            
        total_due = len(due_emails)
        processed_count = 0
        
        for sender_email, account_data in accounts_dict.items():
            q_logs.append(f"[{time.strftime('%X')}] 🔐 Authenticating for account {sender_email}...")
            q_log_container.code('\n'.join(q_logs[-15:]), language='text')
            
            try:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL("mail.streamax.com", 465, timeout=30, context=context)
                server.login(sender_email, account_data['password'])
                
                for row in account_data['emails']:
                    email_id = row['id']
                    target = row['target_email']
                    q_logs.append(f"[{time.strftime('%X')}] 📤 Sending ID {email_id} to {target}...")
                    q_log_container.code('\n'.join(q_logs[-15:]), language='text')
                    
                    try:
                        msg = MIMEMultipart("alternative")
                        msg["From"] = f"{row['sender_name']} <{row['sender_email']}>"
                        msg["To"] = target
                        msg["Subject"] = row['subject']
                        msg["Message-ID"] = make_msgid(domain=row['sender_email'].split("@")[-1])
                        msg.attach(MIMEText(row['html_body'], "html", "utf-8"))
                        
                        server.send_message(msg)
                        
                        # Mark sent
                        c.execute("UPDATE scheduled_emails SET status = 'sent' WHERE id = ?", (email_id,))
                        q_logs.append(f"   ✅ Success!")
                    except Exception as e:
                        q_logs.append(f"   ❌ Failed: {str(e)}")
                        c.execute("UPDATE scheduled_emails SET status = 'failed' WHERE id = ?", (email_id,))
                        
                    conn.commit()
                    processed_count += 1
                    q_progress.progress(processed_count / total_due)
                    q_log_container.code('\n'.join(q_logs[-15:]), language='text')
                    time.sleep(0.5)
                    
                server.quit()
            except Exception as e:
                q_logs.append(f"[{time.strftime('%X')}] ❌ Critical Auth Error for {sender_email}: {str(e)}")
                q_log_container.code('\n'.join(q_logs[-15:]), language='text')
                
        st.success("Queue processing complete!")
        time.sleep(2)
        st.rerun() # Refresh the UI to update the tables

    conn.close()
